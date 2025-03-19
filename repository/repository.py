import logging
from models import User, Expense, db

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class UserRepository:
    def create(self, name, email):
        try:
            with db.atomic():
                user = User.create(name=name, email=email)
                logging.info(f"Usuário criado: {user.id} - {name} ({email})")
                return user
        except Exception as e:
            logging.error(f"Erro ao criar usuário: {e}")
            return None

    def get_by_id(self, user_id):
        try:
            user = User.get_or_none(User.id == user_id)
            if user:
                logging.info(f"Usuário encontrado: {user.id} - {user.name}")
            else:
                logging.warning(f"Usuário não encontrado: {user_id}")
            return user
        except Exception as e:
            logging.error(f"Erro ao buscar usuário {user_id}: {e}")
            return None

    def get_expenses(self, user_id):
        try:
            user = self.get_by_id(user_id)
            if user:
                logging.info(f"Recuperando despesas do usuário {user_id}")
                return user.expenses
            return []
        except Exception as e:
            logging.error(f"Erro ao buscar despesas do usuário {user_id}: {e}")
            return []

class ExpenseRepository:

    def create(self, expense, user):
        try:
            with db.atomic():
                expense = (
                    Expense.from_dict(expense, user)
                    if isinstance(expense, dict)
                    else expense
                )

                expense.save()
                logging.info(f"Despesa criada: {expense.id} - {expense.description} ({expense.value})")
                return expense
        except Exception as e:
            logging.error(f"Erro ao criar despesa: {e}")
            return None

    def get_by_user(self, user_id):
        try:
            expenses = Expense.select().join(User).where(User.id == user_id)
            logging.info(f"Despesas recuperadas para o usuário {user_id}: {expenses.count()} encontradas")
            return expenses
        except Exception as e:
            logging.error(f"Erro ao buscar despesas do usuário {user_id}: {e}")
            return []
