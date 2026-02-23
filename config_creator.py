def create_config():
    """Создает файл конфигурации"""
    config = """# Конфигурация бота
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Получите у @BotFather
LOGSEQ_PATH = "/home/user/Documents/logseq"   # Путь к вашей базе Logseq
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama2"  # или "mistral", "codellama", "llama3", "phi"

# Настройки фильтрации по умолчанию
MAX_MONTHS = 3  # Показывать задачи не старше N месяцев (0 = все задачи)
DEFAULT_STATUS_FILTER = ["TODO", "DOING", "NOW", "LATER"]  # Статусы по умолчанию

# Настройки для определения рабочих задач
WORK_KEYWORDS = [
    "работа", "work", "job", "проект", "project", "task", "задача",
    "дедлайн", "deadline", "отчет", "report", "клиент", "client",
    "встреча", "meeting", "презентация", "presentation", "код", "code",
    "разработка", "development", "баг", "bug", "фича", "feature",
    "документация", "documentation", "письмо", "email", "звонок", "call"
]

WORK_TAGS = ["работа", "work", "job", "проект", "клиент", "рабочее"]

PERSONAL_KEYWORDS = [
    "личное", "personal", "дом", "home", "семья", "family",
    "отдых", "rest", "хобби", "hobby", "спорт", "sport",
    "здоровье", "health", "магазин", "shop", "купить", "buy"
]

# Настройки для голосовых сообщений
VOICE_TASK_PAGE = "Inbox"  # Страница для новых задач (Inbox.md)
DEFAULT_TASK_STATUS = "TODO"  # Статус по умолчанию для новых задач
AUTO_CLASSIFY_VOICE = True  # Автоматически классифицировать задачу (рабочая/личная)
"""
    
    with open("config.py", "w") as f:
        f.write(config)
    
    print("✅ Создан файл config.py")

def create_requirements():
    """Создает файл с зависимостями"""
    requirements = """python-telegram-bot==20.7
aiohttp==3.9.1
aiofiles==23.2.1
pytz==2023.3
SpeechRecognition==3.10.0
pydub==0.25.1
ffmpeg-python==0.2.0
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    
    print("✅ Создан файл requirements.txt")
