import os
import cv2
import json
import base64
import socket
import asyncio
import datetime
import threading
import websockets
from collections import deque

from ftplib import FTP

class Client:
	def __init__(self):
		self.broadcaster_address = '192.168.100.53' # need a way to query this automatically

		self.ftp_host_port = 1026
		self.ftp_host_address = self.broadcaster_address
		self.host_file_dir = "/vids"

		self.ftp = FTP("")
		self.ftp.connect(self.ftp_host_address, self.ftp_host_port)
		self.ftp.login(user="test", passwd="testpw")
		self.ftp.cwd('vids')

		self.cam_id = "cam1"
		self.wsocket_uri = f"ws://{self.broadcaster_address}:8765"

		self.frame_size = (640,480)

		self.fps = 30
		self.max_seconds = 10
		self.max_buffer_frames = self.max_seconds * self.fps

		self.buffer_complete = False
		self.buffer = deque(maxlen=self.max_buffer_frames) # 20 secs at 30fps

		self.local_address = socket.gethostbyname(socket.gethostname())
		self.websocket_stream = self.local_address
		self.websocket_stream_port = 9001

		self.server = None

	def save_to_buffer(self):
		try:
			cap = cv2.VideoCapture(0)

			while cap.isOpened():
				_, frame = cap.read()
				self.buffer.append(frame)

				if not self.buffer_complete:
					if len(self.buffer) == self.max_buffer_frames:
						self.buffer_complete = True
						print("[ READY ] Buffer full")

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
			data = {"id":self.cam_id, "address":self.local_address}
			await websocket.send(json.dumps(data))

			while True:
				msg = await websocket.recv()
				msg = json.loads(msg)

				header = msg["header"]

				if header == "SAVE-VIDEO":
					trigger_data = msg["data"]
					vid_duration = trigger_data["clip_duration"]

					trigger_mid = int(vid_duration/2)

					get_buffer_frames_thread = threading.Timer(trigger_mid, self.get_buffer_frames, args=(trigger_data,))
					get_buffer_frames_thread.start()

				elif header == "START-STREAM-SERVER":
					print("[ STREAMING CAMERA MSG RECV ]")
					await self.start_streaming_server()


	async def start_streaming_server(self):
		# need it like this to retrieve an await Websocket Server
		self.server = await websockets.serve(self.handler, self.websocket_stream, self.websocket_stream_port)

	async def handler(self, websocket, path):
		try:
			async for msg in websocket:
				data = json.loads(msg)
				id = data["id"]

				print(f"[ NEW STREAMING CONNECTION ] {id}")

				while True:
					await asyncio.sleep(0)

					data = json.dumps({ "base64":self.get_current_frame()})
					await websocket.send(data)

		except Exception as e:
			print("[ STREAMING CLIENT CLOSED CONNECTION ]", e)
			self.server.close()

	def get_current_frame(self):
		dq = self.buffer.copy()
		frame = dq.pop()

		timestamp = datetime.datetime.now()
		cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

		retval, buffer = cv2.imencode('.jpg', frame)
		bas64 = base64.b64encode(buffer)
		res = bas64.decode("utf-8")
		return res


	def get_buffer_frames(self, data):
		if not self.buffer_complete:
			current_buffer_size = len(self.buffer)
			print(f"[ ERROR ] Buffer is only {current_buffer_size} frame, need {self.max_buffer_frames} frames")
			return

		c_time = datetime.datetime.now()
		node_id, timestamp = data["node_id"], f"{c_time.day}-{c_time.month}-{c_time.year}-{c_time.minute}-{c_time.second}"
		filename = f"{node_id}-{timestamp}.mp4"
		delay_frames, duration_frames = data["tag_delay"] * self.fps, data["clip_duration"] * self.fps


		fourcc = cv2.VideoWriter_fourcc(*'mp4v') # mp4v or webm
		out = cv2.VideoWriter(filename, fourcc, self.fps, self.frame_size)

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

		wait_clean_save_thread = threading.Timer(5, self.upload_delete_file, args=[filename])
		wait_clean_save_thread.start()


	def upload_delete_file(self, filename):
		self.ftp.storbinary(f"STOR {filename}", open(filename, 'rb'))
		print("[ FINISH UPLOADING VIDEO ]")

		# delete file
		CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
		file = os.path.join(CURRENT_PATH, filename)
		os.system(f"rm {file}")
		print("[ DELETING VIDEO LOCALLY ]")


async def main():
	client = Client()
	client.save_to_buffer_thread()

	await client.listen()

if __name__ == '__main__':
	asyncio.run(main())
