import json
import asyncio
import requests
import threading
import websocket # iiwari client
import websockets

import pymysql

from common_funcs import cred_login, get_site, calculate_distance

tags = {}
clients = {}
triggers = {}
THRESHOLD = 100 # cm


def wsocket_client_listener(session, site_id):
    # websocket
    key, value = session.cookies.items()[0]
    cookies = f"{key}={value}"

    wss = websocket.WebSocketApp(f"wss://dash.iiwari.cloud/api/v1/sites/{site_id}/locations/stream?",
                                on_message=on_message,
                                cookie=cookies)

    wss.run_forever()

async def listen_mouse():
    uri = "ws://localhost:8780"

    async with websockets.connect(uri) as websocket:
        await websocket.send(f"cam3")
        while True:
            msg = await websocket.recv()
            on_message(None, msg)


def on_message(ws, message):
    global tags
    data = json.loads(message)
    id, x, y, z, ts = data["node"], data["x"], data["y"], data["z"], data["ts"]
    tags[id] = {"x":x, "y":y, "ts":ts}


async def handler(websocket, path):
    try:
        async for id in websocket:
            print(f"[NEW CONNECTION] {id} connected")
            clients[id] = {
                "wsocket":websocket,
                "send_signal":False
            }

            if id == 'DEV':
                grab_triggers()

    finally:
        del clients[id]


async def broadcast():
    while True:

        if "GUI" in clients:
            ws = clients["GUI"]["wsocket"]
            await ws.send(json.dumps(tags))

        for _, trigger_data in triggers.items():

            target = trigger_data["target"]
            if target not in clients:
                continue

            if clients[target]["send_signal"] == True:
                continue

            point1 = trigger_data["pos"]

            for tag_id, tag_data in tags.items():
                point2 = [tag_data["x"], tag_data["y"]]

                distance = calculate_distance(point1, point2)

                if distance <= THRESHOLD:
                    print("sending")

                    client_socket = clients[target]["wsocket"]
                    await client_socket.send(json.dumps(trigger_data))

                    clients[target]["send_signal"] = True
                    seconds_to_wait = trigger_data["delay"] + trigger_data["duration"]

                    set_signal_default_thread = threading.Timer(seconds_to_wait, set_signal_default, args=(target,))
                    set_signal_default_thread.start()

        await asyncio.sleep(0.2)

def set_signal_default(target_id):
    global clients

    if target_id in clients:
        clients[target_id]["send_signal"] = False


def grab_triggers():
    print("[CHECKING DB]")
    global triggers

    mydb = pymysql.connect(
    db='example',
    user='root',
    passwd='',
    host='localhost',
    database='tags')

    TABLE = "iiwari_triggers"

    my_cursor = mydb.cursor()

    my_cursor.execute(f"SELECT * FROM {TABLE}")
    data = my_cursor.fetchall()

    for x in data:
        id, target, json_pos, delay, duration = x[0], x[1], json.loads(x[2]), x[3], x[4]
        pos = [json_pos["x"], json_pos["y"]]
        triggers[id] = {"target":target, "pos":pos, "delay":delay, "duration":duration}


async def main():
    grab_triggers()

    asyncio.create_task(listen_mouse())

    asyncio.create_task(broadcast())

    print("[CREATING BROADCAST SERVER]")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())
