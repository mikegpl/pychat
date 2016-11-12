import socket
import threading
import time


class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.buffer_size = 1024
        self.connection_list = []
        self.login_list = {}
        # Why those parameters
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # How does socket.bind() work?
        self.sock.bind((str(self.host), int(self.port)))

        # How to choose socket.listen() parameters?
        self.sock.listen(10)

        # What is and how does work socket.setblocking()
        self.sock.setblocking(False)

        listener = threading.Thread(target=self.listen)
        processor = threading.Thread(target=self.process)

        listener.daemon = True
        listener.start()
        processor.daemon = True
        processor.start()

        while True:
            message = input("->")
            if message == "quit":
                self.sock.close()
                break

    def listen(self):
        while True:
            try:
                connection, address = self.sock.accept()
                connection.setblocking(False)
                if connection not in self.connection_list:
                    self.connection_list.append(connection)
            except:
                pass

    def process(self):
        print("Initiated processing thread")
        while True:
            if len(self.connection_list) > 0:
                for connection in self.connection_list:
                    try:
                        data = connection.recv(self.buffer_size)
                        if data:
                            message = data.decode('utf-8')
                            message = message.split(";")
                            print(message)

                            if message[0] == 'login' and len(message) > 1:
                                self.login_list[message[1]] = connection
                                print(self.login_list)
                                prompt = message[1] + " has logged in"
                                self.send_to_all(connection, prompt.encode('utf-8'))
                            elif message[0] == 'logout' and len(message) > 1:
                                self.connection_list.remove(self.login_list[message[1]])
                                del self.login_list[message[1]]
                                prompt = message[1] + " has logged out"
                                self.send_to_all(connection, prompt.encode('utf-8'))
                            elif message[0] == 'list':
                                print("DUPA")
                                print(self.login_list)
                                active_users = 'Logins:'
                                for login, address in self.login_list.items():
                                    print(login)
                                    active_users += '\n' +login
                                if active_users == 'Logins:':
                                    active_users = 'None'
                                print(active_users)
                                self.send_to_one(connection, active_users)
                            elif message[0] == 'msg' and message[2] != 'all':
                                prompt = message[1] + ": " + message[3]
                                target = self.login_list[message[2]]
                                if target:
                                    self.send_to_one(target, prompt)
                            else:
                                prompt = message[1] + ": " + message[3]
                                self.send_to_all(connection, prompt.encode('utf-8'))
                    except:
                        pass

    def send_to_all(self, origin, data):
        for connection in self.connection_list:
            if connection != origin:
                try:
                    connection.send(data)
                except:
                    self.connection_list.remove(connection)
                    for login, address in self.login_list:
                        if address == connection:
                            del self.login_list[login]

    def send_to_one(self, target, message):
        try:
            data = message.encode('utf-8')
            target.send(data)
        except:
            self.connection_list.remove(target)
            for login, address in self.login_list.items():
                if address == target:
                    del self.login_list[login]


server = Server('localhost', 8888)
