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
