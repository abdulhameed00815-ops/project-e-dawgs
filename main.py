from functools import wraps
from fastapi.staticfiles import StaticFiles
import os
from cryptography.fernet import Fernet
from urllib.parse import unquote
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, Response
from sqlalchemy import create_engine, Column, String, Integer, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
import bcrypt
from fastapi.responses import JSONResponse
from fastapi_jwt_auth2 import AuthJWT
from fastapi_jwt_auth2.exceptions import AuthJWTException
from decouple import config
import re
import asyncio
from asyncio import Future, iscoroutine
from typing import Callable, Any

request_queue = asyncio.Queue()

fastapi = FastAPI()


#this async func awaits to get a job from the queue, it then executes it, all in a sequential manner.
async def queue_worker():
    while True:
        job = await request_queue.get()
        try:
            await job()
        except Exception as e:
            print("Error in queued job:", e)
        finally:
            request_queue.task_done()


#this decorator awakes the worker function on server startup, this doesn't disrupt the normal endpoints from doing their work (they work like threads).
@fastapi.on_event("startup")
async def startup_event():
    asyncio.create_task(queue_worker())


#this function enqueues jobs (func).
async def enqueue(func: Callable[[], Any]):
    await request_queue.put(func)


#this is a decorator/wrapper, it wraps the endpoint logic into a job function, this function will be enqueued to our queue instead of being executed at once.
def queued_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        future = Future()

        async def job():
            try:
                result = func(*args, **kwargs)
                if iscoroutine(result):
                    result = await result
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
        await enqueue(job)
        return await future

    return wrapper


fastapi.mount("/static", StaticFiles(directory="frontend/", html=True), name="frontend")


email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


def write_key():
    key = Fernet.generate_key()
    with open("key.key", "wb") as key_file:
        key_file.write(key)


def load_key():
    return open("key.key", "rb").read()


if not os.path.exists("key.key"):
    write_key()

key = load_key()

f = Fernet(key)


jwt_secret = config("jwt_secret")
jwt_algo = config("jwt_algorithm")


Base = declarative_base()


engine_dawgs = create_engine("postgresql://postgres:1234@localhost/dawgs")
SessionLocalDawgs = sessionmaker(autocommit=False, autoflush=False, bind=engine_dawgs)
session_dawgs = SessionLocalDawgs()


engine_messages = create_engine("postgresql://postgres:1234@localhost/messages")
SessionLocalMessages = sessionmaker(autocommit=False, autoflush=False, bind=engine_messages)
session_messages = SessionLocalMessages()



engine_dms = create_engine("postgresql://postgres:1234@localhost/dms")
SessionLocalDms = sessionmaker(autocommit=False, autoflush=False, bind=engine_dms)
session_dms = SessionLocalDms()


class Dawg(Base):
    __tablename__ = "dawgs"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    display_name = Column(String, unique=True)
    password = Column(String)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    message_content = Column(String)

class Dm(Base):
    __tablename__ = "dms"
    message_id = Column(Integer, primary_key=True)
    dm_id = Column(Integer)
    dm_content = Column(LargeBinary)


Base.metadata.create_all(bind=engine_dawgs)
Base.metadata.create_all(bind=engine_messages)
Base.metadata.create_all(bind=engine_dms)


class DawgSignup(BaseModel):
    email:str
    display_name:str
    password:str


def get_db_dawgs():
    db = SessionLocalDawgs()
    try:
        yield db
    finally:
        db.close()


def get_db_messages():
    db = SessionLocalMessages()
    try:
        yield db
    finally:
        db.close()


def get_db_dms():
    db = SessionLocalDms()
    try:
        yield db
    finally:
        db.close()


class DawgSignin(BaseModel):
    email:str
    password:str


class Settings(BaseModel):
    authjwt_secret_key: str = jwt_secret


@AuthJWT.load_config
def get_config():
    return Settings()


@fastapi.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
            )


