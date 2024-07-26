from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from sqlmodel import SQLModel, Field, Session, create_engine
from aiokafka import AIOKafkaProducer       # type: ignore
from aiokafka.errors import KafkaError      # type: ignore
from products import settings
import os

app = FastAPI(title="Product Service", description="Manages product catalog")

# Database setup
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)
engine = create_engine(
    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
)
SQLModel.metadata.create_all(engine)

# Kafka setup
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

# Models
class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float
    inventory: int

# CRUD operations
@app.post("/products/")
async def create_product(product: Product):
    with Session(engine) as session:
        session.add(product)
        session.commit()
        session.refresh(product)
    await producer.start()
    try:
        await producer.send_and_wait(KAFKA_TOPIC, value={"type": "product_created", "data": product.dict()})
    except KafkaError as e:
        await producer.stop()
        raise HTTPException(status_code=500, detail="Failed to send event to Kafka topic")
    await producer.stop()
    return JSONResponse(content={"message": "Product created successfully"}, status_code=201)

@app.get("/products/")
async def read_products():
    with Session(engine) as session:
        products = session.query(Product).all()
    return JSONResponse(content={"products": [product.dict() for product in products]})

@app.get("/products/{product_id}")
async def read_product(product_id: int):
    with Session(engine) as session:
        product = session.query(Product).get(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
    return JSONResponse(content={"product": product.dict()})

@app.put("/products/{product_id}")
async def update_product(product_id: int, product: Product):
    with Session(engine) as session:
        existing_product = session.query(Product).get(product_id)
        if existing_product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        existing_product.name = product.name
        existing_product.description = product.description
        existing_product.price = product.price
        existing_product.inventory = product.inventory
        session.commit()
    await producer.start()
    try:
        await producer.send_and_wait(KAFKA_TOPIC, value={"type": "product_updated", "data": product.dict()})
    except KafkaError as e:
        await producer.stop()
        raise HTTPException(status_code=500, detail="Failed to send event to Kafka topic")
    await producer.stop()
    return JSONResponse(content={"message": "Product updated successfully"})

@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    with Session(engine) as session:
        product = session.query(Product).get(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        session.delete(product)
        session.commit()
    await producer.start()
    try:
        await producer.send_and_wait(KAFKA_TOPIC, value={"type": "product_deleted", "data": {"id": product_id}})
    except KafkaError as e:
        await producer.stop()
        raise HTTPException(status_code=500, detail="Failed to send event to Kafka topic")
    await producer.stop()
    return JSONResponse(content={"message": "Product deleted successfully"})

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(content={"error": exc.detail}, status_code=exc.status_code)

@app.exception_handler(KafkaError)
async def kafka_exception_handler(request: Request, exc: KafkaError):
    return JSONResponse(content={"error": "Failed to send event to Kafka topic"}, status_code=500)