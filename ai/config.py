"""Управление конфигурацией приложения"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    import tomllib
 except ImportError:
    import tomli as tomllib

from rich.console import Console
from rich.panel import Panel

console = Console()


class Config:
    """Класс для работы с конфигурацией"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "ai"
        self.config_file = self.config_dir / "config.toml"
        self.chats_dir = Path.home() / ".local" / "share" / "ai" / "chats"
        self.log_file = Path.home() / ".local" / "share" / "ai" / "ai.log"
        
        self._config = None
        self._load_config()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создать необходимые директории"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.chats_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self):
        """Загрузить конфигурацию из файла"""
        if not self.config_file.exists():
            self._create_default_config()
            console.print(
                Panel(
                    f"[yellow]Создан файл конфигурации: {self.config_file}[/yellow]\n"
                    "[red]Пожалуйста, добавьте ваш ProxyAPI ключ в config.toml[/red]",
                    title="Конфигурация",
                    border_style="yellow"
                )
            )
            sys.exit(1)
        
        try:
            with open(self.config_file, "rb") as f:
                self._config = tomllib.load(f)
        except Exception as e:
            console.print(f"[red]Ошибка чтения конфигурации: {e}[/red]")
            sys.exit(1)
    
    def _create_default_config(self):
        """Создать конфигурацию по умолчанию"""
        default_config = """[api]
proxyapi_key = "sk-..."
base_url = "https://api.proxyapi.ru/openrouter/v1"

[models]
search = "perplexity/sonar"
ask = "deepseek/deepseek-v3.2"
chat = "claude-opus-4-5-20251101"

[storage]
chats_dir = "~/.local/share/ai/chats"
"""
        self.config_file.write_text(default_config, encoding="utf-8")
    
    @property
    def api_key(self) -> str:
        """Получить API ключ"""
        key = self._config.get("api", {}).get("proxyapi_key", "")
        if not key or key == "sk-...":
            console.print("[red]Ошибка: ProxyAPI ключ не настроен в config.toml[/red]")
            sys.exit(1)
        return key
    
    @property
    def base_url(self) -> str:
        """Получить базовый URL API"""
        return self._config.get("api", {}).get(
            "base_url", 
            "https://api.proxyapi.ru/openrouter/v1"
        )
    
    @property
    def model_search(self) -> str:
        """Модель для поиска"""
        return self._config.get("models", {}).get("search", "perplexity/sonar")
    
    @property
    def model_ask(self) -> str:
        """Модель для вопросов"""
        return self._config.get("models", {}).get("ask", "deepseek/deepseek-v3.2")
    
    @property
    def model_chat(self) -> str:
        """Модель для чата"""
        return self._config.get("models", {}).get("chat", "anthropic/claude-opus-4.5")
    
    @property
    def chats_directory(self) -> Path:
        """Директория для сохранения чатов"""
        chats_dir = self._config.get("storage", {}).get("chats_dir", "~/.local/share/ai/chats")
        return Path(chats_dir).expanduser()


# Глобальный экземпляр конфигурации
config = Config()
