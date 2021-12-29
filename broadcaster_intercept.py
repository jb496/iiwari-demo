"""
Websocket client to iiwari websocket
Broadcaster for sending iiwari tag data to clients
"""

import os
import json
import asyncio
import pymysql
import requests
import threading
import websocket # iiwari client
import websockets

import socket

from collections import deque
from modules.common_funcs import cred_login, get_site, check_intercept


class Point():
	def __init__(self, id):
		self.id = id
		self.x = None
		self.y = None
		self.pos = deque(maxlen=2)

	def add_pos(self, x, y):
		self.pos.append([x,y])
		self.x = x
		self.y = y


class WebSocketClient:
	def __init__(self):
		self.email = "Dan@501entertainment.co.uk"
		self.password = "kREBu5rRdarDqs2Z"

		self.session = requests.Session();
		cred_login(self.session, self.email, self.password)

		self.site_id = get_site(self.session)
		self.iiwari_uri = f"wss://dash.iiwari.cloud/api/v1/sites/{self.site_id}/locations/stream?"

		self.tags = {}

	def start_listening(self):
		key, value = self.session.cookies.items()[0]
		cookies = f"{key}={value}"

		wss = websocket.WebSocketApp(self.iiwari_uri,
									on_message=self.on_message,
									cookie=cookies)
		wss.run_forever()

	def on_message(self, ws, msg):
		data = json.loads(msg)
		node_id, x, y, z = data["node"], data["x"], data["y"], data["z"]

		if node_id not in self.tags:
			node = Point(node_id)
			node.add_pos(x, y)
			node.add_pos(x, y)
			self.tags[node_id] = node

		else:
			self.tags[node_id].add_pos(x, y)

	def start_listening_thread(self):
		listen_thread = threading.Thread(target=self.start_listening, daemon=True)
		listen_thread.start()

	async def listen_mouse(self):
		uri = "ws://localhost:8780"

		async with websockets.connect(uri) as websocket:
			await websocket.send(f"WEBSOCKET LISTENER")
			while True:
				msg = await websocket.recv()
				self.on_message(None, msg)


