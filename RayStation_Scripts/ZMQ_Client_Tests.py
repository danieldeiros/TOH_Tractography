# Client for Primitive Tractography

#
#   Hello World client in Python
#   Connects REQ socket to tcp://localhost:5555
#   Sends "Hello" to server, expects "World" back
#

import zmq
import subprocess

context = zmq.Context()

# Define ports
server_ip = "10.244.196.191"
port = "5560"

#  Socket to talk to server
print("Connecting to hello world server…")
socket = context.socket(zmq.REQ)
# socket.connect(f"tcp://localhost:{port}")
socket.connect(f"tcp://{server_ip}:{port}")
# print(f"tcp://{server_ip}:{port}")

poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)

# Ping server to check if responsive
subprocess.run(f"ping {server_ip}", check=True)

#  Do 10 requests, waiting each time for a response
for request in range(10):
    print(f"Sending request {request+1} …")
    socket.send(b"Hello")

    try:
        if dict(poller.poll(timeout=3000)): # wait 3 seconds
            #  Get the reply.
            message = socket.recv().decode()
            print(f"Received reply {request+1} [ {message} ]\n")
        else:
            print(f"No response for request {request + 1} (timed out)\n")
    except Exception as e:
        print(f"Error during request {request + 1}: {e}\n")
    
# close stuff
socket.close()
context.term()
        