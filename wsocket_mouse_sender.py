import websockets
import json
import asyncio
import cv2
import numpy as np
import threading
import pymysql

pos = None
triggers = {}

def mouse_tracker(event, x, y, flags, params):
    global pos
    x, y, = int(x*5), int(y*5)
    pos = json.dumps({
        "node":None,
        "x":x,
        "y":y,
        "z":1,
        "ts":"Jan 01"
    })


def update_pos():
    img = np.ones([592, 182, 3])
    cv2.namedWindow("Iiwari site", cv2.WINDOW_NORMAL)

    sites = [data["pos"] for _, data in triggers.items()]

    while True:
        cv2.setMouseCallback("Iiwari site", mouse_tracker)

        for site in sites:
            x, y = int(site[0] / 5), int(site[1] / 5)
            cv2.circle(img, (x, y), 5, (0,0,0), -1) # target

        cv2.imshow("Iiwari site", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


def grab_triggers():
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


async def handler(websocket, path):
    print("[NEW CONNECTION]")
    while True:
        if pos is not None:
            await websocket.send(pos)

async def main():
    grab_triggers()

    mouse_tracker_thread = threading.Thread(target=update_pos, daemon=True)
    mouse_tracker_thread.start()

    print("[CREATING SERVER]")
    async with websockets.serve(handler, "localhost", 8780):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    asyncio.run(main())
