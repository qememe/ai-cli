"""Команда search - быстрый веб-поиск"""

import asyncio
import re
from rich.console import Console
from rich.markdown import Markdown

from ai.api import api_client
from ai.config import config

console = Console()

SEARCH_SYSTEM_PROMPT = """You are a precise web search assistant. Provide concise, factual answers with current information from the web. Structure responses as:
1. Direct answer (1-2 sentences)
2. Key facts (bullet points)
3. Sources (if available)

Keep responses under 300 words. Focus on accuracy and relevance.

IMPORTANT: Do NOT include citation numbers in square brackets like [1], [2], etc. in your response. Provide information naturally without reference markers."""


async def search_command(query: str, verbose: bool = False):
    """Выполнить поисковый запрос"""
    console.print(f"[cyan]🔍 Поиск: {query}[/cyan]\n")
    
    messages = [
        {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
        {"role": "user", "content": query}
    ]
    
    try:
        if verbose:
            console.print(f"[dim]Модель: {config.model_search}[/dim]")
            console.print(f"[dim]Temperature: 0.3[/dim]\n")
        
        response = await api_client.get_completion(
            model=config.model_search,
            messages=messages,
            temperature=0.3,
        )
        
        # Очистка ответа от квадратных скобок с цифрами (ссылки на источники)
        cleaned_response = re.sub(r'\[\d+\]', '', response)
        # Удаление множественных пробелов после очистки
        cleaned_response = re.sub(r'\s+', ' ', cleaned_response)
        # Удаление пробелов в начале строк
        cleaned_response = re.sub(r'\n\s+', '\n', cleaned_response)
        
        console.print(Markdown(cleaned_response))
        
        if verbose:
            console.print(f"\n[dim]Запрос выполнен успешно[/dim]")
    
    except Exception as e:
        console.print(f"[red]Ошибка при выполнении поиска: {e}[/red]")
        raise


def run_search(query: str, verbose: bool = False):
    """Синхронная обертка для команды search"""
    asyncio.run(search_command(query, verbose))
