from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Импортируйте вашу модель
from db import Base

# Этот URL должен быть таким же, как и в вашем alembic.ini
DATABASE_URL = "sqlite+aiosqlite:///./database.db"

# Создание асинхронного двигателя
engine = create_async_engine(DATABASE_URL, echo=True)

def run_migrations_online():
    # Этот контекст позволяет Alembic управлять асинхронной миграцией
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            compare_type=True,  # Чтобы сравнивать типы
        )

        with context.begin_transaction():
            context.run_migrations()

if __name__ == "__main__":
    run_migrations_online()
