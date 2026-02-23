import logging
from datetime import datetime
from typing import List
import aiohttp
from .models import Task

logger = logging.getLogger(__name__)

class MotivationGenerator:
    """Генератор мотивационных сообщений через Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
        
    async def generate_motivation(self, tasks: List[Task], focus_work: bool = False) -> str:
        """
        Генерирует мотивационное сообщение на основе списка задач
        """
        if not tasks:
            return "У тебя нет невыполненных задач! Отличная работа! 🎉"
        
        if focus_work:
            work_tasks = [t for t in tasks if t.is_work]
            if not work_tasks:
                return "У тебя нет рабочих задач! Можешь отдохнуть или заняться личными делами. 🌟"
            tasks_to_show = work_tasks
            focus_text = "РАБОЧИЕ задачи"
        else:
            tasks_to_show = tasks
            focus_text = "ВСЕ задачи"
        
        tasks_desc = []
        now = datetime.now()
        
        for task in tasks_to_show[:10]:
            deadline_info = ""
            if task.deadline:
                days_left = (task.deadline - now).days
                if days_left < 0:
                    deadline_info = f"(просрочено на {abs(days_left)} дней)"
                elif days_left == 0:
                    deadline_info = "(сегодня дедлайн)"
                else:
                    deadline_info = f"(осталось {days_left} дней)"
            
            status_emoji = self._get_status_emoji(task.status)
            priority_emoji = "🔴" if task.priority == "высокий" else "🟡" if task.priority == "средний" else "🟢"
            work_marker = "💼 " if task.is_work else "🏠 "
            
            task_line = f"{work_marker}{status_emoji}{priority_emoji} {task.content} {deadline_info}"
            if task.tags:
                task_line += f" #{' #'.join(task.tags)}"
            
            tasks_desc.append(task_line)
        
        work_count = len([t for t in tasks_to_show if t.is_work])
        personal_count = len([t for t in tasks_to_show if t.is_work is False])
        overdue_count = len([t for t in tasks_to_show if t.deadline and t.deadline < now])
        
        prompt = f"""Ты - мотивационный тренер. У пользователя есть список {focus_text}:

{chr(10).join(tasks_desc)}

Статистика:
• Всего задач: {len(tasks_to_show)}
• Рабочих: {work_count}
• Личных: {personal_count}
• Просрочено: {overdue_count}

Напиши короткое (не более 500 символов) мотивирующее сообщение.
Учти соотношение рабочих и личных задач, просрочки и срочность.
Будь дружелюбным, используй эмодзи.
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                }
                
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "Давай, ты сможешь! 💪").strip()
                    else:
                        logger.error(f"Ошибка Ollama: {response.status}")
                        return self._get_fallback_message(tasks_to_show, focus_work)
                        
        except Exception as e:
            logger.error(f"Ошибка при обращении к Ollama: {e}")
            return self._get_fallback_message(tasks_to_show, focus_work)
    
    def _get_status_emoji(self, status: str) -> str:
        """Возвращает эмодзи для статуса задачи"""
        emoji_map = {
            'TODO': '📝', 'DOING': '⚡', 'DONE': '✅',
            'NOW': '🔥', 'LATER': '⏳', 'WAITING': '⏸️',
            'CANCELED': '❌'
        }
        return emoji_map.get(status, '📌')
    
    def _get_fallback_message(self, tasks: List[Task], focus_work: bool) -> str:
        """Запасное сообщение"""
        now = datetime.now()
        overdue = [t for t in tasks if t.deadline and t.deadline < now]
        doing = [t for t in tasks if t.status in ['DOING', 'NOW']]
        work_tasks = [t for t in tasks if t.is_work]
        
        if focus_work:
            if overdue:
                return f"💼 У тебя {len(overdue)} просроченных рабочих задач! Самое время ими заняться."
            elif work_tasks:
                return f"💼 У тебя {len(work_tasks)} рабочих задач. Сосредоточься на карьере!"
            else:
                return "💼 Рабочих задач нет. Отличное время для отдыха!"
        else:
            if overdue:
                return f"⚠️ У тебя {len(overdue)} просроченных задач! Самое время их выполнить."
            elif doing:
                return f"⚡ Продолжай работу над {len(doing)} задачами в процессе."
            else:
                return f"📋 У тебя {len(tasks)} невыполненных задач."
