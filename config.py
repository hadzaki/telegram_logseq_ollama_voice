
# ID разрешенных пользователей (ваш Telegram ID)
# Как узнать свой ID: напишите боту @userinfobot в Telegram
ALLOWED_USER_IDS = [3333333333]  # Замените на ваш реальный ID!

# Настройки фильтрации по умолчанию
MAX_MONTHS = 3  # Показывать задачи не старше N месяцев (0 = все задачи)
DEFAULT_STATUS_FILTER = ["TODO", "DOING", "NOW", "LATER"]  # Статусы по умолчанию


# Настройки для голосовых сообщений
VOICE_TASK_PAGE = "Inbox"  # Страница для новых задач (Inbox.md)
DEFAULT_TASK_STATUS = "DOING"  # Статус по умолчанию для новых задач
AUTO_CLASSIFY_VOICE = True  # Автоматически классифицировать задачу (рабочая/личная)





# Конфигурация бота
BOT_TOKEN = "8888888888888888888888888888888888888888888888"  # Получите у @BotFather
LOGSEQ_PATH = "/mnt/disk_1GB/syncting/Logseq"   # Путь к вашей базе Logseq
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"  # или "mistral", "codellama", "llama3", "phi"

# Настройки фильтрации по умолчанию
MAX_MONTHS = 3  # Показывать задачи не старше N месяцев (0 = все задачи)
DEFAULT_STATUS_FILTER = ["TODO", "DOING", "NOW", "LATER"]  # Статусы по умолчанию

# Настройки для определения рабочих задач
WORK_KEYWORDS = [
    "работа", "work", "job", "проект", "project", "task", "задача",
    "дедлайн", "deadline", "отчет", "report", "клиент", "client",
    "встреча", "meeting", "презентация", "presentation", "код", "code",
    "разработка", "development", "баг", "bug", "фича", "feature",
    "документация", "documentation", "письмо", "email", "звонок", 
    "call","работе", "насос","задвижка","птп"
]

WORK_TAGS = ["работа", "work", "job", "проект", "клиент", "рабочее"]

PERSONAL_KEYWORDS = [
    "личное", "personal", "дом", "home", "семья", "family",
    "отдых", "rest", "хобби", "hobby", "спорт", "sport",
    "здоровье", "health", "магазин", "shop", "купить", "buy"
]

