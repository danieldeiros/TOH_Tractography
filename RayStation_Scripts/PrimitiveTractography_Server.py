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

# Create context
context = zmq.Context()

# Main socket for work
main_socket = context.socket(zmq.REP)
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

# Track last heartbeat time per client ID
last_heartbeat = {}
heartbeat_timeout = 15 # seconds

def monitor_heartbeats():
    while True:
        try:
            socks = dict(heartbeat_poller.poll(timeout=100)) # Check for 100 ms
            if heartbeat_socket in socks:
                message = heartbeat_socket.recv().decode()
                if message.startswith("PING:"):
                    client_id = message.split(":")[1]
                    last_heartbeat[client_id] = time.time()
                    readable_time = datetime.datetime.fromtimestamp(last_heartbeat[client_id]).strftime("%d/%m/%Y %H:%M:%S.%f")
                    print(f"[{readable_time}] [Heartbeat] Received from {client_id}.")
                    heartbeat_socket.send(b"PONG")
                else:
                    heartbeat_socket.send(b"UNKNOWN")

            now = time.time()
            to_remove = []
            for client_id, timestamp in last_heartbeat.items():
                if now - timestamp > heartbeat_timeout:
                    readable_time = datetime.datetime.fromtimestamp(now).strftime("%d/%m/%Y %H:%M:%S.%f")
                    print(f"[{readable_time}] [Heartbeat] Client '{client_id}' missed heartbeat! Assuming disconnected.")
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
    print("Waiting for client message...")
    while True:
        socks = dict(main_poller.poll(timeout=100)) # Check for 100 ms
        if main_socket in socks:
            #  Wait for next request from client
            message = main_socket.recv().decode()
            if message == "READY":
                # Let client know server is ready
                main_socket.send(b"READY")
            elif message == "FINISHED":
                # Start tractography script
                path = "V:/Common/Staff Personal Folders/DanielH/RayStation_Scripts/Tractography/PrimitiveTractography.py"
                try:
                    # Call tractography script with python venv
                    subprocess.run([sys.executable, path], capture_output=True, check=True)
                    # print("Tractography completed succesfully.")
                    main_socket.send(b"FINISHED")
                except subprocess.CalledProcessError as e:
                    print("Script failed with return code", e.returncode)
                    print("STDERR:", e.stderr)
                    main_socket.send(b"ERROR")
            else:
                print(f"Unexpected message received from client")
except KeyboardInterrupt:
    print("\nShutting down server from user (KeyboardInterrupt).")
finally:
    # Close sockets and terminate context
    main_socket.close()
    heartbeat_socket.close()
    context.term()
