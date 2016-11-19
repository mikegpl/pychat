import socket
import threading
import queue
import time


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
        self.connection_list = []
        self.login_list = {}
        self.queue = queue.Queue()

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
            listener = threading.Thread(target=self.listen)
            receiver = threading.Thread(target=self.receive)
            sender = threading.Thread(target=self.send)
            self.lock = threading.RLock()

            listener.daemon = True
            listener.start()
            receiver.daemon = True
            receiver.start()
            sender.daemon = True
            sender.start()

        # Main server loop
        while not self.shutdown:
            message = input()
            if message == "quit":
                self.sock.close()
                self.shutdown = True

        # End of __init__

    # Methods used directly by threads
    # 1) listener - self.listen()

    def listen(self):
        print('Initiated listener thread')
        while True:
            try:
                self.lock.acquire()
                connection, address = self.sock.accept()
                connection.setblocking(False)
                if connection not in self.connection_list:
                    self.connection_list.append(connection)
            except socket.error:
                pass
            finally:
                self.lock.release()
            time.sleep(0.050)

    # 2) receiver - self.receive()
    def receive(self):
        print('Initiated receiver thread')
        while True:
            if len(self.connection_list) > 0:
                for connection in self.connection_list:
                    try:
                        self.lock.acquire()
                        data = connection.recv(self.buffer_size)
                    except socket.error:
                        data = None
                    finally:
                        self.lock.release()

                    # Process received data
                    if data:
                        message = data.decode('utf-8')
                        # at most 4 splits (don't split the message if it contains ;)
                        message = message.split(";", 3)

                        # Process messages
                        # 1) new user logged in
                        if message[0] == 'login':
                            tmp_login = message[1]
                            # if nickname already in use
                            while message[1] in self.login_list:
                                message[1] += '#'
                            if tmp_login != message[1]:
                                prompt = 'msg;server;' + message[1] + ';Login ' + tmp_login \
                                         + ' already in use. Your login changed to ' + message[1] + '\n'
                                self.queue.put((message[1], 'server', prompt.encode('utf-8')))

                            self.login_list[message[1]] = connection
                            print(message[1] + ' has logged in')

                            # Update list of active users
                            self.update_login_list()

                        # 2) user logged out
                        elif message[0] == 'logout':
                            self.connection_list.remove(self.login_list[message[1]])
                            if message[1] in self.login_list:
                                del self.login_list[message[1]]
                            print(message[1] + ' has logged out')

                            # Update list of active users
                            self.update_login_list()

                        # 3) Message from one user to another (msg;origin;target;message)
                        elif message[0] == 'msg' and message[2] != 'all':
                            msg = data.decode('utf-8') + '\n'
                            data = msg.encode('utf-8')
                            self.queue.put((message[2], message[1], data))

                        # 4) Message from one user to all users (msg;origin;all;message)
                        elif message[0] == 'msg':
                            msg = data.decode('utf-8') + '\n'
                            data = msg.encode('utf-8')
                            self.queue.put(('all', message[1], data))

    # 3) sender - self.send()
    def send(self):
        print('Initiated sender thread')
        while True:
            if not self.queue.empty():
                target, origin, data = self.queue.get()
                if target == 'all':
                    self.send_to_all(origin, data)
                else:
                    self.send_to_one(target, data)
                self.queue.task_done()
            else:
                time.sleep(0.05)

    # Methods used by threads:
    # 1) sending messages

    # Send to all users except origin
    def send_to_all(self, origin, data):
        if origin != 'server':
            origin_address = self.login_list[origin]
        else:
            origin_address = None

        for connection in self.connection_list:
            if connection != origin_address:
                try:
                    self.lock.acquire()
                    connection.send(data)
                except socket.error:
                    self.remove_connection(connection)
                finally:
                    self.lock.release()

    # Send to one user, specified as target
    def send_to_one(self, target, data):
        target_address = self.login_list[target]
        try:
            self.lock.acquire()
            target_address.send(data)
        except socket.error:
            self.remove_connection(target_address)
        finally:
            self.lock.release()

    # Remove connection if needed
    def remove_connection(self, connection):
        self.connection_list.remove(connection)
        for login, address in self.login_list.items():
            if address == connection:
                del self.login_list[login]
                break
        self.update_login_list()

    # Update list of logged in users
    def update_login_list(self):
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';all' + '\n'
        self.queue.put(('all', 'server', logins.encode('utf-8')))

# Create new server with (IP, port)
if __name__ == '__main__':
    server = Server('localhost', 8888)
