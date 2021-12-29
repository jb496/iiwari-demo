from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

import socket

local_address = socket.gethostbyname(socket.gethostname())

authorizer = DummyAuthorizer()
authorizer.add_user("test", "testpw", "/home/dev/Desktop/iiwari", perm="elradfmw")

handler = FTPHandler
handler.authorizer = authorizer

server = FTPServer((local_address, 1026), handler)

server.serve_forever()
