# README #

Simple chat in Python with GUI on client side. Default (IP, port) = (localhost, 8888).  


* Dependencies  
     Python 3.4 or higher  

     Python modules:  


     * socket
     * tkinter
     * threading
     * select 
     * time
     * queue

* Usage
     * Launching  
       To use locally, you need to run server file first, for example `python server_multithreaded.py`, then you can run `client.py` in separate terminal.  
       There are 3 server versions:  
          * `server_multi.py` - main thread only listens for new connections, then it creates new thread for each new client
          * `server_multithreaded.py` - it has 3 threads - listener, receiver and sender
          * `server_select.py` - it has 1 thread which uses select.select()

     * Exiting  
       To exit client, simply click 'Exit' button or 'x' in upper right corner.  
       To exit server:
          * `server_multithreaded.py` and `server_multi.py` - type 'quit' in terminal, then press Enter
          * `server_select.py` - you need to use Ctrl+C in terminal (SIGINT)