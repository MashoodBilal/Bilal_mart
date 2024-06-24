import requests
import json
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, Session, create_engine
from products import settings

app = FastAPI()

# Create a Postgres engine
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(connection_string, connect_args={}, pool_recycle=300)

# Define the Product model
class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    type: str
    price: float
    sku: str
    details: str
    stock_availability: str

# Create the tables in the database
SQLModel.metadata.create_all(engine)

# Get the JSON API data
response = requests.get("https://dummyjson.com/products")
data = response.json()

# Remove unwanted items and keep only 7 items
products = []
for product in data["products"][:7]:
    products.append({
        "name": product["title"],
        "type": product["category"],
        "price": product["price"],
        "sku": product["sku"],
        "details": product["description"],
        "stock_availability": product["availabilityStatus"]
    })

# Enter the details into the Postgres database
with Session(engine) as session:
    for product in products:
        db_product = Product(**product)
        session.add(db_product)
    session.commit()

# Define the FastAPI endpoints
@app.get("/products/")
def get_all_products():
    with Session(engine) as session:
        products = session.query(Product).all()
        return [{"id": product.id, "name": product.name, "type": product.type, "price": product.price, "stock_availability": product.stock_availability} for product in products]

@app.get("/products/{item_number}")
def get_product_by_item_number(item_number: int):
    with Session(engine) as session:
        product = session.query(Product).filter(Product.id == item_number).first()
        if product:
            return {"id": product.id, "name": product.name, "type": product.type, "price": product.price, "sku": product.sku, "details": product.details, "stock_availability": product.stock_availability}
        else:
            raise HTTPException(status_code=404, detail="Product not found")