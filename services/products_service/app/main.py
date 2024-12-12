from fastapi import FastAPI, Depends, HTTPException, Request
import requests
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import init_db, SessionLocal, get_db
from app.routes import product_router
from app.models import Product
from app.schemas import ProductAddToCartRequest

app = FastAPI(
    title="Product Catalog Service",
    description="Микросервис для управления каталогом продуктов",
    version="1.0.0"
)

AUTH_SERVICE_URL = "http://nginx/auth/verify_token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Инициализация базы данных
init_db()

def seed_data():
    db = SessionLocal()
    db.query(Product).delete()
    db.commit()
    if not db.query(Product).first():  # Проверяем, пустая ли таблица
        products = [
            Product(name='Печенье "Лакомка"', description="Fresh and juicy apples", price=89.99, image_url="https://example.com/apple.jpg"),
            Product(name='Чай черный в пакетиках (25 шт.)', description="Ripe bananas", price=109.89, image_url="https://example.com/banana.jpg"),
            Product(name="Чипсы May's со сметанной и луком", description="Sweet oranges", price=129.99, image_url="https://example.com/orange.jpg"),
            Product(name="Хлеб ржаной", description="Sweet oranges", price=29.99, image_url="https://example.com/orange.jpg"),
            Product(name="Бананы спелые (1 шт)", description="Sweet oranges", price=39.90, image_url="https://example.com/orange.jpg"),
            Product(name="Картофель (100 г)", description="Sweet oranges", price=29.90, image_url="https://example.com/orange.jpg"),
            Product(name='Лимонад "Буратино"', description="Sweet oranges", price=19.50, image_url="https://example.com/orange.jpg"),
        ]
        db.add_all(products)
        db.commit()
    db.close()

seed_data()

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Проверка токена через auth_service и получение текущего пользователя."""
    print(token)
    response = requests.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
    print(response.json())
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

    print(current_user["email"])
    response = requests.post(
        "http://nginx/orders/cart/add",  # URL order_service
        json={"product_id": request.product_id, "quantity": 1, "user_email": current_user["email"]},
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json()["detail"])

    return {"message": f"Product {product.name} added to cart for user {current_user['email']}"}

# Подключение маршрутов
app.include_router(product_router)