def display_name(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    claims = Authorize.get_raw_jwt()
    display_name = claims.get("display_name")
    return display_name


@fastapi.post('/signup')
@queued_endpoint
def sign_up(dawg: DawgSignup, db: Session = Depends(get_db_dawgs), Authorize: AuthJWT = Depends()):
    if db.query(Dawg.email).filter(Dawg.email == dawg.email).first():
        raise HTTPException(status_code=409, detail="user email already in use")
    if not re.fullmatch(email_regex, dawg.email):
        raise HTTPException(status_code=400, detail="invalid email")
    if len(dawg.display_name) == 0:
        raise HTTPException(status_code=400, detail="please enter a display name")
    if len(dawg.password) < 4:
        raise HTTPException(status_code=400, detail="password too short")
    if len(dawg.password) > 50:
        raise HTTPException(status_code=400, detail="password too long")
    if len(dawg.display_name) > 20:
        raise HTTPException(status_code=400, detail="display name too long man")
    hashed_pw = bcrypt.hashpw(dawg.password.encode('utf-8'), bcrypt.gensalt())
    new_dawg = Dawg(email = dawg.email, display_name = dawg.display_name, password = hashed_pw.decode('utf-8')) 
    db.add(new_dawg)
    db.commit()


def sign_in_logic(db, dawg, response, Authorize):
    if not db.query(Dawg.email).filter(Dawg.email == dawg.email).first():
        raise HTTPException(status_code=404, detail="User doesn't exist")
    pass_key = db.query(Dawg.password).filter(Dawg.email == dawg.email).scalar()
    if bcrypt.checkpw(dawg.password.encode('utf-8'), pass_key.encode('utf-8')):
        dawg_id = db.query(Dawg.id).filter(Dawg.email == dawg.email).scalar()
        display_name = db.query(Dawg.display_name).filter(Dawg.email == dawg.email).scalar()
        custom_expires_time = timedelta(minutes=30)
        refresh_expires_time = timedelta(days=7)
        access_token = Authorize.create_access_token(subject=dawg_id, expires_time=custom_expires_time, user_claims={"email": dawg.email, "display_name": display_name}) 
        refresh_token = Authorize.create_refresh_token(subject=dawg_id, expires_time=refresh_expires_time, user_claims={"email": dawg.email, "display_name": display_name})
        response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite="lax",
                path="/",
                max_age=604800,
                expires=604800
        )
        return {
                "access_token": access_token, 
                "display_name": display_name
        }
    else:
        raise HTTPException(status_code=401, detail="incorrect password")



@fastapi.post('/signin')
@queued_endpoint
def sign_in(response: Response, dawg: DawgSignin, db: Session = Depends(get_db_dawgs), Authorize: AuthJWT = Depends()):
    sign_in_logic(response, dawg, db, Authorize)


@fastapi.get('/refresh/')
@queued_endpoint
def refresh(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token == None:
        raise HTTPException(status_code=404, detail="missing refresh token")
    refresh_token = refresh_token.strip()
    if refresh_token.startswith("b'") and refresh_token.endswith("'"):
        refresh_token = refresh_token[2:-1]
    Authorize = AuthJWT()
    Authorize._token = refresh_token
    Authorize.jwt_refresh_token_required()
    claims = Authorize.get_raw_jwt()
    email = claims.get("email")
    display_name = claims.get("display_name")
    dawg_id = claims.get("sub")
    custom_expires_time = timedelta(minutes=30)
    access_token = Authorize.create_access_token(subject=dawg_id, expires_time=custom_expires_time, user_claims={"email": email, "display_name": display_name}) 
    return {"access_token": access_token, "display_name": display_name}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}


    async def connect(self, websocket: WebSocket, display_name: str = Depends(display_name)):
        await websocket.accept()
        self.active_connections[display_name] = websocket


    def disconnect(self, websocket: WebSocket, display_name: str = Depends(display_name)):
        self.active_connections.pop(display_name, None)

            
    async def broadcasts(self, message: str):
        for websocket in self.active_connections.values():
            await websocket.send_text(message)


    async def dm(self, message: str, target: str):
        websocket = self.active_connections.get(target)
        if not websocket:
            return
        try:
            await websocket.send_text(message)
        except (RuntimeError, WebSocketDisconnect): 
            self.active_connections.pop(target, None)
#so, the dm function at top basically checks if the target has an active connection, if it does then you get to send a message directly without issues, but if he doesnt, then it basically cleans the function of his remainders (pop), by cleaning you allow the app to not crash basically (I AM NOT A VIBE CODER).

manager = ConnectionManager()


