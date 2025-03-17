from models import User, Expense, db

class UserRepository:
    def create(self, name, email):
        with db.atomic():
            return User.create(name=name, email=email)

    def get_by_id(self, user_id):
        return User.get_or_none(User.id == user_id)

    def get_expenses(self, user_id):
        user = self.get_by_id(user_id)
        return user.expenses if user else []

class ExpenseRepository:
    def create(self, expense_data, user):
        with db.atomic():
            return Expense.create(
                description=expense_data["description"],
                value=expense_data["value"],
                category=expense_data["category"],
                user=user
            )

    def get_by_user(self, user_id):
        return Expense.select().join(User).where(User.id == user_id)