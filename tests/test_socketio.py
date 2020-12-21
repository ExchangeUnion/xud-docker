import socketio
import pytest
from urllib.request import urlopen
import ssl
from asyncio import sleep
import time


@pytest.mark.asyncio
async def test1():
    sio = socketio.AsyncClient(ssl_verify=False)

    # @sio.event
    # def message(data):
    #     print("I received a message!")
    #
    # @sio.on('my message')
    # def on_message(data):
    #     print("I received a message!")
    #
    # @sio.event
    # async def message(data):
    #     print("I received a message!")

    # @sio.event
    # def connect():
    #     print("I'm connected!")
    #
    # @sio.event
    # def connect_error(error):
    #     print("The connection failed!")
    #
    # @sio.event
    # def disconnect():
    #     print("I'm disconnected!")

    await sio.connect("https://localhost:8080", transports=['websocket'], headers={
        "X-Type": "Launcher v2.0.0-alpha.3"
    })
    print('my sid is', sio.sid)

    await sleep(10)

    await sio.disconnect()


def test2():
    sio = socketio.Client(ssl_verify=False)
    sio.connect("https://localhost:8080", transports=['websocket'], headers={
        "X-Type": "Launcher v2.0.0-alpha.3"
    })
    print('my sid is', sio.sid)
    time.sleep(10)
    sio.disconnect()


def test_socketio_protocol_version():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    r = urlopen("https://localhost:8080/socket.io/?EIO=3&transport=polling&t=ML4jUwU&b64=1", context=ctx)
    print(r.read())

