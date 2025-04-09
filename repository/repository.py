from abc import ABC
from typing import Generic, TypeVar, Type
from models import Base
from typing import List
from datetime import datetime
from sqlalchemy import func
from models import Expense
from typing import Optional
from sqlalchemy.orm import Session
from models import User

T = TypeVar('T', bound=Base)

class Repository(Generic[T], ABC):
    """Classe base para repositórios."""

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    def get_by_id(self, id: int) -> Optional[T]:
        return self.session.query(self.model_class).filter(self.model_class.id == id).first()

    def get_all(self) -> List[T]:
        return self.session.query(self.model_class).all()

    def create(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        self.session.merge(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, id: int) -> bool:
        entity = self.get_by_id(id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False

    def filter_by(self, **kwargs) -> List[T]:
        return self.session.query(self.model_class).filter_by(**kwargs).all()


class UserRepository(Repository[User]):

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()

class ExpenseRepository(Repository[Expense]):

    def __init__(self, session: Session):
        super().__init__(session, Expense)

    def get_expenses_by_user(self, user_id: int) -> List[Expense]:
        return self.session.query(Expense).filter(Expense.user_id == user_id).all()

    def get_expenses_by_category(self, user_id: int, category: str) -> List[Expense]:
        return self.session.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.category == category
        ).all()

    def get_expenses_by_date_range(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Expense]:
        return self.session.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.created_at >= start_date,
            Expense.created_at <= end_date
        ).all()

    def get_total_by_category(self, user_id: int) -> List[dict]:
        result = self.session.query(
            Expense.category,
            func.sum(Expense.value).label('total')
        ).filter(
            Expense.user_id == user_id
        ).group_by(
            Expense.category
        ).all()

        return [{"category": r.category, "total": r.total} for r in result]