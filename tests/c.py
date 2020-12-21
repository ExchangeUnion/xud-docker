import asyncio
import aiohttp
import json
import threading
import time


fut = None
_ws = None


async def main(loop):

    global _ws

    timeout = aiohttp.ClientTimeout(total=3, connect=3, sock_read=3, sock_connect=3)
    async with aiohttp.ClientSession(loop=loop, timeout=timeout) as session:
        async with session.ws_connect("http://localhost:8080/launcher") as ws:

            _ws = ws

            # async def close():
            #     await asyncio.wrap_future(fut, loop=loop)
            #     print("close")
            #     await ws.close()
            #     print("closed")
            #
            # loop.create_task(close())

            print("1")

            async for msg in ws:

                print("2")
                print(msg)

                msg: aiohttp.WSMessage
                if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break

                req = json.loads(msg.data)
                if req["method"] == "getinfo":
                    info = {
                        "wallets": {
                            "defaultPassword": True,
                            "mnemonicShown": False,
                        },
                        "backup": {
                            "location": "...",
                            "defaultLocation": True,
                        }
                    }
                    resp = {"result": json.dumps(info), "error": None, "id": req["id"]}
                    print(resp)
                    await ws.send_json(resp)

            print("3")


def stop(loop):
    time.sleep(10)
    print("set_result")
    # fut.set_result(None)
    asyncio.run_coroutine_threadsafe(_ws.close(), loop)
    print("set_result done")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    t = threading.Thread(target=stop, args=(loop,))
    t.start()
    loop.run_until_complete(main(loop))
