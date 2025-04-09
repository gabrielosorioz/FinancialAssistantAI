
from typing import Optional
from sqlalchemy.orm import Session
from models import User
from .repository import Repository

class UserRepository(Repository[User]):

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter(User.email == email).first()
