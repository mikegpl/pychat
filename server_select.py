import socket
import select
import queue


class Server(object):
    def __init__(self, host, port):
        # socket init
        self.host = host
        self.port = port
        self.buffer_size = 1024
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # processing connections
        self.connection_list = []
        self.login_list = {}
        self.queue = queue.Queue()

        # for quitting
        self.exit = ''

        # socket setup
        self.sock.bind((str(self.host), int(self.port)))
        self.sock.listen(10)
        self.sock.setblocking(False)

        



server = Server('localhost', 8888)