class Broadcaster:
	def __init__(self, websocket_client):
		self.clients = {}
		self.triggers = {}

		self.wsocket_client = websocket_client
		self.ip_address = socket.gethostbyname(socket.gethostname())
		self.port = 8765
		self.current_frame = None

		self.VID_PATH = r"/vids" # vids created by client sent into this public folder
		self.TARGET_PATH = r"/var/www/webApp/webApp/static/videos" # move vids into this admin folder
		self.CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

		self.db = None
		self.db_cursor = None

		self.cam_data = None
		self.cam_data_table = "cam_data"

	def initDB(self):
		self.db = pymysql.connect(db='example',
							   user='dev',
							   passwd='',
							   host='localhost',
							   database='tags_db')

		self.db_cursor = self.db.cursor()

		self.grab_cam_data()
		self.grab_trigger_data()


	def grab_cam_data(self):
		self.db_cursor.execute(f"SELECT * FROM {self.cam_data_table}")
		self.cam_data = self.db_cursor.fetchall()
		print(self.cam_data)

	def grab_trigger_data(self):
		parse_pos = lambda json_pos: [json_pos["x"], json_pos["y"]]

		table = "trigger_data"
		self.db_cursor.execute(f"SELECT * FROM {table}")

		trigger_data = self.db_cursor.fetchall()
		print(f"List of triggers: {trigger_data}")

		for data in trigger_data:
			id, cam_name, cam_pos, cam_fov, trigger_pos, trigger_thresh, clip_duration, tag_delay = data
			self.triggers[id] = {
				"cam_name":cam_name,
				"trigger_pos":parse_pos(json.loads(trigger_pos)),
				"tag_delay":tag_delay,
				"clip_duration":clip_duration,
				"trigger_thresh":trigger_thresh
			}

	async def start_server(self):
		print("[ CREATING BROADCASTING SERVER ]")

		async with websockets.serve(self.handler, self.ip_address, self.port):
			await asyncio.Future()  # run forever

	async def handler(self, websocket, path):
		id = None
		try:
			async for data in websocket:
				data = json.loads(data)
				id = data["id"]

				print(f"[ NEW CONNECTION ] {id} connected")

				self.clients[id] = { "wsocket":websocket, "send_signal":False}

				if id == 'DEV':
					self.grab_trigger_data()

				elif id == "START-STREAM":
					# check streaming cam is available and send stream command
					cam_target = data["cam_name"]
					if cam_target in self.clients:
						print(f"sending stream command to {cam_target}")

						cam_target_ws = self.clients[cam_target]["wsocket"]
						msg = json.dumps({"header":"START-STREAM-SERVER"})
						await cam_target_ws.send(msg)

				else:
					# add/update db for camera local address
					cam_ids = [cam_id for key, cam_id, address in self.cam_data]
					if id not in cam_ids:
						self.add_cam_data(id, data["address"])
					else:
						self.update_cam_data(id, data["address"])
						self.clients[id]["buffer_full"] = data["buffer_full"]

		except Exception as e:
			print(f"[ ERROR IN BROADCASTER HANDLER FUNCTION ] {e}")

		finally:
			if id in self.clients:
				del self.clients[id]

	def add_cam_data(self, cam_id, address):
		sql_cmd = "INSERT INTO {} (cam_name, cam_address) VALUES {};".format(self.cam_data_table, (cam_id, address))
		self.db_cursor.execute(sql_cmd)
		self.db.commit()

	def update_cam_data(self, cam_name, address):
		sql_cmd = "UPDATE {} SET cam_address='{}' WHERE cam_name='{}';".format(self.cam_data_table, address, cam_name)
		print(sql_cmd)

		self.db_cursor.execute(sql_cmd)
		self.db.commit()


	async def broadcast(self):
		while True:
			await asyncio.sleep(0.1) # blocks other task without sleep

			tags = self.wsocket_client.tags

			if len(tags) == 0:
				continue


			# SEND ALL POINTS TO GUI FOR SHOWING TAG POSITIONS
			if "DEV" in self.clients:
				ws = self.clients["DEV"]["wsocket"]
				data = json.dumps({id:{"x":point.x, "y":point.y} for id, point in tags.items()})
				await ws.send(data)

			# LOGIC FOR SENDING COMMANDS TO RASP MODULES
			for _, trigger_data in self.triggers.items():
				cam_name = trigger_data["cam_name"]

				if cam_name not in self.clients:
					continue

				if self.clients[cam_name]["send_signal"] == True:
					continue

				for tag_id, tag_data in tags.items():

					# TAG DATA POS: [[prev.x, prev.y], [new.x, new.y]]
					p1 = tag_data.pos[0]
					p2 = tag_data.pos[1]

					intercepted = check_intercept(trigger_data["trigger_pos"], trigger_data["trigger_thresh"], p1, p2)

					if intercepted and not self.clients[cam_name]["send_signal"] and self.clients[cam_name]["buffer_full"]:
						trigger_data["node_id"] = tag_id # add tag id for refencing video

						msg = json.dumps({
							"header":"SAVE-VIDEO",
							"data":trigger_data
						})

						client_socket = self.clients[cam_name]["wsocket"]
						await client_socket.send(msg)

						print(f"[ {cam_name} ] SETTING SEND SIGNAL TO TRUE")
						self.clients[cam_name]["send_signal"] = True

						wait_secs = trigger_data["tag_delay"] + trigger_data["clip_duration"]
						reset_cam_state_thread = threading.Timer(wait_secs, self.transfer_file, args=[cam_name])
						reset_cam_state_thread.start()


	def transfer_file(self, cam):
		print("[ QUERYING VIDEO WRITE FINISHED ]")

		vid_path = os.path.join(self.CURRENT_PATH + self.VID_PATH)
		videos = os.listdir(vid_path)

		if len(videos) != 0:
			if cam in self.clients:
				print(f"[ RESETTING SEND SIGNAL TO FALSE ] {cam}")
				self.clients[cam]["send_signal"] = False

			for filename in videos:
				file = os.path.join(vid_path, filename)
				# print(f"echo 5522 | sudo -S mv {file} {self.TARGET_PATH}") # one line cmd transfer file
				os.system(f"echo 5522 | sudo -S mv {file} {self.TARGET_PATH}")

		else:
			print("[ ERROR ] NO FILES FOUND, QUERYING AGAIN IN 1s")
			query_file_thread = threading.Timer(1, self.transfer_file, args=[cam])
			query_file_thread.start()


async def main():
	try:
		websocket_client = WebSocketClient()
		websocket_client.start_listening_thread()
		# asyncio.create_task(websocket_client.listen_mouse())

		broadcaster = Broadcaster(websocket_client)
		broadcaster.initDB()
		asyncio.create_task(broadcaster.broadcast()) #coroutine
		await broadcaster.start_server()

	except Exception as e:
		print(f"[ ERROR IN MAIN ] {e}")


if __name__ == '__main__':
	asyncio.run(main())
