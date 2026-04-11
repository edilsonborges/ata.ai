from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="member")
    created_at: datetime = Field(default_factory=datetime.utcnow)
