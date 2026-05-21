from app.models.user import UserInfo
from app.utils.security import hash_password
from app.config import settings
from datetime import datetime, timedelta
from jose import jwt

def get_user_by_email(db, email):       # This will return a matched email between user input and DB query

    return db.query(UserInfo).filter(UserInfo.email == email).first()

def create_user(db, email, password):       # this will create the new user and put users info as an object in class UserInfo

    hashed = hash_password(password)
    new_user = UserInfo(email = email, hashed_password = hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def create_access_token(user_id):      # Gives a user a access token for first time login, token is killed after 24hr and user will have to login again and get a new one
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")