import socket
import threading
import queue
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText


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
        self.login_label = None
        self.login_entry = None
        self.login_button = None
        self.login_root = None
        self.root = None
        self.messages_list = None
        self.login = ''

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

        while not self.shutdown:
            message = input()
            if message != 'quit' and message != 'logout':
                try:
                    self.queue.put(message.encode('utf-8'))
                except:
                    self.shutdown = True
            else:
                message = 'logout;' + self.login
                data = message.encode('utf-8')
                try:
                    self.send_message(data)
                except:
                    pass
                finally:
                    self.sock.close()
                    self.shutdown = True

    def gui(self):

        # login input
        self.login_root = tk.Tk()
        self.login_root.title("Login")
        self.login_label = tk.Label(self.login_root, text='Enter your login')
        self.login_label.pack(side=tk.LEFT)
        self.login_entry = tk.Entry(self.login_root, width=15)
        self.login_entry.pack(side=tk.LEFT)
        self.login_button = tk.Button(self.login_root, text='Submit')
        self.login_button.pack(side=tk.LEFT)
        self.login_button.bind('<Button-1>', self.get_login_event)
        self.login_root.mainloop()
        self.login_root.destroy()

        # main window config before login attempt
        self.root = tk.Tk()
        self.root.title("Python Chat")
        frame = tk.Frame(self.root)
        frame.pack()
        self.messages_list = ScrolledText(frame, height=20, width=100)
        self.messages_list.pack()
        self.messages_list.insert(tk.END, 'Welcome to Python Chat\n')
        self.messages_list.configure(state='disabled')
        # Todo - somewhere here get Entry (button + Return), and list of other clients

        try:
            message = 'login;' + self.login
            self.queue.put(message.encode('utf-8'))
        except:
            self.sock.close()

        self.root.mainloop()

    def get_login_event(self, event):
        self.login = self.login_entry.get()
        self.login_root.quit()

    def send(self):
        while True:
            if not self.queue.empty():
                data = self.queue.get()
                self.send_message(data)
                self.queue.task_done()
            time.sleep(0.050)

    def receive(self):
        while True:
            try:
                received_data = self.sock.recv(self.buffer_size)
            except:
                received_data = None

            if received_data:
                message = received_data.decode('utf-8')
                message = message.split(';', 3)

                # Todo here would go message processing
                self.messages_list.configure(state='normal')
                self.messages_list.insert(tk.END, message)
                self.messages_list.configure(state='disabled')
                self.messages_list.see(tk.END)

    def send_message(self, data):
        try:
            self.lock.acquire()
            self.sock.send(data)
        except:
            self.sock.close()
        finally:
            self.lock.release()


client = Client('localhost', 8888)
