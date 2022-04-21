import numpy as np

def calculate_distance(pointA, pointB):
	distance = np.sqrt((pointA[0]-pointB[0])**2 + (pointA[1]-pointB[1])**2) # distance between two points
	return distance
