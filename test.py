import asyncio
import os
from modules.voice_creator import VoiceTaskCreator

async def test():
    # Укажите реальный путь к вашему Logseq
    creator = VoiceTaskCreator(logseq_path="/путь/к/logseq")
    
    # Укажите путь к тестовому голосовому файлу .ogg
    test_file = "test.ogg"  # положите любой .ogg файл рядом
    
    if not os.path.exists(test_file):
        print(f"Файл {test_file} не найден")
        return
    
    success, message = await creator.create_task_from_voice_async(test_file)
    print(f"Результат: {success}")
    print(f"Сообщение: {message}")

if __name__ == "__main__":
    asyncio.run(test())
