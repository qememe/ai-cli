"""Команда chat - интерактивный чат с сохранением"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ai.api import api_client
from ai.config import config

console = Console()

CHAT_SYSTEM_PROMPT = """You are Claude, a thoughtful AI assistant optimized for deep conversations and philosophical discussions. You are helping a technical user who values:
- Direct, honest communication without corporate politeness
- Deep reasoning and nuanced thinking
- Code examples in C++, Python, Rust when relevant
- Arch Linux and FOSS ecosystem knowledge

Engage naturally in extended dialogues. Ask clarifying questions. Provide detailed explanations when the topic is complex. Use Russian language. Be intellectually curious and explore ideas thoroughly."""


class ChatSession:
    """Класс для управления сессией чата"""
    
    def __init__(self, name: Optional[str] = None):
        self.name = name or f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.created = datetime.now().isoformat() + "Z"
        self.model = config.model_chat
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT}
        ]
        self.chats_dir = config.chats_directory
    
    def add_message(self, role: str, content: str):
        """Добавить сообщение в историю"""
        self.messages.append({"role": role, "content": content})
    
    def save(self) -> Path:
        """Сохранить чат в файл"""
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        
        # Удалить системный промпт из сохранения
        save_messages = [msg for msg in self.messages if msg["role"] != "system"]
        
        chat_data = {
            "name": self.name,
            "created": self.created,
            "model": self.model,
            "messages": save_messages
        }
        
        filename = f"{self.name}.json"
        filepath = self.chats_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    @classmethod
    def load(cls, name: str) -> "ChatSession":
        """Загрузить чат из файла"""
        chats_dir = config.chats_directory
        filepath = chats_dir / f"{name}.json"
        
        if not filepath.exists():
            raise FileNotFoundError(f"Чат '{name}' не найден")
        
        with open(filepath, "r", encoding="utf-8") as f:
            chat_data = json.load(f)
        
        session = cls(name=chat_data["name"])
        session.created = chat_data.get("created", session.created)
        session.model = chat_data.get("model", config.model_chat)
        
        # Восстановить сообщения с системным промптом
        session.messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        session.messages.extend(chat_data.get("messages", []))
        
        return session
    
    @classmethod
    def list_chats(cls) -> List[str]:
        """Получить список всех сохраненных чатов"""
        chats_dir = config.chats_directory
        if not chats_dir.exists():
            return []
        
        chats = []
        for filepath in chats_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                    chats.append(chat_data.get("name", filepath.stem))
            except Exception:
                continue
        
        return sorted(chats)


async def chat_command(chat_name: Optional[str] = None, verbose: bool = False):
    """Запустить интерактивный чат"""
    console.print(Panel(
        "[bold cyan]AI Chat Assistant[/bold cyan]\n"
        "Команды: /new, /load, /list, /save, /exit",
        border_style="cyan"
    ))
    console.print()
    
    session: Optional[ChatSession] = None
    
    try:
        # Загрузить существующий чат или создать новый
        if chat_name:
            try:
                session = ChatSession.load(chat_name)
                console.print(f"[green]✓ Загружен чат: {session.name}[/green]\n")
            except FileNotFoundError:
                console.print(f"[yellow]Чат '{chat_name}' не найден. Создаю новый...[/yellow]\n")
                session = ChatSession(name=chat_name)
        else:
            session = ChatSession()
        
        if verbose:
            console.print(f"[dim]Модель: {session.model}[/dim]")
            console.print(f"[dim]Temperature: 0.7[/dim]")
            console.print(f"[dim]Max tokens: 4000[/dim]\n")
        
        # Основной цикл чата
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]Вы[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Обработка команд
                if user_input.startswith("/"):
                    command = user_input.split()[0]
                    
                    if command == "/exit":
                        console.print("[yellow]Выход из чата...[/yellow]")
                        break
                    
                    elif command == "/save":
                        filepath = session.save()
                        console.print(f"[green]✓ Чат сохранен: {filepath}[/green]\n")
                        continue
                    
                    elif command == "/new":
                        name = " ".join(user_input.split()[1:]) if len(user_input.split()) > 1 else None
                        session = ChatSession(name=name)
                        console.print(f"[green]✓ Создан новый чат: {session.name}[/green]\n")
                        continue
                    
                    elif command == "/load":
                        if len(user_input.split()) < 2:
                            console.print("[red]Укажите название чата: /load <название>[/red]\n")
                            continue
                        
                        name = " ".join(user_input.split()[1:])
                        try:
                            session = ChatSession.load(name)
                            console.print(f"[green]✓ Загружен чат: {session.name}[/green]\n")
                        except FileNotFoundError:
                            console.print(f"[red]Чат '{name}' не найден[/red]\n")
                        continue
                    
                    elif command == "/list":
                        chats = ChatSession.list_chats()
                        if not chats:
                            console.print("[yellow]Нет сохраненных чатов[/yellow]\n")
                        else:
                            table = Table(title="Сохраненные чаты")
                            table.add_column("Название", style="cyan")
                            for chat in chats:
                                table.add_row(chat)
                            console.print(table)
                            console.print()
                        continue
                    
                    else:
                        console.print(f"[red]Неизвестная команда: {command}[/red]\n")
                        continue
                
                # Отправка сообщения
                session.add_message("user", user_input)
                
                console.print("[bold green]AI[/bold green]")
                response_text = ""
                
                # Streaming ответ
                async for chunk in api_client.chat_completion(
                    model=session.model,
                    messages=session.messages,
                    temperature=0.7,
                    max_tokens=4000,
                    stream=True,
                ):
                    response_text += chunk
                    console.print(chunk, end="", markup=False)
                
                console.print("\n")
                session.add_message("assistant", response_text)
            
            except KeyboardInterrupt:
                console.print("\n[yellow]Прервано. Используйте /exit для выхода[/yellow]\n")
                continue
            except Exception as e:
                console.print(f"[red]Ошибка: {e}[/red]\n")
                continue
        
        # Автосохранение при выходе
        if session:
            try:
                session.save()
                console.print("[dim]Чат автоматически сохранен[/dim]")
            except Exception:
                pass
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Выход из чата...[/yellow]")
        if session:
            try:
                session.save()
            except Exception:
                pass
    except Exception as e:
        console.print(f"[red]Критическая ошибка: {e}[/red]")
        raise


def run_chat(chat_name: Optional[str] = None, verbose: bool = False):
    """Синхронная обертка для команды chat"""
    asyncio.run(chat_command(chat_name, verbose))
