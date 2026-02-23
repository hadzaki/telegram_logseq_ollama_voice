import logging
from typing import List, Optional
import aiohttp
from .models import Task

logger = logging.getLogger(__name__)

class WorkTaskClassifier:
    """Классификатор рабочих задач с использованием Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2",
                 work_keywords: List[str] = None, work_tags: List[str] = None,
                 personal_keywords: List[str] = None):
        self.base_url = base_url
        self.model = model
        self.work_keywords = work_keywords or [
            "работа", "work", "job", "проект", "project", "task", "задача",
            "дедлайн", "deadline", "отчет", "report", "клиент", "client"
        ]
        self.work_tags = work_tags or ["работа", "work", "job", "проект", "клиент", "рабочее"]
        self.personal_keywords = personal_keywords or [
            "личное", "personal", "дом", "home", "семья", "family",
            "отдых", "rest", "хобби", "hobby", "спорт", "sport"
        ]
        
        # Кэш для результатов классификации
        self.classification_cache = {}
        
    async def is_work_task(self, task: Task) -> bool:
        """
        Определяет, является ли задача рабочей
        """
        cache_key = task.id
        if cache_key in self.classification_cache:
            return self.classification_cache[cache_key]
        
        quick_result = self._quick_classify(task)
        if quick_result is not None:
            self.classification_cache[cache_key] = quick_result
            return quick_result
        
        result = await self._ollama_classify(task)
        self.classification_cache[cache_key] = result
        return result
    
    def _quick_classify(self, task: Task) -> Optional[bool]:
        """
        Быстрая классификация по ключевым словам и тегам
        """
        content_lower = task.content.lower()
        
        for tag in task.tags:
            if tag in self.work_tags:
                return True
            if tag in ["личное", "personal", "дом", "home"]:
                return False
        
        work_match = any(keyword in content_lower for keyword in self.work_keywords)
        personal_match = any(keyword in content_lower for keyword in self.personal_keywords)
        
        if work_match and not personal_match:
            return True
        if personal_match and not work_match:
            return False
        
        return None
    
    async def _ollama_classify(self, task: Task) -> bool:
        """
        Использует Ollama для классификации задачи
        """
        prompt = f"""Ты - помощник, который определяет, относится ли задача к работе или к личным делам.

Задача: {task.content}
Контекст: {'Дедлайн: ' + task.deadline.strftime('%Y-%m-%d') if task.deadline else 'Без дедлайна'}
Теги: {', '.join(task.tags) if task.tags else 'Нет тегов'}

Ответь только "work" если задача рабочая, или "personal" если личная.
Не пиши ничего кроме одного слова.
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "max_tokens": 10
                    }
                }
                
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result.get("response", "").strip().lower()
                        
                        if "work" in answer:
                            return True
                        elif "personal" in answer:
                            return False
                        else:
                            return self._heuristic_classify(task)
                    else:
                        logger.error(f"Ошибка Ollama: {response.status}")
                        return self._heuristic_classify(task)
                        
        except Exception as e:
            logger.error(f"Ошибка при обращении к Ollama: {e}")
            return self._heuristic_classify(task)
    
    def _heuristic_classify(self, task: Task) -> bool:
        """
        Эвристическая классификация
        """
        content_lower = task.content.lower()
        
        work_count = sum(1 for kw in self.work_keywords if kw in content_lower)
        personal_count = sum(1 for kw in self.personal_keywords if kw in content_lower)
        
        for tag in task.tags:
            if tag in self.work_tags:
                work_count += 2
            if tag in ["личное", "personal"]:
                personal_count += 2
        
        if task.deadline:
            work_count += 1
        
        return work_count > personal_count
