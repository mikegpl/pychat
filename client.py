import socket
import threading
import queue
import time
import select
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox


# todo -> move gui classes to another module
# todo -> docstrings

class GUI(threading.Thread):
    def __init__(self, client):
        super().__init__(daemon=False, target=self.run_gui)
        self.client = client
        self.display_queue = queue.Queue()
        self.login_window = LoginWindow()
        self.main_window = ChatWindow()

    def run_gui(self):
        pass


class Window(object):
    def __init__(self, title):
        self.root = tk.Tk()
        self.title = title
        self.root.title(title)


class LoginWindow(Window):
    def __init__(self):
        super().__init__("Login")
        self.label = None
        self.entry = None
        self.button = None
        self.login = None

        self.build_window()
        self.root.mainloop()
        self.destroy_window()

    def build_window(self):
        # Label
        self.label = tk.Label(self.root, text='Enter your login', width=20, font=('Helvetica', 13))
        self.root.pack(side=tk.LEFT, expand=tk.YES)

        # Login entry field
        self.entry = tk.Entry(self.root, width=20, font=('Helvetica', 13))
        self.entry.focus_set()
        self.entry.pack(side=tk.LEFT)
        self.entry.bind('<Return>', self.get_login_event)

        # Button for confirmation
        self.button = tk.Button(self.root, text='Login', font=('Helvetica', 13))
        self.button.pack(side=tk.LEFT)
        self.button.bind('<Button-1>', self.get_login_event)

    def destroy_window(self):
        # Clean bindings and close window
        self.button.unbind('<Button-1>')
        self.entry.unbind('<Return>')

        # Close login window
        self.root.destroy()

    def get_login_event(self, event):
        """Get login from login box and close login window"""
        self.login = self.entry.get()
        self.root.quit()


class ChatWindow(Window):
    def __init__(self):
        super().__init__("Python Chat")
        self.messages_list = None
        self.logins_list = None
        self.entry = None
        self.send_button = None
        self.exit_button = None

        self.build_window()
        self.root.mainloop()
        self.root.destroy()

    def build_window(self):
        # Size config
        self.root.geometry('750x500')
        self.root.minsize(600, 400)

        # Frames config
        main_frame = tk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky=tk.N + tk.S + tk.W + tk.E)

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # List of messages
        frame00 = tk.Frame(main_frame)
        frame00.grid(column=0, row=0, rowspan=2, sticky=tk.N + tk.S + tk.W + tk.E)

        # List of logins
        frame01 = tk.Frame(main_frame)
        frame01.grid(column=1, row=0, rowspan=3, sticky=tk.N + tk.S + tk.W + tk.E)

        # Message entry
        frame02 = tk.Frame(main_frame)
        frame02.grid(column=0, row=2, columnspan=1, sticky=tk.N + tk.S + tk.W + tk.E)

        # Buttons
        frame03 = tk.Frame(main_frame)
        frame03.grid(column=0, row=3, columnspan=2, sticky=tk.N + tk.S + tk.W + tk.E)

        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # ScrolledText widget for displaying messages
        self.messages_list = scrolledtext.ScrolledText(frame00, wrap='word', font=('Helvetica', 13))
        self.messages_list.insert(tk.END, 'Welcome to Python Chat\n')
        self.messages_list.configure(state='disabled')

        # Listbox widget for displaying active users and selecting them
        # selectmode = tk.SINGLE for choosing only one user at a time
        # exportselection = False to enable highlighting login in list even if multiple clients are opened
        self.logins_list = tk.Listbox(frame01, selectmode=tk.SINGLE, font=('Helvetica', 13),
                                      exportselection=False)
        self.logins_list.bind('<<ListboxSelect>>', self.selected_login_event)

        # Entry widget for typing messages in
        self.entry = tk.Text(frame02, font=('Helvetica', 13))
        self.entry.focus_set()
        self.entry.bind('<Return>', self.send_entry_event)

        # Button widget for sending messages
        self.send_button = tk.Button(frame03, text='Send', font=('Helvetica', 13))
        self.send_button.bind('<Button-1>', self.send_entry_event)

        # Button for exiting
        self.exit_button = tk.Button(frame03, text='Exit', font=('Helvetica', 13))
        self.exit_button.bind('<Button-1>', self.exit_event)

        # Positioning widgets in frame
        self.messages_list.pack(fill=tk.BOTH, expand=tk.YES)
        self.logins_list.pack(fill=tk.BOTH, expand=tk.YES)
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.send_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.exit_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

        # Protocol for closing window using 'x' button
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_event)

    def selected_login_event(self, event):
        """Set as target currently selected login on login list"""
        self.target = self.logins_list.get(self.logins_list.curselection())

    def send_entry_event(self, event):
        """Send message from entry field to target"""
        text = self.entry.get(1.0, tk.END)
        if text != '\n':
            message = 'msg;' + self.login + ';' + self.target + ';' + text[:-1]
            self.queue.put(message.encode('utf-8'))
            self.entry.mark_set(tk.INSERT, 1.0)
            self.entry.delete(1.0, tk.END)
            self.entry.focus_set()
        else:
            messagebox.showinfo('Warning', 'You must enter non-empty message')

        # todo -> think about queueing message displaying, then no lock would be necessary
        with self.lock:
            self.messages_list.configure(state='normal')
            if text != '\n':
                self.messages_list.insert(tk.END, text)
            self.messages_list.configure(state='disabled')
            self.messages_list.see(tk.END)
        return 'break'

    def exit_event(self, event):
        # todo -> self.client.logout()
        """Send logout message and quit app when "Exit" pressed"""
        message = 'logout;' + self.login
        data = message.encode('utf-8')

        self.send_message(data)
        self.root.quit()
        self.sock.close()

    def on_closing_event(self):
        """Exit window when 'x' button is pressed"""
        self.exit_event(None)


