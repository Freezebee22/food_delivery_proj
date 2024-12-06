from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from routes import auth_router, register_user, login
from database import Base, engine, get_db
from schemas import UserCreate
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from utils import decode_access_token, SECRET_KEY, ALGORITHM

# Создание таблиц
Base.metadata.create_all(bind=engine)

# Инициализация приложения
app = FastAPI(
    title="Auth Service",
    description="Микросервис авторизации для Food Delivery",
    version="1.0.0"
)

# Шаблоны
templates = Jinja2Templates(directory="../../../frontend/templates")

# Подключение маршрутов API
app.include_router(auth_router, prefix="/auth")


def get_current_user(request: Request):
    """Извлекает токен пользователя из cookies."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    """Рендеринг домашней страницы."""
    token = request.cookies.get("access_token")
    user_name = None
    if token:
        try:
            payload = decode_access_token(token)
            user_name = payload.get("full_name")
        except HTTPException:
            pass
    return templates.TemplateResponse("index.html", {"request": request, "user_name": user_name})


@app.get("/register_page", response_class=HTMLResponse)
def register_page(request: Request):
    """Страница регистрации."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/login_page", response_class=HTMLResponse)
def login_page(request: Request):
    """Страница входа."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/logout")
def logout():
    """Выход из аккаунта."""
    response = RedirectResponse(url="/home", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request):
    """Страница продуктов доступна только авторизованным пользователям."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login_page", status_code=303)
    return templates.TemplateResponse("products.html", {"request": request, "user": user})


@app.post("/register_form")
def register_form(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    db: Session = Depends(get_db),
):
    """Обработка формы регистрации."""
    user_data = UserCreate(email=email, password=password, full_name=full_name)
    register_user(user_data, db)
    return RedirectResponse(url="/login_page", status_code=303)


@app.post("/login_form")
def login_form(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Обработка формы входа."""
    response = login(email, password, db)
    access_token = response["access_token"]
    redirect_response = RedirectResponse(url="http://localhost:8001/products_page", status_code=303)
    redirect_response.set_cookie(key="access_token", value=access_token)
    return redirect_response
