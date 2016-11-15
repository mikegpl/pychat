import socket
import threading
import queue
import tkinter as tk


class Client(threading.Thread):
    def __init__(self, host, port):

        # sockety stuff
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((str(self.host), int(self.port)))
        self.buffer_size = 1024
        self.shutdown = False
        self.queue = queue.Queue()

        # gui stuff



        # threads
        self.lock = threading.RLock()
        gui = threading.Thread(target=self.gui)
        receiver = threading.Thread(target=self.receive)
        sender = threading.Thread(target=self.send)

        receiver.daemon = True
        receiver.start()
        gui.daemon = False
        gui.start()
        sender.daemon = True
        sender.start()

        # guiThread.start()

        self.login = input('Enter your login: ')
        try:
            message = 'login;' + self.login
            self.queue.put(message.encode('utf-8'))
        except:
            self.sock.close()
            self.shutdown = True

        while not self.shutdown:
            message = input()
            if message != 'quit' and message != 'logout':
                try:
                    self.queue.put(message.encode('utf-8'))
                except:
                    self.sock.close()
                    self.shutdown = True
            else:
                message = 'logout;' + self.login
                try:
                    self.queue.put(message.encode('utf-8'))
                except:
                    pass
                finally:
                    self.sock.close()
                self.shutdown = True


                # sendingThread = threading.Thread(target=self.send)
                # sendingThread.start()

    def gui(self):
        pass

    def send(self):
        while True:
            if not self.queue.empty():
                data = self.queue.get()
                self.send_message(data)
                self.queue.task_done()


    def receive(self):
        while True:
            try:
                received_data = self.sock.recv(self.buffer_size)
                if received_data:
                    message = received_data.decode('utf-8')
                    print(message)
            except:
                pass

    def send_message(self, data):
        try:
            self.lock.acquire()
            self.sock.send(data)
        except:
            self.sock.close()
        finally:
            self.lock.release()



client = Client('localhost', 8888)
