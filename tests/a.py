import socketio
import time
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

sio = socketio.Client(ssl_verify=False, logger=logging.getLogger("root"))

@sio.event
def connect():
    print("I'm connected!")

@sio.event
def connect_error(error):
    print("The connection failed!")

@sio.event
def disconnect():
    print("I'm disconnected!")


# sio.connect("https://localhost:8080", transports=['websocket'], headers={
#     "X-Type": "Launcher v2.0.0-alpha.3"
# })
sio.connect("http://localhost:8080", transports=['websocket'])
print('my sid is', sio.sid)
time.sleep(10)
sio.disconnect()
