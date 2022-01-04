import os
import cv2
import json
import base64
import asyncio
import datetime
import threading
import websockets

from collections import deque
from ftplib import FTP


class Client:
	def __init__(self):
		self.broadcaster_address = "immanuel.local"

		self.ftp_host_port = 1026
		self.host_file_dir = "/vids"

		self.ftp = FTP("")
		self.ftp.connect(self.broadcaster_address, self.ftp_host_port)
		self.ftp.login(user="test", passwd="testpw")

		self.main_websocket_url = f"ws://{self.broadcaster_address}:8765"

		self.fps = 30
		self.max_seconds = 20
		self.frame_size = (640,480)
		self.max_buffer_frames = self.max_seconds * self.fps

		self.buffer_complete = False
		self.buffer = deque(maxlen=self.max_buffer_frames) # 20 secs at 30fps

		self.local_address = self.get_my_ip_address()
		self.websocket_stream_port = 9001
		self.webstreaming_clients = {}

		self.invalid_chars = ["-", " ", ".", ":"]


	def get_my_ip_address(self):
		cmd_res = os.popen(f"ifconfig | grep '192'").read()
		cmd_res = cmd_res.strip()
		cmd_res = cmd_res.split(" ")
		inet, ip_address, *res = cmd_res
		print(f"[ IP ADDRESS ] {ip_address}")
		return ip_address


	def save_images_to_buffer(self):
		cap = cv2.VideoCapture(0)

		while cap.isOpened():
			_, frame = cap.read()
			self.buffer.append(frame)

			if not self.buffer_complete:
				if len(self.buffer) == self.max_buffer_frames:
					self.buffer_complete = True

			cv2.imshow("cam", frame)

			if cv2.waitKey(1) & 0xFF == ord('q'):
				break

		cv2.destroyAllWindows()


	async def listen(self):
		print("[ FILLING BUFFER SIZE ... PLEASE WAIT ]")
		while not self.buffer_complete:
			# TODO: display red led animation
			pass

		print("[ READY. BUFFER SIZE FULL ]")
		async with websockets.connect(self.main_websocket_url) as websocket:
			data = json.dumps({"id": "Raspberry Pi", "msg": f"hello server from client {self.local_address}"})
			await websocket.send(data)

			while True:
				msg = await websocket.recv()
				msg = json.loads(msg)

				if msg["header"] == "SAVE-VIDEO":
					print("[ SAVE VIDEO MSG RECV ]")

					trigger_data = msg["data"]

					vid_duration = trigger_data["clip_duration"]
					trigger_mid = int(vid_duration/2)

					get_buffer_frames_thread = threading.Timer(trigger_mid, self.get_buffer_frames, args=(trigger_data,))
					get_buffer_frames_thread.start()


	async def start_webstreamer(self):
		print("[ STARTING WEBSTREAMING SERVER ]")
		async with websockets.serve(self.webstreaming_handler, self.local_address, self.websocket_stream_port):
			await asyncio.Future()


	async def webstreaming_handler(self, websocket, path):
		async for msg in websocket:
			client_address, port = websocket.remote_address
			print(f"[ NEW CONNECTION ] GUI at {client_address}:{port}")
			self.webstreaming_clients[f"{client_address}:{port}"] = websocket


	async def webstreamer_broadcast(self):
		client_address = None
		while True:
			try:
				await asyncio.sleep(0)

				data = json.dumps({"base64": self.get_current_frame()})
				for addr, websocket in self.webstreaming_clients.items():
					client_address = addr
					await websocket.send(data)

			except Exception as e:
				print(f"[ DISCONNECTED ] Raspberry Pi at {client_address}")
				if client_address in self.webstreaming_clients:
					del self.webstreaming_clients[client_address]


	def get_current_frame(self):
		if len(self.buffer) == 0:
			return

		frame = self.buffer[len(self.buffer)-1]

		timestamp = datetime.datetime.now()
		cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

		retval, buffer = cv2.imencode('.jpg', frame)
		bas64 = base64.b64encode(buffer)
		res = bas64.decode("utf-8")
		return res


	def get_buffer_frames(self, data):
		node_id = data["node_id"]
		timestamp = "".join([ch if ch not in self.invalid_chars else "_" for ch in str(datetime.datetime.now())])
		filename = f"{timestamp}_{node_id}.webm"

		delay_frames, duration_frames = data["tag_delay"] * self.fps, data["clip_duration"] * self.fps

		fourcc = cv2.VideoWriter_fourcc(*'VP80') # mp4v or webm
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

	# start saving images to buffer in another thread
	save_images_to_buffer_thread = threading.Thread(target=client.save_images_to_buffer, daemon=True)
	save_images_to_buffer_thread.start()

	# start listener to immanuel.local
	asyncio.create_task(client.listen())

	# start broadcasting to clients in another thread
	asyncio.create_task(client.webstreamer_broadcast())

	# start webstreaming clients for accepting clients
	await client.start_webstreamer()

	# start listening to main websocket for saving videos
	await client.listen()

if __name__ == '__main__':
	asyncio.run(main())
