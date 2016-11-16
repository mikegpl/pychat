import socket
import threading
import queue
import time


# Todo - work on too broad exception clauses
class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)

        # socket init
        self.host = host
        self.port = port
        self.buffer_size = 2048
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # processing connections
        self.connection_list = []
        self.login_list = {}
        self.queue = queue.Queue()

        # for quitting
        self.exit = ''

        # socket setup
        self.sock.bind((str(self.host), int(self.port)))
        self.sock.listen(10)
        self.sock.setblocking(False)

        # threads
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

        while True:
            message = input()
            if message == "quit":
                self.sock.close()
                break

    def listen(self):
        print('Initiated listener thread')
        while True:
            try:
                self.lock.acquire()
                connection, adress = self.sock.accept()
                connection.setblocking(False)
                if connection not in self.connection_list:
                    self.connection_list.append(connection)
            except:
                pass
            finally:
                self.lock.release()
            time.sleep(0.1)

    def receive(self):
        print('Initiated receiver thread')
        while True:
            if len(self.connection_list) > 0:
                for connection in self.connection_list:
                    try:
                        self.lock.acquire()
                        data = connection.recv(self.buffer_size)
                    except:
                        data = None
                    finally:
                        self.lock.release()

                    # process received data
                    if data:
                        message = data.decode('utf-8')
                        # at most 4 splits (don't split the message if it contains ;)
                        message = message.split(";", 3)

                        # do stuff with message
                        if message[0] == 'login':
                            tmp_login = message[1]
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
                        elif message[0] == 'logout':
                            self.connection_list.remove(self.login_list[message[1]])
                            if message[1] in self.login_list:
                                del self.login_list[message[1]]
                            print(message[1] + ' has logged out')

                            # Update list of active users
                            self.update_login_list()
                        elif message[0] == 'msg' and message[2] != 'all':
                            msg = data.decode('utf-8') + '\n'
                            data = msg.encode('utf-8')
                            self.queue.put((message[2], message[1], data))
                        elif message[0] == 'msg':
                            msg = data.decode('utf-8') + '\n'
                            data = msg.encode('utf-8')
                            self.queue.put(('all', message[1], data))

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

    def remove_connection(self, connection):
        self.connection_list.remove(connection)
        for login, address in self.login_list.items():
            if address == connection:
                del self.login_list[login]
                break
        self.update_login_list()

    def update_login_list(self):
        logins = 'login'
        for login in self.login_list:
            logins += ';' + login
        logins += ';all' + '\n'
        self.queue.put(('all', 'server', logins.encode('utf-8')))

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
                except:
                    self.remove_connection(connection)
                finally:
                    self.lock.release()

    def send_to_one(self, target, data):
        target_address = self.login_list[target]
        try:
            self.lock.acquire()
            target_address.send(data)
        except:
            self.remove_connection(target_address)
        finally:
            self.lock.release()


if __name__ == '__main__':
    server = Server('localhost', 8888)
