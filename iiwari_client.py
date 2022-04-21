"""
Listener to iiwari's websocket
"""

import json
import asyncio
import requests
import threading
import websocket # iiwari uses this package
import websockets # standard websocket library


# LOGIN_DETAILS
EMAIL = "Dan@501entertainment.co.uk"
PASSWORD = "kREBu5rRdarDqs2Z"

MOUSE_SIM_ADDRESS = "localhost" # listen to this address
MOUSE_SIM_PORT = 8785 # listen to this port


class Tag:
	def __init__(self, id):
		self.id = id
		self.x = None
		self.y = None

	def add_pos(self, x, y):
		self.x = x
		self.y = y

	def get_pos(self):
		return self.x, self.y

	def get_id(self):
		return self.id


class IiwariWebSocketClient:
	def __init__(self):
		self.session = self.cred_login(EMAIL, PASSWORD)

		self.site_id = self.get_site(self.session)
		self.iiwari_uri = f"wss://dash.iiwari.cloud/api/v1/sites/{self.site_id}/locations/stream?"

		# testing with mouse
		self.mouse_uri = f"ws://{MOUSE_SIM_ADDRESS}:{MOUSE_SIM_PORT}"

		self.tags = {}

	def cred_login(self, username, password):
		session = requests.Session();
		headers = {"Content-Type": "application/json", "Accept": "text/plain"}
		url = "https://dash.iiwari.cloud/api/v1/users/login"
		creds = {"Email":username, "Password":password}
		request = session.post(url, json=creds, headers=headers)
		return session

	def get_site(self, session):
		""" Return first site id for seeking tag streams """
		url = "https://dash.iiwari.cloud/api/v1/sites"
		sites = session.get(url)
		data = sites.json()[0]
		site_id = data["id"]
		return site_id

	def listen_iiwari_websocket_connection(self):
		key, value = self.session.cookies.items()[0]
		cookies = f"{key}={value}"

		wss = websocket.WebSocketApp(self.iiwari_uri,
									on_message=self.on_message,
									cookie=cookies)
		wss.run_forever()

	def on_message(self, ws, msg):
		data = json.loads(msg)

		node_id = data["node"]
		x, y, z = data["x"], data["y"], data["z"]

		print(node_id, x, y, z)

		if node_id not in self.tags:
			node = Tag(node_id)
			node.add_pos(x, y)
			self.tags[node_id] = node

		else:
			self.tags[node_id].add_pos(x, y)

	def listen_iiwari_websocket_connection_thread(self):
		listen_thread = threading.Thread(target=self.listen_iiwari_websocket_connection, daemon=True)
		listen_thread.start()

	async def listen_mouse(self):
		async with websockets.connect(self.mouse_uri) as websocket:

			await websocket.send(f"hello iiwari station")
			while True:
				msg = await websocket.recv()
				self.on_message(None, msg)

	def get_tags(self):
		return self.tags

	def is_tags_free(self):
		return len(self.get_tags()) > 0
