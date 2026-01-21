# AI CLI помощник для Arch Linux

Консольная программа на Python 3.13 для работы с ProxyAPI через OpenRouter-совместимый интерфейс.

## Возможности

- **`ai search <запрос>`** - быстрый веб-поиск с использованием Perplexity Sonar
- **`ai ask <вопрос>`** - одиночные вопросы с ограничением до 3 обменов (DeepSeek)
- **`ai chat [название]`** - интерактивный чат с сохранением истории (Claude Opus 4.5)

## Установка

### Вариант 1: Использование pipx (рекомендуется для Arch Linux)

**Быстрая установка через скрипт:**
```bash
./install.sh
```

**Или вручную:**
1. Установите pipx (если еще не установлен):
```bash
sudo pacman -S python-pipx
```

2. Установите приложение:
```bash
pipx install --editable .
```

3. Настройте конфигурацию:
   - При первом запуске будет создан файл `~/.config/ai/config.toml`
   - Добавьте ваш ProxyAPI ключ в файл конфигурации

**Примечание**: После установки через pipx команда `ai` будет доступна глобально из любого места.

### Вариант 2: Использование виртуального окружения

**Быстрая установка через скрипт:**
```bash
./install-venv.sh
```

**Или вручную:**
1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # или: . venv/bin/activate
```

2. Установите зависимости и приложение:
```bash
pip install -e .
```

3. Настройте конфигурацию:
   - При первом запуске будет создан файл `~/.config/ai/config.toml`
   - Добавьте ваш ProxyAPI ключ в файл конфигурации

**Примечание**: После установки через venv, команда `ai` будет доступна только при активированном виртуальном окружении. Для глобальной доступности используйте pipx.

**Совет**: Для удобства можно добавить алиас в `~/.zshrc` или `~/.bashrc`:
```bash
alias ai='source /path/to/project/venv/bin/activate && ai'
```

## Конфигурация

Файл конфигурации: `~/.config/ai/config.toml`

```toml
[api]
proxyapi_key = "sk-..."
base_url = "https://api.proxyapi.ru/openrouter/v1"

[models]
search = "perplexity/sonar"
ask = "deepseek/deepseek-v3.2"
chat = "claude-opus-4-5-20251101"

[storage]
chats_dir = "~/.local/share/ai/chats"
```

## Использование

### Поиск
```bash
ai search "курс доллара сегодня"
```

### Быстрый вопрос
```bash
ai ask "как установить nvidia драйвера в arch"
```

### Интерактивный чат
```bash
# Создать новый чат
ai chat

# Загрузить существующий чат
ai chat философия
```

**Команды в чате:**
- `/new [название]` - создать новый чат
- `/load <название>` - загрузить существующий чат
- `/list` - показать все сохраненные чаты
- `/save` - сохранить текущий чат
- `/exit` - выход из чата

## Структура проекта

```
ai/
├── ai/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   ├── api.py          # ProxyAPI client
│   ├── search.py       # search command
│   ├── ask.py          # ask command
│   ├── chat.py         # chat command + TUI
│   └── config.py       # config management
├── pyproject.toml
└── README.md
```

## Хранение данных

- Конфигурация: `~/.config/ai/config.toml`
- Чаты: `~/.local/share/ai/chats/*.json`
- Логи: `~/.local/share/ai/ai.log`

## Формат сохранения чатов

Чаты сохраняются в JSON формате:

```json
{
  "name": "философия-ai",
  "created": "2026-01-22T00:04:00Z",
  "model": "anthropic/claude-opus-4.5",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

## Зависимости

- Python 3.13+
- openai >= 1.0.0
- anthropic >= 0.34.0
- rich >= 13.0.0
- click >= 8.0.0
- tomli >= 2.0.0 (для Python < 3.11)

## Особенности

- ✅ Streaming ответов в режиме чата
- ✅ Цветной вывод с поддержкой Markdown
- ✅ Обработка ошибок (таймауты, кредиты, сеть)
- ✅ Graceful shutdown (Ctrl+C)
- ✅ Автоматическое создание директорий
- ✅ Логирование в файл

## Лицензия

MIT
