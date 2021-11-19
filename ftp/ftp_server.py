from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


authorizer = DummyAuthorizer()
authorizer.add_user("test", "testpw", "/home/dev/Desktop/iiwari", perm="elradfmw")

handler = FTPHandler
handler.authorizer = authorizer

server = FTPServer(("192.168.100.49", 1026), handler)

server.serve_forever()
