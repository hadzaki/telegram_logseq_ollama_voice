import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TaskDatabase:
    """База данных для отслеживания отправленных задач и настроек"""
    
    def __init__(self, db_path: str = "tasks.db", default_status_filter: List[str] = None):
        self.db_path = db_path
        self.default_status_filter = default_status_filter or ['TODO', 'DOING', 'NOW', 'LATER']
        self._init_db()
        self._migrate_db()
    
    def _init_db(self):
        """Инициализирует базу данных"""
        with sqlite3.connect(self.db_path) as conn:
            # Таблица отправленных задач
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_tasks (
                    task_id TEXT PRIMARY KEY,
                    sent_date TIMESTAMP,
                    user_id INTEGER
                )
            """)
            
            # Таблица настроек пользователей
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    notify_time TEXT,
                    timezone TEXT,
                    auto_motivation BOOLEAN DEFAULT 1,
                    notify_overdue BOOLEAN DEFAULT 1,
                    notify_daily BOOLEAN DEFAULT 1,
                    notify_work BOOLEAN DEFAULT 0,
                    last_notification TIMESTAMP
                )
            """)
            
            # Новая таблица для истории оповещений
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    sent_time TIMESTAMP,
                    tasks_count INTEGER,
                    message TEXT
                )
            """)
    
    def _migrate_db(self):
        """Обновляет структуру базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("PRAGMA table_info(user_settings)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Добавляем новые колонки если их нет
                if 'status_filter' not in columns:
                    default_filter_str = ','.join(self.default_status_filter)
                    conn.execute(f"ALTER TABLE user_settings ADD COLUMN status_filter TEXT DEFAULT '{default_filter_str}'")
                    logger.info("✅ Добавлена колонка status_filter")
                
                if 'notify_overdue' not in columns:
                    conn.execute("ALTER TABLE user_settings ADD COLUMN notify_overdue BOOLEAN DEFAULT 1")
                    logger.info("✅ Добавлена колонка notify_overdue")
                
                if 'notify_daily' not in columns:
                    conn.execute("ALTER TABLE user_settings ADD COLUMN notify_daily BOOLEAN DEFAULT 1")
                    logger.info("✅ Добавлена колонка notify_daily")
                
                if 'notify_work' not in columns:
                    conn.execute("ALTER TABLE user_settings ADD COLUMN notify_work BOOLEAN DEFAULT 0")
                    logger.info("✅ Добавлена колонка notify_work")
                
                if 'last_notification' not in columns:
                    conn.execute("ALTER TABLE user_settings ADD COLUMN last_notification TIMESTAMP")
                    logger.info("✅ Добавлена колонка last_notification")
                    
        except Exception as e:
            logger.error(f"⚠️ Ошибка при миграции базы данных: {e}")
    
    def mark_task_sent(self, task_id: str, user_id: int):
        """Отмечает задачу как отправленную"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sent_tasks (task_id, sent_date, user_id) VALUES (?, ?, ?)",
                (task_id, datetime.now(), user_id)
            )
    
    def get_sent_tasks(self, user_id: int, hours: int = 24) -> List[str]:
        """Получает список отправленных задач"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT task_id FROM sent_tasks WHERE user_id = ? AND sent_date > ?",
                (user_id, cutoff)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def get_user_settings(self, user_id: int) -> Dict:
        """Получает настройки пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("PRAGMA table_info(user_settings)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Формируем запрос в зависимости от наличия колонок
                select_cols = ["user_id", "notify_time", "timezone", "auto_motivation"]
                if 'status_filter' in columns:
                    select_cols.append("status_filter")
                if 'notify_overdue' in columns:
                    select_cols.append("notify_overdue")
                if 'notify_daily' in columns:
                    select_cols.append("notify_daily")
                if 'notify_work' in columns:
                    select_cols.append("notify_work")
                if 'last_notification' in columns:
                    select_cols.append("last_notification")
                
                query = f"SELECT {', '.join(select_cols)} FROM user_settings WHERE user_id = ?"
                cursor = conn.execute(query, (user_id,))
                row = cursor.fetchone()
                
                if row:
                    settings = {
                        "notify_time": row[1],
                        "timezone": row[2],
                        "auto_motivation": bool(row[3]),
                    }
                    
                    # Добавляем опциональные поля
                    idx = 4
                    if 'status_filter' in columns:
                        settings["status_filter"] = row[idx].split(',') if row[idx] else self.default_status_filter.copy()
                        idx += 1
                    else:
                        settings["status_filter"] = self.default_status_filter.copy()
                    
                    if 'notify_overdue' in columns:
                        settings["notify_overdue"] = bool(row[idx])
                        idx += 1
                    else:
                        settings["notify_overdue"] = True
                    
                    if 'notify_daily' in columns:
                        settings["notify_daily"] = bool(row[idx])
                        idx += 1
                    else:
                        settings["notify_daily"] = True
                    
                    if 'notify_work' in columns:
                        settings["notify_work"] = bool(row[idx])
                        idx += 1
                    else:
                        settings["notify_work"] = False
                    
                    if 'last_notification' in columns and row[idx]:
                        settings["last_notification"] = datetime.fromisoformat(row[idx])
                    else:
                        settings["last_notification"] = None
                    
                    return settings
        except Exception as e:
            logger.error(f"Ошибка при получении настроек: {e}")
        
        # Значения по умолчанию
        return {
            "notify_time": "09:00",
            "timezone": "Europe/Moscow",
            "auto_motivation": True,
            "status_filter": self.default_status_filter.copy(),
            "notify_overdue": True,
            "notify_daily": True,
            "notify_work": False,
            "last_notification": None
        }
    
    def update_user_settings(self, user_id: int, **kwargs):
        """Обновляет настройки пользователя"""
        settings = self.get_user_settings(user_id)
        settings.update(kwargs)
        
        with sqlite3.connect(self.db_path) as conn:
            # Проверяем наличие всех колонок
            cursor = conn.execute("PRAGMA table_info(user_settings)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Базовые поля
            base_cols = ["user_id", "notify_time", "timezone", "auto_motivation"]
            base_vals = [user_id, settings["notify_time"], settings["timezone"], settings["auto_motivation"]]
            
            # Дополнительные поля
            extra_cols = []
            extra_vals = []
            
            if 'status_filter' in columns:
                extra_cols.append("status_filter")
                extra_vals.append(','.join(settings["status_filter"]))
            
            if 'notify_overdue' in columns:
                extra_cols.append("notify_overdue")
                extra_vals.append(settings["notify_overdue"])
            
            if 'notify_daily' in columns:
                extra_cols.append("notify_daily")
                extra_vals.append(settings["notify_daily"])
            
            if 'notify_work' in columns:
                extra_cols.append("notify_work")
                extra_vals.append(settings["notify_work"])
            
            if 'last_notification' in columns and settings.get("last_notification"):
                extra_cols.append("last_notification")
                extra_vals.append(settings["last_notification"].isoformat())
            
            # Формируем запрос
            all_cols = base_cols + extra_cols
            placeholders = ','.join(['?' for _ in all_cols])
            update_sql = f"INSERT OR REPLACE INTO user_settings ({', '.join(all_cols)}) VALUES ({placeholders})"
            
            conn.execute(update_sql, base_vals + extra_vals)
    
    def save_notification(self, user_id: int, notif_type: str, tasks_count: int, message: str):
        """Сохраняет запись об отправленном уведомлении"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO notifications (user_id, type, sent_time, tasks_count, message) VALUES (?, ?, ?, ?, ?)",
                (user_id, notif_type, datetime.now(), tasks_count, message[:200])  # Ограничиваем длину сообщения
            )
    
    def get_last_notification_time(self, user_id: int, notif_type: str) -> Optional[datetime]:
        """Получает время последнего уведомления указанного типа"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT sent_time FROM notifications WHERE user_id = ? AND type = ? ORDER BY sent_time DESC LIMIT 1",
                (user_id, notif_type)
            )
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
            return None
