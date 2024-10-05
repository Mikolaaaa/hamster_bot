import asyncpg
import asyncio

async def check_connection():
    DATABASE_URL = 'postgresql+asyncpg://postgres:1576@localhost:5432/tapalka'

    # Разделите строку на части
    parts = DATABASE_URL.split("://")
    scheme = parts[0]
    credentials, db_info = parts[1].split("@")
    user, password = credentials.split(":")
    host, port_db = db_info.split(":")
    port, database = port_db.split("/")  # Разделяем на порт и имя базы данных

    try:
        # Установка соединения
        conn = await asyncpg.connect(user=user, password=password,
                                      database=database, host=host, port=int(port))
        print("Подключение успешно!")
        await conn.close()
    except Exception as e:
        print(f"Ошибка подключения: {e}")

# Запуск асинхронной функции
asyncio.run(check_connection())
