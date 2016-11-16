import socket
import threading
import queue
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText


# Todo - work on too broad exception clauses
# Todo - some refactoring, moving send button to the left of exit button
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
        self.text_entry = None
        self.prompt = None
        self.send_button = None
        self.exit_button = None
        self.login_list_box = None

        self.login = ''
        self.target = ''
        self.login_list = []

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

    def gui(self):

        # login input
        self.login_root = tk.Tk()
        self.login_root.title("Login")
        self.login_label = tk.Label(self.login_root, text='Enter your login', width=20, font=('Helvetica', 13))
        self.login_label.pack(side=tk.LEFT)
        self.login_entry = tk.Entry(self.login_root, width=15, font=('Helvetica', 13))
        self.login_entry.focus_set()
        self.login_entry.pack(side=tk.LEFT)
        self.login_button = tk.Button(self.login_root, text='Login', font=('Helvetica', 13))
        self.login_button.pack(side=tk.LEFT)
        self.login_button.bind('<Button-1>', self.get_login_event)
        self.login_root.mainloop()
        self.login_button.unbind('<Button-1>')
        self.login_root.destroy()

        # main window config before login attempt
        self.root = tk.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.title("Python Chat")
        frame = tk.Frame(self.root, width=130)
        frame.pack(anchor='w')
        self.messages_list = ScrolledText(frame, height=20, width=100, font=('Helvetica', 13))
        self.messages_list.pack(side=tk.LEFT)
        self.messages_list.insert(tk.END, 'Welcome to Python Chat\n')
        self.messages_list.configure(state='disabled')
        self.login_list_box = tk.Listbox(frame, selectmode=tk.SINGLE, width=25, height=20, font=('Helvetica', 13),
                                         exportselection=False)
        self.login_list_box.bind('<<ListboxSelect>>', self.selected_login_event)
        self.messages_list.pack(side=tk.LEFT)
        self.login_list_box.pack(anchor='e', side=tk.LEFT)

        outer_frame = tk.Frame(self.root, width=130)
        outer_frame.pack(anchor='w')
        self.prompt = tk.Label(outer_frame, text=self.login + ' >>', font=('Helvetica', 13))
        self.text_entry = tk.Entry(outer_frame, width=100, font=('Helvetica', 13))
        self.text_entry.focus_set()
        self.text_entry.bind(sequence='<Return>', func=self.send_entry)
        self.send_button = tk.Button(outer_frame, text='Send', font=('Helvetica', 13))
        self.send_button.bind('<Button-1>', self.send_entry)
        self.exit_button = tk.Button(outer_frame, text='Exit', font=('Helvetica', 13))
        self.exit_button.bind('<Button-1>', self.exit_event)

        self.prompt.pack(side=tk.LEFT)
        self.text_entry.pack(side=tk.LEFT)
        self.exit_button.pack( side=tk.LEFT)
        self.send_button.pack(side=tk.LEFT)

        try:
            message = 'login;' + self.login
            self.queue.put(message.encode('utf-8'))
        except:
            self.sock.close()

        self.root.mainloop()
        self.root.destroy()

    def selected_login_event(self, event):
        self.target = self.login_list_box.get(self.login_list_box.curselection())

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
                message = message.split('\n')

                for msg in message:
                    if msg != '':
                        msg = msg.split(';')

                        # possible messages
                        # 1) from somebody to me
                        # msg;sb;me;message
                        if msg[0] == 'msg':
                            text = msg[1] + ' >> ' + msg[3] + '\n'
                            self.display_message(text)
                            if msg[2] != self.login:
                                self.login = msg[2]

                        # 2) from server to me, updating login list
                        # login;l1;l2;l3;...
                        elif msg[0] == 'login':
                            self.update_login_list(msg[1:])

    def send_entry(self, args):
        self.messages_list.configure(state='normal')
        text = self.text_entry.get()
        if text != '':
            message = 'msg;' + self.login + ';' + self.target + ';' + text
            self.queue.put(message.encode('utf-8'))
            if self.target != self.login:
                self.messages_list.insert(tk.END, 'Me (' + self.login + ') >> ' + text + '\n')
            self.text_entry.delete(0, tk.END)
        self.text_entry.focus_set()
        self.messages_list.configure(state='disabled')
        self.messages_list.see(tk.END)
        pass

    def display_message(self, message):
        self.messages_list.configure(state='normal')
        self.messages_list.insert(tk.END, message)
        self.messages_list.configure(state='disabled')
        self.messages_list.see(tk.END)

    def update_login_list(self, active_users):
        self.login_list_box.delete(0, tk.END)
        for user in active_users:
            self.login_list_box.insert(tk.END, user)
        self.login_list_box.select_set(0)
        self.target = self.login_list_box.get(self.login_list_box.curselection())

    def exit_event(self, event):
        message = 'logout;' + self.login
        data = message.encode('utf-8')
        try:
            self.send_message(data)
            self.root.quit()
        except:
            pass
        finally:
            self.sock.close()

    def on_closing(self):
        self.exit_event(None)

    def send_message(self, data):
        try:
            self.lock.acquire()
            self.sock.send(data)
        except:
            self.sock.close()
        finally:
            self.lock.release()


client = Client('localhost', 8888)
