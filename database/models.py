from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(100))
    username = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

    # Паспортные данные
    nickname = Column(String(50))
    rank = Column(String(50))
    town = Column(String(50))
    awards = Column(JSON, default=list)

    # Медицинская карта
    durdom = Column(Integer, default=0)
    approve_work = Column(Integer, default=1)

    # Новости
    news_svo = Column(Boolean, default=False)
    news_zhizhn = Column(Boolean, default=False)

    # Дополнительные поля
    is_made = Column(Boolean, default=True)
    chudjo = Column(Integer, default=0)