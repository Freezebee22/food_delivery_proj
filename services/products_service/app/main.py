from fastapi import FastAPI, Depends, HTTPException, Request
import requests
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, get_db
from routes import product_router
from models import Product
from schemas import ProductAddToCartRequest

app = FastAPI(
    title="Product Catalog Service",
    description="Микросервис для управления каталогом продуктов",
    version="1.0.0"
)

AUTH_SERVICE_URL = "http://localhost:8000/auth/verify_token"  # Указать реальный URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Инициализация базы данных
init_db()

def seed_data():
    db = SessionLocal()
    if not db.query(Product).first():  # Проверяем, пустая ли таблица
        products = [
            Product(name="Apple", description="Fresh and juicy apples", price=0.99, image_url="https://example.com/apple.jpg"),
            Product(name="Banana", description="Ripe bananas", price=0.79, image_url="https://example.com/banana.jpg"),
            Product(name="Orange", description="Sweet oranges", price=1.25, image_url="https://example.com/orange.jpg"),
        ]
        db.add_all(products)
        db.commit()
    db.close()

seed_data()

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Проверка токена через auth_service и получение текущего пользователя."""
    print(token)
    response = requests.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return response.json()  # Возвращает данные о пользователе

@app.post("/add_to_cart")
def add_to_cart(request: ProductAddToCartRequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Добавляет товар в корзину."""
    current_user = get_current_user(token)
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Здесь будет логика отправки данных в order_service (в будущем)
    return {"message": f"Product {product.name} added to cart for user {current_user['email']}"}

# Подключение маршрутов
app.include_router(product_router)
