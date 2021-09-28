import cv2
import asyncio
import websockets
import threading
from collections import deque

CAM_ID = "cam3"
buffer = deque(maxlen=600) # 20secs
buffer_lock = threading.Lock()


async def listen():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        await websocket.send(CAM_ID)
        while True:
            data = await websocket.recv()

            if data and not save_clip:
                # data = {"target": "cam3", "pos": [850, 1075], "delay": 2, "duration": 8}
                save_clip()
                pass

def save_clip():
    if buffer_lock.locked():
        buffer_lock.release()

    buffer_lock.acquire(True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter("test.mp4", fourcc, 30.0, (640,480))

    for frame in buffer:
        out.write(frame)

    buffer_lock.release()


def save_to_buffer():
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        _, frame = cap.read()

        if not buffer_lock.locked():
            buffer_lock.acquire()
            buffer.append(frame)


if __name__ == '__main__':
    buffer_append_thread = threading.Thread(target=save_to_buffer, daemon=True)
    buffer_append_thread.start()

    asyncio.run(listen())
