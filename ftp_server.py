from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

FTP_PORT = 1026
FTP_USER = "test"
FTP_PASSWORD = "testpw"
FTP_VIDEO_PATH = "/home/immanuel/Desktop/iiwari_demo/videos"

FTP_HOSTNAME = "dev-iiwari.local" # rpi will listen to this machine


class FTPWrapper:
	def __init__(self):
		self.authorizer = DummyAuthorizer()
		self.authorizer.add_user(FTP_USER, FTP_PASSWORD, FTP_VIDEO_PATH, perm="elradfmw")

		self.handler = FTPHandler
		self.handler.authorizer = authorizer

		server = FTPServer((FTP_HOSTNAME, FTP_PORT), self.handler)

		serve_thread = threading.Thread(target=self.serve_forever, daemon=True)
		serve_thread.start()

	def serve_forever(self):
		self.server.serve_forever()
