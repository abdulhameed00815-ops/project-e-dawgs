from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
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


class Dawg(Base):
    __tablename__ = "dawgs"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    display_name = Column(String, unique=True)
    password = Column(String)


Base.metadata.create_all(bind=engine_dawgs)


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


@fastapi.post('/signup')
def sign_up(dawg: DawgSignup, db: Session = Depends(get_db_dawgs)):
    if db.query(Dawg.display_name).filter(Dawg.display_name == dawg.display_name).first():
        raise HTTPException(status_code=409, detail="Display name already in use")
    new_dawg = Dawg(email = dawg.email, display_name = dawg.display_name, password = dawg.password) 
    db.add(new_dawg)
    db.commit()



@fastapi.post('/signin')
def sign_in(dawg: DawgSignin, db: Session = Depends(get_db_dawgs), Authorize: AuthJWT = Depends()):
    if not db.query(Dawg.display_name).filter(Dawg.display_name == dawg.display_name).first():
        raise HTTPException(status_code=404, detail="User doesn't exist")
    dawg_id = db.query(Dawg.id).filter(Dawg.email == dawg.email).scalar()
    access_token = Authorize.create_access_token(subject=dawg.id, claims={"email": dawg.email, "id": dawg_id}) 
    return {"acces_token": access_token}

    
@fastapi.websocket('/ws/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcasts(f'Client #{client_id}: {data}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcasts(f'Client #{client_id} lef the chat')
        
