from abc import ABC
from typing import Generic, TypeVar, Type
from models import Base
from typing import List
from typing import Optional
from sqlalchemy.orm import Session

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

