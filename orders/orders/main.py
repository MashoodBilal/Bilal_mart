# inventory_service/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, Field, Session, create_engine
from kafka import KafkaProducer      # type: ignore
from orders import settings
import os
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Inventory Service", description="Handles order creation, updating, and tracking")

# Database setup
connection_string = str(settings.DATABASE_URL).replace("postgresql", "postgresql+psycopg")

engine = create_engine(connection_string, connect_args={"sslmode": "require"}, pool_recycle=300)
SQLModel.metadata.create_all(engine)

# Kafka setup
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC_ORDER_CREATED = os.environ["KAFKA_TOPIC_ORDER_CREATED"]
KAFKA_TOPIC_ORDER_UPDATED = os.environ["KAFKA_TOPIC_ORDER_UPDATED"]
KAFKA_TOPIC_ORDER_TRACKED = os.environ["KAFKA_TOPIC_ORDER_TRACKED"]

kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)


class Order(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int
    status: str

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    email: str

class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float


@app.post("/orders/")
async def create_order(order: Order):
    try:
        with Session(engine) as session:
            session.add(order)
            session.commit()
            session.refresh(order)
            kafka_producer.send(KAFKA_TOPIC_ORDER_CREATED, value={"type": "order_created", "data": order.dict()})
            return JSONResponse(content={"message": "Order created successfully"}, status_code=201)
    except Exception as e:
        logging.error(f"Error creating order: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/orders/")
async def read_orders():
    try:
        with Session(engine) as session:
            orders = session.query(Order).all()
        return JSONResponse(content={"orders": [o.dict() for o in orders]})
    except Exception as e:
        logging.error(f"Error reading orders: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/orders/{order_id}")
async def read_order_by_id(order_id: int):
    try:
        with Session(engine) as session:
            order = session.query(Order).get(order_id)
            if order is None:
                raise HTTPException(status_code=404, detail="Order not found")
        return JSONResponse(content={"order": order.dict()})
    except Exception as e:
        logging.error(f"Error reading order by id: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.put("/orders/{order_id}")
async def update_order(order_id: int, order: Order):
    try:
        with Session(engine) as session:
            existing_order = session.query(Order).get(order_id)
            if existing_order is None:
                raise HTTPException(status_code=404, detail="Order not found")
            existing_order.quantity = order.quantity
            existing_order.status = order.status
            session.commit()
            kafka_producer.send(KAFKA_TOPIC_ORDER_UPDATED, value={"type": "order_updated", "data": order.dict()})
            return JSONResponse(content={"message": "Order updated successfully"}, status_code=200)
    except Exception as e:
        logging.error(f"Error updating order: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/orders/{order_id}/track")
async def track_order(order_id: int):
    try:
        with Session(engine) as session:
            order = session.query(Order).get(order_id)
            if order is None:
                raise HTTPException(status_code=404, detail="Order not found")
            order.status = "tracked"
            session.commit()
            kafka_producer.send(KAFKA_TOPIC_ORDER_TRACKED, value={"type": "order_tracked", "data": order.dict()})
            return JSONResponse(content={"message": "Order tracked successfully"}, status_code=200)
    except Exception as e:
        logging.error(f"Error tracking order: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)