from typing import Optional
from pydantic import BaseModel # type: ignore

class UserBase(BaseModel):
    name : str
    email : str

class UserCreate(UserBase):
    password : str

class User(UserBase):
    id : int
    score : Optional[int] = 0
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class UserScore(BaseModel):
    name: str
    score: int = 0