import asyncio
import websockets

async def listen():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        await websocket.send(f"cam3")
        while True:
            msg = await websocket.recv()
            print(msg)

asyncio.run(listen())
