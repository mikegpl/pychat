import socket
import threading
import queue
import time


class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)

        # socket stuff
        self.host = host
        self.port = port
        self.buffer_size = 1024
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # processing connections
        self.connection_list = []
        self.login_list = {}
        self.queue = queue.Queue()

        # How does socket.bind() work?
        self.sock.bind((str(self.host), int(self.port)))
        # How to choose socket.listen() parameters?
        self.sock.listen(10)
        # What is and how does work socket.setblocking()
        self.sock.setblocking(False)

        # threads
        listener = threading.Thread(target=self.listen)
        receiver = threading.Thread(target=self.receive)
        sender = threading.Thread(target=self.send)

        listener.daemon = True
        listener.start()
        receiver.daemon = True
        receiver.start()
        sender.daemon = True
        sender.start()

        while True:
            message = input("->")
            if message == "quit":
                self.sock.close()
                break

    def listen(self):
        print("Initiated listener thread")
        while True:
            try:
                connection, adress = self.sock.accept()
                connection.setblocking(False)
                if connection not in self.connection_list:
                    self.connection_list.append(connection)
            except:
                pass

    def receive(self):
        print("Initiated receiver thread")
        while True:

            # Here probably would go selectors
            if len(self.connection_list) > 0:
                for connection in self.connection_list:
                    try:
                        # Selectors go here? If sth is ready to be received from client:
                        data = connection.recv(self.buffer_size)

                        # received data processing
                        if data and len(data.decode('utf-8')) > 1:

                            message = data.decode('utf-8')
                            # at most 4 splits (don't split the message if it contains ;)
                            message = message.split(";", 3)

                            # do stuff with message
                            if message[0] == 'login':
                                self.login_list[message[1]] = connection
                                print(message[1] + ' has logged in')

                                # Update list of active users
                                self.update_login_list()
                            elif message[0] == 'logout':
                                self.connection_list.remove(self.login_list[message[1]])
                                del self.login_list[message[1]]
                                print(message[1] + ' has logged out')

                                # Update list of active users
                                self.update_login_list()
                            elif message[0] == 'msg' and message[2] != 'all':
                                self.queue.put(('all', message[1], data))

                            else:
                                self.queue.put((message[2], message[1], data))

                    except:
                        # it must be pass, otherwise it would ~endlessly do stuff
                        pass
            time.sleep(0.050)

    def update_login_list(self):
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';all'
        self.queue.put(('all', 'server', logins.encode('utf-8')))

    def send(self):
        while True:
            if not self.queue.empty():
                target, origin, data = self.queue.get()
                if target == 'all':
                    self.send_to_all(origin, data)
                else:
                    self.send_to_one(target, origin, data)
                self.queue.task_done()

    def send_to_all(self, origin, data):
        # Here probably would go selectors (again)
        if origin != 'server':
            origin_address = self.login_list[origin]
        else:
            origin_address = None

        for connection in self.connection_list:
            if connection != origin_address:
                try:
                    connection.send(data)
                except:
                    self.connection_list.remove(connection)
                    for login, address in self.login_list:
                        if address == connection:
                            del self.login_list[login]
                    self.update_login_list()

    def send_to_one(self, target, data):
        try:
            target_address = self.login_list[target]
            target_address.send(data)
        except:
            self.connection_list.remove(target)
            for login, address in self.login_list.items():
                if address == target:
                    del self.login_list[login]
            self.update_login_list()


server = Server('localhost', 8888)
