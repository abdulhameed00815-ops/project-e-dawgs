from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
import bcrypt
from fastapi.responses import JSONResponse
from fastapi_jwt_auth2 import AuthJWT
from fastapi_jwt_auth2.exceptions import AuthJWTException
from decouple import config
import re


jwt_secret = config("jwt_secret")
jwt_algo = config("jwt_algorithm")

fastapi = FastAPI()


origins = [
        "http://localhost:5500"
]


fastapi.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

Base = declarative_base()


engine_dawgs = create_engine("postgresql://postgres:1234@localhost/dawgs")
SessionLocalDawgs = sessionmaker(autocommit=False, autoflush=False, bind=engine_dawgs)
session_dawgs = SessionLocalDawgs()


engine_messages = create_engine("postgresql://postgres:1234@localhost/messages")
SessionLocalMessages = sessionmaker(autocommit=False, autoflush=False, bind=engine_messages)
session_messages = SessionLocalMessages()


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


Base.metadata.create_all(bind=engine_dawgs)
Base.metadata.create_all(bind=engine_messages)


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


class DawgSignin(BaseModel):
    email:str
    password:str


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcasts(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


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
def sign_up(dawg: DawgSignup, db: Session = Depends(get_db_dawgs), Authorize: AuthJWT = Depends()):
    if db.query(Dawg.email).filter(Dawg.email == dawg.email).first():
        raise HTTPException(status_code=409, detail="Display name already in use")
    new_dawg = Dawg(email = dawg.email, display_name = dawg.display_name, password = dawg.password) 
    db.add(new_dawg)
    db.commit()
    dawg_id = db.query(Dawg.id).filter(Dawg.email == dawg.email).scalar()
    display_name = db.query(Dawg.display_name).filter(Dawg.email == dawg.email).scalar()
    access_token = Authorize.create_access_token(subject=dawg_id, user_claims={"email": dawg.email, "display_name": display_name}) 
    return {"acces_token": access_token}




@fastapi.post('/signin')
def sign_in(dawg: DawgSignin, db: Session = Depends(get_db_dawgs), Authorize: AuthJWT = Depends()):
    if not db.query(Dawg.email).filter(Dawg.email == dawg.email).first():
        raise HTTPException(status_code=404, detail="User doesn't exist")
    dawg_id = db.query(Dawg.id).filter(Dawg.email == dawg.email).scalar()
    display_name = db.query(Dawg.display_name).filter(Dawg.email == dawg.email).scalar()
    access_token = Authorize.create_access_token(subject=dawg_id, user_claims={"email": dawg.email, "display_name": display_name}) 
    return {
            "access_token": access_token, 
            "display_name": display_name
    }




#you cant add authorization or depends to a websocket like you would on a restful api, so you gotta pass the token as a parameter in the websocket request link, get this parameter in the route, manually set it as a jwt token, grab the claims of this token and use them as you like, jwt ofc checks if the password is their when it checks the token so dont worry.
@fastapi.websocket('/ws')
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
    

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            now = datetime.now()    
            time = now.strftime("%H:%M")
            await manager.broadcasts(f'{display_name}: {data} {time}')
            message = f'{display_name}: {data} {time}'
            new_message = Message(message_content = message)
            db.add(new_message)
            db.commit()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcasts(f'{display_name} lef the chat')
        

@fastapi.get('/getmessages')
def get_messages(db: Session = Depends(get_db_messages), Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    messages = db.query(Message).all()
    return list(messages)

