📘 README.md для GitHub

```markdown
# 🤖 Logseq Telegram Bot

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://core.telegram.org/bots)
[![Logseq](https://img.shields.io/badge/Logseq-Integration-85C0F9?logo=logseq)](https://logseq.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ollama](https://img.shields.io/badge/Ollama-AI-5B5B5B?logo=ollama)](https://ollama.ai/)

Telegram бот для интеграции с [Logseq](https://logseq.com/) — голосовой ввод задач, ИИ-мотивация через Ollama, синхронизация с Google Calendar и умная фильтрация.

## ✨ Возможности

### 🎤 **Голосовой ввод задач**
- Отправьте голосовое сообщение — задача автоматически создаётся в `journals/ГГГГ_ММ_ДД.md`
- Распознавание дат: "завтра", "послезавтра", "15 февраля", "в пятницу"
- Определение приоритетов: "срочно", "важно"
- Автоматические теги: #работа, #личное, #покупки, #здоровье (через Ollama)

### 🤖 **ИИ-мотивация через Ollama**
- Персонализированные мотивирующие сообщения
- Классификация задач на рабочие и личные
- Анализ просроченных задач и приоритетов
- Локальная работа — все данные остаются у вас

### 📅 **Синхронизация с Google Calendar**
- Автоматическое создание событий из задач с дедлайнами
- Цветовая кодировка по приоритетам (красный - высокий, жёлтый - средний, зелёный - низкий)
- Двусторонняя синхронизация
- Напоминания о задачах

### 📊 **Управление задачами**
- `/tasks` — просмотр всех задач с фильтрацией
- `/work` — только рабочие задачи
- `/personal` — только личные задачи
- `/stats` — детальная статистика

### 🔔 **Умные уведомления**
- Ежедневная сводка по задачам
- Оповещения о просроченных задачах
- Напоминания о рабочих задачах (9:00-18:00)

### 🎯 **Гибкая фильтрация**
- По статусам: TODO, DOING, DONE, NOW, LATER, WAITING
- По дате: задачи за последние N месяцев
- По типу: рабочие/личные

### 🔒 **Безопасность**
- Белый список пользователей (только для владельца)
- Локальная работа с Ollama
- Все данные хранятся на вашем устройстве
- OAuth 2.0 для Google Calendar

## 🚀 Быстрый старт

### Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/hadzaki/telegram_logseq_ollama_voice.git
cd telegram_logseq_ollama_voice

# Запустите инициализацию
python bot.py --init

# Установите зависимости
pip install -r requirements.txt

# Установите ffmpeg (для голосовых сообщений)
sudo apt-get update
sudo apt-get install ffmpeg
```

Настройка

1. Получите токен бота у @BotFather
2. Узнайте свой Telegram ID через @userinfobot
3. Настройте Google Calendar (опционально):
   · Создайте проект в Google Cloud Console
   · Включите Google Calendar API
   · Создайте OAuth 2.0 Client ID (Desktop app)
   · Скачайте credentials.json в папку проекта
4. Отредактируйте config.py:

```python
# Telegram
BOT_TOKEN = "ваш_токен_от_botfather"
ALLOWED_USER_IDS = [ваш_telegram_id]  # Белый список

# Logseq
LOGSEQ_PATH = "/путь/к/вашей/базе/logseq"  # Например: /home/user/Documents/logseq

# Ollama
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama2"  # или mistral, phi, codellama

# Google Calendar (опционально)
GOOGLE_CALENDAR_ENABLED = True
GOOGLE_CREDENTIALS_PATH = "credentials.json"
```

Запуск

```bash
# Запуск вручную
python bot.py

# Или через systemd (автозапуск)
sudo cp logseq-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable logseq-bot
sudo systemctl start logseq-bot
```

📖 Использование

Основные команды

Команда Описание
/start Начало работы
/tasks Показать все задачи
/work Только рабочие задачи
/personal Только личные задачи
/motivate Получить мотивацию
/stats Статистика
/filter Настройка фильтра статусов
/notifications Управление уведомлениями
/calendar Статус Google Calendar
/sync Ручная синхронизация с календарем
/settings Все настройки
/help Справка

Голосовые команды

Голосовое сообщение Результат
"Купить молоко завтра" - DOING Купить молоко DEADLINE: <2026-02-24> #покупки #голосовое
"Срочно сдать отчет 15 февраля" - DOING Срочно сдать отчет DEADLINE: <2026-02-15> PRIORITY: A #работа #голосовое
"Позвонить маме в пятницу" - DOING Позвонить маме DEADLINE: <2026-02-28> #личное #коммуникация #голосовое
"Записаться к врачу" - DOING Записаться к врачу #здоровье #голосовое

