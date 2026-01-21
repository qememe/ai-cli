"""CLI точка входа для приложения"""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console

from ai.config import config
from ai.search import run_search
from ai.ask import run_ask
from ai.chat import run_chat

console = Console()

# Настройка логирования
log_file = config.log_file
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        # Не выводим логи в консоль, только в файл
    ]
)

# Отключаем логирование httpx в консоль
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """AI CLI помощник для Arch Linux с ProxyAPI"""
    pass


@cli.command()
@click.argument("query", required=True)
@click.option("--verbose", "-v", is_flag=True, help="Показать дополнительную информацию")
def search(query: str, verbose: bool):
    """Быстрый веб-поиск"""
    try:
        run_search(query, verbose)
    except KeyboardInterrupt:
        console.print("\n[yellow]Прервано пользователем[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("question", required=True)
@click.option("--verbose", "-v", is_flag=True, help="Показать дополнительную информацию")
def ask(question: str, verbose: bool):
    """Одиночные вопросы (до 3 обменов)"""
    try:
        run_ask(question, verbose)
    except KeyboardInterrupt:
        console.print("\n[yellow]Прервано пользователем[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("name", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Показать дополнительную информацию")
def chat(name: str, verbose: bool):
    """Интерактивный чат с сохранением"""
    try:
        run_chat(name, verbose)
    except KeyboardInterrupt:
        console.print("\n[yellow]Прервано пользователем[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Ошибка: {e}[/red]")
        sys.exit(1)


def main():
    """Главная функция для входа в приложение"""
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Критическая ошибка: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
