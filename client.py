import socket
import threading
import queue
import time
import select
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox


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
        self.start()
        gui.daemon = False
        gui.start()
        # Only gui is non-daemon thread, so after closing gui app will quit
        # End of __init__

    # Threads methods:
    # 1) main thread - run
    # After setting up GUI in its thread, we will modify GUI only from main thread in self.run
    def run(self):
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

                if data:
                    message = data.decode('utf-8')
                    message = message.split('\n')

                    for msg in message:
                        if msg != '':
                            msg = msg.split(';')

                            # possible messages
                            # 1) sb to me
                            # msg;sb;me;message
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

    # 2) gui - self.gui()
    def gui(self):

        ###############################################################
        # Login window
        self.login_root = tk.Tk()
        self.login_root.title("Login")

        # Label
        self.login_label = tk.Label(self.login_root, text='Enter your login', width=20, font=('Helvetica', 13))
        self.login_label.pack(side=tk.LEFT, expand=tk.YES)

        # Text entry field
        self.login_entry = tk.Entry(self.login_root, width=20, font=('Helvetica', 13))
        self.login_entry.focus_set()
        self.login_entry.pack(side=tk.LEFT)
        self.login_entry.bind('<Return>', self.get_login_event)

        # Button for confirmation
        self.login_button = tk.Button(self.login_root, text='Login', font=('Helvetica', 13))
        self.login_button.pack(side=tk.LEFT)
        self.login_button.bind('<Button-1>', self.get_login_event)

        # Window main loop
        self.login_root.mainloop()

        # Cleaning binding
        self.login_button.unbind('<Button-1>')
        self.login_entry.unbind('<Return>')

        # Close login window
        self.login_root.destroy()

        ###############################################################
        # Main chat window
        self.root = tk.Tk()

        # Protocol for closing window using 'x' button
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing_event)
        self.root.title("Python Chat")
        self.root.geometry('750x500')
        self.root.minsize(600, 400)
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
        self.login_list_box = tk.Listbox(frame01, selectmode=tk.SINGLE, font=('Helvetica', 13),
                                         exportselection=False)
        self.login_list_box.bind('<<ListboxSelect>>', self.selected_login_event)

        # Positioning widgets in frame
        self.messages_list.pack(fill=tk.BOTH, expand=tk.YES)
        self.login_list_box.pack(fill=tk.BOTH, expand=tk.YES)

        # Entry widget for typing messages in
        self.text_entry = tk.Text(frame02, font=('Helvetica', 13))
        self.text_entry.focus_set()
        self.text_entry.bind('<Return>', self.send_entry_event)

        # Button widget for sending messages
        self.send_button = tk.Button(frame03, text='Send', font=('Helvetica', 13))
        self.send_button.bind('<Button-1>', self.send_entry_event)

        # Button for exiting
        self.exit_button = tk.Button(frame03, text='Exit', font=('Helvetica', 13))
        self.exit_button.bind('<Button-1>', self.exit_event)

        # Positioning widgets in frame
        self.text_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.send_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)
        self.exit_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.YES)

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
    def send_entry_event(self, event):

        text = self.text_entry.get(1.0, tk.END)
        if text != '\n':
            # text[:-1] because last char is a newline
            message = 'msg;' + self.login + ';' + self.target + ';' + text[:-1]
            self.queue.put(message.encode('utf-8'))
            self.text_entry.mark_set(tk.INSERT, 1.0)
            self.text_entry.delete(1.0, tk.END)
            self.text_entry.focus_set()
        else:
            messagebox.showinfo('Warning', 'You must enter non-empty message')

        with self.lock:
            self.messages_list.configure(state='normal')
            if text != '\n':
                self.messages_list.insert(tk.END, text)
            self.messages_list.configure(state='disabled')
            self.messages_list.see(tk.END)
            # if event was called by pressing Enter, then without returning break cursor will go to next line
        return 'break'

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
        with self.lock:
            self.messages_list.configure(state='normal')
            self.messages_list.insert(tk.END, message)
            self.messages_list.configure(state='disabled')
            self.messages_list.see(tk.END)

    # Update listbox with list of active users
    # method below can be used without locks, because login_list is only used by main thread
    def update_login_list(self, active_users):
        self.login_list_box.delete(0, tk.END)
        for user in active_users:
            self.login_list_box.insert(tk.END, user)
        self.login_list_box.select_set(0)
        self.target = self.login_list_box.get(self.login_list_box.curselection())

    # 3) main thread method:
    def send_message(self, data):
        with self.lock:
            try:
                self.sock.send(data)
            except socket.error:
                self.sock.close()
                messagebox.showinfo('Error', 'Server error has occurred. Exit app')



# Create new client with (IP, port)
if __name__ == '__main__':
    Client('localhost', 8888)
