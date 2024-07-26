# tests/test_user_service.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from kafka import KafkaProducer

from user.main import app, get_session, get_producer

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def session():
    engine = create_engine("postgresql://user:password@localhost/user_db")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def producer():
    producer = KafkaProducer(bootstrap_servers="localhost:9092")
    yield producer

def test_register_user(client, session, producer):
    response = client.post("/register", json={"username": "testuser", "email": "test@example.com", "password": "password"})
    assert response.status_code == 201
    user = session.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    assert producer.flush() == {"type": "user_created", "user_id": user.id}

def test_login_user(client, session):
    user = User(username="testuser", email="test@example.com", password="password")
    session.add(user)
    session.commit()
    response = client.post("/token", json={"username": "testuser", "password": "password"})
    assert response.status_code == 200
    assert response.json()["access_token"] is not None

def test_get_user_profile(client, session):
    user = User(username="testuser", email="test@example.com", password="password")
    session.add(user)
    session.commit()
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
    assert response.json()["email"] == "test@example.com"

def test_update_user_profile(client, session, producer):
    user = User(username="testuser", email="test@example.com", password="password")
    session.add(user)
    session.commit()
    response = client.patch("/users/1", json={"username": "newusername", "email": "new@example.com"})
    assert response.status_code == 200
    user_db = session.query(User).filter(User.id == 1).first()
    assert user_db.username == "newusername"
    assert user_db.email == "new@example.com"
    assert producer.flush() == {"type": "user_updated", "user_id": 1}

def test_delete_user(client, session, producer):
    user = User(username="testuser", email="test@example.com", password="password")
    session.add(user)
    session.commit()
    response = client.delete("/users/1")
    assert response.status_code == 200
    user_db = session.query(User).filter(User.id == 1).first()
    assert user_db is None
    assert producer.flush() == {"type": "user_deleted", "user_id": 1}