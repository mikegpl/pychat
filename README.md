# PythonChat    
### Simple chat in Python with Tkinter GUI on client side. 

## Getting started

### Requirements  
Python 3.4 or higher  

Modules:  
``` 
socket
tkinter
threading
select 
time
queue
```   
## Usage

### Launching  
To use locally, you need to run server file first, for example `python server_multithreaded.py`, then you can run `client.py` in a separate terminal.    
There are 3 server versions:      
     * `server_multi.py` - main thread only listens for new connections, then it creates new thread for each new client     
     * `server_multithreaded.py` - it has 3 threads - listener, receiver and sender     
     * `server_select.py` - it has 1 thread which uses select.select()


### Exiting     
To exit client, simply click 'Exit' button or 'x' in upper right corner.    
To exit server:    
     * `server_multithreaded.py` and `server_multi.py` - type 'quit' in terminal, then press Enter     
     * `server_select.py` - you need to use Ctrl+C in terminal (SIGINT)
     

### Messaging protocol

This server uses simple communication protocol, which is as following:

* template: `action_type;origin;target;message_contents`
* user1 sends message to user2: `msg;user1;user2;message_contents`
* user sends message to all users: `msg;user;ALL;message_contents`
* user logs in or out: `login;user` / `logout;user`
* server notifies users about changes in login list `login;user1;user2;user3;[...];ALL`

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
