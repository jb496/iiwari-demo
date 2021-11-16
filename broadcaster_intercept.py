"""
Websocket client to iiwari websocket
Broadcaster for sending iiwari tag data to clients
"""

import json
import asyncio
import pymysql
import requests
import threading
import websocket # iiwari client
import websockets

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
        self.ip_address = "192.168.100.49"
        self.port = 8765
        self.current_frame = None

    def grab_trigger_data(self):
        parse_pos = lambda json_pos: [json_pos["x"], json_pos["y"]]

        mydb = pymysql.connect(db='example',
                               user='dev',
                               passwd='',
                               host='localhost',
                               database='tags_db')

        cursor = mydb.cursor()

        table = "trigger_data"
        cursor.execute(f"SELECT * FROM {table}")

        trigger_data = cursor.fetchall()
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

                self.clients[id] = { "wsocket":websocket, "send_signal":False }

                if id == 'DEV':
                    self.grab_trigger_data()

                elif id == "STREAM":
                    self.clients[id]["cam_name"] = data["cam_name"]

                elif id == "STREAM-VIDEO-RESPONSE":
                    self.current_frame = data["base64"]

        except Exception as e:
            print(f"[ ERROR IN BROADCASTER HANDLER FUNCTION ] {e}")


        finally:
            if id in self.clients:
                del self.clients[id]

    async def broadcast(self):
        while True:
            await asyncio.sleep(0.1) # blocks other task without sleep

            tags = self.wsocket_client.tags

            if len(tags) == 0:
                continue

            # SEND ALL POINTS TO GUI FOR SHOWING TAG POSITIONS
            if "GUI" in self.clients:
                ws = self.clients["GUI"]["wsocket"]
                data = json.dumps({id:{"x":point.x, "y":point.y} for id, point in tags.items()})
                await ws.send(data)

            # SEND STREAMING DATA FOR SHOWING CAMERA FRAME
            elif "STREAM" in self.clients:
                cam_name = self.clients["STREAM"]["cam_name"]
                cam_ws = self.clients[cam_name]["wsocket"]
                await cam_ws.send(json.dumps({"header":"STREAM-VIDEO"}))

                if self.current_frame is not None:
                    stream_ws = self.clients["STREAM"]["wsocket"]
                    data = json.dumps({"base64":self.current_frame})
                    await stream_ws.send(data)

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

                    if intercepted:
                        trigger_data["node_id"] = tag_id # add tag id for refencing video

                        client_socket = self.clients[cam_name]["wsocket"]
                        await client_socket.send(json.dumps({"header":"SAVE-VIDEO", "data":trigger_data}))

                        print(f"[ {cam_name} ] SETTING SEND SIGNAL TO TRUE")
                        self.clients[cam_name]["send_signal"] = True

                        seconds_to_wait = trigger_data["tag_delay"] + trigger_data["clip_duration"]

                        set_signal_default_thread = threading.Timer(seconds_to_wait, self.set_signal_default, args=[cam_name,])
                        set_signal_default_thread.start()


    def set_signal_default(self, cam):
        if cam in self.clients:
            print(f"[ {cam} ] SETTING SEND SIGNAL TO FALSE")
            self.clients[cam]["send_signal"] = False


async def main():
    try:
        websocket_client = WebSocketClient()
        websocket_client.start_listening_thread()
        # asyncio.create_task(websocket_client.listen_mouse())

        broadcaster = Broadcaster(websocket_client)
        broadcaster.grab_trigger_data()
        asyncio.create_task(broadcaster.broadcast()) #coroutine
        await broadcaster.start_server()

    except Exception as e:
        print(f"[ ERROR IN MAIN ] {e}")


if __name__ == '__main__':
    asyncio.run(main())
