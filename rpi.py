"""
RPi Client for listening to broadcaster
"""

import cv2
import json
import asyncio
import datetime
import threading
import websockets

from collections import deque

RPI_NAME = "cam1" # every rpi needs to have different RPI_NAME

BROADCASTER_MDNS_HOSTNAME = "dev.local" # listen to this device on local network
BROADCASTER_PORT = 9876 # listen to this port


class RPiClient:
	def __init__(self):
		self.broadcaster_uri = f"ws://{BROADCASTER_MDNS_HOSTNAME}:{BROADCASTER_PORT}"

		self.fps = 30
		self.max_seconds = 20
		self.max_buffer_frames = self.max_seconds * self.fps
		self.buffer = deque(maxlen=self.max_buffer_frames) # 20 secs at 30fps

		self.buffer_full = False
		self.can_process_save_video_request = False
		self.processing_video_request = False

		# change fourcc and extension for diff video format
		self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		self.extension = "mp4"

		self.frame_size = (640,480)

	def start_cam(self):
		""" Fill buffer with frames, no error handling for cam not found """
		cap = cv2.VideoCapture(0)

		while cap.isOpened():
			_, frame = cap.read()
			self.buffer.append(frame)

			if len(self.buffer) >= self.max_buffer_frames and not self.buffer_full:
				self.can_process_save_video_request = True
				self.buffer_full = True
				print("Buffer full. Ready to take request.")

			cv2.imshow(f"{RPI_NAME} feed", frame)

			if cv2.waitKey(1) & 0xFF == ord('q'):
				break

		cv2.destroyAllWindows()

	def save_video(self, data):
		""" Process to save video in current dir """
		clip_duration_fps = data["clip_duration"] * self.fps
		tag_delay_fps = data["tag_delay"] * self.fps

		filename = self.get_timestamp(data["node"])
		video_writer = cv2.VideoWriter(filename, self.fourcc, self.fps, self.frame_size)

		buffer = self.buffer.copy()
		vid_buffer = deque(maxlen=clip_duration_fps)

		# pop and save latest frames, ignore frames within tag delay fps frame
		for i in range(clip_duration_fps + tag_delay_fps):
			frame = buffer.pop()

			if i >= tag_delay_fps:
				vid_buffer.append(frame)

		# need another loop as vid_buffer is reversed
		for _ in range(clip_duration_fps):
			frame = vid_buffer.pop()
			video_writer.write(frame)

		self.processing_video_request = False
		self.can_process_save_video_request = True

	def get_timestamp(self, tag_id):
		""" e.g 21-04-22-11-38-44-tag_id """
		curr_timestamp = datetime.datetime.now()
		date = curr_timestamp.strftime("%x").replace("/","-")
		time = curr_timestamp.strftime("%X").replace(":","-")
		return f"{date}-{time}-{tag_id}.{self.extension}"

	async def listen(self):
		""" Listen for commands from broadcaster """
		async with websockets.connect(self.broadcaster_uri) as websocket:
			data = json.dumps({"id":RPI_NAME})
			await websocket.send(data)

			while True:
				msg = await websocket.recv()
				msg = json.loads(msg)

				if not self.can_process_save_video_request:

					if self.processing_video_request:
						print("Can't process request. Processing prior request.")
					else:
						print("Can't process request. Buffer is not full.")

					continue

				self.processing_video_request = True
				self.can_process_save_video_request = False

				# assuming we want the trigger in the middle of video
				clip_duration_mid = int(msg["clip_duration"] / 2)

				save_buffer_frames_thread = threading.Timer(clip_duration_mid, self.save_video, args=(msg,))
				save_buffer_frames_thread.start()


async def main():
	client = RPiClient()

	# start saving images to buffer in another thread
	take_images_thread = threading.Thread(target=client.start_cam, daemon=True)
	take_images_thread.start()

	await client.listen()


if __name__ == '__main__':
	asyncio.run(main())
