from sqlalchemy import Column, Integer, String, text # type: ignore
from be.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index= True)
    name = Column(String, index=True)
    email = Column(String, unique = True, index = True)
    hashed_password =Column(String)
    score = Column(Integer, nullable=False, server_default=text("0"))