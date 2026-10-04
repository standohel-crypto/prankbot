import asyncio
import json
import os
from dataclasses import dataclass
from typing import Dict

from aiohttp import web
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "Nurda2020")
PAIRING_KEY = os.getenv("PAIRING_KEY", "CHANGE_ME")

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "10000"))

authorized_chats = set()
devices: Dict[str, "Device"] = {}

# Сервер управляет только именами заранее встроенных безопасных действий.
ENABLED_ACTIONS = {
    "warning": "⚠️ Warning",
    "error": "❌ Error",
    "joke": "😂 Joke",
    "prank": "😈 Prank",
    "fake_bsod": "🟦 Fake BSOD",
    "fake_lock": "🔒 Fake Lock",
    "fake_freeze": "🥶 Fake Freeze",
    "fake_shutdown": "⏻ Fake Shutdown",
    "status": "📡 Status",
}


@dataclass
class Device:
    device_id: str
    name: str
    ws: web.WebSocketResponse


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥 Устройства", callback_data="devices")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="devices")],
    ])


def device_menu(device_id: str):
    rows = []
    actions = [(k, v) for k, v in ENABLED_ACTIONS.items() if k != "status"]

    for i in range(0, len(actions), 2):
        row = []
        for action, title in actions[i:i+2]:
            row.append(
                InlineKeyboardButton(
                    title,
                    callback_data=f"cmd:{device_id}:{action}"
                )
            )
        rows.append(row)

    rows.append([
        InlineKeyboardButton(
            "📡 Status",
            callback_data=f"cmd:{device_id}:status"
        )
    ])
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="devices")])
    return InlineKeyboardMarkup(rows)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: /login пароль")
        return

    if " ".join(context.args) != LOGIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль")
        return

    authorized_chats.add(update.effective_chat.id)
    await update.message.reply_text(
        "✅ Вход выполнен",
        reply_markup=main_menu()
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in authorized_chats:
        await update.message.reply_text("🔐 Сначала /login пароль")
        return

    await update.message.reply_text(
        "🎛 PrankBot Cloud",
        reply_markup=main_menu()
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    if q.message.chat.id not in authorized_chats:
        await q.answer("Сначала /login пароль", show_alert=True)
        return

    await q.answer()
    data = q.data or ""

    if data == "home":
        await q.edit_message_text(
            "🎛 PrankBot Cloud",
            reply_markup=main_menu()
        )
        return

    if data == "devices":
        if not devices:
            await q.edit_message_text(
                "Нет подключённых устройств.",
                reply_markup=main_menu()
            )
            return

        rows = [
            [
                InlineKeyboardButton(
                    f"🟢 {dev.name}",
                    callback_data=f"device:{device_id}"
                )
            ]
            for device_id, dev in sorted(
                devices.items(),
                key=lambda x: x[1].name.lower()
            )
        ]
        rows.append([
            InlineKeyboardButton("⬅️ Назад", callback_data="home")
        ])

        await q.edit_message_text(
            "Выбери ПК:",
            reply_markup=InlineKeyboardMarkup(rows)
        )
        return

    if data.startswith("device:"):
        device_id = data.split(":", 1)[1]
        dev = devices.get(device_id)

        if not dev:
            await q.edit_message_text(
                "🔴 ПК оффлайн.",
                reply_markup=main_menu()
            )
            return

        await q.edit_message_text(
            f"🖥 {dev.name}\nСтатус: 🟢 онлайн",
            reply_markup=device_menu(device_id)
        )
        return

    if data.startswith("cmd:"):
        _, device_id, action = data.split(":", 2)

        if action not in ENABLED_ACTIONS:
            await q.edit_message_text("❌ Действие отключено.")
            return

        dev = devices.get(device_id)

        if not dev:
            await q.edit_message_text(
                "🔴 ПК уже отключился.",
                reply_markup=main_menu()
            )
            return

        try:
            await dev.ws.send_json({
                "type": "action",
                "name": action,
            })

            await q.edit_message_text(
                f"✅ {ENABLED_ACTIONS[action]} отправлено на {dev.name}",
                reply_markup=device_menu(device_id)
            )
        except Exception:
            devices.pop(device_id, None)
            await q.edit_message_text(
                "❌ Связь потеряна.",
                reply_markup=main_menu()
            )


async def health_handler(request):
    return web.json_response({
        "ok": True,
        "service": "PrankBot Cloud",
        "devices_online": len(devices),
    })


async def root_handler(request):
    return web.Response(
        text="PrankBot Cloud is running",
        content_type="text/plain"
    )


async def websocket_handler(request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    device_id = None

    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)

        if first.get("type") != "register":
            await ws.close(code=4001, message=b"register required")
            return ws

        if first.get("pairing_key") != PAIRING_KEY:
            await ws.close(code=4003, message=b"bad pairing key")
            return ws

        device_id = str(first.get("device_id", ""))[:80]
        name = str(first.get("name", "PC"))[:40]

        if not device_id:
            await ws.close(code=4004, message=b"missing device id")
            return ws

        old = devices.get(device_id)
        if old and old.ws is not ws:
            try:
                await old.ws.close()
            except Exception:
                pass

        devices[device_id] = Device(device_id, name, ws)

        await ws.send_json({
            "type": "registered",
            "enabled_actions": list(ENABLED_ACTIONS.keys()),
        })

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    continue

                if data.get("type") == "ping":
                    await ws.send_json({"type": "pong"})

            elif msg.type in (
                web.WSMsgType.ERROR,
                web.WSMsgType.CLOSED,
            ):
                break

    except Exception:
        pass
    finally:
        if device_id:
            current = devices.get(device_id)
            if current and current.ws is ws:
                devices.pop(device_id, None)

    return ws


async def start_telegram(app):
    if BOT_TOKEN == "PASTE_BOT_TOKEN_HERE":
        raise RuntimeError("Set BOT_TOKEN environment variable")

    tg = Application.builder().token(BOT_TOKEN).build()
    tg.add_handler(CommandHandler("login", login))
    tg.add_handler(CommandHandler("start", start))
    tg.add_handler(CallbackQueryHandler(callback))

    await tg.initialize()
    await tg.start()
    await tg.updater.start_polling()

    app["telegram"] = tg


async def stop_telegram(app):
    tg = app.get("telegram")
    if not tg:
        return

    await tg.updater.stop()
    await tg.stop()
    await tg.shutdown()


def create_app():
    app = web.Application()

    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ws", websocket_handler)

    app.on_startup.append(start_telegram)
    app.on_cleanup.append(stop_telegram)

    return app


if __name__ == "__main__":
    web.run_app(
        create_app(),
        host=HOST,
        port=PORT,
    )
