import asyncio
import json
import os
import queue
import socket
import threading
import tkinter as tk
import uuid

import pystray
from PIL import Image, ImageDraw
import websockets

from actions import ACTIONS

APP_NAME = "PrankBot Agent"

# Пример:
# wss://prankbot-cloud-xxxx.onrender.com/ws
SERVER_URL = os.getenv(
    "PRANKBOT_SERVER_URL",
    "wss://YOUR-SERVER.onrender.com/ws"
)

PAIRING_KEY = os.getenv(
    "PAIRING_KEY",
    "CHANGE_ME"
)

events = queue.Queue()
connection_status = "Отключено"


def get_device_id():
    raw = f"{socket.gethostname()}-{uuid.getnode()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))


def get_device_name():
    return socket.gethostname()[:40]


root = tk.Tk()
root.withdraw()
root.title(APP_NAME)


def run_action(name):
    func = ACTIONS.get(name)
    if func is None:
        return

    try:
        func(root)
    except Exception:
        pass


def process_queue():
    try:
        while True:
            action = events.get_nowait()
            run_action(action)
    except queue.Empty:
        pass

    root.after(100, process_queue)


async def connection_loop():
    global connection_status

    delay = 2

    while True:
        try:
            connection_status = "Подключение..."

            async with websockets.connect(
                SERVER_URL,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:

                await ws.send(json.dumps({
                    "type": "register",
                    "device_id": get_device_id(),
                    "name": get_device_name(),
                    "pairing_key": PAIRING_KEY,
                }))

                reply = json.loads(
                    await asyncio.wait_for(
                        ws.recv(),
                        timeout=10
                    )
                )

                if reply.get("type") != "registered":
                    raise RuntimeError("registration failed")

                enabled = set(reply.get("enabled_actions", []))

                connection_status = "Подключено"
                delay = 2

                async def heartbeat_sender():
                    while True:
                        await asyncio.sleep(60)
                        await ws.send(json.dumps({
                            "type": "ping"
                        }))

                heartbeat_task = asyncio.create_task(
                    heartbeat_sender()
                )

                try:
                    async for raw in ws:
                        msg = json.loads(raw)

                        if msg.get("type") != "action":
                            continue

                        name = msg.get("name")

                        if name in enabled and name in ACTIONS:
                            events.put(name)
                finally:
                    heartbeat_task.cancel()

        except Exception:
            connection_status = "Отключено"
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


def network_thread():
    asyncio.run(connection_loop())


def make_icon():
    img = Image.new(
        "RGBA",
        (64, 64),
        (40, 40, 40, 255)
    )
    d = ImageDraw.Draw(img)
    d.ellipse(
        (8, 8, 56, 56),
        fill=(245, 190, 45, 255)
    )
    return img


def show_status(icon=None, item=None):
    messagebox = __import__(
        "tkinter.messagebox",
        fromlist=["messagebox"]
    )
    messagebox.showinfo(
        APP_NAME,
        f"Устройство: {get_device_name()}\n"
        f"Статус: {connection_status}",
        parent=root
    )


def exit_app(icon=None, item=None):
    if icon:
        icon.stop()
    root.after(0, root.destroy)


tray = pystray.Icon(
    APP_NAME,
    make_icon(),
    APP_NAME,
    menu=pystray.Menu(
        pystray.MenuItem("Статус", show_status),
        pystray.MenuItem("Выход", exit_app),
    ),
)

threading.Thread(
    target=tray.run,
    daemon=True
).start()

threading.Thread(
    target=network_thread,
    daemon=True
).start()

root.after(100, process_queue)
root.mainloop()
