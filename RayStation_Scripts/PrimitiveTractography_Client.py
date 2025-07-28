# Client for Primitive Tractography

# Imports
import zmq
import time
import datetime
import threading
import uuid

# Create context
context = zmq.Context()

# Define client ID
client_id = str(uuid.uuid4())[:8] # unique short ID

# Define ports
server_ip = "10.244.196.191"
main_port = "5560"
heartbeat_port = "5561"

#  Socket for work
print("Connecting to PrimitiveTractography server…")
main_socket = context.socket(zmq.REQ)
main_socket.linger = 0 # doesn't wait for anything when closing
main_socket.connect(f"tcp://{server_ip}:{main_port}")

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

    def stop(self):
        # Close the socket
        self.running = False
        self.thread.join()
        self.socket.close()

    def _heartbeat_loop(self):
        # Send (and check for) heartbeats while running
        while self.running:
            try:
                # Send string
                self.socket.send_string(f"PING:{self.client_id}")
                if dict(self.poller.poll(timeout=1000)): # Check for heartbeat for 1 second
                    reply = self.socket.recv_string() # Receive string
                    print(f"[{datetime.datetime.now()}] [Heartbeat] Received: {reply}")
                else:
                    # No reply. Recreate socket
                    print(f"[{datetime.datetime.now()}] [Heartbeat] No response! Reconnecting...")
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

# Create poller to wait for server
poller = zmq.Poller()
poller.register(main_socket, zmq.POLLIN)

try:
    print("Sending request to server...")
    main_socket.send(b"READY")
    if dict(poller.poll(timeout=5000)): # Check for reply for 5 seconds
        #  Get the reply.
        message = main_socket.recv().decode()
        if message == "READY":
            print("Server available. Starting tractography...")
            main_socket.send(b"FINISHED")
            while True:
                if dict(poller.poll(timeout=1000)): # Check for reply for 1 second
                    message = main_socket.recv().decode()
                    if message == "FINISHED":
                        print("White matter path length maps succesfully compeleted.")
                        break
                    elif message == "ERROR":
                        print("Error during tractography.")
                        break
                    else:
                        print("Unexpected returned message while performing tractography.")
                        break
                else:
                    pass # Just have to wait for tractography to be done...
        else:
            print("Unexpected returned message prior to commencing tractography.")
except Exception as e:
        print(f"Error: {e}")
finally:
    # Close sockets and terminate context
    main_socket.close()
    heartbeat.stop() # Calls stop method in HeartbeatManager class
    context.term()