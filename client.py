import cv2
import json
import asyncio
import websockets
import threading
from collections import deque

from ftplib import FTP

class Client:
    def __init__(self):
        self.ftp_host_port = 1026
        self.ftp_host_address = '192.168.100.49'
        self.host_file_dir = "Desktop/websockets/ftp"

        self.ftp = FTP("")
        self.ftp.connect(self.ftp_host_address, self.ftp_host_port)
        self.ftp.login()
        self.ftp.cwd(self.host_file_dir)

        self.cam_id = "CAM1"
        self.wsocket_uri = "ws://192.168.100.49:8765"

        self.fps = 30
        self.buffer = deque(maxlen=20 * self.fps) # 20 secs at 30fps

    def save_to_buffer(self):
        try:
            cap = cv2.VideoCapture(0)

            while cap.isOpened():
                _, frame = cap.read()
                self.buffer.append(frame)

                cv2.imshow("cam", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cv2.destroyAllWindows()

        except Exception as err:
            print(err)


    def save_to_buffer_thread(self):
        buffer_append_thread = threading.Thread(target=self.save_to_buffer, daemon=True)
        buffer_append_thread.start()

    async def listen(self):
        async with websockets.connect(self.wsocket_uri) as websocket:
            await websocket.send(self.cam_id)

            while True:
                data = await websocket.recv()
                data = json.loads(data)

                vid_duration = data["duration"]
                trigger_mid = int(vid_duration/2)

                get_buffer_frames_thread = threading.Timer(trigger_mid, self.get_buffer_frames, args=(data,))
                get_buffer_frames_thread.start()

    def get_buffer_frames(self, data):
        filename = f"{data['ts']}.mp4"
        delay_frames, duration_frames = data["delay"] * self.fps, data["duration"] * self.fps

        if len(self.buffer) < delay_frames + duration_frames:
            print("[ ERROR ] Wait for buffer to complete")
            return

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filename, fourcc, 30.0, (640,480))

        buffer_copy = self.buffer.copy()
        vid_buffer = deque(maxlen=duration_frames)

        for i in range(duration_frames + delay_frames):
            frame = buffer_copy.pop()

            if i >= delay_frames:
                vid_buffer.append(frame)

        for i in range(duration_frames):
            frame = vid_buffer.pop()
            out.write(frame)

        print("[ FINISH WRITING VIDEO ]")

        wait_clean_save_thread = threading.Timer(5, self.upload_file, args=[filename])
        wait_clean_save_thread.start()

    def upload_file(self, filename):
        self.ftp.storbinary(f"STOR {filename}", open(filename, 'rb'))
        self.ftp.quit()

        print("[ FINISH UPLOADING VIDEO ]")


async def main():
    client = Client()
    client.save_to_buffer_thread()

    await client.listen()

if __name__ == '__main__':
    asyncio.run(main())
