import socket
import select
import queue
import signal

HOST = 'localhost'
PORT = 8888
ENCODING = 'utf-8'


class Server(object):
    def __init__(self, host, port):

        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # login:connection dictionary
        self.login_list = {}

        self.inputs = [self.sock]
        self.outputs = []
        self.message_queues = {}

        self.shutdown = False
        try:
            self.sock.bind((str(self.host), int(self.port)))
            self.sock.listen(10)
            self.sock.setblocking(False)
        except socket.error:
            self.shutdown = True

        # Trap for SIGINT for exiting
        signal.signal(signal.SIGINT, self.sighandler)
        self.run()

    def run(self):
        """Main server method"""
        if self.shutdown:
            raise Exception("This server was unable to bind with socket")
        print("Server started")
        while self.inputs:
            try:
                # Use select to get lists of sockets ready for IO operations
                read, write, exceptional = select.select(self.inputs, self.outputs, [])
            except select.error:
                break

            # Sockets processing
            # 1) readable sockets
            for socket in read:
                # a) processing server socket (incoming connection)
                if socket is self.sock:
                    try:
                        connection, address = socket.accept()
                        connection.setblocking(False)
                    except socket.error:
                        pass

                    self.inputs.append(connection)
                    self.outputs.append(connection)
                    self.message_queues[connection] = queue.Queue()

                # b) processing client socket (incoming messages)
                else:
                    data = socket.recv(self.buffer_size)
                    self.process_data(data, socket)

            # 2) writeable sockets
            for socket in write:
                if socket in self.inputs:
                    if not self.message_queues[socket].empty():
                        data = self.message_queues[socket].get()
                        socket.send(data)

            # 3) sockets where exceptions has occured
            for socket in exceptional:
                self.inputs.remove(socket)
                if socket in self.outputs:
                    self.outputs.remove(socket)
                del self.message_queues[socket]
                socket.close()

                for login, address in self.login_list.items():
                    if address == socket:
                        del self.login_list[login]
                        break

                self.update_login_list()

    def process_data(self, data, socket):
        """Process data received by socket"""
        if data:
            message = data.decode(ENCODING)
            message = message.split(';', 3)
            # at most 4 splits (don't split the message if it contains ;)

            # Processing data
            # 1) new user logged in
            if message[0] == 'login':
                tmp_login = message[1]
                while message[1] in self.login_list:
                    message[1] += '#'
                if tmp_login != message[1]:
                    prompt = 'msg;server;' + message[1] + ';Login ' + tmp_login \
                             + ' already in use. Your login changed to ' + message[1] + '\n'
                    self.message_queues[socket].put(prompt.encode(ENCODING))

                self.login_list[message[1]] = socket
                print(message[1] + ' has logged in')

                # Update list of active users, send it to clients
                self.update_login_list()

            # 2) user logged out
            elif message[0] == 'logout':
                print(message[1] + ' has logged out')

                self.inputs.remove(socket)
                if socket in self.outputs:
                    self.outputs.remove(socket)
                del self.message_queues[socket]
                socket.close()

                for login, address in self.login_list.items():
                    if address == socket:
                        del self.login_list[login]
                        break

                # Update list of active users, send it to clients
                self.update_login_list()

            # 3) Message from one user to another (msg;origin;target;message)
            elif message[0] == 'msg' and message[2] != 'all':
                msg = data.decode(ENCODING) + '\n'
                data = msg.encode(ENCODING)
                target = self.login_list[message[2]]
                self.message_queues[target].put(data)

            # 4) Message from one user to all users (msg;origin;all;message)
            elif message[0] == 'msg':
                msg = data.decode(ENCODING) + '\n'
                data = msg.encode(ENCODING)
                for connection, connection_queue in self.message_queues.items():
                    if connection != socket:
                        connection_queue.put(data)

        # Empty result in socket ready to be read from == closed connection
        else:
            self.inputs.remove(socket)
            if socket in self.outputs:
                self.outputs.remove(socket)
            del self.message_queues[socket]
            socket.close()

            for login, address in self.login_list.items():
                if address == socket:
                    del self.login_list[login]
                    break

            self.update_login_list()

    def update_login_list(self):
        """Update login list and send it to active users"""
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';all' + '\n'
        logins = logins.encode(ENCODING)
        for connection, connection_queue in self.message_queues.items():
            connection_queue.put(logins)

    def sighandler(self, signum, frame):
        """Handle trapped SIGINT"""
        # close the server
        print('Shutting down server...')
        # close existing client sockets
        for connection in self.outputs:
            connection.close()
        self.sock.close()


if __name__ == '__main__':
    server = Server(HOST, PORT)
