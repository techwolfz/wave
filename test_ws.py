import asyncio
import websockets

async def listen():
    uri = "wss://wave-0xto.onrender.com/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket. Waiting for messages...")
            while True:
                message = await websocket.recv()
                print(f"Received: {message}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(listen())
