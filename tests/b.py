import asyncio
import socketio
from asyncio import sleep
import logging
import sys

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


async def main():
    sio = socketio.AsyncClient(ssl_verify=False, logger=logging.getLogger("root"))

    # @sio.event
    # def message(data):
    #     print("I received a message!")
    #
    # @sio.on('my message')
    # def on_message(data):
    #     print("I received a message!")
    #
    @sio.event
    async def message(data):
        print("message", data)

    @sio.event
    def connect():
        print("connect")

    @sio.event
    def connect_error(error):
        print("connect_error", error)

    @sio.event
    def disconnect():
        print("disconnect")

    await sio.connect("http://localhost:8080", transports=['websocket'], headers={
        "X-Type": "Launcher v2.0.0-alpha.3"
    }, namespaces=['/sss'])
    print('my sid is', sio.sid)

    await sio.sleep(3)

    await sio.emit("test", "hello")

    await sio.sleep(10)

    await sio.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
