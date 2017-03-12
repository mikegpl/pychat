import socket
import threading
import queue
import time
import select

ENCODING = 'utf-8'
HOST = 'localhost'
PORT = 8888


class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True, target=self.listen)

        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
            self.start()
        except socket.error:
            self.shutdown = True

        # Main loop
        while not self.shutdown:
            message = input()
            if message == 'quit':
                for sock in self.connection_list:
                    sock.close()
                self.shutdown = True
                self.sock.close()

    def listen(self):
        """Main thread method, listens for new connections"""
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

    def update_login_list(self):
        """Alert all users that login list has changed"""
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';ALL' + '\n'
        logins = logins.encode(ENCODING)
        for connection, connection_queue in self.message_queues.items():
            connection_queue.put(logins)


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

    def run(self):
        """Main method for client's thread, processes client's socket"""
        print('New thread started for connection from ' + str(self.address))
        self.inputs = [self.socket]
        self.outputs = [self.socket]
        while self.inputs:
            try:
                read, write, exceptional = select.select(self.inputs, self.outputs, self.inputs)
            except select.error:
                self.remove_connection()
                break

            if self.socket in read:
                try:
                    data = self.socket.recv(self.buffer_size)
                except socket.error:
                    self.remove_connection()
                    break

                shutdown = self.process_data(data)

                # Empty result in socket ready to be read from == closed connection
                if shutdown:
                    self.remove_connection()
                    break

            if self.socket in write:
                if not self.master.message_queues[self.socket].empty():
                    data = self.master.message_queues[self.socket].get()
                    try:
                        self.socket.send(data)
                    except socket.error:
                        self.remove_connection()
                        break

            if self.socket in exceptional:
                self.remove_connection()

        # If exited from main run loop
        print('Closing client thread, connection' + str(self.address))

    def process_data(self, data):
        """Process data received by client's socket"""
        shutdown = False
        if data:
            message = data.decode(ENCODING)
            message = message.split(';', 3)

            if message[0] == 'login':
                tmp_login = message[1]
                while message[1] in self.master.login_list:
                    message[1] += '#'
                if tmp_login != message[1]:
                    prompt = 'msg;server;' + message[1] + ';Login ' + tmp_login \
                             + ' already in use. Your login changed to ' + message[1] + '\n'
                    self.master.message_queues[self.socket].put(prompt.encode(ENCODING))

                self.login = message[1]
                self.master.login_list[message[1]] = self.socket
                print(message[1] + ' has logged in')

                # Update list of active users, send it to clients
                self.master.update_login_list()

            elif message[0] == 'logout':
                print(message[1] + ' has logged out')
                shutdown = True

            elif message[0] == 'msg' and message[2] != 'ALL':
                msg = data.decode(ENCODING) + '\n'
                data = msg.encode(ENCODING)
                target = self.master.login_list[message[2]]
                self.master.message_queues[target].put(data)

            elif message[0] == 'msg':
                msg = data.decode(ENCODING) + '\n'
                data = msg.encode(ENCODING)
                for connection, connection_queue in self.master.message_queues.items():
                    if connection != self.socket:
                        connection_queue.put(data)
        else:
            shutdown = True
        return shutdown

    def remove_connection(self):
        """Remove connection with client from server"""
        print('Client {} has disconnected.'.format(self.login))
        if self.login in self.master.login_list:
            del self.master.login_list[self.login]
        if self.socket in self.master.connection_list:
            self.master.connection_list.remove(self.socket)
        if self.socket in self.master.message_queues:
            del self.master.message_queues[self.socket]
        self.socket.close()
        self.master.update_login_list()


# Create new server with (IP, port)
if __name__ == '__main__':
    server = Server(HOST, PORT)
