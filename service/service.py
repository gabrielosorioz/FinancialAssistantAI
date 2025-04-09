from datetime import datetime, timedelta
from models import Expense
from repository import ExpenseRepository, UserRepository
from agents.expense_extractor import ExpenseExtractorAgent
from typing import Optional, List
from models import User


class ExpenseService:
    """Serviço para operações relacionadas a despesas."""

    def __init__(self, expense_repository: ExpenseRepository, expense_extractor: ExpenseExtractorAgent = None):
        self.expense_repository = expense_repository
        self.expense_extractor = expense_extractor

    def create_expense(self, description: str, value: float, category: str, user_id: int, installments: int = None) -> Expense:
        expense = Expense(
            description=description,
            value=value,
            category=category,
            user_id=user_id,
            installments=installments
        )
        return self.expense_repository.create(expense)

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        return self.expense_repository.get_by_id(expense_id)

    def get_user_expenses(self, user_id: int) -> List[Expense]:
        return self.expense_repository.get_expenses_by_user(user_id)

    def get_expenses_by_category(self, user_id: int, category: str) -> List[Expense]:
        return self.expense_repository.get_expenses_by_category(user_id, category)

    def get_monthly_expenses(self, user_id: int, year: int, month: int) -> List[Expense]:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        return self.expense_repository.get_expenses_by_date_range(user_id, start_date, end_date)

    def get_installment_expenses(self, user_id: int) -> List[Expense]:
        return self.expense_repository.get_installment_expenses(user_id)

    def process_expense_message(self, user_id: int, message: str) -> List[Expense]:
        if self.expense_extractor is None:
            raise ValueError("Expense extractor agent is not configured")

        extracted_expenses = self.expense_extractor.process(message)

        saved_expenses = []
        for expense_data in extracted_expenses:
            expense = Expense(
                description=expense_data.description,
                value=expense_data.value,
                category=expense_data.category,
                user_id=user_id,
                installments=getattr(expense_data, 'installments', None)
            )
            saved_expense = self.expense_repository.create(expense)
            saved_expenses.append(saved_expense)

        return saved_expenses

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def create_user(self, name: str, email: str) -> User:
        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError(f"Usuário com email {email} já existe.")

        user = User(name=name, email=email)
        return self.user_repository.create(user)

    def get_user(self, user_id: int) -> Optional[User]:
        return self.user_repository.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.user_repository.get_by_email(email)

    def get_all_users(self) -> List[User]:
        return self.user_repository.get_all()

    def update_user(self, user_id: int, name: str = None, email: str = None) -> User:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"Usuário com ID {user_id} não encontrado.")

        if name:
            user.name = name
        if email:
            existing_user = self.user_repository.get_by_email(email)
            if existing_user and existing_user.id != user_id:
                raise ValueError(f"Email {email} já está em uso.")
            user.email = email

        return self.user_repository.update(user)

    def delete_user(self, user_id: int) -> bool:
        return self.user_repository.delete(user_id)