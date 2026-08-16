from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    pass


def generate_short_id():
    return uuid.uuid4().hex[:8]


class Poll(Base):
    __tablename__ = 'polls'

    id = Column(String(16), primary_key=True, default=generate_short_id)
    question = Column(String(300), nullable=False)
    allow_multiple = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    options = relationship('PollOption', back_populates='poll', cascade='all, delete-orphan')


class PollOption(Base):
    __tablename__ = 'poll_options'

    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(String(16), ForeignKey('polls.id'), nullable=False)
    text = Column(String(200), nullable=False)
    vote_count = Column(Integer, default=0)

    poll = relationship('Poll', back_populates='options')
