from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


fastapi = FastAPI()


origins = [
        "http://localhost:5500"
]


class ConnectionManager:
        def __init__(self):
            self.active_connections: list[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            self.active_connections.remove(websocket)

        async def send_personal_message(self, message: str, websocket: WebSocket):
            await websocket.send_text(message)

        async def broadcasts(self, message: str):
            for connection in self.active_connections:
                await connection.send_text(message)


manager = ConnectionManager()


fastapi.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)


@fastapi.websocket('/ws/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f'You wrote: {data}', websocket)
            await manager.broadcasts(f'Client #{client_id}: {data}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcasts(f'Client #{client_id} lef the chat')
        
