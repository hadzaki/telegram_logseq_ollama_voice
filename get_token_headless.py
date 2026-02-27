#!/usr/bin/env python3
import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Создаем поток с явным указанием порта
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', 
    SCOPES
)

# Запускаем локальный сервер без автоматического открытия браузера
creds = flow.run_local_server(
    port=0,  # Автоматический выбор порта
    open_browser=False  # Не открывать браузер автоматически
)

# Сохраняем токен
with open('token.pickle', 'wb') as token:
    pickle.dump(creds, token)

print("\n" + "="*60)
print("✅ token.pickle успешно создан!")
print("📁 Файл сохранен в:", os.path.abspath('token.pickle'))
print("="*60)
print("\n🔗 Теперь вы можете использовать команду /calendar в боте")
