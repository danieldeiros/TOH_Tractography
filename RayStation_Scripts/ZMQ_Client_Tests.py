# Client for zmq tests

#
#   Hello World client in Python
#   Connects REQ socket to tcp://localhost:5555
#   Sends "Hello" to server, expects "World" back
#

import zmq
import time
import datetime
import subprocess
import threading
import uuid

context = zmq.Context()

client_id = str(uuid.uuid4())[:8] # unique short ID

# Define ports
server_ip = "10.244.196.191"
main_port = "5560"
heartbeat_port = "5561"

#  Socket to talk to server
print("Connecting to hello world server…")
main_socket = context.socket(zmq.REQ)
main_socket.linger = 0
# socket.connect(f"tcp://localhost:{port}")
main_socket.connect(f"tcp://{server_ip}:{main_port}")

# Socket to have heartbeat
# print('Connecting to heartbeat server...')
# heartbeat_socket = context.socket(zmq.REQ)
# heartbeat_socket.connect(f"tcp://{server_ip}:{heartbeat_port}")

# # Define heartbeat function
# def heartbeat():
#     global heartbeat_socket
#     while True:
#         try:
#             heartbeat_socket.send_string(f"PING:{client_id}")
#             if heartbeat_socket.poll(timeout=1000):  # 1 sec timeout
#                 reply = heartbeat_socket.recv_string()
#                 print(f"[Heartbeat] Received: {reply}")
#             else:
#                 print("[Heartbeat] No response from server!")
#                 # Reset by recreating the socket
#                 poller.unregister(heartbeat_socket)
#                 heartbeat_socket.close()
#                 heartbeat_socket = context.socket(zmq.REQ)
#                 heartbeat_socket.connect(f"tcp://{server_ip}:{heartbeat_port}")
#                 poller.register(heartbeat_socket, zmq.POLLIN)
#                 # Wait 9+1 seconds for another attempt
#                 time.sleep(9) # Wait 9 secs
#         except zmq.ZMQError as e:
#             print(f"[Heartbeat] ZMQ error: {e}")
#             break
#         time.sleep(1)  # ping every 1 sec

# # Start heartbeat in background
# heartbeat_thread = threading.Thread(target=heartbeat, daemon=True).start()

# Define heartbeat class
class HeartbeatManager:
    def __init__(self, context, server_ip, heartbeat_port, client_id):
        self.context = context
        self.server_ip = server_ip
        self.heartbeat_port = heartbeat_port
        self.client_id = client_id
        self.poller = zmq.Poller()
        self.running = True

        # Create the socket
        self._create_socket()

    def _create_socket(self):
        self.socket = self.context.socket(zmq.REQ)
        self.socket.linger = 0
        self.socket.connect(f"tcp://{self.server_ip}:{self.heartbeat_port}")
        self.poller.register(self.socket, zmq.POLLIN)

    def _recreate_socket(self):
        try:
            self.poller.unregister(self.socket)
        except KeyError:
            pass  # Socket may not have been registered

        self.socket.close()
        self._create_socket()

    def start(self):
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        # if self.thread:
        self.thread.join()
        self.socket.close()

    def _heartbeat_loop(self):
        while self.running:
            try:
                self.socket.send_string(f"PING:{self.client_id}")
                time.sleep(10) # Wait 10 seconds between heartbeats
                if dict(self.poller.poll(timeout=1000)): # Check for heartbeat for 1 second
                    reply = self.socket.recv_string()
                    print(f"[{datetime.datetime.now()}] [Heartbeat] Received: {reply}")
                else:
                    print(f"[{datetime.datetime.now()}] [Heartbeat] No response! Reconnecting...")
                    self._recreate_socket()
                    time.sleep(9)  # wait before retrying
            except zmq.ZMQError as e:
                print(f"[{datetime.now()}] [Heartbeat] ZMQ error: {e}")
                self._recreate_socket()
                time.sleep(9) # wait before retrying

heartbeat = HeartbeatManager(context, server_ip, heartbeat_port, client_id)
heartbeat.start()

# Create poller to wait for server
poller = zmq.Poller()
poller.register(main_socket, zmq.POLLIN)

# Ping server to check if responsive
# subprocess.run(f"ping {server_ip}", check=True)

#  Do 10 requests, waiting each time for a response
try:
    try:
        for request in range(10):
            print(f"Sending request {request+1} …")
            main_socket.send(b"Hello")
            if dict(poller.poll(timeout=10000)): # wait 10 seconds
                #  Get the reply.
                message = main_socket.recv().decode()
                print(f"Received reply {request+1} [ {message} ]\n")
            else:
                print(f"No response for request {request + 1} (timed out)\n")
                # Reset by recreating the socket
                poller.unregister(main_socket)
                main_socket.close()
                main_socket = context.socket(zmq.REQ)
                main_socket.linger = 0
                main_socket.connect(f"tcp://{server_ip}:{main_port}")
                poller.register(main_socket, zmq.POLLIN)

    except Exception as e:
        print(f"Error during request {request + 1}: {e}\n")
    
finally:
    # close stuff
    main_socket.close()
    heartbeat.stop()
    context.term()


# HEARTBEAT TESTS

# context = zmq.Context()
# socket = context.socket(zmq.REQ)
# socket.connect(f"tcp://{server_ip}:{port}")

# poller = zmq.Poller()
# poller.register(socket, zmq.POLLIN)

# try:
#     while True:
#         socket.send(b"PING")
#         print("Sent heartbeat to server...")

#         socks = dict(poller.poll(timeout=2000))  # wait up to 2s
#         if socket in socks:
#             reply = socket.recv().decode()
#             print(f"Received reply: {reply}")
#         else:
#             print("No response from server (timeout)")

#         time.sleep(5)  # send heartbeat every 5s

# except KeyboardInterrupt:
#     print("Client shutting down.")
# finally:
#     socket.close()
#     context.term()
        