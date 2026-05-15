from datetime import UTC, datetime, timedelta
import jwt
from config import settings
import hashlib


def create_access_token(data:dict,expires_delta:timedelta|None=None):
    to_encode=data.copy()
    if expires_delta:
        expire = datetime.now(UTC)+expires_delta
    else:
        expire = datetime.now(UTC)+timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({'exp':expire,
                      'type':'access'})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(data:dict,expires_delta:timedelta|None=None):
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.now(UTC)+expires_delta
    else:
        expire=datetime.now(UTC)+timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({'exp':expire,
                      'type':'refresh'})

    encoded_jwt=jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
    )
    return encoded_jwt



def verify_access_token(token:str):
    try:
        payload=jwt.decode(token,
                   settings.secret_key.get_secret_value(),
                   algorithms=[settings.algorithm],
                   options = {"require":["sub", "exp", "session_id"]}
                   )
    except jwt.InvalidTokenError:
        return None
    if payload.get('type') != 'access':
        return None

    return payload




def verify_refresh_token(token:str):
    try:
        payload=jwt.decode(token,
                   settings.secret_key.get_secret_value(),
                   algorithms=[settings.algorithm],
                   options = {"require":["sub", "exp", "session_id","type"]}
                   )
    except jwt.InvalidTokenError:
        return None
    if payload.get('type')!='refresh':
        return None

    return payload


def hash_refresh_token(token:str):
    return hashlib.sha256(token.encode()).hexdigest()