import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from .models import Task

logger = logging.getLogger(__name__)

class LogseqTaskParser:
    """Парсер задач из файлов Logseq с поддержкой TODO формата и фильтрацией по дате"""
    
    # Все возможные статусы задач в Logseq
    ALL_STATUSES = ['TODO', 'DOING', 'DONE', 'NOW', 'LATER', 'WAITING', 'CANCELED']
    
    def __init__(self, logseq_path: str, max_months: int = 3):
        self.logseq_path = Path(logseq_path)
        self.journals_path = self.logseq_path / "journals"
        self.pages_path = self.logseq_path / "pages"
        self.max_months = max_months  # Максимальный возраст задачи в месяцах (0 = без фильтра)
        
        # Маппинг статусов и эмодзи
        self.status_emojis = {
            'TODO': '📝',
            'DOING': '⚡',
            'DONE': '✅',
            'NOW': '🔥',
            'LATER': '⏳',
            'WAITING': '⏸️',
            'CANCELED': '❌'
        }
        
    def parse_all_tasks(self, filter_by_date: bool = True, status_filter: Set[str] = None) -> List[Task]:
        """
        Парсит все задачи из всех файлов с опциональной фильтрацией по дате и статусам
        """
        tasks = []
        
        # Проверяем существование пути
        if not self.logseq_path.exists():
            logger.error(f"Путь не существует: {self.logseq_path}")
            return tasks
        
        # Парсим файлы журналов
        if self.journals_path.exists():
            for file_path in self.journals_path.glob("*.md"):
                if filter_by_date and self.max_months > 0 and not self._is_file_recent(file_path):
                    logger.debug(f"Пропускаем старый файл журнала: {file_path.name}")
                    continue
                tasks.extend(self._parse_file(file_path))
        
        # Парсим страницы
        if self.pages_path.exists():
            for file_path in self.pages_path.glob("*.md"):
                tasks.extend(self._parse_file(file_path))
        
        # Парсим файлы в корне
        for file_path in self.logseq_path.glob("*.md"):
            if file_path.name not in ['README.md', 'index.md']:
                tasks.extend(self._parse_file(file_path))
        
        # Фильтруем по дате
        if filter_by_date and self.max_months > 0:
            tasks = self._filter_tasks_by_date(tasks)
        
        # Фильтруем по статусам
        if status_filter is not None:
            tasks = [t for t in tasks if t.status in status_filter]
        
        logger.info(f"Всего найдено задач после фильтрации: {len(tasks)}")
        return tasks
    
    def _is_file_recent(self, file_path: Path) -> bool:
        """Проверяет, является ли файл журнала достаточно свежим"""
        try:
            filename = file_path.stem
            date_formats = ['%Y_%m_%d', '%Y-%m-%d', '%Y%m%d']
            
            file_date = None
            for date_format in date_formats:
                try:
                    file_date = datetime.strptime(filename, date_format)
                    break
                except ValueError:
                    continue
            
            if file_date is None:
                file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            cutoff_date = datetime.now() - timedelta(days=30 * self.max_months)
            return file_date > cutoff_date
            
        except Exception as e:
            logger.error(f"Ошибка при проверке даты файла {file_path}: {e}")
            return True
    
    def _filter_tasks_by_date(self, tasks: List[Task]) -> List[Task]:
        """Фильтрует задачи по дате создания"""
        cutoff_date = datetime.now() - timedelta(days=30 * self.max_months)
        filtered_tasks = []
        
        for task in tasks:
            if 'journals' in task.file_path:
                if task.created_date and task.created_date > cutoff_date:
                    filtered_tasks.append(task)
                elif task.deadline and task.deadline > cutoff_date:
                    filtered_tasks.append(task)
            else:
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    def _parse_file(self, file_path: Path) -> List[Task]:
        """Парсит один файл с поддержкой вложенных задач"""
        tasks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            task_stack = []  # (task, indent_level)
            
            for i, line in enumerate(lines):
                raw_line = line
                indent_level = len(raw_line) - len(raw_line.lstrip())
                
                task = self._parse_line(line, file_path, i + 1)
                
                if task:
                    while task_stack and task_stack[-1][1] >= indent_level:
                        task_stack.pop()
                    
                    if task_stack:
                        task.parent_id = task_stack[-1][0].id
                    
                    tasks.append(task)
                    task_stack.append((task, indent_level))
                    
        except Exception as e:
            logger.error(f"Ошибка при парсинге файла {file_path}: {e}")
            
        return tasks
    
    def _parse_line(self, line: str, file_path: Path, line_number: int) -> Optional[Task]:
        """Парсит одну строку и извлекает задачу в формате Logseq"""
        
        original_line = line
        line = line.strip()
        
        if not line or line.startswith('#'):
            return None
        
        status = None
        content = None
        completed = False
        
        # Паттерны для разных форматов Logseq
        patterns = [
            (r'^[-*]\s*(TODO|DOING|DONE|LATER|NOW|WAITING|CANCELED)\s+(.*)', True),
            (r'^[-*]\s*\[( |x|X|\.|>|✔|❌|✅|⬜)\]\s*(.*)', True),
            (r'^[-*]\s*(TODO|DOING|DONE)\s+\[([A-C])\]\s+(.*)', True),
            (r'^[-*]\s*(✔|❌|▶|⏸|✅|⬜|🔴|🟡|🟢)\s+(.*)', True),
            (r'^[-*]\s+([^#].*?)(?:\s+#\w+)*$', False)
        ]
        
        for pattern, has_status in patterns:
            match = re.search(pattern, line)
            if match:
                if has_status:
                    if len(match.groups()) == 2:
                        status = match.group(1)
                        content = match.group(2)
                    elif len(match.groups()) == 3:
                        status = match.group(1)
                        content = match.group(3)
                else:
                    content = match.group(1)
                break
        
        if not content:
            if re.search(r'#\w+', line) and line.startswith(('-', '*')):
                content = line.lstrip('-* ').strip()
            else:
                return None
        
        # Нормализуем статус
        if status:
            status_upper = status.upper()
            if status_upper in self.ALL_STATUSES:
                status = status_upper
        
        # Определяем выполненность
        if status:
            if status in ['DONE', 'CANCELED'] or status in ['✔', '✅', '❌']:
                completed = True
            elif status in ['TODO', 'LATER', 'WAITING'] or status in ['⬜']:
                completed = False
            elif status in ['DOING', 'NOW'] or status in ['▶']:
                completed = False
        else:
            completed = False
        
        deadline = self._extract_deadline(original_line)
        priority = self._extract_priority(original_line, status)
        scheduled = self._extract_scheduled(original_line)
        tags = self._extract_tags(original_line)
        created_date = self._extract_created_date(file_path, line_number)
        
        task_id = f"{file_path.stem}_{line_number}"
        content = content.strip()
        
        return Task(
            id=task_id,
            content=content,
            deadline=deadline,
            priority=priority,
            file_path=str(file_path),
            line_number=line_number,
            completed=completed,
            scheduled=scheduled,
            tags=tags,
            status=status,
            parent_id=None,
            created_date=created_date,
            is_work=None
        )
    
    def _extract_created_date(self, file_path: Path, line_number: int) -> Optional[datetime]:
        """Извлекает дату создания задачи"""
        if 'journals' in str(file_path):
            try:
                filename = file_path.stem
                date_formats = ['%Y_%m_%d', '%Y-%m-%d', '%Y%m%d']
                
                for date_format in date_formats:
                    try:
                        return datetime.strptime(filename, date_format)
                    except ValueError:
                        continue
            except Exception:
                pass
        
        try:
            return datetime.fromtimestamp(file_path.stat().st_mtime)
        except Exception:
            return None
    
    def _extract_deadline(self, line: str) -> Optional[datetime]:
        """Извлекает дедлайн"""
        deadline = None
        
        patterns = [
            r'DEADLINE:\s*<(\d{4}-\d{2}-\d{2})',
            r'deadline::\s*(\d{4}-\d{2}-\d{2})',
            r'due:\s*(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in patterns:
            deadline_match = re.search(pattern, line, re.IGNORECASE)
            if deadline_match:
                try:
                    deadline = datetime.strptime(deadline_match.group(1), '%Y-%m-%d')
                    return deadline
                except ValueError:
                    pass
        
        return None
    
    def _extract_scheduled(self, line: str) -> Optional[datetime]:
        """Извлекает запланированную дату"""
        scheduled = None
        
        patterns = [
            r'SCHEDULED:\s*<(\d{4}-\d{2}-\d{2})',
            r'scheduled::\s*(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in patterns:
            scheduled_match = re.search(pattern, line, re.IGNORECASE)
            if scheduled_match:
                try:
                    scheduled = datetime.strptime(scheduled_match.group(1), '%Y-%m-%d')
                except ValueError:
                    pass
        
        return scheduled
    
    def _extract_priority(self, line: str, status: Optional[str]) -> str:
        """Извлекает приоритет"""
        
        # Приоритет в квадратных скобках [A]
        priority_match = re.search(r'\[([A-Ca-c])\]', line)
        if priority_match:
            priority_map = {'A': 'высокий', 'B': 'средний', 'C': 'обычный',
                           'a': 'высокий', 'b': 'средний', 'c': 'обычный'}
            return priority_map.get(priority_match.group(1), 'обычный')
        
        # Приоритет PRIORITY: высокий
        priority_match = re.search(r'PRIORITY:\s*(\w+)', line, re.IGNORECASE)
        if priority_match:
            priority = priority_match.group(1).lower()
            if priority in ['высокий', 'средний', 'обычный', 'high', 'medium', 'low']:
                priority_map = {'high': 'высокий', 'medium': 'средний', 'low': 'обычный'}
                return priority_map.get(priority, priority)
        
        return 'обычный'
    
    def _extract_tags(self, line: str) -> List[str]:
        """Извлекает теги"""
        tags = []
        
        # Теги в формате #тег
        tag_matches = re.findall(r'#(\w+)', line)
        tags.extend(tag_matches)
        
        # Теги в формате :тег:
        tag_matches = re.findall(r':(\w+):', line)
        tags.extend(tag_matches)
        
        return tags
