"""
Simulates iiwari's tracking system
IiwariStation shouldn't have access to db, just for drawing purposes
"""

import cv2
import json
import socket
import asyncio
import threading
import websockets
import numpy as np

from db_handler import DBHandler
from modules.common_funcs import calculate_distance

# drawing
LAYOUT_WIDTH, LAYOUT_HEIGHT = 300, 600
LINE_THICKNESS = 2
BLACK = (0, 0, 0)
FILL = -1

MOUSE_SIM_ADDRESS = "localhost" # broadcaster will listen to this address
MOUSE_SIM_PORT = 8785 # broadcaster will listen to this port


class IiwariStation:
	def __init__(self):
		self.x = None
		self.y = None

		self.clients = set()

		self.ip_address = MOUSE_SIM_ADDRESS
		self.port = MOUSE_SIM_PORT

		# only one tag
		self.node_id = "tag1"

		# db data
		self.triggers = None

	async def start_broadcasting_server(self):
		""" Boilerplate to create simple broadcasting server """
		async with websockets.serve(self.handler, self.ip_address, self.port):
			await asyncio.Future()  # run forever

	async def handler(self, websocket, path):
		""" Register listener to set for returning x, y positions """
		async for _ in websocket:
			print("A broadcaster just subscribed to the station")
			self.clients.add(websocket)

	async def broadcast(self):
		""" Broadcast current mouse positions to subscribers, handle closed connections """
		while True:
			await asyncio.sleep(0.1) # blocks other task without sleep

			if self.x is None or self.y is None:
				continue

			# copy iiwari data format
			msg = json.dumps({
				"node": self.node_id,
				"x": self.x,
				"y": self.y,
				"z": 1
			})

			closed_connections = []
			for ws in self.clients:
				if ws.open:
					await ws.send(msg)
				else:
					closed_connections.append(ws)

			for closed_ws in closed_connections:
				self.clients.remove(closed_ws)

	def start_mouse_dev(self):
		""" Simulate tag position with mouse """
		window_name = "Room Layout"

		img = np.ones([LAYOUT_HEIGHT, LAYOUT_WIDTH, 3])
		cv2.namedWindow(window_name, cv2.WINDOW_GUI_NORMAL)

		db_handler = DBHandler()
		self.triggers = db_handler.get_trigger_data()

		# draw triggers and its thresholds
		for trigger_data in self.triggers.values():
			trigger_pos = tuple(trigger_data["trigger_position"])
			cv2.circle(img, trigger_pos, LINE_THICKNESS, BLACK, FILL)
			cv2.circle(img, trigger_pos, int(trigger_data["trigger_threshold"] / 2), BLACK, LINE_THICKNESS)

		while True:
			cv2.setMouseCallback(window_name, self.mouse_tracker)

			cv2.imshow(window_name, img)

			if cv2.waitKey(1) & 0xFF == ord('q'):
				break

		cv2.destroyAllWindows()

	def mouse_tracker(self, event, x, y, flags, params):
		self.x, self.y = x, y


async def main():
	station = IiwariStation()

	# coroutines
	asyncio.create_task(station.broadcast())

	# coroutine but on thread
	cv2_thread = threading.Thread(target=station.start_mouse_dev, daemon=True)
	cv2_thread.start()

	# main thread
	await station.start_broadcasting_server()


if __name__ == "__main__":
	asyncio.run(main())
