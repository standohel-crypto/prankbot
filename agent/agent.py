import asyncio
import ctypes
import json
import logging
import os
import queue
import socket
import sys
import threading
import tkinter as tk
import uuid
from pathlib import Path

import pystray
from PIL import Image, ImageDraw
import websockets

from actions import ACTIONS

APP_NAME = "PrankBot Agent"
SERVER_URL = os.getenv(
    "PRANKBOT_SERVER_URL",
    "wss://prankbot-gmz7.onrender.com/ws"
)
PAIRING_KEY = os.getenv(
    "PAIRING_KEY",
    "Nurdix_Prank_2026_7xK91"
)

events = queue.Queue()
connection_status = "Отключено"
_single_instance_handle = None


def setup_logging():
    try:
        base = Path(os.getenv("LOCALAPPDATA", Path.home())) / "PrankBot"
        base.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=base / "agent.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            encoding="utf-8",
        )
    except Exception:
        logging.basicConfig(level=logging.INFO)


def ensure_single_instance():
    """Do not allow two agents with the same device id to fight for one socket."""
    global _single_instance_handle

    if os.name != "nt":
        return

    kernel32 = ctypes.windll.kernel32
    kernel32.SetLastError(0)
    handle = kernel32.CreateMutexW(None, False, "Local\\PrankBotAgent_SingleInstance_v1")
    error = kernel32.GetLastError()

    if not handle or error == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)

    _single_instance_handle = handle


def get_device_id():
    raw = f"{socket.gethostname()}-{uuid.getnode()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))


def get_device_name():
    return socket.gethostname()[:40]


setup_logging()
ensure_single_instance()

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
        logging.exception("Action failed: %s", name)


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

    # Keep reconnects quick. The old version could back off all the way to
    # 30 seconds, which made the device disappear from Telegram for a while.
    delay = 1.0

    while True:
        try:
            connection_status = "Подключение..."
            logging.info("Connecting to %s", SERVER_URL)

            async with websockets.connect(
                SERVER_URL,
                ping_interval=15,
                ping_timeout=30,
                close_timeout=5,
                open_timeout=15,
            ) as ws:
                await ws.send(json.dumps({
                    "type": "register",
                    "device_id": get_device_id(),
                    "name": get_device_name(),
                    "pairing_key": PAIRING_KEY,
                }))

                reply = json.loads(
                    await asyncio.wait_for(ws.recv(), timeout=10)
                )

                if reply.get("type") != "registered":
                    raise RuntimeError(f"registration failed: {reply!r}")

                enabled = set(reply.get("enabled_actions", []))
                connection_status = "Подключено"
                delay = 1.0
                logging.info("Registered as %s", get_device_name())

                async def heartbeat_sender():
                    # An actual text message every 10s both detects dead links
                    # quickly and counts as inbound WebSocket traffic on Render.
                    while True:
                        await asyncio.sleep(10)
                        await ws.send(json.dumps({"type": "ping"}))

                heartbeat_task = asyncio.create_task(heartbeat_sender())

                try:
                    async for raw in ws:
                        msg = json.loads(raw)

                        if msg.get("type") == "pong":
                            continue

                        if msg.get("type") != "action":
                            continue

                        name = msg.get("name")
                        if name in enabled and name in ACTIONS:
                            events.put(name)
                finally:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass

        except Exception as exc:
            connection_status = "Отключено"
            logging.warning("Connection lost: %r; reconnect in %.1fs", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 5.0)


def network_thread():
    try:
        asyncio.run(connection_loop())
    except Exception:
        logging.exception("Network thread stopped unexpectedly")


def make_icon():
    img = Image.new("RGBA", (64, 64), (40, 40, 40, 255))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=(245, 190, 45, 255))
    return img


def show_status(icon=None, item=None):
    messagebox = __import__("tkinter.messagebox", fromlist=["messagebox"])
    messagebox.showinfo(
        APP_NAME,
        f"Устройство: {get_device_name()}\n"
        f"Статус: {connection_status}",
        parent=root,
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

threading.Thread(target=tray.run, daemon=True).start()
threading.Thread(target=network_thread, daemon=True).start()

root.after(100, process_queue)
root.mainloop()
