"""API клиент для ProxyAPI (OpenRouter совместимый)"""

import asyncio
import logging
import threading
import queue as thread_queue
from typing import AsyncIterator, List, Optional, Dict, Any

from openai import AsyncOpenAI
from anthropic import Anthropic
from rich.console import Console

from ai.config import config

console = Console()
logger = logging.getLogger(__name__)


class ProxyAPIClient:
    """Клиент для работы с ProxyAPI через OpenAI-совместимый интерфейс"""
    
    def __init__(self):
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.timeout = 60.0
    
    def _is_anthropic_model(self, model: str) -> bool:
        """Проверить, является ли модель Anthropic"""
        model_lower = model.lower()
        return "claude" in model_lower or "anthropic" in model_lower
    
    def _get_endpoint_for_model(self, model: str) -> str:
        """Определить правильный endpoint для модели"""
        model_lower = model.lower()
        
        # Anthropic модели используют нативный endpoint
        if self._is_anthropic_model(model):
            return "https://api.proxyapi.ru/anthropic"
        elif model_lower.startswith("openai/"):
            return "https://api.proxyapi.ru/openai/v1"
        else:
            # Все остальные модели через OpenRouter endpoint
            return "https://api.proxyapi.ru/openrouter/v1"
    
    def _get_client(self, model: str):
        """Получить клиент с правильным endpoint для модели"""
        if self._is_anthropic_model(model):
            # Используем нативный Anthropic клиент
            return Anthropic(
                api_key=self.api_key,
                base_url="https://api.proxyapi.ru/anthropic",
            )
        else:
            # Используем OpenAI-совместимый клиент
            endpoint = self._get_endpoint_for_model(model)
            return AsyncOpenAI(
                api_key=self.api_key,
                base_url=endpoint,
                timeout=self.timeout,
            )
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> AsyncIterator[str]:
        """
        Выполнить запрос к API
        
        Args:
            model: Название модели
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            stream: Включить streaming ответов
        
        Yields:
            Части ответа (для streaming) или полный ответ
        """
        try:
            # Для Anthropic моделей используем нативный API
            if self._is_anthropic_model(model):
                client = self._get_client(model)
                
                # Преобразуем формат сообщений из OpenAI в Anthropic
                anthropic_messages = []
                system_content = None
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_content = msg["content"]
                    elif msg["role"] in ["user", "assistant"]:
                        # Anthropic использует формат, где content может быть строкой или списком
                        content = msg["content"]
                        if isinstance(content, str):
                            anthropic_messages.append({
                                "role": msg["role"],
                                "content": content
                            })
                        else:
                            # Если content уже список, используем как есть
                            anthropic_messages.append({
                                "role": msg["role"],
                                "content": content
                            })
                
                # Если было system сообщение, добавляем его в начало как user
                if system_content:
                    anthropic_messages.insert(0, {
                        "role": "user",
                        "content": f"System: {system_content}"
                    })
                
                kwargs = {
                    "model": model,  # Используем название модели как есть (claude-opus-4-5-20251101)
                    "max_tokens": max_tokens or 4000,
                    "messages": anthropic_messages,
                }
                
                if temperature is not None:
                    kwargs["temperature"] = temperature
                
                # Anthropic API синхронный, используем thread queue для live streaming
                if stream:
                    thread_queue_obj = thread_queue.Queue()
                    stream_error = [None]  # Используем список для передачи ошибки из потока
                    
                    def _stream_anthropic():
                        """Синхронная функция для streaming в отдельном потоке"""
                        try:
                            with client.messages.stream(**kwargs) as stream_response:
                                for text_delta in stream_response.text_stream:
                                    thread_queue_obj.put(text_delta)
                        except Exception as e:
                            stream_error[0] = e
                            thread_queue_obj.put(("error", e))
                        finally:
                            thread_queue_obj.put(None)  # Сигнал завершения
                    
                    # Запускаем streaming в отдельном потоке
                    thread = threading.Thread(target=_stream_anthropic, daemon=True)
                    thread.start()
                    
                    # Читаем чанки из очереди по мере поступления
                    try:
                        while True:
                            try:
                                # Ждем чанк с таймаутом
                                chunk = thread_queue_obj.get(timeout=0.1)
                                
                                # None означает завершение
                                if chunk is None:
                                    break
                                
                                # Проверяем, не ошибка ли это
                                if isinstance(chunk, tuple) and chunk[0] == "error":
                                    raise chunk[1]
                                
                                yield chunk
                            except thread_queue.Empty:
                                # Проверяем, завершен ли поток
                                if not thread.is_alive():
                                    # Проверяем, есть ли еще данные
                                    try:
                                        while True:
                                            chunk = thread_queue_obj.get_nowait()
                                            if chunk is None:
                                                break
                                            if isinstance(chunk, tuple) and chunk[0] == "error":
                                                raise chunk[1]
                                            yield chunk
                                    except thread_queue.Empty:
                                        break
                                continue
                    finally:
                        # Ждем завершения потока
                        thread.join(timeout=5)
                        
                        # Если была ошибка в потоке, поднимаем её
                        if stream_error[0]:
                            raise stream_error[0]
                else:
                    def _create_anthropic():
                        response = client.messages.create(**kwargs)
                        return response.content[0].text
                    
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, _create_anthropic)
                    yield result
            else:
                # Для остальных моделей используем OpenAI-совместимый API
                client = self._get_client(model)
                actual_model = model
                
                kwargs = {
                    "model": actual_model,
                    "messages": messages,
                    "temperature": temperature,
                }
                
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                
                if stream:
                    stream_response = await client.chat.completions.create(
                        **kwargs,
                        stream=True
                    )
                    async for chunk in stream_response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                else:
                    response = await client.chat.completions.create(**kwargs)
                    yield response.choices[0].message.content or ""
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"API ошибка: {error_msg}")
            
            # Специальная обработка ошибок для Anthropic моделей
            if self._is_anthropic_model(model) and ("403" in error_msg or "404" in error_msg):
                console.print("[yellow]Попытка использовать альтернативный формат модели для Anthropic...[/yellow]")
                # Пробуем разные варианты названия модели
                try:
                    client = Anthropic(
                        api_key=self.api_key,
                        base_url="https://api.proxyapi.ru/anthropic",
                    )
                    
                    # Пробуем разные варианты названия модели
                    model_variants = [
                        model,  # Как есть в конфиге
                        "claude-opus-4-5-20251101",  # Точное название
                        "claude-3-opus-20240229",  # Стандартная модель Claude 3 Opus
                        "claude-3-5-sonnet-20241022",  # Claude 3.5 Sonnet
                    ]
                    
                    # Преобразуем сообщения для Anthropic
                    anthropic_messages = []
                    system_content = None
                    for msg in messages:
                        if msg["role"] == "system":
                            system_content = msg["content"]
                        elif msg["role"] in ["user", "assistant"]:
                            content = msg["content"]
                            anthropic_messages.append({
                                "role": msg["role"],
                                "content": content if isinstance(content, str) else content
                            })
                    
                    if system_content:
                        anthropic_messages.insert(0, {
                            "role": "user",
                            "content": f"System: {system_content}"
                        })
                    
                    for variant in model_variants:
                        try:
                            kwargs = {
                                "model": variant,
                                "max_tokens": max_tokens or 4000,
                                "messages": anthropic_messages,
                            }
                            if temperature is not None:
                                kwargs["temperature"] = temperature
                            
                            loop = asyncio.get_event_loop()
                            
                            if stream:
                                # Используем ту же логику live streaming с threading
                                retry_queue = thread_queue.Queue()
                                retry_error = [None]
                                
                                def _stream_retry():
                                    try:
                                        with client.messages.stream(**kwargs) as stream_response:
                                            for text_delta in stream_response.text_stream:
                                                retry_queue.put(text_delta)
                                    except Exception as e:
                                        retry_error[0] = e
                                        retry_queue.put(("error", e))
                                    finally:
                                        retry_queue.put(None)
                                
                                retry_thread = threading.Thread(target=_stream_retry, daemon=True)
                                retry_thread.start()
                                
                                try:
                                    while True:
                                        try:
                                            chunk = retry_queue.get(timeout=0.1)
                                            if chunk is None:
                                                break
                                            if isinstance(chunk, tuple) and chunk[0] == "error":
                                                raise chunk[1]
                                            yield chunk
                                        except thread_queue.Empty:
                                            if not retry_thread.is_alive():
                                                try:
                                                    while True:
                                                        chunk = retry_queue.get_nowait()
                                                        if chunk is None:
                                                            break
                                                        if isinstance(chunk, tuple) and chunk[0] == "error":
                                                            raise chunk[1]
                                                        yield chunk
                                                except thread_queue.Empty:
                                                    break
                                            continue
                                finally:
                                    retry_thread.join(timeout=5)
                                    if retry_error[0]:
                                        raise retry_error[0]
                            else:
                                def _create_retry():
                                    response = client.messages.create(**kwargs)
                                    return response.content[0].text
                                
                                result = await loop.run_in_executor(None, _create_retry)
                                yield result
                            console.print(f"[green]✓ Использована модель: {variant}[/green]")
                            return
                        except Exception:
                            continue
                    
                    raise Exception("Не удалось найти подходящий формат модели")
                except Exception as retry_error:
                    console.print(f"[red]Ошибка при повторной попытке: {retry_error}[/red]")
                    console.print("[yellow]Подсказка: Убедитесь, что модель claude-opus-4-5-20251101 доступна в ProxyAPI[/yellow]")
                    console.print("[yellow]Проверьте доступные модели в документации ProxyAPI[/yellow]")
            
            if "insufficient_quota" in error_msg.lower() or "credits" in error_msg.lower():
                console.print("[red]Ошибка: Недостаточно кредитов на ProxyAPI[/red]")
            elif "timeout" in error_msg.lower():
                console.print("[red]Ошибка: Таймаут запроса к API[/red]")
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                console.print("[red]Ошибка: Проблема с сетью[/red]")
            else:
                console.print(f"[red]Ошибка API: {error_msg}[/red]")
            
            raise
    
    async def get_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Получить полный ответ (не streaming)"""
        content = ""
        async for chunk in self.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        ):
            content += chunk
        return content


# Глобальный экземпляр клиента
api_client = ProxyAPIClient()
