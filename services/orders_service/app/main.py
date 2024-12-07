from fastapi import FastAPI, Depends, Request, HTTPException
import requests
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse

from database import init_db, get_db
from models import CartItem, Order, OrderItem
from schemas import AddToCartRequest, OrderResponse

app = FastAPI(
    title="Order Service",
    description="Микросервис для управления корзиной и заказами",
    version="1.0.0",
)

# Инициализация базы данных
init_db()

# Настройка шаблонов
templates = Jinja2Templates(directory="../../../frontend/templates")

AUTH_SERVICE_URL = "http://localhost:8000/auth/verify_token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_token_from_cookies(request: Request):
    token = request.cookies.get("access_token")  # Читаем токен из cookies
    if not token:
        raise HTTPException(status_code=401, detail="Access token missing")
    return token

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Проверка токена через auth_service и получение текущего пользователя."""
    print(token)
    response = requests.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return response.json()

@app.post("/cart/add")
def add_to_cart(request: AddToCartRequest, db: Session = Depends(get_db)):
    """Добавление продукта в корзину."""
    #user_email = request.user_email
    cart_item = db.query(CartItem).filter(
        CartItem.user_email == request.user_email,
        CartItem.product_id == request.product_id
    ).first()
    if cart_item:
        cart_item.quantity += request.quantity
    else:
        cart_item = CartItem(
            user_email=request.user_email,
            product_id=request.product_id,
            quantity=request.quantity,
        )
        db.add(cart_item)

    db.commit()
    return {"message": "Product added to cart"}

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, token: str = Depends(get_token_from_cookies), db: Session = Depends(get_db)):
    """Отображение корзины пользователя."""
    print("view_cart", token)
    current_user = get_current_user(token)  # Проверяем токен и извлекаем данные о пользователе
    user_email = current_user["email"]
    cart_items = db.query(CartItem).filter(CartItem.user_email == user_email).all()
    return templates.TemplateResponse(
        "cart.html",
        {"request": request, "cart_items": cart_items, "user_email": user_email},
    )

@app.post("/order/create", response_model=OrderResponse)
def create_order(token: str = Depends(get_token_from_cookies), db: Session = Depends(get_db)):
    """Создание заказа из корзины."""
    current_user = get_current_user(token)
    user_email = current_user["email"]
    cart_items = db.query(CartItem).filter(CartItem.user_email == user_email).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Создаем заказ
    order = Order(user_email=user_email)
    db.add(order)
    db.commit()
    # db.refresh(order)

    # Переносим товары из корзины в заказ
    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
        )
        db.add(order_item)
        # db.delete(item)  # Удаляем из корзины

    db.commit()
    return order
