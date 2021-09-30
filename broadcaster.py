"""
Websocket client to iiwari websocket
Broadcaster for sending iiwari tag data to clients
"""

import json
import asyncio
import requests
import threading
import websocket # iiwari client
import websockets
import pymysql
from common_funcs import cred_login, get_site, calculate_distance


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
        id, x, y, z, ts = data["node"], data["x"], data["y"], data["z"], data["ts"]
        self.tags[id] = {"x":x, "y":y, "ts":ts}

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
        self.THRESHOLD = 50 # cm

        self.wsocket_client = websocket_client
        self.ip_address = "192.168.100.49"
        self.port = 8765

    def grab_trigger_data(self):
        parse_pos = lambda json_pos: [json_pos["x"], json_pos["y"]]

        table = "iiwari_triggers"
        mydb = pymysql.connect(db='example',
                               user='root',
                               passwd='',
                               host='localhost',
                               database='tags')

        cursor = mydb.cursor()

        cursor.execute(f"SELECT * FROM {table}")

        for data in cursor.fetchall():
            id, target, raw_pos, delay, duration = data
            self.triggers[id] = {"target":target, "pos":parse_pos(json.loads(raw_pos)), "delay":delay, "duration":duration}

    async def start_server(self):
        print("[ CREATING BROADCASTING SERVER ]")

        async with websockets.serve(self.handler, self.ip_address, self.port):
            await asyncio.Future()  # run forever

    async def handler(self, websocket, path):
        try:
            async for id in websocket:
                print(f"[ NEW CONNECTION ] {id} connected")

                self.clients[id] = { "wsocket":websocket, "send_signal":False }

                if id == 'DEV':
                    self.grab_trigger_data()

        finally:
            del self.clients[id]

    async def broadcast(self):
        while True:
            await asyncio.sleep(0.2) # blocks other task without sleep

            tags = self.wsocket_client.tags

            if len(tags) == 0:
                continue

            if "GUI" in self.clients:
                ws = self.clients["GUI"]["wsocket"]
                await ws.send(json.dumps(tags))

            for _, trigger_data in self.triggers.items():
                target = trigger_data["target"]

                if target not in self.clients:
                    continue

                if self.clients[target]["send_signal"] == True:
                    continue

                point1 = trigger_data["pos"]

                for tag_id, tag_data in tags.items():
                    point2 = [tag_data["x"], tag_data["y"]]

                    distance = calculate_distance(point1, point2)

                    if distance <= self.THRESHOLD:
                        print(f"[ SENDING SIGNAL ]")

                        trigger_data["ts"] = tags[tag_id]["ts"]

                        client_socket = self.clients[target]["wsocket"]
                        await client_socket.send(json.dumps(trigger_data))

                        self.clients[target]["send_signal"] = True
                        seconds_to_wait = trigger_data["delay"] + trigger_data["duration"]

                        set_signal_default_thread = threading.Timer(seconds_to_wait, self.set_signal_default, args=[target,])
                        set_signal_default_thread.start()


    def set_signal_default(self, target_id):
        print("setting default")
        if target_id in self.clients:
            self.clients[target_id]["send_signal"] = False


async def main():
    websocket_client = WebSocketClient()
    websocket_client.start_listening_thread()
    # asyncio.create_task(websocket_client.listen_mouse())

    broadcaster = Broadcaster(websocket_client)
    broadcaster.grab_trigger_data()
    asyncio.create_task(broadcaster.broadcast()) #coroutine
    await broadcaster.start_server()


if __name__ == '__main__':
    asyncio.run(main())
