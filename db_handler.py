import json
import pymysql

# DB LOGIN DETAILS
USER = "iiwari"
HOST = "localhost"
PASSWORD = "iiwari_pw"
DATABASE = "iiwari_db"

class DBHandler:
	def __init__(self):
		self.db = pymysql.connect(db='example',
							   user=USER,
							   passwd=PASSWORD,
							   host=HOST,
							   database=DATABASE)

		self.db_cursor = self.db.cursor()

		self.camera_table = "camera_table"
		self.camera_data = self.get_cam_data()

		self.trigger_table = "trigger_table"
		self.trigger_data = self.get_trigger_data()

	def get_cam_data(self):
		""" Grab registered cameras """
		self.db_cursor.execute(f"SELECT * FROM {self.camera_table}")
		return self.db_cursor.fetchall()

	def get_trigger_data(self):
		""" Grab registered triggers """
		triggers = {}

		self.db_cursor.execute(f"SELECT * FROM {self.trigger_table}")

		for data in self.db_cursor.fetchall():
			id, camera_name, trigger_pos, trigger_thresh, clip_duration, tag_delay = data
			triggers[id] = {
				"camera":camera_name,
				"trigger_position":json.loads(trigger_pos),
				"trigger_threshold":trigger_thresh,
				"clip_duration":clip_duration,
				"tag_delay":tag_delay
			}

		return triggers
