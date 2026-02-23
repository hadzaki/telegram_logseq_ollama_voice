import os
import re
import tempfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import which

from .models import Task

logger = logging.getLogger(__name__)

# Глобальная проверка ffmpeg при импорте
ffmpeg_path = which("ffmpeg")
if ffmpeg_path:
    AudioSegment.converter = ffmpeg_path
    logger.info(f"✅ ffmpeg найден: {ffmpeg_path}")
else:
    logger.error("❌ ffmpeg не найден! Голосовые сообщения не будут работать.")
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if os.path.exists(path):
            AudioSegment.converter = path
            logger.info(f"✅ ffmpeg найден по пути: {path}")
            break

class VoiceTaskCreator:
    """Класс для создания задач из голосовых сообщений"""
    
    def __init__(self, logseq_path: str, default_page: str = "Inbox", 
                 default_status: str = "TODO", classifier=None):
        self.logseq_path = Path(logseq_path)
        self.pages_path = self.logseq_path / "pages"
        self.journals_path = self.logseq_path / "journals"
        self.default_page = default_page
        self.default_status = default_status
        self.classifier = classifier
        
        # Создаём папки если их нет
        self.pages_path.mkdir(exist_ok=True)
        self.journals_path.mkdir(exist_ok=True)
        
        # Инициализация распознавателя
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5
        
        logger.info(f"🎤 VoiceTaskCreator инициализирован. Журналы: {self.journals_path}, Страницы: {self.pages_path}")
    
    def _get_daily_journal_path(self) -> Path:
        """
        Возвращает путь к файлу ежедневного журнала в формате ГГГГ_ММ_ДД.md
        """
        today = datetime.now()
        filename = today.strftime("%Y_%m_%d") + ".md"
        return self.journals_path / filename
    
    async def process_voice(self, file_path: str) -> Optional[str]:
        """Обрабатывает голосовой файл и возвращает распознанный текст"""
        logger.info("=" * 60)
        logger.info("🎤 НАЧАЛО ОБРАБОТКИ ГОЛОСОВОГО ФАЙЛА")
        logger.info(f"Файл: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл не существует: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        logger.info(f"Размер файла: {file_size} байт")
        
        if not AudioSegment.converter:
            logger.error("❌ ffmpeg не настроен!")
            return None
        
        wav_path = None
        try:
            # Конвертация OGG → WAV
            logger.info("🔄 Конвертация OGG в WAV...")
            audio = AudioSegment.from_ogg(file_path)
            logger.info(f"   → Длительность: {len(audio)/1000:.1f}с, каналы: {audio.channels}, частота: {audio.frame_rate}Гц")
            
            # Приводим к оптимальному формату
            if audio.channels > 1:
                audio = audio.set_channels(1)
                logger.info("   → Приведено к моно")
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
                logger.info("   → Частота дискретизации установлена на 16000 Гц")
            
            # Нормализация громкости
            if audio.dBFS < -30:
                gain = min(30, abs(audio.dBFS) - 20)
                audio = audio.apply_gain(gain)
                logger.info(f"   → Применено усиление {gain:.1f} дБ")
            
            # Создаём временный WAV-файл
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                wav_path = tmp_wav.name
            
            # Экспортируем
            audio.export(
                wav_path,
                format="wav",
                parameters=[
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1"
                ]
            )
            logger.info(f"✅ WAV файл создан: {wav_path}")
            
            # Распознавание речи
            logger.info("🔍 Распознавание речи...")
            with sr.AudioFile(wav_path) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = self.recognizer.record(source)
                
                # Пробуем русский
                try:
                    text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                    logger.info(f"✅ Распознано (русский): {text}")
                    return text
                except sr.UnknownValueError:
                    logger.warning("⚠️ Не удалось распознать на русском, пробуем английский...")
                except sr.RequestError as e:
                    logger.error(f"❌ Ошибка сервиса Google (русский): {e}")
                
                # Пробуем английский
                try:
                    text = self.recognizer.recognize_google(audio_data, language="en-US")
                    logger.info(f"✅ Распознано (английский): {text}")
                    return text
                except sr.UnknownValueError:
                    logger.error("❌ Не удалось распознать речь ни на одном языке")
                    return None
                except sr.RequestError as e:
                    logger.error(f"❌ Ошибка сервиса Google (английский): {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке голоса: {e}", exc_info=True)
            return None
        finally:
            # Удаляем временные файлы
            if wav_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                    logger.info(f"🧹 Удалён временный WAV: {wav_path}")
                except Exception as e:
                    logger.error(f"Ошибка удаления WAV: {e}")
            
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"🧹 Удалён исходный OGG: {file_path}")
                except Exception as e:
                    logger.error(f"Ошибка удаления OGG: {e}")
            
            logger.info("=" * 60)
    
    def _parse_date_from_text(self, text: str) -> Optional[datetime]:
        """Извлекает дату из текста голосового сообщения с поддержкой месяцев словами"""
        text_lower = text.lower()
        today = datetime.now()
        
        # 1. Проверка на "завтра", "послезавтра", "сегодня"
        if "послезавтра" in text_lower:
            logger.info("Распознано: послезавтра")
            return today + timedelta(days=2)
        elif "завтра" in text_lower:
            logger.info("Распознано: завтра")
            return today + timedelta(days=1)
        elif "сегодня" in text_lower:
            logger.info("Распознано: сегодня")
            return today
        
        # 2. Проверка дней недели
        days_map = {
            "понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3,
            "пятница": 4, "суббота": 5, "воскресенье": 6,
            "пн": 0, "вт": 1, "ср": 2, "чт": 3, "пт": 4, "сб": 5, "вс": 6
        }
        for day_name, day_num in days_map.items():
            if day_name in text_lower:
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                logger.info(f"Распознан день недели: {day_name} -> через {days_ahead} дней")
                return today + timedelta(days=days_ahead)
        
        # 3. Распознавание месяцев словами (январь, февраль, март и т.д.)
        months_map = {
            "январь": 1, "января": 1, "янв": 1,
            "февраль": 2, "февраля": 2, "фев": 2,
            "март": 3, "марта": 3,
            "апрель": 4, "апреля": 4, "апр": 4,
            "май": 5, "мая": 5,
            "июнь": 6, "июня": 6,
            "июль": 7, "июля": 7,
            "август": 8, "августа": 8, "авг": 8,
            "сентябрь": 9, "сентября": 9, "сен": 9,
            "октябрь": 10, "октября": 10, "окт": 10,
            "ноябрь": 11, "ноября": 11, "ноя": 11,
            "декабрь": 12, "декабря": 12, "дек": 12
        }
        
        # Поиск паттерна "число + месяц" (например "15 февраля", "3 марта")
        for month_name, month_num in months_map.items():
            # Паттерн: число + месяц
            pattern = r'(\d{1,2})\s*' + re.escape(month_name)
            match = re.search(pattern, text_lower)
            if match:
                try:
                    day = int(match.group(1))
                    year = today.year
                    
                    # Проверяем корректность дня для данного месяца
                    try:
                        date = datetime(year, month_num, day)
                        if date < today:
                            date = date.replace(year=year + 1)
                        logger.info(f"Распознана дата: {day} {month_name} -> {date.strftime('%d.%m.%Y')}")
                        return date
                    except ValueError:
                        logger.warning(f"Некорректная дата: {day}.{month_num}.{year}")
                        continue
                except ValueError as e:
                    logger.error(f"Ошибка при создании даты: {e}")
                    continue
        
        # 4. Поиск паттерна "месяц + число" (например "марта 15", "февраля 3")
        for month_name, month_num in months_map.items():
            pattern = re.escape(month_name) + r'\s*(\d{1,2})'
            match = re.search(pattern, text_lower)
            if match:
                try:
                    day = int(match.group(1))
                    year = today.year
                    
                    try:
                        date = datetime(year, month_num, day)
                        if date < today:
                            date = date.replace(year=year + 1)
                        logger.info(f"Распознана дата: {month_name} {day} -> {date.strftime('%d.%m.%Y')}")
                        return date
                    except ValueError:
                        logger.warning(f"Некорректная дата: {day}.{month_num}.{year}")
                        continue
                except ValueError as e:
                    logger.error(f"Ошибка при создании даты: {e}")
                    continue
        
        # 5. Проверка даты в формате ДД.ММ.ГГГГ или ДД-ММ-ГГГГ
        date_match = re.search(r'(\d{1,2})[\.\-](\d{1,2})[\.\-](\d{4})', text)
        if date_match:
            try:
                day, month, year = map(int, date_match.groups())
                logger.info(f"Распознана дата в формате ДД.ММ.ГГГГ: {day}.{month}.{year}")
                return datetime(year, month, day)
            except ValueError as e:
                logger.error(f"Ошибка парсинга даты: {e}")
        
        # 6. Проверка даты в формате ДД.ММ (без года)
        date_match = re.search(r'(\d{1,2})[\.\-](\d{1,2})', text)
        if date_match:
            try:
                day, month = map(int, date_match.groups())
                year = today.year
                date = datetime(year, month, day)
                if date < today:
                    date = date.replace(year=year + 1)
                logger.info(f"Распознана дата в формате ДД.ММ: {day}.{month} -> {date.strftime('%d.%m.%Y')}")
                return date
            except ValueError as e:
                logger.error(f"Ошибка парсинга даты: {e}")
        
        return None
    
    def _extract_priority(self, text: str) -> str:
        """Определяет приоритет из текста"""
        text_lower = text.lower()
        high_words = ["срочно", "важно", "очень", "критично", "немедленно", "быстро", "срочное"]
        low_words = ["потом", "не срочно", "можно позже", "не важно", "когда-нибудь", "если будет время"]
        
        if any(word in text_lower for word in high_words):
            logger.info(f"Распознан высокий приоритет")
            return "высокий"
        if any(word in text_lower for word in low_words):
            logger.info(f"Распознан низкий приоритет")
            return "низкий"
        
        return "обычный"
    
    async def _extract_tags_async(self, text: str) -> List[str]:
        """Асинхронно извлекает теги из текста с использованием классификатора"""
        tags = []
        text_lower = text.lower()
        
        # Определяем категорию через классификатор
        if self.classifier:
            # Создаем временную задачу для классификации
            temp_task = Task(
                id=f"temp_{datetime.now().timestamp()}",
                content=text,
                deadline=None,
                priority="обычный",
                file_path="",
                line_number=0,
                tags=[]
            )
            
            # Спрашиваем Ollama, рабочая это задача или личная
            try:
                is_work = await self.classifier.is_work_task(temp_task)
                if is_work:
                    tags.append("работа")
                    logger.info(f"Задача классифицирована как рабочая: {text}")
                else:
                    tags.append("личное")
                    logger.info(f"Задача классифицирована как личная: {text}")
            except Exception as e:
                logger.error(f"Ошибка при классификации: {e}")
        
        # Добавляем теги по ключевым словам
        if any(word in text_lower for word in ["проект", "работа", "клиент", "бизнес", "задача", "дедлайн", "отчет"]):
            tags.append("проект")
        if any(word in text_lower for word in ["дом", "семья", "личное", "быт", "дома", "родные", "дети"]):
            tags.append("дом")
        if any(word in text_lower for word in ["здоровье", "спорт", "тренировка", "врач", "больница", "фитнес", "зарядка"]):
            tags.append("здоровье")
        if any(word in text_lower for word in ["купить", "магазин", "продукты", "покупка", "шопинг", "супермаркет"]):
            tags.append("покупки")
        if any(word in text_lower for word in ["встреча", "позвонить", "написать", "созвон", "переговоры"]):
            tags.append("коммуникация")
        
        return list(set(tags))  # Убираем дубликаты
    
    def _extract_tags_sync(self, text: str) -> List[str]:
        """Синхронное извлечение тегов (для случаев без классификатора)"""
        tags = []
        text_lower = text.lower()
        
        # Добавляем теги по ключевым словам
        if any(word in text_lower for word in ["проект", "работа", "клиент", "бизнес", "задача", "дедлайн", "отчет"]):
            tags.append("проект")
        if any(word in text_lower for word in ["дом", "семья", "личное", "быт", "дома", "родные", "дети"]):
            tags.append("дом")
        if any(word in text_lower for word in ["здоровье", "спорт", "тренировка", "врач", "больница", "фитнес", "зарядка"]):
            tags.append("здоровье")
        if any(word in text_lower for word in ["купить", "магазин", "продукты", "покупка", "шопинг", "супермаркет"]):
            tags.append("покупки")
        if any(word in text_lower for word in ["встреча", "позвонить", "написать", "созвон", "переговоры"]):
            tags.append("коммуникация")
        
        return list(set(tags))
    
    async def create_task_from_text_async(self, text: str, source: str = "voice") -> str:
        """Создаёт задачу в Logseq из текста"""
        logger.info(f"📝 Создание задачи из текста: {text}")
        
        # Определяем дату
        deadline = self._parse_date_from_text(text)
        if deadline:
            logger.info(f"📅 Извлечена дата дедлайна: {deadline.strftime('%Y-%m-%d')}")
        
        # Определяем приоритет
        priority = self._extract_priority(text)
        if priority != "обычный":
            logger.info(f"⚡ Извлечен приоритет: {priority}")
        
        # Асинхронно извлекаем теги
        if self.classifier:
            tags = await self._extract_tags_async(text)
        else:
            tags = self._extract_tags_sync(text)
        
        if tags:
            logger.info(f"🏷️ Извлечены теги: {tags}")
        
        # Формируем строку задачи в формате Logseq
        task_line = f"- DOING {text}"
        
        # Добавляем дедлайн если есть
        if deadline:
            deadline_str = deadline.strftime("%Y-%m-%d")
            task_line += f" DEADLINE: <{deadline_str}>"
        
        # Добавляем приоритет если не обычный
        if priority != "обычный":
            priority_map = {"высокий": "A", "низкий": "C"}
            priority_letter = priority_map.get(priority, "B")
            task_line += f" PRIORITY: {priority_letter}"
        
        # Добавляем теги
        if tags:
            for tag in tags:
                task_line += f" #{tag}"
        
        # Добавляем источник
        if source == "voice":
            task_line += " #голосовое"
        else:
            task_line += " #текстовое"
        
        # Получаем путь к файлу ежедневного журнала
        journal_file = self._get_daily_journal_path()
        logger.info(f"💾 Сохранение задачи в файл: {journal_file}")
        
        # Если файл не существует, создаём с заголовком
        if not journal_file.exists():
            today_str = datetime.now().strftime("%Y-%m-%d")
            with open(journal_file, "w", encoding="utf-8") as f:
                f.write(f"# {today_str}\n\n")
            logger.info(f"📄 Создан новый файл журнала: {journal_file}")
        
        # Добавляем задачу в файл
        with open(journal_file, "a", encoding="utf-8") as f:
            f.write(f"{task_line}\n")
        
        logger.info(f"✅ Задача успешно записана: {task_line}")
        return str(journal_file)
    
    async def create_task_from_voice_async(self, file_path: str) -> Tuple[bool, str]:
        """Основной метод создания задачи из голоса"""
        logger.info("=" * 60)
        logger.info("🎤 НАЧАЛО create_task_from_voice_async")
        
        # Распознаем речь
        text = await self.process_voice(file_path)
        
        if not text:
            logger.error("❌ НЕ УДАЛОСЬ РАСПОЗНАТЬ РЕЧЬ")
            logger.info("=" * 60)
            return False, "❌ Не удалось распознать речь. Попробуйте говорить чётче или отправьте текстом."
        
        logger.info(f"✅ РАСПОЗНАННЫЙ ТЕКСТ: {text}")
        
        # Создаем задачу
        try:
            journal_file = await self.create_task_from_text_async(text, source="voice")
            filename = Path(journal_file).name
            logger.info(f"✅ ЗАДАЧА УСПЕШНО СОЗДАНА В ФАЙЛЕ: {filename}")
            logger.info("=" * 60)
            
            return True, f"✅ Задача создана!\n\n📝 Текст: {text}\n📄 Файл: {filename}\n📌 Статус: DOING"
        except Exception as e:
            logger.error(f"❌ ОШИБКА ПРИ СОЗДАНИИ ЗАДАЧИ: {e}", exc_info=True)
            logger.info("=" * 60)
            return False, f"❌ Ошибка при создании задачи: {str(e)}"
