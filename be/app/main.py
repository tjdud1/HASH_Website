import os
import re
import time
from fastapi import FastAPI, Depends, HTTPException, Request, Response # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from sqlalchemy.orm import Session # type: ignore
from typing import List
from be.app.schemas import User, UserCreate, UserLogin, UserScore
from be.app import models, database, crud  # 절대 경로로 임포트
from be.app.database import init_db
from passlib.context import CryptContext # type: ignore
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv
from be.app.database import init_db
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "default_unsafe_secret") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# 로그인 시도 제한 (IP 기반)
FAILED_LOGIN_ATTEMPTS = {}
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_BLOCK_TIME = 300  # 5분

# 비밀번호 해싱을 위한 CryptContext 설정 (bcrypt 사용)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 시에는 특정 도메인을 입력하는 것이 안전합니다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="front"), name="static")

database.Base.metadata.create_all(bind=database.engine)



def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 애플리케이션 시작 시 DB 초기화
@app.on_event("startup")
def startup():
    init_db()



def validate_email(email: str):
    """ 이메일 형식 검증 (간단한 정규식 사용) """
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, email):
        raise HTTPException(status_code=400, detail="Invalid email format!")



def validate_password(password: str):
    """ 보안 강화를 위한 비밀번호 정책 (최소 8자, 대/소문자, 숫자, 특수문자 포함) """
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long!")
    
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter!")
    
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter!")
    
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit!")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character!")


def create_access_token(data: dict, expires_delta: timedelta = None):
    """ JWT 토큰 생성 (발급 시간, 활성화 시간 포함) """
    to_encode = data.copy()
    now = datetime.utcnow()
    to_encode.update({"iat": now, "nbf": now})

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)



#회원가입 엔드포인트
@app.post("/signup", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    validate_email(user.email)
    validate_password(user.password)

    if not (6 <= len(user.name) <= 20):
        raise HTTPException(status_code=400, detail="Id(name) must be 6-20 characters long!")
    
    existing_email = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists!")
    
    existing_name = db.query(models.User).filter(models.User.name == user.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Username already exists!")
    
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password, name=user.name)
    try:
        db.add(db_user)
        db.commit()  
        db.refresh(db_user)
        return JSONResponse(
            content={
                "message": "Signup successful!",
                "name": db_user.name,
                "email": db_user.email,
                #"redirect_url": "/static/login.html"
            },
            status_code=201
        )
    except Exception as e:
        db.rollback()  
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

#사용자 조회 엔드포인트(user_id로 조회)
@app.get("/users/{user_id}", response_model=User)
def read_user(user_id:int,  db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail = "user not found")
    return user

# 전체 사용자 목록 조회 엔드포인트 (모든 사용자의 id 포함)
@app.get("/users", response_model=List[str])
def read_users(db: Session = Depends(get_db)):
    users = db.query(models.User.name).all()
    return [u[0] for u in users]

 
@app.post("/login")
def login(request: Request, user_credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host

    # 로그인 시도 차단 확인
    if client_ip in FAILED_LOGIN_ATTEMPTS and FAILED_LOGIN_ATTEMPTS[client_ip]["attempts"] >= LOGIN_ATTEMPT_LIMIT:
        block_time = FAILED_LOGIN_ATTEMPTS[client_ip]["time"]
        if time.time() - block_time < LOGIN_BLOCK_TIME:
            raise HTTPException(status_code=403, detail="Too many failed attempts! Try again later.")
        else:
            # 차단 시간 지나면 초기화
            FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)

    db_user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not db_user or not pwd_context.verify(user_credentials.password, db_user.hashed_password):
        if client_ip not in FAILED_LOGIN_ATTEMPTS:
            FAILED_LOGIN_ATTEMPTS[client_ip] = {"attempts": 1, "time": time.time()}
        else:
            FAILED_LOGIN_ATTEMPTS[client_ip]["attempts"] += 1
            FAILED_LOGIN_ATTEMPTS[client_ip]["time"] = time.time()
        
        raise HTTPException(status_code=400, detail="Incorrect email or password!")

    # 로그인 성공 시 IP 차단 해제
    if client_ip in FAILED_LOGIN_ATTEMPTS:
        FAILED_LOGIN_ATTEMPTS.pop(client_ip, None)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": db_user.email}, expires_delta=access_token_expires)
    response.set_cookie(
        key="access_token", value=f"Bearer {token}", httponly=True, secure=False, samesite="Lax"
    )
    db.commit()
    return {"message": "Login successful"}


#로그인 상태 확인 API
@app.get("/hash")
def get_user_from_token(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token.split("Bearer ")[1], SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        user = db.query(models.User).filter(models.User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"name": user.name}


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}

@app.get("/scores", response_model=List[UserScore])
def get_scores(db: Session=Depends(get_db)):
    #score 내림차순하여 사용자별로 score 반환
    users = db.query(models.User).order_by(models.User.score.desc()).all()
    return [{"name": user.name, "score": user.score or 0} for user in users]
