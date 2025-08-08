# Client for Primitive Tractography

# Imports
import zmq
import time
import datetime
import threading
import uuid
import sys
import pickle
from pathlib import Path
import json
# from connect import *

# Add RayStation scripts folder to path
rs_scripts_path = r"V:\Common\Staff Personal Folders\DanielH\RayStation_Scripts\Tractography".replace("\\","/")
sys.path.append(rs_scripts_path)

# Make imports
from Subscripts.Visualization_Utils import show_tracts, show_wmpl 
from Subscripts.RS_Utils import get_img_registration, copy_roi_geometries

# Environment setup parameters
# patient = get_current("Patient")
# case = get_current("Case")

# Obtain image registration required
# case, trans_matrix = get_img_registration(case)
# print(trans_matrix)
# Copy ROI geometries from CT to MR
# copy_roi_geometries(case)

# Create context
context = zmq.Context()

# Define client ID
# client_id = str(patient.PatientID) + "-" + str(uuid.uuid4())[:8] # unique short ID
client_id = str(uuid.uuid4())[:8] # unique short ID

# Define ports
server_ip = "10.244.196.191"
main_port = "5560"
heartbeat_port = "5561"
stream_port = "5562"
data_port = "5563"

#  Socket for work
print("\nConnecting to PrimitiveTractography server...")
main_socket = context.socket(zmq.DEALER)
main_socket.linger = 0 # doesn't wait for anything when closing
main_socket.connect(f"tcp://{server_ip}:{main_port}")

# Socket for receiving terminal outputs
stream_socket = context.socket(zmq.PULL)
stream_socket.connect(f"tcp://{server_ip}:{stream_port}")

# Socket for receiving data
data_socket = context.socket(zmq.DEALER)
data_socket.connect(f"tcp://{server_ip}:{data_port}")

# Define heartbeat class
class HeartbeatManager:
    def __init__(self, context, server_ip, heartbeat_port, client_id):
        # Initialize by defining stuff
        self.context = context
        self.server_ip = server_ip
        self.heartbeat_port = heartbeat_port
        self.client_id = client_id
        self.poller = zmq.Poller()
        self.running = True
        self.connection_disconnects = 0

        # Create the socket
        self._create_socket()

    def _create_socket(self):
        # Create socket
        self.socket = self.context.socket(zmq.REQ)
        self.socket.linger = 0 # doesn't wait for anything when closing
        self.socket.connect(f"tcp://{self.server_ip}:{self.heartbeat_port}")
        self.poller.register(self.socket, zmq.POLLIN)

    def _recreate_socket(self):
        # Recreate socket (called when there's an error. REQ can't send without receiving first...)
        self.poller.unregister(self.socket) # Unregister from poller
        self.socket.close()
        self._create_socket()

    def start(self):
        # Start thread as daemon (background worker)
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()

    def stop(self, called_from_thread=False):
        # Close the socket
        self.running = False
        if not called_from_thread:
            self.thread.join()
        self.socket.close()

    def _heartbeat_loop(self):
        # Send (and check for) heartbeats while running
        while self.running:
            try:
                # Send string
                self.socket.send_string(f"PING:{self.client_id}")
                if dict(self.poller.poll(timeout=5000)): # Check for heartbeat for 5 seconds
                    reply = self.socket.recv_string() # Receive string
                    if reply == "PONG":
                        # print(f"[{datetime.datetime.now()}] [Heartbeat] Received from server")
                        self.connection_disconnects = 0 # Reset disconnects to 0
                    else:
                        print(f"[{datetime.datetime.now()}] [Heartbeat] Received from unexpected reply from server: {reply}")
                else:
                    # No reply. Recreate socket
                    print(f"[{datetime.datetime.now()}] [Heartbeat] No response! Reconnecting...")
                    self.connection_disconnects += 1 # add 1 to consecutive missed heartbeats
                    if self.connection_disconnects >= 3:
                        # Stop program if 3 missed heartbeats in a row
                        print("\nConnection with server unavailable. Stopping the program.")
                        # Close sockets and terminate context
                        global main_socket_active 
                        global stream_socket_active
                        global data_socket_active
                        main_socket_active = False # exit main socket loop
                        stream_socket_active = False # exit stream socket loop
                        data_socket_active = False # exit data socket loop
                        # time.sleep(0.1) # wait a bit

                        return # exit daemon function
                        # time.sleep(3) # wait for main socket to be done trying to receive 
                        # Let main socket be the one to close sockets

                        # main_socket.close()
                        # heartbeat.stop(called_from_thread=True) # Calls stop method in HeartbeatManager class
                        # context.term()
                        # sys.exit()
                    self._recreate_socket()

                time.sleep(10) # Wait 10 seconds between heartbeats
            except zmq.ZMQError as e:
                # Unexpected error. Recreate socket
                print(f"[{datetime.now()}] [Heartbeat] ZMQ error: {e}")
                self._recreate_socket()
                time.sleep(9) # Wait before retrying

# Initialize class and start
heartbeat = HeartbeatManager(context, server_ip, heartbeat_port, client_id)
heartbeat.start()