#you cant add authorization or depends to a websocket like you would on a restful api, so you gotta pass the token as a parameter in the websocket request link, get this parameter in the route, manually set it as a jwt token, grab the claims of this token and use them as you like, jwt ofc checks if the password is their when it checks the token so dont worry.
@fastapi.websocket('/ws')
@queued_endpoint
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db_messages)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    Authorize = AuthJWT()

    try:
        Authorize._token = token
        Authorize.jwt_required()
        claims = Authorize.get_raw_jwt()
    except AuthJWTException:
        await websocket.close(code=1008)
        return

    display_name = claims.get("display_name")


    await manager.connect(websocket, display_name)

    try:
        while True:
            data = await websocket.receive_text()
            now = datetime.now()    
            time = now.strftime("%H:%M")
            await manager.broadcasts(f'[{display_name}]   {data} {time}')
            message = f'[{display_name}]   {data} {time}'
            new_message = Message(message_content = message)
            db.add(new_message)
            db.commit()
    except WebSocketDisconnect:
        return
        
        
@fastapi.websocket("/wsdm")
@queued_endpoint
async def dm_route(websocket: WebSocket, db_dawgs: Session = Depends(get_db_dawgs), db_dms: Session = Depends(get_db_dms)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    Authorize = AuthJWT()

    try:
        Authorize._token = token
        Authorize.jwt_required()
        claims = Authorize.get_raw_jwt()
    except AuthJWTException:
        await websocket.close(code=1008)
        return


    display_name = claims.get("display_name")

    your_dawg_id = db_dawgs.query(Dawg.id).filter(Dawg.display_name == display_name).scalar()

    target_display_name = websocket.query_params.get("target")

    target_display_name = unquote(target_display_name)

    target_dawg_id = db_dawgs.query(Dawg.id).filter(Dawg.display_name == target_display_name).scalar()

#function that returns a unique dm_id out of two numbers.
    def dm_id(you: int, target: int) -> int:
        x = min(you, target)
        y = max(you, target)
        return (x + y) * (x + y + 1) // 2 + y


    dm_id_value = dm_id(you=your_dawg_id, target=target_dawg_id)

    await manager.connect(websocket, display_name)

    try:
        while True:
            data = await websocket.receive_text()
            now = datetime.now()    
            time = now.strftime("%H:%M")
            message = f"[{display_name}] {data} {time}"
            encoded_message = message.encode("utf-8")
            encrypted_message = f.encrypt(encoded_message)
            await manager.dm(target=target_display_name, message=message)
            await manager.dm(target=display_name, message=message)
            new_dm = Dm(dm_id = dm_id_value, dm_content = encrypted_message)
            db_dms.add(new_dm)
            db_dms.commit()
    except WebSocketDisconnect:
        return


def get_messages_logic(db):
    return db.query(Message).all()


@fastapi.get('/getmessages')
def get_messages(db: Session = Depends(get_db_messages), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    messages = fetch_messages(db)
    return list(messages)


def get_dm_id_logic(db_dawgs):
    def dm_id(you: int, target: int) -> int:
        x = min(you, target)
        y = max(you, target)
        return (x + y) * (x + y + 1) // 2 + y


    your_id = db_dawgs.query(Dawg.id).filter(Dawg.display_name == display_name).scalar()

    target_id = db_dawgs.query(Dawg.id).filter(Dawg.display_name == target_display_name).scalar()

    if your_id is None or target_id is None:
        raise HTTPException(status_code=404, detail="user not found")


    dm_id_value = dm_id(your_id, target=target_id)

    return dm_id_value


@fastapi.get('/getdmid/{display_name}/{target_display_name}')
def get_dm_id(display_name: str, target_display_name: str, db_dawgs: Session = Depends(get_db_dawgs), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()


    dm_id_value = get_dm_id_logic(db_dawgs)


    return {"dm_id": dm_id_value}


def get_dms_logic(db):
    dms = db.query(Dm.dm_content).filter(Dm.dm_id == dm_id).all()
    result = []
#so we basically check if the encrypted message (from the db) is txt or binary, its surely binary but why not.
    for (encrypted,) in dms:
        if isinstance(encrypted, str):
            encrypted = encrypted.encode()
        decrypted = f.decrypt(encrypted).decode()
        result.append({
            "dm_content": decrypted
        })


@fastapi.get('/getdms/{dm_id}')
def get_dms(dm_id: int, db: Session = Depends(get_db_dms), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    get_dms_logic(db)
    return {"dms": result}
