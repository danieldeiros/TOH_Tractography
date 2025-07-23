# Server for Primitive Tractography

#
#   Hello World server in Python
#   Binds REP socket to tcp://*:5555
#   Expects b"Hello" from client, replies with b"World"
#

import time
import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)

try:
    while True:
        socks = dict(poller.poll(timeout=100)) # Check every 100 ms
        if socket in socks:
            #  Wait for next request from client
            message = socket.recv().decode()
            print(f"Received request: {message}\n")

            #  Do some 'work'
            time.sleep(1)

            #  Send reply back to client
            socket.send(b"World")
except KeyboardInterrupt:
    print("\nShutting down server from user (KeyboardInterrupt).")
finally:
    socket.close()
    context.term()