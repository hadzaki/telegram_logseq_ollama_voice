import os
import pickle
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import Task

logger = logging.getLogger(__name__)

# Если измените scope, удалите файл token.pickle
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarSync:
    """Синхронизация задач с Google Calendar"""
    
    def __init__(self, credentials_path: str = 'credentials.json', 
                 token_path: str = 'token.pickle',
                 db_path: str = 'tasks.db'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.db_path = db_path
        self.service = None
        self.calendar_id = 'primary'  # Основной календарь
        
    def authenticate(self) -> bool:
        """Аутентификация в Google Calendar"""
        creds = None
        
        # Загружаем сохраненный токен
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("✅ Токен загружен из файла")
            except Exception as e:
                logger.error(f"Ошибка загрузки токена: {e}")
        
        # Если нет действительных учетных данных, просим пользователя войти
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("✅ Токен обновлен")
                except Exception as e:
                    logger.error(f"Ошибка обновления токена: {e}")
                    return False
            else:
                if not os.path.exists(self.credentials_path):
                    logger.error(f"❌ Файл {self.credentials_path} не найден")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    logger.info("✅ Новая аутентификация выполнена")
                except Exception as e:
                    logger.error(f"❌ Ошибка аутентификации: {e}")
                    return False
            
            # Сохраняем токен
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"✅ Токен сохранен в {self.token_path}")
            except Exception as e:
                logger.error(f"Ошибка сохранения токена: {e}")
        
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Подключение к Google Calendar установлено")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка создания сервиса: {e}")
            return False
    
    def task_to_event(self, task: Task) -> Optional[Dict]:
        """Конвертирует задачу Logseq в событие Google Calendar"""
        if not task.deadline:
            return None
        
        # Определяем время события (по умолчанию весь день)
        is_all_day = True
        
        # Проверяем, есть ли конкретное время в дедлайне
        if task.deadline.hour != 0 or task.deadline.minute != 0:
            is_all_day = False
        
        # Определяем статус задачи для отображения
        status_emoji = {
            'TODO': '📝',
            'DOING': '⚡',
            'DONE': '✅',
            'NOW': '🔥',
            'LATER': '⏳',
            'WAITING': '⏸️',
            'CANCELED': '❌'
        }.get(task.status, '📌')
        
        event = {
            'summary': f"{status_emoji} {task.content}",
            'description': (
                f"Задача из Logseq\n"
                f"📋 Статус: {task.status}\n"
                f"🎯 Приоритет: {task.priority}\n"
                f"📁 Файл: {Path(task.file_path).name}\n"
                f"🔖 Теги: {', '.join(['#'+t for t in task.tags]) if task.tags else 'нет'}"
            ),
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'email', 'minutes': 60},
                ],
            },
            'extendedProperties': {
                'private': {
                    'logseq_task_id': task.id,
                    'logseq_file': task.file_path,
                    'logseq_status': task.status,
                }
            }
        }
        
        if is_all_day:
            # Событие на весь день
            event['start'] = {
                'date': task.deadline.strftime('%Y-%m-%d'),
                'timeZone': 'UTC',
            }
            event['end'] = {
                'date': task.deadline.strftime('%Y-%m-%d'),
                'timeZone': 'UTC',
            }
        else:
            # Событие с конкретным временем
            event['start'] = {
                'dateTime': task.deadline.isoformat(),
                'timeZone': 'UTC',
            }
            event['end'] = {
                'dateTime': (task.deadline + timedelta(hours=1)).isoformat(),
                'timeZone': 'UTC',
            }
        
        # Добавляем цвет в зависимости от приоритета
        color_map = {
            'высокий': '11',  # Красный
            'средний': '5',    # Желтый
            'низкий': '9',     # Зеленый
            'обычный': '1'     # Синий
        }
        event['colorId'] = color_map.get(task.priority, '1')
        
        return event
    
    def create_event(self, task: Task) -> Optional[str]:
        """Создает событие в календаре из задачи"""
        if not self.service:
            if not self.authenticate():
                return None
        
        event = self.task_to_event(task)
        if not event:
            return None
        
        try:
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            logger.info(f"✅ Событие создано: {task.content[:50]}...")
            return created_event.get('id')
        except HttpError as e:
            logger.error(f"❌ Ошибка создания события: {e}")
            return None
    
    def update_event(self, task: Task, event_id: str) -> bool:
        """Обновляет существующее событие"""
        if not self.service:
            if not self.authenticate():
                return False
        
        event = self.task_to_event(task)
        if not event:
            return False
        
        try:
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            logger.info(f"✅ Событие обновлено: {task.content[:50]}...")
            return True
        except HttpError as e:
            logger.error(f"❌ Ошибка обновления события: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """Удаляет событие из календаря"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            logger.info(f"✅ Событие удалено: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"❌ Ошибка удаления события: {e}")
            return False
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """Получает предстоящие события"""
        if not self.service:
            if not self.authenticate():
                return []
        
        now = datetime.utcnow().isoformat() + 'Z'
        later = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now,
                timeMax=later,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except HttpError as e:
            logger.error(f"❌ Ошибка получения событий: {e}")
            return []
    
    def find_event_by_task_id(self, task_id: str) -> Optional[str]:
        """Ищет событие по ID задачи"""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            page_token = None
            while True:
                events = self.service.events().list(
                    calendarId=self.calendar_id,
                    pageToken=page_token
                ).execute()
                
                for event in events.get('items', []):
                    props = event.get('extendedProperties', {}).get('private', {})
                    if props.get('logseq_task_id') == task_id:
                        return event['id']
                
                page_token = events.get('nextPageToken')
                if not page_token:
                    break
        except HttpError as e:
            logger.error(f"❌ Ошибка поиска события: {e}")
        
        return None
