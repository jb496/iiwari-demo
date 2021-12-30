import os
import math
import json
import numpy as np

def cred_login(session, username, password):
    headers = {"Content-Type": "application/json", "Accept": "text/plain"}
    url = "https://dash.iiwari.cloud/api/v1/users/login"
    creds = {"Email":username, "Password":password}
    request = session.post(url, json=creds, headers=headers)


def get_site(session):
    url = "https://dash.iiwari.cloud/api/v1/sites"
    sites = session.get(url)
    data = sites.json()[0]
    site_id = data["id"]
    return site_id


def calculate_distance(pointA, pointB):
	distance = int(np.sqrt((pointA[0]-pointB[0])**2 + (pointA[1]-pointB[1])**2)) # distance between two points
	return distance



def check_intercept(circle_centrepoint, circle_r, p0, p1):
    if p0 == p1:
        distance = calculate_distance(circle_centrepoint, p1)

        if distance <= circle_r:
            return True
        else:
            return False

    p0 = {"x":p0[0], "y":p0[1]}
    p1 = {"x":p1[0], "y":p1[1]}
    circle = {"x":circle_centrepoint[0], "y":circle_centrepoint[1], "r":circle_r}

    a = (p1["x"] - p0["x"]) ** 2 + (p1["y"] - p0["y"]) ** 2
    b = 2 * (p1["x"] - p0["x"]) * (p0["x"] - circle["x"]) + 2 * (p1["y"] - p0["y"]) * (p0["y"] - circle["y"])
    c = (p0["x"] - circle["x"]) ** 2 + (p0["y"] - circle["y"]) ** 2 - (circle["r"]**2)

    discriminant = (b ** 2) - 4 * a * c

    if discriminant < 0:
        return False

    discriminant = math.sqrt(discriminant)

    t1 = (-b - discriminant)/(2*a)
    t2 = (-b + discriminant)/(2*a)

    if t1 < 0 and t2 < 0 or t1 > 1 and t2 > 1:
        return False

    return True


def get_hardware_id(key):
    cmd_res = os.popen(f"hostnamectl | grep '{key}'").read()
    machine_key, id = cmd_res.strip().split(": ")
    return id
