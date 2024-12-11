from fastapi import FastAPI, Depends, Request, HTTPException
import requests
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import HTMLResponse

from app.database import init_db, get_db
from app.models import CartItem, Order, OrderItem
from app.schemas import AddToCartRequest, OrderResponse

app = FastAPI(
    title="Order Service",
    description="Микросервис для управления корзиной и заказами",
    version="1.0.0",
)

# Инициализация базы данных
init_db()

# Настройка шаблонов
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "../frontend/templates"))

AUTH_SERVICE_URL = "http://nginx/auth/verify_token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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

PRODUCT_SERVICE_URL = "http://nginx/products"  # URL сервиса продуктов

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, token: str = Depends(get_token_from_cookies), db: Session = Depends(get_db)):
    """Отображение корзины пользователя с названиями продуктов."""
    current_user = get_current_user(token)  # Проверяем токен и извлекаем данные о пользователе
    user_email = current_user["email"]

    # Получаем товары из корзины
    cart_items = db.query(CartItem).filter(CartItem.user_email == user_email).all()
    if not cart_items:
        return templates.TemplateResponse(
            "cart.html", {"request": request, "cart_items": [], "user_email": user_email}
        )

    # Получаем данные о продуктах через API `products_service`
    product_ids = [item.product_id for item in cart_items]
    print(product_ids)
    response = requests.post(f"{PRODUCT_SERVICE_URL}/bulk", json=product_ids)
    products = response.json()
    print(products)
    product_details = {product["id"]: product for product in products}

    # Обогащаем данные корзины
    enriched_cart_items = [
        {
            "product_name": product_details.get(item.product_id, {}).get("name", "Unknown Product"),
            "quantity": item.quantity,
            "price": product_details.get(item.product_id, {}).get("price", 0.0),
            "total": item.quantity * product_details[item.product_id]["price"],
        }
        for item in cart_items
    ]

    return templates.TemplateResponse(
        "cart.html",
        {"request": request, "cart_items": enriched_cart_items, "user_email": user_email},
    )

@app.post("/cart/clear")
async def clear_cart(db: Session = Depends(get_db), token: str = Depends(get_token_from_cookies)):
    try:
        # Очистить все товары в корзине для текущего пользователя
        current_user = get_current_user(token)
        user_email = current_user["email"]
        db.query(CartItem).filter(CartItem.user_email == user_email).delete()
        db.commit()
        print("vso ok")
        return RedirectResponse(url="/orders/cart", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при очистке корзины")

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
    print(cart_items, order)
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
        db.delete(item)  # Удаляем из корзины

    db.commit()
    return order
