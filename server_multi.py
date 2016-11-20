import socket
import threading
import queue
import time
import select


# Todo - add locking (!)
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
            try:
                self.lock.acquire()
                connection, address = self.sock.accept()
            except socket.error:
                self.lock.release()
                time.sleep(0.05)
                continue

            self.lock.release()
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
        self.start()
        print('New thread started for connection from ' + str(self.address))

    def run(self):
        inputs = [self.socket]
        outputs = [self.socket]
        shutdown = False
        while inputs:
            try:
                read, write, exceptional = select.select(inputs, outputs, inputs)
            except select.error:
                # delete queue
                # remove from login list etc
                # update login list
                self.socket.close()
                break

            if self.socket in read:
                data = self.socket.recv(self.buffer_size)

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

                        inputs.remove(self.socket)
                        outputs.remove(self.socket)
                        del self.master.message_queues[self.socket]
                        del self.master.login_list[self.login]
                        self.socket.close()
                        shutdown = True
                        self.update_login_list()

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
                    print(self.login + ' has disconnected.')
                    inputs.remove(self.socket)
                    outputs.remove(self.socket)
                    del self.master.message_queues[self.socket]
                    del self.master.login_list[self.login]
                    self.socket.close()
                    shutdown = True
                    self.update_login_list()

            if self.socket in write:
                if self.socket in self.master.message_queues:
                    if not self.master.message_queues[self.socket].empty():
                        data = self.master.message_queues[self.socket].get()
                        self.socket.send(data)

            if self.socket in exceptional and not shutdown:
                print(self.login + ' has disconnected.')
                inputs.remove(self.socket)
                outputs.remove(self.socket)
                del self.master.message_queues[self.socket]
                del self.master.login_list[self.login]
                self.socket.close()

                self.update_login_list()

        print('Closing client thread, connection' + str(self.address))

    def update_login_list(self):
        logins = 'login'
        for login in self.master.login_list:
            logins += ';' + login
        logins += ';ALL' + '\n'
        logins = logins.encode('utf-8')
        for connection, connection_queue in self.master.message_queues.items():
            connection_queue.put(logins)


if __name__ == '__main__':
    server = Server('localhost', 8888)
