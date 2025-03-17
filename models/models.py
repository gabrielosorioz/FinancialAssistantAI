from peewee import *
from datetime import datetime

db = SqliteDatabase('financial_assistant.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(max_length=100)
    email = CharField(max_length=100, unique=True)
    created_at = DateTimeField(default=datetime.now)

    def __repr__(self):
        return f"User(id={self.id}, name='{self.name}', email='{self.email}')"

class Expense(BaseModel):
    id = AutoField(primary_key=True)
    description = CharField(max_length=255)
    value = FloatField()
    category = CharField(max_length=100)
    created_at = DateTimeField(default=datetime.now)
    user = ForeignKeyField(User, backref='expenses')

    def __repr__(self):
        return f"Expense(id={self.id}, description='{self.description}', value={self.value}, category='{self.category}')"

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "value": self.value,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id
        }

    @classmethod
    def from_dict(cls, data, user):
        return cls(
            description=data["description"],
            value=data["value"],
            category=data["category"],
            user=user
        )

db.create_tables([User, Expense], safe=True)