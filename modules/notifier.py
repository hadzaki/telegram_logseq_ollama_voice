import logging
from datetime import datetime, timedelta
from typing import List, Optional
import pytz

from telegram import Bot
from telegram.error import TelegramError

from .models import Task
from .database import TaskDatabase

logger = logging.getLogger(__name__)

class TaskNotifier:
    """Класс для отправки уведомлений о задачах"""
    
    def __init__(self, db: TaskDatabase, classifier, motivator):
        self.db = db
        self.classifier = classifier
        self.motivator = motivator
    
    async def _classify_tasks(self, tasks: List[Task]) -> List[Task]:
        """Классифицирует задачи на рабочие/личные"""
        classified_tasks = []
        for task in tasks:
            if task.is_work is None:
                task.is_work = await self.classifier.is_work_task(task)
            classified_tasks.append(task)
        return classified_tasks
    
    async def check_overdue_tasks(self, bot: Bot, user_id: int, parser) -> bool:
        """
        Проверяет просроченные задачи и отправляет уведомление
        Возвращает True если уведомление было отправлено
        """
        settings = self.db.get_user_settings(user_id)
        
        # Проверяем включены ли уведомления о просроченных задачах
        if not settings.get("notify_overdue", True):
            return False
        
        # Проверяем когда было последнее уведомление (не чаще раза в день)
        last_notif = self.db.get_last_notification_time(user_id, "overdue")
        if last_notif and (datetime.now() - last_notif) < timedelta(hours=12):
            return False
        
        # Получаем задачи
        all_tasks = parser.parse_all_tasks(filter_by_date=True, status_filter=set(settings["status_filter"]))
        all_tasks = await self._classify_tasks(all_tasks)
        
        # Фильтруем просроченные и невыполненные
        now = datetime.now()
        overdue_tasks = [
            t for t in all_tasks 
            if not t.completed and t.deadline and t.deadline < now
        ]
        
        if not overdue_tasks:
            return False
        
        # Группируем по типу
        work_overdue = [t for t in overdue_tasks if t.is_work]
        personal_overdue = [t for t in overdue_tasks if t.is_work is False]
        
        # Формируем сообщение
        message = f"⚠️ **У вас {len(overdue_tasks)} просроченных задач!**\n\n"
        
        if work_overdue:
            message += f"💼 Рабочих: {len(work_overdue)}\n"
            for task in work_overdue[:3]:
                days = (now - task.deadline).days
                message += f"  • {task.content} (просрочено {days} дн.)\n"
        
        if personal_overdue:
            message += f"🏠 Личных: {len(personal_overdue)}\n"
            for task in personal_overdue[:3]:
                days = (now - task.deadline).days
                message += f"  • {task.content} (просрочено {days} дн.)\n"
        
        if len(overdue_tasks) > 6:
            message += f"\n...и еще {len(overdue_tasks) - 6} задач"
        
        message += "\n\n/tasks - посмотреть все задачи"
        
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            self.db.save_notification(user_id, "overdue", len(overdue_tasks), message)
            logger.info(f"Отправлено уведомление о просроченных задачах пользователю {user_id}")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
            return False
    
    async def send_daily_summary(self, bot: Bot, user_id: int, parser) -> bool:
        """
        Отправляет ежедневную сводку по задачам
        """
        settings = self.db.get_user_settings(user_id)
        
        if not settings.get("notify_daily", True):
            return False
        
        # Проверяем время последнего уведомления
        last_notif = self.db.get_last_notification_time(user_id, "daily")
        if last_notif and (datetime.now() - last_notif) < timedelta(hours=20):
            return False
        
        # Получаем задачи
        all_tasks = parser.parse_all_tasks(filter_by_date=True, status_filter=set(settings["status_filter"]))
        all_tasks = await self._classify_tasks(all_tasks)
        
        # Статистика
        now = datetime.now()
        total = len(all_tasks)
        completed = len([t for t in all_tasks if t.completed])
        active = total - completed
        
        overdue = len([t for t in all_tasks if not t.completed and t.deadline and t.deadline < now])
        due_today = len([t for t in all_tasks if not t.completed and t.deadline and t.deadline.date() == now.date()])
        
        work_tasks = len([t for t in all_tasks if t.is_work and not t.completed])
        personal_tasks = len([t for t in all_tasks if t.is_work is False and not t.completed])
        
        # Формируем сообщение
        message = f"📊 **Ежедневная сводка по задачам**\n\n"
        message += f"📋 Всего задач: {total}\n"
        message += f"✅ Выполнено: {completed}\n"
        message += f"📝 Активных: {active}\n\n"
        
        if overdue:
            message += f"⚠️ Просрочено: {overdue}\n"
        if due_today:
            message += f"🔥 На сегодня: {due_today}\n"
        
        message += f"\n💼 Рабочих: {work_tasks}\n"
        message += f"🏠 Личных: {personal_tasks}\n"
        
        # Добавляем мотивацию
        if active > 0:
            motivation = await self.motivator.generate_motivation(
                [t for t in all_tasks if not t.completed], 
                focus_work=False
            )
            message += f"\n💪 {motivation}"
        
        message += "\n\n/tasks - посмотреть все задачи"
        
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            self.db.save_notification(user_id, "daily", active, message)
            logger.info(f"Отправлена ежедневная сводка пользователю {user_id}")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка при отправке сводки: {e}")
            return False
    
    async def check_work_tasks(self, bot: Bot, user_id: int, parser) -> bool:
        """
        Проверяет рабочие задачи и отправляет напоминание (для рабочего времени)
        """
        settings = self.db.get_user_settings(user_id)
        
        if not settings.get("notify_work", False):
            return False
        
        # Проверяем рабочее время (9:00 - 18:00)
        tz = pytz.timezone(settings["timezone"])
        now = datetime.now(tz)
        if now.hour < 9 or now.hour > 18:
            return False
        
        # Проверяем когда было последнее уведомление (не чаще раза в 3 часа)
        last_notif = self.db.get_last_notification_time(user_id, "work")
        if last_notif and (datetime.now() - last_notif) < timedelta(hours=3):
            return False
        
        # Получаем задачи
        all_tasks = parser.parse_all_tasks(filter_by_date=True, status_filter=set(settings["status_filter"]))
        all_tasks = await self._classify_tasks(all_tasks)
        
        # Фильтруем рабочие задачи
        work_tasks = [t for t in all_tasks if t.is_work and not t.completed]
        
        if not work_tasks:
            return False
        
        # Приоритетные задачи
        high_priority = [t for t in work_tasks if t.priority == "высокий"]
        overdue = [t for t in work_tasks if t.deadline and t.deadline < datetime.now()]
        
        message = f"💼 **Рабочие задачи**\n\n"
        message += f"Всего: {len(work_tasks)}\n"
        
        if high_priority:
            message += f"🔴 С высоким приоритетом: {len(high_priority)}\n"
        
        if overdue:
            message += f"⚠️ Просрочено: {len(overdue)}\n"
        
        message += "\n**Ближайшие:**\n"
        for task in sorted(work_tasks, key=lambda x: x.deadline or datetime.max)[:3]:
            deadline = f" (дедлайн: {task.deadline.strftime('%d.%m')})" if task.deadline else ""
            message += f"• {task.content}{deadline}\n"
        
        message += "\n/work - посмотреть все рабочие задачи"
        
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            self.db.save_notification(user_id, "work", len(work_tasks), message)
            logger.info(f"Отправлено напоминание о рабочих задачах пользователю {user_id}")
            return True
        except TelegramError as e:
            logger.error(f"Ошибка при отправке напоминания: {e}")
            return False
