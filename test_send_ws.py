import asyncio
import websockets
import json

async def send_and_listen():
    uri = "wss://wave-0xto.onrender.com/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected. Sending ping...")
            payload = json.dumps({"id": "PC-Test", "lat": 1.23, "lng": 4.56, "accuracy": 10})
            await websocket.send(payload)
            print("Sent ping!")
            
            while True:
                msg = await websocket.recv()
                print(f"Received from server: {msg}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(send_and_listen())
