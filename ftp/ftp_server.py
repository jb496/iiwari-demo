from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

authorizer = DummyAuthorizer()
authorizer.add_user("user", "12345", "/home/dev", perm="elradfmw")
authorizer.add_anonymous("/home/dev", perm="elradfmw")

handler = FTPHandler
handler.authorizer = authorizer

# server = FTPServer(("127.0.0.1", 1026), handler)
server = FTPServer(("192.168.100.49", 1026), handler)

server.serve_forever()
