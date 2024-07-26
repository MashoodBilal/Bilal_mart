# inventory_service/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from sqlmodel import SQLModel, Field, Session, create_engine
from kafka import KafkaConsumer, KafkaProducer      # type: ignore
from inventory import settings
import os
import json

app = FastAPI(title="Inventory Service", description="Manages stock levels and inventory updates")

# Database setup
connection_string = str(settings.DATABASE_URL).replace("postgresql", "postgresql+psycopg")

engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
)
SQLModel.metadata.create_all(engine)

# Kafka setup
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC_INVENTORY_UPDATED = os.environ["KAFKA_TOPIC_INVENTORY_UPDATED"]
KAFKA_TOPIC_PRODUCT_CREATED = os.environ["KAFKA_TOPIC_PRODUCT_CREATED"]
KAFKA_TOPIC_PRODUCT_UPDATED = os.environ["KAFKA_TOPIC_PRODUCT_UPDATED"]
KAFKA_TOPIC_PRODUCT_DELETED = os.environ["KAFKA_TOPIC_PRODUCT_DELETED"]

producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
consumer = KafkaConsumer(KAFKA_TOPIC_PRODUCT_CREATED, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
consumer.subscribe([KAFKA_TOPIC_PRODUCT_CREATED, KAFKA_TOPIC_PRODUCT_UPDATED, KAFKA_TOPIC_PRODUCT_DELETED])

# Models
class Inventory(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    quantity: int

class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float

# CRUD operations
@app.post("/inventory/")
async def create_inventory(inventory: Inventory):
    try:
        with Session(engine) as session:
            session.add(inventory)
            session.commit()
            session.refresh(inventory)
        producer.send(KAFKA_TOPIC_INVENTORY_UPDATED, value={"type": "inventory_created", "data": inventory.dict()})
        return JSONResponse(content={"message": "Inventory created successfully"}, status_code=201)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/inventory/")
async def read_inventory():
    try:
        with Session(engine) as session:
            inventory = session.query(Inventory).all()
        return JSONResponse(content={"inventory": [i.dict() for i in inventory]})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/inventory/{inventory_id}")
async def read_inventory_by_id(inventory_id: int):
    try:
        with Session(engine) as session:
            inventory = session.query(Inventory).get(inventory_id)
            if inventory is None:
                raise HTTPException(status_code=404, detail="Inventory not found")
        return JSONResponse(content={"inventory": inventory.dict()})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.put("/inventory/{inventory_id}")
async def update_inventory(inventory_id: int, inventory: Inventory):
    try:
        with Session(engine) as session:
            existing_inventory = session.query(Inventory).get
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)