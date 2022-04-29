"""
rpi client with cameras <-> WebSocketClient <-> IiwariStation

Listener to iiwari's websocket
Broadcaster to rpi clients with cameras
"""

import os
import json
import asyncio
import threading
import websockets


from db_handler import DBHandler
from ftp_server import FTPWrapper
from iiwari_client import IiwariWebSocketClient
from modules.common_funcs import calculate_distance

USE_MOUSE_SIM = True
IIWARI_LISTENER, BROADCASTER = None, None

BROADCASTER_MDNS_HOSTNAME = "dev-iiwari.local" # rpi will listen to this machine
BROADCASTER_PORT = 9876 # rpi will listen to this port


class RPiWebsocket():
	def __init__(self, id, ws):
		self.id = id
		self.ws = ws

	async def send_message(self, msg):
		await self.ws.send(msg)

	def is_open_connection(self):
		return self.ws.open


class Broadcaster:
	def __init__(self):
		self.clients = {}

		self.ip_address = BROADCASTER_MDNS_HOSTNAME
		self.port = BROADCASTER_PORT

		self.db_handler = DBHandler()
		self.triggers = self.db_handler.get_trigger_data()

		self.ftp_server = FTPWrapper()

	async def start_broadcasting_server(self):
		""" Boilerplate to create simple broadcasting server """
		print("Starting Broadcasting Server")
		async with websockets.serve(self.handler, self.ip_address, self.port):
			await asyncio.Future()  # run forever

	async def handler(self, websocket, path):
		""" Register rpi clients """
		async for data in websocket:
			data = json.loads(data)
			id = data["id"]

			print(f"Listener {id} just subscribed to the station")

			self.clients[id] = RPiWebsocket(id, websocket)

	async def broadcast(self):
		""" Broadcast current mouse positions to subscribers, handle closed connections """
		while True:
			await asyncio.sleep(0.1) # blocks other task without sleep

			if not IIWARI_LISTENER.is_tags_free() or len(self.clients) == 0:
				continue

			# compare triggers and tags
			closed_connections = []
			for trigger_data in self.triggers.values():
				cam_target = trigger_data["camera"]

				if cam_target not in self.clients:
					continue

				if not self.clients[cam_target].is_open_connection():
					closed_connections.append(cam_target)
					continue

				trigger_pos = trigger_data["trigger_position"]
				trigger_thresh_rad = trigger_data["trigger_threshold"] / 2

				tag_data = IIWARI_LISTENER.get_tags()
				for tag in tag_data.values():
					distance = calculate_distance(trigger_pos, tag.get_pos())

					if distance <= trigger_thresh_rad:
						trigger_data["node"] = tag.get_id() # add tag id for referencing which tag hit trigger
						data = json.dumps(trigger_data)
						await self.clients[cam_target].send_message(data)

			for ws in closed_connections:
				del self.clients[ws]

async def main():
	global IIWARI_LISTENER, BROADCASTER

	IIWARI_LISTENER = IiwariWebSocketClient()
	BROADCASTER = Broadcaster()

	# mouse simulator vs iiwari websocket
	if USE_MOUSE_SIM:
		asyncio.create_task(IIWARI_LISTENER.listen_mouse())
	else:
		IIWARI_LISTENER.listen_iiwari_websocket_connection_thread()

	asyncio.create_task(BROADCASTER.broadcast())

	await BROADCASTER.start_broadcasting_server()

if __name__ == '__main__':
	asyncio.run(main())
