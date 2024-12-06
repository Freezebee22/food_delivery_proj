# В products_service.py
from fastapi import Depends, HTTPException, Request
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import get_db

SECRET_KEY = "my_secret_key"
ALGORITHM = "HS256"


def get_current_user(request: Request):
    """Извлекает и проверяет токен из заголовков запроса"""
    token = request.headers.get("Authorization")
    if token is None:
        raise HTTPException(status_code=401, detail="Authorization token missing")

    try:
        token = token.split(" ")[1]  # Извлекаем сам токен после "Bearer "
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_email  # Возвращаем email пользователя
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
