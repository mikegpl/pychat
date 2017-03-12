import socket
import time
import select
import queue
from gui import *

ENCODING = 'utf-8'
HOST = 'localhost'
PORT = 8888


class Client(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True, target=self.run)

        self.host = host
        self.port = port
        self.sock = None
        self.connected = self.connect_to_server()
        self.buffer_size = 1024

        self.queue = queue.Queue()
        self.lock = threading.RLock()

        self.login = ''
        self.target = ''
        self.login_list = []

        if self.connected:
            self.gui = GUI(self)
            self.start()
            self.gui.start()
            # Only gui is non-daemon thread, therefore after closing gui app will quit

    def connect_to_server(self):
        """Connect to server via socket interface, return (is_connected)"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((str(self.host), int(self.port)))
        except ConnectionRefusedError:
            print("Server is inactive, unable to connect")
            return False
        return True

    def run(self):
        """Handle client-server communication using select module"""
        inputs = [self.sock]
        outputs = [self.sock]
        while inputs:
            try:
                read, write, exceptional = select.select(inputs, outputs, inputs)
            # if server unexpectedly quits, this will raise ValueError exception (file descriptor < 0)
            except ValueError:
                print('Server error')
                GUI.display_alert('Server error has occurred. Exit app')
                self.sock.close()
                break

            if self.sock in read:
                with self.lock:
                    try:
                        data = self.sock.recv(self.buffer_size)
                    except socket.error:
                        print("Socket error")
                        GUI.display_alert('Socket error has occurred. Exit app')
                        self.sock.close()
                        break

                self.process_received_data(data)

            if self.sock in write:
                if not self.queue.empty():
                    data = self.queue.get()
                    self.send_message(data)
                    self.queue.task_done()
                else:
                    time.sleep(0.05)

            if self.sock in exceptional:
                print('Server error')
                GUI.display_alert('Server error has occurred. Exit app')
                self.sock.close()
                break

    def process_received_data(self, data):
        """Process received message from server"""
        if data:
            message = data.decode(ENCODING)
            message = message.split('\n')

            for msg in message:
                if msg != '':
                    msg = msg.split(';')

                    if msg[0] == 'msg':
                        text = msg[1] + ' >> ' + msg[3] + '\n'
                        print(msg)
                        self.gui.display_message(text)

                        # if chosen login is already in use
                        if msg[2] != self.login and msg[2] != 'ALL':
                            self.login = msg[2]

                    elif msg[0] == 'login':
                        self.gui.main_window.update_login_list(msg[1:])

    def notify_server(self, action, action_type):
        """Notify server if action is performed by client"""
        self.queue.put(action)
        if action_type == "login":
            self.login = action.decode(ENCODING).split(';')[1]
        elif action_type == "logout":
            self.sock.close()

    def send_message(self, data):
        """"Send encoded message to server"""
        with self.lock:
            try:
                self.sock.send(data)
            except socket.error:
                self.sock.close()
                GUI.display_alert('Server error has occurred. Exit app')


# Create new client with (IP, port)
if __name__ == '__main__':
    Client(HOST, PORT)
