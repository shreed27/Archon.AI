from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    tokens_used = Column(Integer, default=0)
    requests_today = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, index=True)
    role = Column(String)  # user, assistant, system
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