Поддерживаемые форматы Logseq

```markdown
- TODO Задача
- DOING В процессе
- DONE Выполнено
- NOW Сейчас
- LATER Потом
- WAITING Ожидание
- CANCELED Отменено
- DEADLINE: <2026-02-28>  # Дедлайн
- PRIORITY: A  # Приоритет (A, B, C)
- #тег  # Теги
```

🏗 Архитектура проекта

```
logseq-bot/
├── bot.py                 # Главный файл
├── config.py              # Конфигурация
├── requirements.txt       # Зависимости
├── modules/
│   ├── __init__.py
│   ├── auth.py            # Авторизация (белый список)
│   ├── calendar_sync.py   # Синхронизация с Google Calendar
│   ├── classifier.py      # Классификация через Ollama
│   ├── database.py        # Работа с SQLite
│   ├── handlers.py        # Обработчики команд Telegram
│   ├── models.py          # Модели данных
│   ├── motivator.py       # Генерация мотивации
│   ├── notifier.py        # Уведомления
│   ├── parser.py          # Парсинг Logseq
│   └── voice_creator.py   # Голосовой ввод
└── utils/
    └── __init__.py
```

🔧 Требования

· Python 3.8+
· Ollama (с моделью llama2 или другой)
· ffmpeg (для голосовых сообщений)
· Logseq (любая версия)
· Google аккаунт (для календаря)

📦 Зависимости

```
python-telegram-bot==20.7
aiohttp==3.9.1
pytz==2023.3
SpeechRecognition==3.10.0
pydub==0.25.1
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.108.0
```

🚀 Установка Ollama

```bash
# Установка Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Запуск сервера
ollama serve

# Скачивание модели (в другом терминале)
ollama pull llama2
# или более легкая версия
ollama pull phi
```

📱 Настройка Google Calendar

1. Перейдите в Google Cloud Console
2. Создайте новый проект
3. Включите Google Calendar API
4. Создайте OAuth 2.0 Client ID (тип "Desktop app")
5. Скачайте credentials.json в папку проекта
6. При первом запуске /calendar бот выдаст ссылку для авторизации

🔒 Безопасность

· Все секреты хранятся в config.py (не добавляйте в git!)
· Токены Google хранятся в token.pickle
· Белый список пользователей
· Локальная работа с Ollama без отправки данных в облако

.gitignore для проекта

```gitignore
# Секретные файлы
config.py
credentials.json
token.pickle
*.db
*.db-journal

# Кэш Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Временные файлы
*.log
*.tmp
*.temp
*.wav
*.ogg

# Бэкапы
backups/
*.tar.gz
*.zip

# Виртуальное окружение
venv/
env/
.venv/
```

🐛 Известные проблемы и решения

Проблема: "No module named 'modules'"

Решение: Запускайте бота из корневой папки проекта:

```bash
cd /home/user/logseq-bot
python bot.py
```

Проблема: "ffmpeg not found"

Решение: Установите ffmpeg:

```bash
sudo apt-get install ffmpeg
```

Проблема: "Google Calendar не настроен"

Решение: Проверьте config.py:

```python
GOOGLE_CALENDAR_ENABLED = True
GOOGLE_CREDENTIALS_PATH = "credentials.json"
```

Проблема: "Access blocked: This app is not verified"

Решение: Нажмите "Advanced" → "Go to Logseq Bot (unsafe)"

🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (git checkout -b feature/amazing)
3. Зафиксируйте изменения (git commit -m 'Add amazing feature')
4. Отправьте изменения (git push origin feature/amazing)
5. Откройте Pull Request

📄 Лицензия

MIT License. Смотрите файл LICENSE для деталей.

📬 Контакты

· GitHub: @hadzaki
· Telegram: @hadzaki83

⭐ Поддержка проекта

Если проект полезен, поставьте звезду на GitHub! Это помогает другим пользователям найти его.

---

Сделано с ❤️ для пользователей Logseq

```

## 📝 **Краткое описание для GitHub (About section)**

```

🤖 Telegram бот для Logseq с голосовым вводом задач, ИИ-мотивацией через Ollama, синхронизацией с Google Calendar и умной фильтрацией. Поддерживает распознавание дат, приоритетов и автоматическую классификацию задач.

```

## 🏷️ **Теги для GitHub (Topics)**

```

logseq, telegram-bot, productivity, task-manager, voice-commands, ollama, ai-motivation, google-calendar, python, personal-knowledge-management, pkm, speech-recognition, ocr

```

Этот README.md содержит всю необходимую информацию для пользователей и разработчиков! 🚀
