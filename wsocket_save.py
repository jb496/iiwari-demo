import cv2
import json
import asyncio
import websockets
import threading
from collections import deque

from ftplib import FTP

CAM_ID = "cam3"
# buffer = deque(maxlen=600) # 20secs
buffer = deque(maxlen=600) # 20secs

ftp = FTP('')
ftp.connect('localhost',1026)
ftp.login()
ftp.cwd('Desktop/websockets/ftp') #replace with your directory
ftp.retrlines('LIST')

def uploadFile():
    filename = 'target.mp4' #replace with your file in your home folder
    ftp.storbinary('STOR '+filename, open(filename, 'rb'))
    ftp.quit()


async def listen():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        await websocket.send(CAM_ID)
        while True:
            data = await websocket.recv()

            if data:
                start_recording_clip(json.loads(data), websocket)


def start_recording_clip(data, ws):
    delay, duration = data["delay"], data["duration"]

    start_recording = threading.Timer(duration/2, save_clip, args=(delay, duration, ws, ))
    start_recording.start()


def save_clip(delay, duration, ws):
    # buffer: oldest -> newest
    # pop right -> newest frames
    # crop newest by delay_fps
    # append frames within duration to new buffer

    filename = "target.mp4"

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, 30.0, (640,480))

    delay_frames, duration_frames = delay * 30, duration * 30 # 30fps

    buffer_copy = buffer.copy()
    save_buffer = deque(maxlen=duration_frames)
    for i in range(duration_frames+delay_frames):
        frame = buffer_copy.pop()

        if i >= delay_frames:
            save_buffer.append(frame)

    for i in range(duration_frames):
        frame = save_buffer.pop()
        out.write(frame)

    # need to sleep to
    upload_thread = threading.Timer(5, uploadFile)
    upload_thread.start()


def save_to_buffer():
    global buffer
    cap = cv2.VideoCapture(0)

    ready = False

    while cap.isOpened():
        _, frame = cap.read()

        buffer.append(frame)

        if len(buffer) == 450 and not ready:
            ready = True
            print("ready to test")

        cv2.imshow("cam3", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    buffer_append_thread = threading.Thread(target=save_to_buffer, daemon=True)
    buffer_append_thread.start()

    asyncio.run(listen())
