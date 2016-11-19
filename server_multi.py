import socket
import threading
import queue
import time
import select


class Server(threading.Thread):
    def __init__(self, host, port):
        # Main thread
        super().__init__(daemon=False)

        # Socket variables
        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Variables for processing connections
        self.message_queues = {}
        self.connections_by_login = {}
        self.connection_list = []
        self.login_list = []

        self.lock = threading.RLock()

        # Socket setup
        self.shutdown = False
        try:
            self.sock.bind((str(self.host), int(self.port)))
            self.sock.listen(10)
            self.sock.setblocking(False)
        except socket.error:
            self.shutdown = True

        # Threads
        if not self.shutdown:
            listener = threading.Thread(target=self.listen, daemon=True)
            listener.start()

        # Main loop
        while not self.shutdown:
            message = input()
            if message == 'quit':
                for sock in self.connection_list:
                    sock.close()
                self.shutdown = True
                self.sock.close()

                # End of __init__()

    def listen(self):
        print('Initiated listener thread')
        while True:
            try:
                self.lock.acquire()
                connection, address = self.sock.accept()
                connection.setblocking(False)
                if connection not in self.connection_list:
                    self.connection_list.append(connection)

                new_client = ClientThread(self, connection, address)
                self.message_queues[connection] = queue.Queue()
            except socket.error:
                time.sleep(0.05)
            finally:
                self.lock.release()


class ClientThread(threading.Thread):
    def __init__(self, master, sock, address):
        super().__init__(daemon=True)
        print('New client thread launched, printing servers list of clients')
        self.master = master
        self.socket = sock
        self.address = address
        self.buffer_size = 2048
        self.login = ''
        print('New thread started for connection from ' + str(self.address))
        self.run()

    def run(self):
        while True:
            try:
                data = self.socket.recv(self.buffer_size)
            except socket.error:
                data = None
                time.sleep(0.05)
                continue
            if data:
                print(data.decode('utf-8'))


    def update_login_list(self):
        logins = 'login'
        for login in self.master.login_list:
            logins += ';' + login
        logins += ';ALL' + '\n'
        logins = logins.encode('utf-8')
        for connection, connection_queue in self.master.message_queues.items():
            connection_queue.put(logins)


server = Server('localhost', 8888)
