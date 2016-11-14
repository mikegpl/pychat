import socket
import select
import queue
import signal


class Server(object):
    def __init__(self, host, port):
        # socket init
        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # processing connections
        self.login_list = {}

        # socket setup
        self.sock.bind((str(self.host), int(self.port)))
        self.sock.listen(10)
        self.sock.setblocking(False)

        # select setup()

        self.inputs = [self.sock]
        self.outputs = []
        self.message_queues = {}

        # for exiting
        signal.signal(signal.SIGINT, self.sighandler)

    # methods


    def sighandler(self, signum, frame):
        # close the server
        print('Shutting down server...')
        # close existing client sockets
        for connection in self.outputs:
            connection.close()
        self.sock.close()

    def run(self):
        print("Server started")
        while self.inputs:
            try:
                read, write, exceptional = select.select(self.inputs, self.outputs, [])
            except:
                break

            # readable sockets
            for socket in read:
                # 1. processing server socket
                if socket is self.sock:
                    connection, address = socket.accept()
                    print("New connection from ", address)
                    connection.setblocking(False)

                    self.inputs.append(connection)
                    self.outputs.append(connection)
                    self.message_queues[connection] = queue.Queue()

                # 2. processing client socket
                else:
                    data = socket.recv(self.buffer_size)
                    if data:
                        message = data.decode('utf-8')
                        message = message.split(';', 3)

                        # processing data
                        # 1) login;nick
                        if message[0] == 'login':
                            tmp_login = message[1]
                            while message[1] in self.login_list:
                                message[1] += '#'
                            if tmp_login != message[1]:
                                prompt = 'msg;' + message[1] + ';' + message[1] + ';Login ' + tmp_login \
                                         + ' already in use. Your login changed to ' + message[1]
                                self.message_queues[socket].put(prompt.encode('utf-8'))

                            self.login_list[message[1]] = socket
                            print(message[1] + ' has logged in')
                            # Update list of active users, send it to clients
                            self.update_login_list()
                        # 2) logout;nick
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
                        # 3) msg;from;somebody;msg
                        elif message[0] == 'msg' and message[2] != 'all':
                            print("Here we go")
                            target = self.login_list[message[2]]
                            self.message_queues[target].put(data)
                        # 4) msg;from;all;msg
                        elif message[0] == 'msg':
                            for connection, connection_queue in self.message_queues.items():
                                if connection != socket:
                                    connection_queue.put(data)

                    # empty result == closed connection
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

            # writeable sockets
            for socket in write:
                if socket in self.inputs:
                    if not self.message_queues[socket].empty():
                        data = self.message_queues[socket].get()
                        socket.send(data)

            # exceptions
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

    def update_login_list(self):
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';all'
        logins = logins.encode('utf-8')
        for connection, connection_queue in self.message_queues.items():
            connection_queue.put(logins)


server = Server('localhost', 8888)
server.run()
