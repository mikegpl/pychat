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
     * Exiting  
       To exit client, simply click 'Exit' button or 'x' in upper right corner.  
       To exit server:
          * `server_multithreaded.py` - type 'quit' in terminal, then press Enter
          * `server_select.py` - you need to use Ctrl+C in terminal (SIGINT)
