from typing import List
from datetime import datetime
from sqlalchemy import func
from models import Expense
from sqlalchemy.orm import Session
from .repository import Repository

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
