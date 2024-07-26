# user_service/main.py
from operator import or_
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2
from pydantic import BaseModel
from sqlmodel import SQLModel, Session, create_engine, Field
from kafka import KafkaProducer
from user import settings
from typing import Optional
from sqlalchemy import or_
import os

# FastAPI app
app = FastAPI()

# Database setup
connection_string = str(settings.DATABASE_URL).replace("postgresql", "postgresql+psycopg")
engine = create_engine(connection_string, connect_args={"sslmode": "require"}, pool_recycle=300)
SQLModel.metadata.create_all(engine)

# Kafka setup
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models
class User(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: Optional[str]
    email: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: str

class Token(BaseModel):
    access_token: str

# Dependency to get the database session
def get_session():
    with Session(engine) as session:
        yield session


# Dependency to get the Kafka producer
def get_producer() -> KafkaProducer:
    return producer

# Register a new user
@app.post("/register", response_model=UserRead)
async def register_user(user: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.query(User).filter_by(email=user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(username=user.username, email=user.email, password=user.password)
    session.add(new_user)
    session.commit()
    await producer.send(KAFKA_TOPIC, value={"type": "user_created", "user_id": new_user.id})
    return new_user

# Login and get an access token
@app.post("/token", response_model=Token)
async def login_user(username: str, password: str, session: Session = Depends(get_session)):
    user = session.query(User).filter(or_(User.username == username, username is None)).first()
    if not user or not user.password == password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = OAuth2.generate_token(user.username)
    return {"access_token": access_token}

# Get a user's profile
@app.get("/users/{user_id}", response_model=UserRead)
async def get_user_profile(user_id: int, session: Session = Depends(get_session)):
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Update a user's profile
@app.patch("/users/{user_id}", response_model=UserRead)
async def update_user_profile(user_id: int, user: UserCreate, session: Session = Depends(get_session)):
    user_db = session.query(User).filter(User.id == user_id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    user_db.username = user.username
    user_db.email = user.email
    session.commit()
    await producer.send(KAFKA_TOPIC, value={"type": "user_updated", "user_id": user_id})
    return user_db

# Delete a user
@app.delete("/users/{user_id}")
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    user_db = session.query(User).filter(User.id == user_id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user_db)
    session.commit()
    await producer.send(KAFKA_TOPIC, value={"type": "user_deleted", "user_id": user_id})
    return {"message": "User deleted"}