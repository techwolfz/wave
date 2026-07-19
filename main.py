import json
import os
import secrets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# --- Database Setup ---
DB_FILE = os.path.join(os.path.dirname(__file__), "tracker.db")
engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Location(Base):
    __tablename__ = "locations"
    device_id = Column(String, primary_key=True, index=True)
    lat = Column(Float)
    lng = Column(Float)
    accuracy = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def update_db_location(device_id, lat, lng, accuracy):
    db = SessionLocal()
    loc = db.query(Location).filter(Location.device_id == device_id).first()
    if loc:
        loc.lat = lat
        loc.lng = lng
        loc.accuracy = accuracy
        loc.timestamp = datetime.utcnow()
    else:
        loc = Location(device_id=device_id, lat=lat, lng=lng, accuracy=accuracy)
        db.add(loc)
    db.commit()
    db.close()

def get_all_locations():
    db = SessionLocal()
    locs = db.query(Location).all()
    db.close()
    return [{"id": l.device_id, "lat": l.lat, "lng": l.lng, "accuracy": l.accuracy, "timestamp": l.timestamp.isoformat()} for l in locs]

# --- App Setup ---
app = FastAPI()

security = HTTPBasic()

# Hardcoded PIN for demonstration. You can change this or use environment variables!
CORRECT_USERNAME = "admin"
CORRECT_PASSWORD = "password123"

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, CORRECT_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, CORRECT_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

public_dir = os.path.join(os.path.dirname(__file__), "public")
os.makedirs(public_dir, exist_ok=True)
app.mount("/public", StaticFiles(directory=public_dir), name="public")

# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send last known locations to the new client
        locs = get_all_locations()
        for loc in locs:
            await websocket.send_text(json.dumps(loc))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str, sender: WebSocket):
        for connection in self.active_connections:
            if connection != sender:
                await connection.send_text(message)

manager = ConnectionManager()

# Protect the main HTML page with Basic Auth
@app.get("/")
async def get(username: str = Depends(get_current_username)):
    index_path = os.path.join(public_dir, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    with open(index_path) as f:
        return HTMLResponse(f.read())

# Websocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed = json.loads(data)
                if "id" in parsed and "lat" in parsed and "lng" in parsed:
                    update_db_location(parsed["id"], parsed["lat"], parsed["lng"], parsed.get("accuracy", 0))
            except json.JSONDecodeError:
                pass
            
            # Broadcast the received location data to all other clients
            await manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
