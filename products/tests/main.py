import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from products.main import app, Product, engine
import logging

# Set up logging
logging.basicConfig(filename='test_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="module")
def test_db():
    SQLModel.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield SessionLocal()

def test_get_all_products(test_client, test_db):
    # Insert test data
    test_data = [
        Product(name="Test Product 1", type="Test Type 1", price=10.0, sku="T1", details="Test Details 1", stock_availability="In Stock"),
        Product(name="Test Product 2", type="Test Type 2", price=20.0, sku="T2", details="Test Details 2", stock_availability="Out of Stock"),
    ]
    test_db.add_all(test_data)
    test_db.commit()

    # Get all products
    response = test_client.get("/products/")
    data = response.json()

    # Check response status code
    assert response.status_code == 200

    # Check response data
    assert len(data) == 2
    assert data[0]["name"] == "Test Product 1"
    assert data[0]["type"] == "Test Type 1"
    assert data[0]["price"] == 10.0
    assert data[0]["stock_availability"] == "In Stock"
    assert data[1]["name"] == "Test Product 2"
    assert data[1]["type"] == "Test Type 2"
    assert data[1]["price"] == 20.0
    assert data[1]["stock_availability"] == "Out of Stock"

    # Log the result
    logging.info("Test get_all_products: PASSED")

def test_get_product_by_item_number(test_client, test_db):
    # Insert test data
    test_data = [
        Product(name="Test Product 1", type="Test Type 1", price=10.0, sku="T1", details="Test Details 1", stock_availability="In Stock"),
        Product(name="Test Product 2", type="Test Type 2", price=20.0, sku="T2", details="Test Details 2", stock_availability="Out of Stock"),
    ]
    test_db.add_all(test_data)
    test_db.commit()

    # Get product by item number
    response = test_client.get("/products/1")
    data = response.json()

    # Check response status code
    assert response.status_code == 200

    # Check response data
    assert data["id"] == 1
    assert data["name"] == "Test Product 1"
    assert data["type"] == "Test Type 1"
    assert data["price"] == 10.0
    assert data["sku"] == "T1"
    assert data["details"] == "Test Details 1"
    assert data["stock_availability"] == "In Stock"

    # Log the result
    logging.info("Test get_product_by_item_number: PASSED")

def test_get_product_by_item_number_not_found(test_client, test_db):
    # Get product by item number
    response = test_client.get("/products/999")

    # Check response status code
    assert response.status_code == 404

    # Check response data
    assert response.json() == {"detail": "Product not found"}

    # Log the result
    logging.info("Test get_product_by_item_number_not_found: PASSED")