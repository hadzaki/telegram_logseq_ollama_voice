#!/usr/bin/env python3
import os
import sys
import logging
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    JobQueue
)
from telegram import Update
import pytz

from modules.parser import LogseqTaskParser
from modules.classifier import WorkTaskClassifier
from modules.motivator import MotivationGenerator
from modules.database import TaskDatabase
from modules.voice_creator import VoiceTaskCreator
from modules.handlers import BotHandlers
from modules.notifier import TaskNotifier

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class LogseqBot:
    """Основной класс бота"""
    
    def __init__(self, config):
        self.config = config
        self.token = config['BOT_TOKEN']
        
        # Инициализация компонентов
        self.parser = LogseqTaskParser(
            config['LOGSEQ_PATH'], 
            config.get('MAX_MONTHS', 3)
        )
        
        self.classifier = WorkTaskClassifier(
            base_url=config.get('OLLAMA_URL', 'http://localhost:11434'),
            model=config.get('OLLAMA_MODEL', 'llama2'),
            work_keywords=config.get('WORK_KEYWORDS'),
            work_tags=config.get('WORK_TAGS'),
            personal_keywords=config.get('PERSONAL_KEYWORDS')
        )
        
        self.motivator = MotivationGenerator(
            base_url=config.get('OLLAMA_URL', 'http://localhost:11434'),
            model=config.get('OLLAMA_MODEL', 'llama2')
        )
        
        self.db = TaskDatabase(
            default_status_filter=config.get('DEFAULT_STATUS_FILTER', ['TODO', 'DOING', 'NOW', 'LATER'])
        )
        
        self.voice_creator = VoiceTaskCreator(
            logseq_path=config['LOGSEQ_PATH'],
            default_page=config.get('VOICE_TASK_PAGE', 'Inbox'),
            default_status=config.get('DEFAULT_TASK_STATUS', 'DOING'),
            classifier=self.classifier if config.get('AUTO_CLASSIFY_VOICE', True) else None
        )
        
        # Инициализация обработчиков с поддержкой белого списка
        self.handlers = BotHandlers(
            parser=self.parser,
            classifier=self.classifier,
            motivator=self.motivator,
            db=self.db,
            voice_creator=self.voice_creator,
            allowed_user_ids=config.get('ALLOWED_USER_IDS', [])  # Передаем список разрешенных ID
        )
        
        # Инициализация уведомлений
        self.notifier = TaskNotifier(
            db=self.db,
            classifier=self.classifier,
            motivator=self.motivator
        )
        
        logger.info(f"✅ Бот инициализирован. Разрешены ID: {config.get('ALLOWED_USER_IDS', [])}")
    
    async def check_notifications(self, context):
        """Проверяет и отправляет уведомления всем пользователям"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute("SELECT user_id FROM user_settings")
                users = cursor.fetchall()
            
            for (user_id,) in users:
                try:
                    # Проверяем просроченные задачи
                    await self.notifier.check_overdue_tasks(
                        context.bot, user_id, self.parser
                    )
                    
                    # Проверяем нужно ли отправить ежедневную сводку
                    settings = self.db.get_user_settings(user_id)
                    tz = pytz.timezone(settings["timezone"])
                    now = datetime.now(tz)
                    current_time = now.strftime("%H:%M")
                    
                    if current_time == settings["notify_time"]:
                        await self.notifier.send_daily_summary(
                            context.bot, user_id, self.parser
                        )
                    
                    # Проверяем рабочие задачи
                    await self.notifier.check_work_tasks(
                        context.bot, user_id, self.parser
                    )
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке уведомлений для пользователя {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в check_notifications: {e}")
    
    def run(self):
        """Запускает бота"""
        application = Application.builder().token(self.token).build()
        
        # Основные команды
        application.add_handler(CommandHandler("start", self.handlers.start))
        application.add_handler(CommandHandler("help", self.handlers.help_command))
        application.add_handler(CommandHandler("setpath", self.handlers.set_path))
        application.add_handler(CommandHandler("tasks", self.handlers.show_tasks))
        application.add_handler(CommandHandler("work", self.handlers.show_work_tasks))
        application.add_handler(CommandHandler("personal", self.handlers.show_personal_tasks))
        application.add_handler(CommandHandler("motivate", self.handlers.motivate))
        application.add_handler(CommandHandler("motivate_work", self.handlers.motivate_work))
        application.add_handler(CommandHandler("motivate_personal", self.handlers.motivate_personal))
        application.add_handler(CommandHandler("stats", self.handlers.show_stats))
        application.add_handler(CommandHandler("filter", self.handlers.status_filter_menu))
        application.add_handler(CommandHandler("settings", self.handlers.settings))
        
        # Команды для настройки времени и часового пояса
        application.add_handler(CommandHandler("set_time", self.handlers.set_time))
        application.add_handler(CommandHandler("set_timezone", self.handlers.set_timezone))
        application.add_handler(CommandHandler("toggle_auto", self.handlers.toggle_auto))
        
        # Команды для уведомлений
        application.add_handler(CommandHandler("notifications", self.handlers.notification_settings))
        application.add_handler(CommandHandler("toggle_daily", self.handlers.toggle_daily))
        application.add_handler(CommandHandler("toggle_overdue", self.handlers.toggle_overdue))
        application.add_handler(CommandHandler("toggle_work", self.handlers.toggle_work))
        
        # Голосовые сообщения
        application.add_handler(MessageHandler(filters.VOICE, self.handlers.handle_voice))
        
        # Обработчик callback-запросов от кнопок
        application.add_handler(CallbackQueryHandler(self.handlers.button_callback))
        
        # Планировщик задач для уведомлений (проверка каждые 15 минут)
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(self.check_notifications, interval=900, first=10)
            logger.info("✅ Планировщик уведомлений запущен (интервал: 15 минут)")
        
        # Запуск
        print("=" * 60)
        print("🤖 Logseq Motivation Bot запущен!")
        print("=" * 60)
        print(f"📁 Путь к Logseq: {self.parser.logseq_path}")
        print(f"🎤 Голосовые задачи сохраняются в: journals/YYYY_MM_DD.md со статусом DOING")
        print(f"🔔 Уведомления: проверка каждые 15 минут")
        print(f"🔒 Белый список ID: {self.config.get('ALLOWED_USER_IDS', [])}")
        print("=" * 60)
        print("🔄 Нажми Ctrl+C для остановки")
        print("=" * 60)
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Точка входа"""
    try:
        from config import (
            BOT_TOKEN, LOGSEQ_PATH, OLLAMA_URL, OLLAMA_MODEL,
            MAX_MONTHS, DEFAULT_STATUS_FILTER,
            WORK_KEYWORDS, WORK_TAGS, PERSONAL_KEYWORDS,
            VOICE_TASK_PAGE, DEFAULT_TASK_STATUS, AUTO_CLASSIFY_VOICE,
            ALLOWED_USER_IDS  # Импортируем список разрешенных ID
        )
        
        config = {
            'BOT_TOKEN': BOT_TOKEN,
            'LOGSEQ_PATH': LOGSEQ_PATH,
            'OLLAMA_URL': OLLAMA_URL,
            'OLLAMA_MODEL': OLLAMA_MODEL,
            'MAX_MONTHS': MAX_MONTHS,
            'DEFAULT_STATUS_FILTER': DEFAULT_STATUS_FILTER,
            'WORK_KEYWORDS': WORK_KEYWORDS,
            'WORK_TAGS': WORK_TAGS,
            'PERSONAL_KEYWORDS': PERSONAL_KEYWORDS,
            'VOICE_TASK_PAGE': VOICE_TASK_PAGE,
            'DEFAULT_TASK_STATUS': DEFAULT_TASK_STATUS,
            'AUTO_CLASSIFY_VOICE': AUTO_CLASSIFY_VOICE,
            'ALLOWED_USER_IDS': ALLOWED_USER_IDS  # Добавляем в конфиг
        }
        
        # Проверяем, что список разрешенных ID не пуст
        if not ALLOWED_USER_IDS:
            print("⚠️ ВНИМАНИЕ: Список разрешенных пользователей пуст!")
            print("🔐 Бот будет доступен всем пользователям Telegram.")
            print("✏️ Отредактируйте config.py и укажите свой ALLOWED_USER_IDS")
            print()
        
    except ImportError as e:
        print(f"❌ Ошибка импорта config.py: {e}")
        print("Запустите с параметром --init для создания:")
        print("python bot.py --init")
        sys.exit(1)
    except NameError as e:
        print(f"❌ Ошибка в config.py: {e}")
        print("Убедитесь, что в config.py определены все необходимые переменные")
        print("Особенно проверьте наличие ALLOWED_USER_IDS = [123456789]")
        sys.exit(1)
    
    # Проверяем наличие токена
    if config['BOT_TOKEN'] == "YOUR_BOT_TOKEN_HERE":
        print("❌ Не указан BOT_TOKEN в config.py")
        print("Получите токен у @BotFather и отредактируйте config.py")
        sys.exit(1)
    
    # Проверяем путь к Logseq
    if config['LOGSEQ_PATH'] == "/home/user/Documents/logseq":
        print("⚠️ Путь к Logseq не изменен в config.py")
        print("Укажите правильный путь или используйте /setpath в боте")
        print()
    
    # Запускаем бота
    bot = LogseqBot(config)
    bot.run()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        from config_creator import create_config, create_requirements
        create_config()
        create_requirements()
        print("""
🚀 Инициализация завершена!

Дальнейшие действия:

1️⃣ Установите системные зависимости:
   sudo apt-get update
   sudo apt-get install ffmpeg

2️⃣ Установите Python зависимости:
   pip install -r requirements.txt

3️⃣ Отредактируйте config.py с вашими настройками:
   - BOT_TOKEN: получите у @BotFather
   - LOGSEQ_PATH: укажите путь к вашей базе Logseq
   - ALLOWED_USER_IDS: укажите ваш Telegram ID

4️⃣ Запустите бота:
   python bot.py

5️⃣ Для автозапуска через systemd:
   sudo cp logseq-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable logseq-bot
   sudo systemctl start logseq-bot
        """)
    else:
        main()
