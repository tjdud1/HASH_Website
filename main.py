from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from schemas import User, UserCreate, UserLogin
import models, database
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "hash2024!!"  # 반드시 안전한 값으로 변경하세요.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    data: 토큰에 포함할 데이터(예: {"sub": user_email})
    expires_delta: 토큰 만료 시간 (timedelta)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 비밀번호 해싱을 위한 CryptContext 설정 (bcrypt 사용)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

database.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

#회원가입 엔드포인트
@app.post("/users/", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_email = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="already exist email!")
    
    existing_name = db.query(models.User).filter(models.User.name == user.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail = "alreasy exist name!")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email, 
        hashed_password = hashed_password,
        name = user.name 
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

#사용자 조회 엔드포인트(user_id로 조회)
@app.get("/users/{user_id}", response_model=User)
def read_user(user_id:int,  db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail = "user not found")
    return user

# 전체 사용자 목록 조회 엔드포인트 (모든 사용자의 id 포함)
@app.get("/users/", response_model=List[User])
def read_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users

@app.post("/login")
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not db_user:
        raise HTTPException(status_code =400, detail = "Incorrect email or pw")
    if not pwd_context.verify(user_credentials.password , db_user.hashed_password):
        raise HTTPException(status_code =400, detail = "Incorrect email or pw")
    
    # 토큰 생성 (사용자 이메일을 sub로 사용)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": token, "token_type": "bearer"}    

@app.get("/scores", response_model=List[User])
def get_scores(db: Session=Depends(get_db)):
    #score 내림차순하여 사용자별로 score 반환
    users = db.query(models.User).order_by(models.User.score.desc()).all()
    return users