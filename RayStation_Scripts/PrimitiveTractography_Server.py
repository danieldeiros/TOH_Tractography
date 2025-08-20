# Server for Primitive Tractography

# Imports
import time
import datetime
import zmq
import threading
import subprocess
import sys

# Define port numbers
main_port = "5560"
heartbeat_port = "5561"
stream_port = "5562"
data_port = "5563"
local_data_port = "5564"

# Create context
context = zmq.Context()

# Main socket for work
main_socket = context.socket(zmq.ROUTER)
main_socket.bind(f"tcp://*:{main_port}")

# Heartbeat socket
heartbeat_socket = context.socket(zmq.REP)
heartbeat_socket.bind(f"tcp://*:{heartbeat_port}")

# Streaming socket (for returning terminal outputs)
stream_socket = context.socket(zmq.PUSH)
stream_socket.bind(f"tcp://*:{stream_port}")

# Data socket
data_socket = context.socket(zmq.ROUTER)
data_socket.bind(f"tcp://*:{data_port}")

# Local data socket
local_data_socket = context.socket(zmq.DEALER)
local_data_socket.bind(f"tcp://*:{local_data_port}")

# Define main poller
main_poller = zmq.Poller()
main_poller.register(main_socket, zmq.POLLIN)

# Define heartbeat poller
heartbeat_poller = zmq.Poller()
heartbeat_poller.register(heartbeat_socket, zmq.POLLIN)

# Define data poller
data_poller = zmq.Poller()
data_poller.register(data_socket, zmq.POLLIN)
data_poller.register(local_data_socket, zmq.POLLIN)

# Track last heartbeat time per client ID
last_heartbeat = {}
heartbeat_timeout = 15 # seconds

# define function to monitor heartbeats
def monitor_heartbeats():
    global heartbeat_polling # Create flag to indicate when we are polling. Allows us to exit program safely with no errors
    while heartbeat_polling:
        try:
            socks = dict(heartbeat_poller.poll(timeout=100)) # Check for 100 ms
            if heartbeat_socket in socks:
                message = heartbeat_socket.recv().decode()
                if message.startswith("PING:"):
                    client_id = message.split(":")[1]
                    if client_id not in last_heartbeat:
                        print(f"[{datetime.datetime.now()}] [Heartbeat] Established connection with {client_id}")
                    last_heartbeat[client_id] = time.time()
                    # print(f"[{datetime.datetime.now()}] [Heartbeat] Received from {client_id}.")
                    heartbeat_socket.send(b"PONG")
                else:
                    heartbeat_socket.send(b"UNKNOWN")

            now = time.time()
            to_remove = []
            for client_id, timestamp in last_heartbeat.items():
                if now - timestamp > heartbeat_timeout: # Check if time between now and last heartbeat exceeds timeout time
                    print(f"[{datetime.datetime.now()}] [Heartbeat] Client '{client_id}' missed heartbeat! Assuming disconnected.")
                    to_remove.append(client_id)
            for client_id in to_remove:
                del last_heartbeat[client_id]

            time.sleep(0.1) # wait a bit... removes weird error messages
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [Heartbeat] ZMQ error: {e}")
    
    return # exit daemon function if not heartbeat polling

# Start heartbeat monitoring thread
heartbeat_polling = True # Set flag to true
heartbeat_thread = threading.Thread(target=monitor_heartbeats, daemon=True)
heartbeat_thread.start()

stream_polling = True # Set flag to true first so that it's defined
# define function to relay terminal outputs from PrimitiveTractography
def stream(identity):
    global stream_polling
    while stream_polling:
        for line in iter(proc.stdout.readline, ''):
            stream_socket.send_json({"type": "stdout", "data": line.strip()})
            if not stream_polling:
                stream_socket.send_json({"type": "stdout", "data": "Connection lost!"}) # tell user connection lost
                return # end daemon function
        stream_socket.send_json({"type": "done", "returncode": proc.wait()})

        if proc.wait() == 0:
            print("\nTractography completed succesfully.")
            main_socket.send_multipart([identity, b'', b"FINISHED"])
            return # end of function
        else:
            print("\nError in tractography script.")
            main_socket.send_multipart([identity, b'', b"ERROR"])
            return # end of function
        
    return # exit function if not stream polling

data_polling = True # Set flag to true first so that it's defined
# Define function to relay data from PrimitiveTractography and relay back when the Fury window is closed
def data_relay():
    global data_polling # Create flag to indicate when we are polling. Allows us to exit program safely with no errors
    while data_polling:
        if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
            # Receive base directory from client
            ds_identity, _, base_dir = data_socket.recv_multipart()
            # Send base directory to server
            local_data_socket.send_multipart([ds_identity, b'', base_dir])
            break # continue to poll for Fury data now
        time.sleep(0.1) # wait a bit... removes weird error messages

    cnt = 0 # Set counter to exit after 2
    while data_polling:
        if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
            ds_identity, _, ds_msg = local_data_socket.recv_multipart() # receive data from PrimitiveTractography

            # Send data to client
            data_socket.send_multipart([ds_identity, b'', ds_msg])

            cnt += 1 # add to counter

            if cnt >= 2:
                return # exit function

        time.sleep(0.1) # wait a bit... removes weird error messages
    return # exit function if not data polling

try:
    print("\nWaiting for client message...")
    while True: #  Wait for next request from client
        socks = dict(main_poller.poll(timeout=3000)) # Check for 3 seconds
        if main_socket in socks:
            # Receive message from client
            identity, _, message = main_socket.recv_multipart()
            message = message.decode()
            if message == "READY":
                # Let client know server is ready
                main_socket.send_multipart([identity, b'', b"READY"])
            elif message == "RUN":

                # Start tractography script
                path = "V:/Common/Staff Personal Folders/DanielH/RayStation_Scripts/Tractography/PrimitiveTractography.py"
                # Call tractography script with python venv
                proc = subprocess.Popen(
                    [sys.executable, "-u", path],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1)
                
                stream_polling = True # Set flag to true first
                
                data_polling = True # Set flag to true first 

                threading.Thread(target=data_relay, daemon=True).start() # start data relay thread

                threading.Thread(target=stream, args=(identity,), daemon=True).start() # start streaming terminal output thread
            else:
                print(f"Unexpected message received from client")
except KeyboardInterrupt:
    print("\nShutting down server from user (KeyboardInterrupt).")
    while heartbeat_polling or data_polling or stream_polling:
        heartbeat_polling = False
        data_polling = False
        stream_polling = False
        time.sleep(3) # Wait until we aren't polling

finally:
    # Close sockets and terminate context
    main_socket.close()
    heartbeat_socket.close()
    stream_socket.close()
    data_socket.close()
    local_data_socket.close()
    context.term()
