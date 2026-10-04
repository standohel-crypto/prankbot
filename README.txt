PRANKBOT CLOUDSAFE — RENDER READY

SERVER ROUTES
-------------
GET /
    Проверка, что приложение отвечает.

GET /health
    JSON health check:
    {
      "ok": true,
      "service": "PrankBot Cloud",
      "devices_online": N
    }

GET /ws
    WebSocket endpoint для Windows Agents.

RENDER
------
В репозиторий для Render нужны:

server/server.py
server/requirements.txt
Dockerfile
render.yaml

Environment variables:

BOT_TOKEN=...
LOGIN_PASSWORD=Nurda2020
PAIRING_KEY=придумай_длинный_секрет

После deploy адрес будет примерно:

https://prankbot-cloud-xxxx.onrender.com

Health URL:

https://prankbot-cloud-xxxx.onrender.com/health

Agent WebSocket URL:

wss://prankbot-cloud-xxxx.onrender.com/ws

UPTIMEROBOT
-----------
Создай HTTP(s) Monitor.

URL:
https://prankbot-cloud-xxxx.onrender.com/health

Interval:
5 minutes

Ожидаемый ответ:
HTTP 200

Free UptimeRobot поддерживает 5-minute checks.

ВАЖНО
------
Render Free также считает входящие WebSocket messages активностью.
Agent этой версии шлёт ping раз в 60 секунд, пока соединение активно.

UptimeRobot полезен ещё и как внешний монитор:
если сервис заснул или был перезапущен, HTTP-запрос разбудит его,
а Agent автоматически переподключится.

WINDOWS AGENT
-------------
Перед сборкой установи в agent/agent.py:

SERVER_URL = "wss://твой-render.onrender.com/ws"
PAIRING_KEY = "тот же ключ, что в Render"

После этого используй build_agent.bat.
