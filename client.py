import socket
import threading
import time


class Client(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((str(self.host), int(self.port)))
        self.buffer_size = 1024
        self.shutdown = False

        # guiThread = threading.Thread(target=self.gui)
        # guiThread.start()

        receivingThread = threading.Thread(target=self.receive)

        # What is and how does work thread.daemon?
        receivingThread.daemon = True
        receivingThread.start()

        self.login = input('Enter your login: ')
        try:
            message = 'login;' + self.login
            self.send(message)
        except:
            self.sock.close()
            self.shutdown = True


        while not self.shutdown:
            message = input()
            if message != 'quit':
                try:
                    self.send(message)
                except:
                    self.sock.close()
                    break
            else:
                message = 'logout;' + self.login
                try:
                    self.send(message)
                except:
                    pass
                self.sock.close()
                break

                # sendingThread = threading.Thread(target=self.send)
                # sendingThread.start()

    def gui(self):
        pass

    def receive(self):
        while True:
            try:
                received_data = self.sock.recv(self.buffer_size)
                if received_data:
                    message = received_data.decode('utf-8')
                    print(message)
            except:
                pass

    def send(self, message):
        data = message.encode('utf-8')
        self.sock.send(data)


client = Client('localhost', 8888)
