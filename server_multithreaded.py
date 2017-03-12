import socket
import threading
import queue
import time

ENCODING = 'utf-8'
HOST = 'localhost'
PORT = 8888


class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=False, target=self.run)

        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connection_list = []
        self.login_list = {}
        self.queue = queue.Queue()

        self.shutdown = False
        try:
            self.sock.bind((str(self.host), int(self.port)))
            self.sock.listen(10)
            self.sock.setblocking(False)
        except socket.error:
            self.shutdown = True

        if not self.shutdown:
            listener = threading.Thread(target=self.listen, daemon=True)
            receiver = threading.Thread(target=self.receive, daemon=True)
            sender = threading.Thread(target=self.send, daemon=True)
            self.lock = threading.RLock()

            listener.start()
            receiver.start()
            sender.start()
            self.start()

    def run(self):
        """Main thread method"""
        print("Enter \'quit\' to exit")
        while not self.shutdown:
            message = input()
            if message == "quit":
                self.sock.close()
                self.shutdown = True

    def listen(self):
        """Listen for new connections"""
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

    def receive(self):
        """Listen for new messages"""
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

                    self.process_data(data, connection)

    def send(self):
        """Send messages from server's queue"""
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

    def send_to_all(self, origin, data):
        """Send data to all users except origin"""
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

    def send_to_one(self, target, data):
        """Send data to specified target"""
        target_address = self.login_list[target]
        try:
            self.lock.acquire()
            target_address.send(data)
        except socket.error:
            self.remove_connection(target_address)
        finally:
            self.lock.release()

    def process_data(self, data, connection):
        """Process received data"""
        if data:
            message = data.decode(ENCODING)
            message = message.split(";", 3)

            if message[0] == 'login':
                tmp_login = message[1]

                while message[1] in self.login_list:
                    message[1] += '#'
                if tmp_login != message[1]:
                    prompt = 'msg;server;' + message[1] + ';Login ' + tmp_login \
                             + ' already in use. Your login changed to ' + message[1] + '\n'
                    self.queue.put((message[1], 'server', prompt.encode(ENCODING)))

                self.login_list[message[1]] = connection
                print(message[1] + ' has logged in')
                self.update_login_list()

            elif message[0] == 'logout':
                self.connection_list.remove(self.login_list[message[1]])
                if message[1] in self.login_list:
                    del self.login_list[message[1]]
                print(message[1] + ' has logged out')
                self.update_login_list()

            elif message[0] == 'msg' and message[2] != 'all':
                msg = data.decode(ENCODING) + '\n'
                data = msg.encode(ENCODING)
                self.queue.put((message[2], message[1], data))

            elif message[0] == 'msg':
                msg = data.decode(ENCODING) + '\n'
                data = msg.encode(ENCODING)
                self.queue.put(('all', message[1], data))

    def remove_connection(self, connection):
        """Remove connection from server's connection list"""
        self.connection_list.remove(connection)
        for login, address in self.login_list.items():
            if address == connection:
                del self.login_list[login]
                break
        self.update_login_list()

    def update_login_list(self):
        """Update list of active users"""
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';all' + '\n'
        self.queue.put(('all', 'server', logins.encode(ENCODING)))


# Create new server with (IP, port)
if __name__ == '__main__':
    server = Server(HOST, PORT)
