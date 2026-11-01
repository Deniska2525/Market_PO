"""
Ручной запуск начального наполнения базы (факультеты, демо-карточки, демо-аккаунты).

При обычной работе через docker-compose делать это НЕ нужно: app/main.py вызывает тот же
код (app/university_seed.py) при каждом старте приложения, идемпотентно.

    python init_db.py
"""
import os
from app.database import SessionLocal
from app.university_seed import run

print("=" * 60)
print("РУЧНОЙ ЗАПУСК НАЧАЛЬНОГО НАПОЛНЕНИЯ БАЗЫ")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'не задана!')[:80]}...")
print("=" * 60)

db = SessionLocal()
try:
    run(db)
finally:
    db.close()

print("Готово.")
