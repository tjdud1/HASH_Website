from sqlalchemy import create_engine # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base # type: ignore
import be.app.models
import os
from dotenv import load_dotenv

load_dotenv()


# 환경 변수 또는 기본 설정 값 사용
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://defaultuser:defaultpassword@localhost/defaultdb")

engine = create_engine(DATABASE_URL, echo = True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind = engine)

Base = declarative_base()

# 테이블 생성 함수 추가
def init_db():
    print("[INFO] Creating database tables if not exist...")
    Base.metadata.drop_all(bind=engine) #,기존 테이블 삭제
    Base.metadata.create_all(bind=engine) #새로운 테이블 생성
    print("[INFO] Database initialized successfully.")
