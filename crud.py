from sqlalchemy.orm import Session
from passlib.context import CryptConetxt
from . import models, schemas

pwd_context = CryptConetxt(schemes=["bycrypt"], deprecated = "auto")
def get_user(db:Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db:Session, email:str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(name = user.name, email = user.email, hashed_password = hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user