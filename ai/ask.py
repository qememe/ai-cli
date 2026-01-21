"""Команда ask - одиночные вопросы с ограничением обменов"""

import asyncio
import re
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ai.api import api_client
from ai.config import config

console = Console()

ASK_SYSTEM_PROMPT = """You are a helpful assistant for quick questions. Provide clear, concise answers in Russian. 

Guidelines:
- Keep responses focused and practical
- Use code examples when relevant
- Prefer bullet points for lists
- Maximum 200 words per response
- Be direct, avoid unnecessary explanations"""

MAX_EXCHANGES = 3


async def ask_command(question: str, verbose: bool = False):
    """Выполнить команду ask с ограничением обменов"""
    messages = [
        {"role": "system", "content": ASK_SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    exchanges_left = MAX_EXCHANGES
    
    try:
        while exchanges_left > 0:
            console.print(f"[yellow]Осталось обменов: {exchanges_left}/{MAX_EXCHANGES}[/yellow]\n")
            
            if verbose and exchanges_left == MAX_EXCHANGES:
                console.print(f"[dim]Модель: {config.model_ask}[/dim]")
                console.print(f"[dim]Temperature: 0.4[/dim]")
                console.print(f"[dim]Max tokens: 1500[/dim]\n")
            
            # Получить ответ
            response = await api_client.get_completion(
                model=config.model_ask,
                messages=messages,
                temperature=0.4,
                max_tokens=1500,
            )
            
            # Очистка ответа от квадратных скобок с цифрами (ссылки на источники)
            cleaned_response = re.sub(r'\[\d+\]', '', response)
            cleaned_response = re.sub(r'\s+', ' ', cleaned_response)
            cleaned_response = re.sub(r'\n\s+', '\n', cleaned_response)
            
            console.print(Markdown(cleaned_response))
            messages.append({"role": "assistant", "content": cleaned_response})
            
            exchanges_left -= 1
            
            if exchanges_left == 0:
                console.print("\n[yellow]Достигнут лимит обменов. Выход...[/yellow]")
                break
            
            # Запросить следующий вопрос
            console.print()
            next_question = console.input("[cyan]Ваш вопрос (или Enter для выхода): [/cyan]")
            
            if not next_question.strip():
                break
            
            messages.append({"role": "user", "content": next_question})
            console.print()
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Прервано пользователем[/yellow]")
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        raise


def run_ask(question: str, verbose: bool = False):
    """Синхронная обертка для команды ask"""
    asyncio.run(ask_command(question, verbose))