class Client(threading.Thread):
    def __init__(self, host, port):
        # Main thread
        super().__init__(daemon=True, target=self.run)

        # Socket variables
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((str(self.host), int(self.port)))
        self.buffer_size = 1024
        self.queue = queue.Queue()
        self.gui = GUI(self)

        # 3) Messaging variables
        self.login = ''
        self.target = ''
        self.login_list = []

        # Threads
        self.lock = threading.RLock()
        gui = threading.Thread(target=self.gui)
        self.start()
        gui.daemon = False
        gui.start()
        # Only gui is non-daemon thread, so after closing gui app will quit
        # End of __init__

    # Threads methods:
    # 1) main thread - run
    def run(self):
        """This method handles client-server communication using select module"""
        inputs = [self.sock]
        outputs = [self.sock]
        while inputs:
            try:
                read, write, exceptional = select.select(inputs, outputs, inputs)
            # if server unexpectedly quit, this will get ValueError (file descriptor < 0)
            except ValueError:
                print('Server error')
                messagebox.showinfo('Error', 'Server error has occurred. Exit app')
                self.sock.close()
                break

            if self.sock in read:
                with self.lock:
                    try:
                        data = self.sock.recv(self.buffer_size)
                    except socket.error:
                        messagebox.showinfo('Error', 'Server error has occurred. Exit app')
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
                messagebox.showinfo('Error', 'Server error has occurred. Exit app')
                self.sock.close()
                break

    def process_received_data(self, data):
        """Process received message from server"""
        if data:
            message = data.decode('utf-8')
            message = message.split('\n')

            for msg in message:
                if msg != '':
                    msg = msg.split(';')

                    # possible messages
                    # 1) user to me
                    # msg;user;me;message
                    if msg[0] == 'msg':
                        text = msg[1] + ' >> ' + msg[3] + '\n'
                        self.display_message(text)

                        # if chosen login is already in use
                        if msg[2] != self.login and msg[2] != 'ALL':
                            self.login = msg[2]

                    # 2) server to me, updating login list
                    # login;l1;l2;l3;ALL
                    elif msg[0] == 'login':
                        self.update_login_list(msg[1:])

    # 2) gui - self.gui()
    def gui(self):
        """This method sets up both login and main window, and starts GUI mainloop"""
        # removed setting up login window, think about returning login passed by user in login window
        # removed setting up main window


        # Send info to server, that user has logged in
        message = 'login;' + self.login
        self.queue.put(message.encode('utf-8'))

    # Methods used by threads:
    # 1) gui events


    # 2) other gui methods
    def display_message(self, message):
        """Display message in ScrolledText widget"""
        with self.lock:
            self.messages_list.configure(state='normal')
            self.messages_list.insert(tk.END, message)
            self.messages_list.configure(state='disabled')
            self.messages_list.see(tk.END)

    def update_login_list(self, active_users):
        """Update listbox with list of active users"""
        self.login_list_box.delete(0, tk.END)
        for user in active_users:
            self.login_list_box.insert(tk.END, user)
        self.login_list_box.select_set(0)
        self.target = self.login_list_box.get(self.login_list_box.curselection())

    def send_message(self, data):
        """"Send encoded message to server"""
        with self.lock:
            try:
                self.sock.send(data)
            except socket.error:
                self.sock.close()
                messagebox.showinfo('Error', 'Server error has occurred. Exit app')


# Create new client with (IP, port)
if __name__ == '__main__':
    Client('localhost', 8888)
