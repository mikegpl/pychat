import socket
import threading
import queue
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText


class Client(threading.Thread):
    def __init__(self, host, port):

        # Main thread
        super().__init__(daemon=True)

        # Socket variables
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((str(self.host), int(self.port)))
        self.buffer_size = 1024
        self.queue = queue.Queue()

        # GUI variables
        # 1) Login window
        self.login_label = None
        self.login_entry = None
        self.login_button = None
        self.login_root = None

        # 2) Main window
        self.root = None
        self.messages_list = None
        self.text_entry = None
        self.prompt = None
        self.send_button = None
        self.exit_button = None
        self.login_list_box = None

        # 3) Messaging variables
        self.login = ''
        self.target = ''
        self.login_list = []

        # Threads
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

        # Only gui is non-daemon thread, so after closing gui app will quit
        # End of __init__

    # Methods used directly by threads:
    # 1) receiver - self.receive()

    def receive(self):
        while True:
            try:
                received_data = self.sock.recv(self.buffer_size)
            except socket.error:
                time.sleep(0.050)
                continue

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

                            # if login you have chosen is already used:
                            if msg[2] != self.login and msg[2] != 'all':
                                self.login = msg[2]

                        # 2) from server to me, updating login list
                        # login;l1;l2;l3;...
                        elif msg[0] == 'login':
                            self.update_login_list(msg[1:])

    # 2) sender - self.send()
    def send(self):
        while True:
            if not self.queue.empty():
                data = self.queue.get()
                self.send_message(data)
                self.queue.task_done()
            else:
                time.sleep(0.050)

    # 3) gui - self.gui()
    def gui(self):

        # Login window
        self.login_root = tk.Tk()
        self.login_root.title("Login")

        # Label
        self.login_label = tk.Label(self.login_root, text='Enter your login', width=20, font=('Helvetica', 13))
        self.login_label.pack(side=tk.LEFT)

        # Text entry field
        self.login_entry = tk.Entry(self.login_root, width=15, font=('Helvetica', 13))
        self.login_entry.focus_set()
        self.login_entry.pack(side=tk.LEFT)

        # Button for confirmation
        self.login_button = tk.Button(self.login_root, text='Login', font=('Helvetica', 13))
        self.login_button.pack(side=tk.LEFT)
        self.login_button.bind('<Button-1>', self.get_login_event)

        # Window main loop
        self.login_root.mainloop()

        # Cleaning binding
        self.login_button.unbind('<Button-1>')

        # Close login window
        self.login_root.destroy()

        # Main chat window
        self.root = tk.Tk()

        # Protocol for closing window using 'x' button
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_event)
        self.root.title("Python Chat")

        # Frame for displaying messages and logins
        frame = tk.Frame(self.root, width=80)
        frame.pack(anchor='w')

        # ScrolledText widget for displaying messages
        self.messages_list = ScrolledText(frame, height=20, width=60, wrap='word', font=('Helvetica', 13))
        self.messages_list.insert(tk.END, 'Welcome to Python Chat\n')
        self.messages_list.configure(state='disabled')

        # Listbox widget for displaying active users and selecting them
        # selectmode = tk.SINGLE for choosing only one user at a time
        # exportselection = False to enable highlighting login in list even if multiple clients are opened
        self.login_list_box = tk.Listbox(frame, selectmode=tk.SINGLE, width=15, height=18, font=('Helvetica', 13),
                                         exportselection=False)
        self.login_list_box.bind('<<ListboxSelect>>', self.selected_login_event)

        # Positioning widgets in frame
        self.messages_list.pack(side=tk.LEFT)
        self.login_list_box.pack(anchor='e', side=tk.LEFT)

        # Frame for prompt, 'Exit' and 'Send' buttons and entry field
        outer_frame = tk.Frame(self.root, width=80)
        outer_frame.pack(anchor='w')

        # Label widget as prompt
        self.prompt = tk.Label(outer_frame, text=self.login + ' >>', font=('Helvetica', 13))

        # Entry widget for typing messages in
        self.text_entry = tk.Entry(outer_frame, width=50, font=('Helvetica', 13))
        self.text_entry.focus_set()
        self.text_entry.bind(sequence='<Return>', func=self.send_entry_event)

        # Button widget for sending messages
        self.send_button = tk.Button(outer_frame, text='Send', font=('Helvetica', 13))
        self.send_button.bind('<Button-1>', self.send_entry_event)

        # Button for exiting
        self.exit_button = tk.Button(outer_frame, text='Exit', font=('Helvetica', 13))
        self.exit_button.bind('<Button-1>', self.exit_event)

        # Positioning widgets in frame
        self.prompt.pack(side=tk.LEFT)
        self.text_entry.pack(side=tk.LEFT)
        self.send_button.pack(side=tk.LEFT)
        self.exit_button.pack(side=tk.LEFT)

        # Send info to server, that user has logged in
        message = 'login;' + self.login
        self.queue.put(message.encode('utf-8'))
        # Window main loop
        self.root.mainloop()
        # Close main window
        self.root.destroy()

    # Methods used by threads:
    # 1) gui events
    # Get login from login window
    def get_login_event(self, event):
        self.login = self.login_entry.get()
        self.login_root.quit()

    # Set as target currently selected login in login list
    def selected_login_event(self, event):
        self.target = self.login_list_box.get(self.login_list_box.curselection())

    # Send message from entry field to currently selected user
    def send_entry_event(self, args):
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

    # Send logout message to server and quit, after pressing 'Exit' button
    def exit_event(self, event):
        message = 'logout;' + self.login
        data = message.encode('utf-8')

        self.send_message(data)
        self.root.quit()
        self.sock.close()

    # Access exit event when window is closed with 'x'
    def on_closing_event(self):
        self.exit_event(None)

    # 2) other gui methods
    # Display a message in ScrolledText widget
    def display_message(self, message):
        self.messages_list.configure(state='normal')
        self.messages_list.insert(tk.END, message)
        self.messages_list.configure(state='disabled')
        self.messages_list.see(tk.END)

    # Update listbox with list of active users
    def update_login_list(self, active_users):
        self.login_list_box.delete(0, tk.END)
        for user in active_users:
            self.login_list_box.insert(tk.END, user)
        self.login_list_box.select_set(0)
        self.target = self.login_list_box.get(self.login_list_box.curselection())

    # 3) sender method:
    def send_message(self, data):
        try:
            self.lock.acquire()
            self.sock.send(data)
        except socket.error:
            self.sock.close()
        finally:
            self.lock.release()


# Create new client with (IP, port)
if __name__ == '__main__':
    client = Client('localhost', 8888)
