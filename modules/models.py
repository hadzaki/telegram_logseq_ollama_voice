from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class Task:
    """Класс для хранения информации о задаче с поддержкой Logseq формата"""
    id: str
    content: str
    deadline: Optional[datetime]
    priority: str
    file_path: str
    line_number: int
    completed: bool = False
    scheduled: Optional[datetime] = None  # Запланированная дата
    tags: List[str] = field(default_factory=list)  # Теги задачи
    status: Optional[str] = None  # TODO, DOING, DONE, NOW, LATER, WAITING
    parent_id: Optional[str] = None  # ID родительской задачи
    created_date: Optional[datetime] = None  # Дата создания задачи
    is_work: Optional[bool] = None  # Флаг, является ли задача рабочей
