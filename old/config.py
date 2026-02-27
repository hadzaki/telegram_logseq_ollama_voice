# Конфигурация бота
BOT_TOKEN = "8224518137:AAFfukVRBCdOZKNno0RRqgywxQBazJQPd7A"  # Получите у @BotFather
LOGSEQ_PATH = "/home/bulat/logseq/logseq"   # Путь к вашей базе Logseq
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
    "документация", "documentation", "письмо", "email", "звонок", "call"
]

WORK_TAGS = ["работа", "work", "job", "проект", "клиент", "рабочее"]

PERSONAL_KEYWORDS = [
    "личное", "personal", "дом", "home", "семья", "family",
    "отдых", "rest", "хобби", "hobby", "спорт", "sport",
    "здоровье", "health", "магазин", "shop", "купить", "buy"
]
