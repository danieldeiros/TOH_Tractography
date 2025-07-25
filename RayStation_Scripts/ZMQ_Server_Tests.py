# Server for zmq tests

#
#   Hello World server in Python
#   Binds REP socket to tcp://*:5555
#   Expects b"Hello" from client, replies with b"World"
#

import time
import datetime
import zmq
import threading

# Define port numbers
main_port = "5560"
heartbeat_port = "5561"

context = zmq.Context()

# Main socket for work
main_socket = context.socket(zmq.REP)
# socket.bind(f"tcp://0.0.0.0:{port}")
main_socket.bind(f"tcp://*:{main_port}")

# Heartbeat socket
heartbeat_socket = context.socket(zmq.REP)
heartbeat_socket.bind(f"tcp://*:{heartbeat_port}")

# Define main poller
main_poller = zmq.Poller()
main_poller.register(main_socket, zmq.POLLIN)

# Define heartbeat poller
heartbeat_poller = zmq.Poller()
heartbeat_poller.register(heartbeat_socket, zmq.POLLIN)

# Tracks last heartneat time per client ID
last_heartbeat = {}
heartbeat_timeout = 15 # seconds

def monitor_heartbeats():
    while True:
        try:
            socks = dict(heartbeat_poller.poll(timeout=100)) # Check every 100 ms
            # print('heartbeat here')
            if heartbeat_socket in socks:
                message = heartbeat_socket.recv().decode()
                if message.startswith("PING:"):
                    client_id = message.split(":")[1]
                    last_heartbeat[client_id] = time.time()
                    readable_time = datetime.datetime.fromtimestamp(last_heartbeat[client_id]).strftime("%d/%m/%Y %H:%M:%S.%f")
                    print(f"[Heartbeat] Received from {client_id}. [{readable_time}]")
                    heartbeat_socket.send(b"PONG")
                else:
                    heartbeat_socket.send(b"UNKNOWN")

            now = time.time()
            to_remove = []
            for client_id, timestamp in last_heartbeat.items():
                if now - timestamp > heartbeat_timeout:
                    readable_time = datetime.datetime.fromtimestamp(now).strftime("%d/%m/%Y %H:%M:%S.%f")
                    print(f"[Heartbeat] Client '{client_id}' missed heartbeat! Assuming disconnected. [{readable_time}]")
                    to_remove.append(client_id)
            for client_id in to_remove:
                del last_heartbeat[client_id]

            time.sleep(1) # wait a bit... removes weird message "Exception in thread Thread-1 (monitor_heartbeats):" after shutting down
        except Exception as e:
            print(f"[{datetime.now()}] [Heartbeat] ZMQ error: {e}")

# Start heartbeat monitoring thread
heartbeat_thread = threading.Thread(target=monitor_heartbeats, daemon=True)
heartbeat_thread.start()

try:
    print("Waiting for message...")
    while True:
        # print("Waiting for message...")
        # print("Polling for new message...")
        socks = dict(main_poller.poll(timeout=100)) # Check every 100 ms
        if main_socket in socks:
            #  Wait for next request from client
            message = main_socket.recv().decode()
            print(f"\nReceived request: {message}")

            #  Do some 'work'
            time.sleep(5)

            #  Send reply back to client
            main_socket.send(b"World")

except KeyboardInterrupt:
    print("\nShutting down server from user (KeyboardInterrupt).")
finally:

    # Close sockets and terminate context
    main_socket.close()
    heartbeat_socket.close()
    context.term()

# HEARTBEAT TESTS

# context = zmq.Context()
# socket = context.socket(zmq.REP)
# socket.bind(f"tcp://0.0.0.0:{port}")

# print("Server started and waiting for heartbeat...")

# try:
#     while True:
#         message = socket.recv().decode()
#         if message == "PING":
#             print("Received heartbeat from client.")
#             socket.send(b"PONG")
#         else:
#             print(f"Received: {message}")
#             socket.send(b"ACK")
# except KeyboardInterrupt:
#     print("Shutting down.")
# finally:
#     socket.close()
#     context.term()