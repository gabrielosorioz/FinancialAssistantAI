from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    expenses = relationship("Expense", back_populates="user")
    incomes = relationship("Income", back_populates="user")

class Expense(Base):
    __tablename__ = 'expense'

    id = Column(Integer, primary_key=True)
    description = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    installments = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship("User", back_populates="expenses")

class Income(Base):
    __tablename__ = 'income'

    id = Column(Integer, primary_key=True)
    description = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    source = Column(String(100), nullable=False)
    date = Column(DateTime, nullable=True)
    recurring = Column(Boolean, default=False)
    notes = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship("User", back_populates="incomes")