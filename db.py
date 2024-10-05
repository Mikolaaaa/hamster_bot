from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

# Замените строку подключения на свою
DATABASE_URL = 'postgresql+asyncpg://postgres:1576@localhost:5432/tapalka'

# Создание асинхронного двигателя
engine = create_async_engine(DATABASE_URL, echo=True)

# Создание сессии без параметра future
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    coins = Column(Integer, default=0)
    hamster_level = Column(Integer, default=1)  # Уровень хомяка
    multiplier_level = Column(Integer, default=1)  # Уровень множителя
    passive_income = Column(Integer, default=0)  # Пассивный доход
    passive_income_level = Column(Integer, default=1)  # Уровень пассивного дохода

async def init_db():
    async with engine.begin() as conn:
        # Создаем таблицы, если их нет
        await conn.run_sync(Base.metadata.create_all)

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()  # Возвращает единственный результат или None

async def add_user(db: AsyncSession, user_id: int):
    user = User(id=user_id)
    db.add(user)
    await db.commit()  # Не забывайте ожидать commit

async def update_coins(db: AsyncSession, user_id: int, coins: int):
    user = await get_user(db, user_id)
    if user:
        user.coins = coins
        await db.commit()  # Не забывайте ожидать commit

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session  # Верните сессию для использования