# Define function to receive stream socket outputs
def receive_stream():
    global stream_socket_active # access stream_socket_active flag
    while stream_socket_active:
        if dict(stream_poller.poll(timeout=3000)): # check for 3 seconds
            # Receive terminal outputs until script is done
            msg = stream_socket.recv_json()
            if msg["type"] == "stdout":
                print(f"[{datetime.datetime.now()}] REMOTE:", msg["data"])
            elif msg["type"] == "done":
                print(f"[{datetime.datetime.now()}] Script finished with code {msg['returncode']}")
                time.sleep(0.1) # Wait for main thread to say completed succesfully or with error
                print(f"\n[{datetime.datetime.now()}] Stopping the program.")
                # Close sockets and terminate context
                global main_socket_active 
                global data_socket_active
                main_socket_active = False # exit main socket loop
                stream_socket_active = False # exit stream socket loop
                data_socket_active = False # exit data socket loop
                # time.sleep(5) # wait for main socket to be done trying to receive 
                # Let main socket be the one to close sockets

                return # end function

                # main_socket.close()
                # heartbeat.stop() # Calls stop method in HeartbeatManager class
                # context.term()
                # sys.exit()
                # break
        time.sleep(0.1) # Wait a bit to remove weird errors when shutting down

# Create poller for main socket
poller = zmq.Poller()
poller.register(main_socket, zmq.POLLIN)

# Create poller for stream socket
stream_poller = zmq.Poller()
stream_poller.register(stream_socket, zmq.POLLIN)

# Create poller for data socket
data_poller = zmq.Poller()
data_poller.register(data_socket, zmq.POLLIN)

# Define function to receive data and plot Fury
data_socket_active = True
def data_dealer():
    global data_socket_active
    global trans_matrix
     # First send data if we have any
    if 'trans_matrix' in globals():
        data_socket.send_multipart([b'', b"RS data available"])
        trans_matrix = pickle.dumps({"trans_matrix" : trans_matrix}) # encode data
        # .encode('utf-8') # encode data in bytes
        data_socket.send_multipart([b'', trans_matrix])
    else: 
        data_socket.send_multipart([b'', b"RS data not available"])
    
    while data_socket_active:
        if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
            # print("Unpickling stuff!")
            # data = pickle.loads(data_socket.recv()) # receive data and unpickle
            # print("Received data on client!")
            _, data = data_socket.recv_multipart()  # receive data
            data = json.loads(data.decode('utf-8')) # decode data

            # Assign variables from data dictionary
            base_dir = Path(data["base_dir"])

            # Show tracts
            show_tracts(base_dir)
            
            # Tell server Fury window closed
            data_socket.send_multipart([b'', b"Data received. Fury window closed"])

            # Wait for data from server to show WMPL map
            while data_socket_active:
                if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
                    # data = data_socket.recv() # receive data and unpickle
                    # data = pickle.loads(data)
                    _, data = data_socket.recv_multipart()  # receive data
                    data = json.loads(data.decode('utf-8')) # decode data
                    
                    # Assign variables from data dictionary
                    base_dir = Path(data["base_dir"])
                    # slice_thickness = data["slice_thickness"]
                    
                    # Show WMPL map
                    show_wmpl(base_dir)

                    # Tell server Fury window closed
                    data_socket.send_multipart([b'', b"Data received. Fury window closed"])

                    # if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
                    #     if data_socket.recv_string() == "Void":
                            # return # Function is finished
                    return # Function is finished
                
        time.sleep(1) # Wait 1 second to avoid error messages when exiting program

try:
    print(f"\n[{datetime.datetime.now()}] Sending request to server...")
    main_socket.send_multipart([b'', b"READY"])
    main_socket_active = True
    while main_socket_active:
        if dict(poller.poll(timeout=3000)): # Check for reply for 3 seconds
            #  Get the reply.
            _, message = main_socket.recv_multipart()
            message = message.decode()
            if message == "READY":
                print(f"\n[{datetime.datetime.now()}] Server available. Starting tractography...")
                main_socket.send_multipart([b'', b"RUN"])
                stream_socket_active = True
                threading.Thread(target=receive_stream, daemon=True).start() # start to receive from stream socket
                threading.Thread(target=data_dealer, daemon=True).start() # start to send/receive data
                while main_socket_active:
                    if dict(poller.poll(timeout=1000)): # Check for reply for 1 second
                        _, message = main_socket.recv_multipart()
                        message = message.decode()
                        if message == "FINISHED":
                            print(f"[{datetime.datetime.now()}] Tractography and white matter path length map succesfully completed!")
                            break
                        elif message == "ERROR":
                            print(f"[{datetime.datetime.now()}] [ERROR] Error during tractography.")
                            break
                        else:
                            print(f"[{datetime.datetime.now()}] Unexpected returned message while performing tractography: {message}.")
                            break
            else:
                print(f"Unexpected returned message prior to commencing tractography: {message}")
                break
except Exception as e:
        print(f"Error: {e}")
finally:
    # Close sockets and terminate context
    time.sleep(3) # Wait a bit for threads to stop polling

    main_socket.close()
    stream_socket.close()
    data_socket.close()
    heartbeat.stop() # Calls stop method in HeartbeatManager class
    context.term()