from notification import settings
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from sqlmodel import SQLModel, Field, Session, create_engine
from kafka import KafkaProducer, KafkaConsumer     # type: ignore
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

app = FastAPI()

# Database configuration
connection_string = str(settings.DATABASE_URL).replace("postgresql", "postgresql+psycopg")

engine = create_engine(connection_string, connect_args={"sslmode": "require"}, pool_recycle=300)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC = "order_notifications"

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
FROM_EMAIL = "notifications@bilalmart.com"

# SQLModel for User data
class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    email: str

# SQLModel for Order data
class Order(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    status: str
    tracking_number: str

# Kafka producer
producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

# Function to send email notification
def send_email_notification(user_email, order_status, tracking_number):
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = user_email
    msg["Subject"] = "Order Update"
    body = f"Your order status has been updated to {order_status}. Tracking number: {tracking_number}"
    msg.attach(MIMEText(body, "plain"))
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(FROM_EMAIL, "your_generated_app_password")  # Use App Password here
    server.sendmail(FROM_EMAIL, user_email, msg.as_string())
    server.quit()


# Function to handle Kafka message
def handle_kafka_message(message):
    order_id = message.value["order_id"]
    order_status = message.value["order_status"]
    tracking_number = message.value["tracking_number"]
    with Session(engine) as session:
        order = session.get(Order, order_id)
        user = session.get(User, order.user_id)
        send_email_notification(user.email, order_status, tracking_number)


consumer = KafkaConsumer(KAFKA_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
consumer.subscribe([KAFKA_TOPIC])

# FastAPI endpoint to handle Kafka messages
@app.post("/kafka_message")
async def handle_kafka_message_endpoint(request: Request):
    message = await request.json()
    handle_kafka_message(message)
    return JSONResponse(status_code=200, content={"message": "Notification sent successfully"})

# FastAPI endpoint to test email notification
@app.get("/test_email_notification")
async def test_email_notification():
    user_email = "test@example.com"
    order_status = "shipped"
    tracking_number = "1234567890"
    send_email_notification(user_email, order_status, tracking_number)
    return JSONResponse(status_code=200, content={"message": "Email notification sent successfully"})