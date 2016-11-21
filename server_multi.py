import socket
import threading
import queue
import time
import select


class Server(threading.Thread):
    def __init__(self, host, port):
        # Main thread
        super().__init__(daemon=True, target=self.listen)

        # Socket variables
        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Variables for processing connections
        self.message_queues = {}
        self.connection_list = []
        self.login_list = {}

        self.lock = threading.RLock()

        # Socket setup
        self.shutdown = False
        try:
            self.sock.bind((str(self.host), int(self.port)))
            self.sock.listen(10)
            self.sock.setblocking(False)
        except socket.error:
            self.shutdown = True

        self.start()

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
            with self.lock:
                try:
                    connection, address = self.sock.accept()
                except socket.error:
                    time.sleep(0.05)
                    continue

            connection.setblocking(False)
            if connection not in self.connection_list:
                self.connection_list.append(connection)

            self.message_queues[connection] = queue.Queue()
            ClientThread(self, connection, address)


class ClientThread(threading.Thread):
    def __init__(self, master, sock, address):
        super().__init__(daemon=True, target=self.run)
        self.master = master
        self.socket = sock
        self.address = address
        self.buffer_size = 2048
        self.login = ''
        self.inputs = []
        self.outputs = []
        self.start()
        print('New thread started for connection from ' + str(self.address))

    # In run we don't need to use locks, because sockets are accessed linearly
    def run(self):
        self.inputs = [self.socket]
        self.outputs = [self.socket]
        shutdown = False
        while self.inputs:
            try:
                read, write, exceptional = select.select(self.inputs, self.outputs, self.inputs)
            except select.error:
                self.client_disconnected()
                break

            if self.socket in read:
                try:
                    data = self.socket.recv(self.buffer_size)
                except socket.error:
                    if self.socket in self.inputs:
                        self.inputs.remove(self.socket)
                    if self.socket in self.outputs:
                        self.outputs.remove(self.socket)
                    self.client_disconnected()
                    break

                if data:
                    message = data.decode('utf-8')
                    message = message.split(';', 3)

                    # Processing data
                    # 1) new user logged in
                    if message[0] == 'login':
                        tmp_login = message[1]
                        while message[1] in self.master.login_list:
                            message[1] += '#'
                        if tmp_login != message[1]:
                            prompt = 'msg;server;' + message[1] + ';Login ' + tmp_login \
                                     + ' already in use. Your login changed to ' + message[1] + '\n'
                            self.master.message_queues[self.socket].put(prompt.encode('utf-8'))

                        self.login = message[1]
                        self.master.login_list[message[1]] = self.socket
                        print(message[1] + ' has logged in')

                        # Update list of active users, send it to clients
                        self.update_login_list()

                    # 2) user logged out
                    elif message[0] == 'logout':
                        print(message[1] + ' has logged out')

                        self.inputs.remove(self.socket)
                        self.outputs.remove(self.socket)
                        del self.master.message_queues[self.socket]
                        del self.master.login_list[self.login]
                        self.socket.close()
                        self.update_login_list()
                        break

                    # 3) Message from one user to another (msg;origin;target;message)
                    elif message[0] == 'msg' and message[2] != 'ALL':
                        msg = data.decode('utf-8') + '\n'
                        data = msg.encode('utf-8')
                        target = self.master.login_list[message[2]]
                        self.master.message_queues[target].put(data)

                    # 4) Message from one user to all users (msg;origin;all;message)
                    elif message[0] == 'msg':
                        msg = data.decode('utf-8') + '\n'
                        data = msg.encode('utf-8')
                        for connection, connection_queue in self.master.message_queues.items():
                            if connection != self.socket:
                                connection_queue.put(data)

                # Empty result in socket ready to be read from == closed connection
                elif not shutdown:
                    if self.socket in self.inputs:
                        self.inputs.remove(self.socket)
                    if self.socket in self.outputs:
                        self.outputs.remove(self.socket)
                    self.client_disconnected()
                    break

            if self.socket in write:
                if self.socket in self.master.message_queues:
                    if not self.master.message_queues[self.socket].empty():
                        data = self.master.message_queues[self.socket].get()
                        try:
                            self.socket.send(data)
                        except socket.error:
                            if self.socket in self.inputs:
                                self.inputs.remove(self.socket)
                            if self.socket in self.outputs:
                                self.outputs.remove(self.socket)
                            self.client_disconnected()
                            break

            if self.socket in exceptional:
                if self.socket in self.inputs:
                    self.inputs.remove(self.socket)
                if self.socket in self.outputs:
                    self.outputs.remove(self.socket)
                self.client_disconnected()

        # If exited from main run loop
        print('Closing client thread, connection' + str(self.address))

    def update_login_list(self):
        logins = 'login'
        for login in self.master.login_list:
            logins += ';' + login
        logins += ';ALL' + '\n'
        logins = logins.encode('utf-8')
        for connection, connection_queue in self.master.message_queues.items():
            connection_queue.put(logins)

    def client_disconnected(self):
        print(self.login + 'has disconnected.')
        if self.login in self.master.login_list:
            del self.master.login_list[self.login]
        if self.socket in self.master.connection_list:
            self.master.connection_list.remove(self.socket)
        if self.socket in self.master.message_queues:
            del self.master.message_queues[self.socket]
        self.socket.close()
        self.update_login_list()

# Create new server with (IP, port)
if __name__ == '__main__':
    server = Server('localhost', 8888)
