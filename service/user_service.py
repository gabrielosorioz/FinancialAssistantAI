from repository import UserRepository
from typing import Optional, List
from models import User


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