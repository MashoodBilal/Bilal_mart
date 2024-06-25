# main.py
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, Session, create_engine
from typing import List
from orders import settings

app = FastAPI()

# Create a Postgres engine
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(connection_string, connect_args={}, pool_recycle=300)

with Session(engine) as session:
    session.commit()

# Define the database models
class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    price: float

class Cart(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    customer_id: int
    products: List["Product"] = []

class Order(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    customer_id: int
    products: List["Product"] = []
    tracking_number: str
    payment_method: str
    purchase_receipt: str



# Define the API endpoints
@app.post("/products/")
def create_product(product: Product):
    session.add(product)
    session.commit()
    return product

@app.get("/products/")
def read_products():
    return session.query(Product).all()

@app.post("/carts/")
def create_cart(customer_id: int):
    cart = Cart(customer_id=customer_id)
    session.add(cart)
    session.commit()
    return cart

@app.get("/carts/{cart_id}")
def read_cart(cart_id: int):
    return session.query(Cart).get(cart_id)

@app.post("/carts/{cart_id}/products/")
def add_product_to_cart(cart_id: int, product_id: int):
    cart = session.query(Cart).get(cart_id)
    product = session.query(Product).get(product_id)
    if cart and product:
        cart.products.append(product)
        session.commit()
        return cart
    else:
        raise HTTPException(status_code=404, detail="Cart or product not found")

@app.delete("/carts/{cart_id}/products/{product_id}")
def remove_product_from_cart(cart_id: int, product_id: int):
    cart = session.query(Cart).get(cart_id)
    product = session.query(Product).get(product_id)
    if cart and product:
        cart.products.remove(product)
        session.commit()
        return cart
    else:
        raise HTTPException(status_code=404, detail="Cart or product not found")

@app.post("/orders/")
def create_order(cart_id: int):
    cart = session.query(Cart).get(cart_id)
    if cart:
        order = Order(customer_id=cart.customer_id, products=cart.products)
        session.add(order)
        session.commit()
        # Redirect to multiple API locations
        redirect_to_inventory(order)
        create_tracking_number(order)
        process_payment(order)
        create_purchase_receipt(order)
        send_packing_request(order)
        return order
    else:
        raise HTTPException(status_code=404, detail="Cart not found")

def redirect_to_inventory(order: Order):
    # Call the inventory API to reduce the unit count
    pass

def create_tracking_number(order: Order):
    # Generate a tracking number for the order
    pass

def process_payment(order: Order):
    # Process the payment for the order
    pass

def create_purchase_receipt(order: Order):
    # Create a purchase receipt for the order
    pass

def send_packing_request(order: Order):
    # Send a packing request to the supplier
    pass