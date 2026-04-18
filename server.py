import asyncio
import json
import os
import shutil
import sys
from subprocess import PIPE, Popen

import websockets

try:
    from config import PROGRAM_CMD, PROGRAM_PATH
except Exception:
    print(
        "Make sure to uncomment the correct PROGRAM_PATH and PROGRAM_CMD in config.py"
    )


def resolve_python():
    """Find the correct python executable (python3 or python)."""
    for name in ("python3", "python"):
        if shutil.which(name):
            return name
    print("No python executable found in PATH")
    sys.exit(1)


HOST = "localhost"
WS_PORT = 1234


_ERROR_PATTERNS = (
    "Traceback",
    "Error",
    "Exception",
    "SyntaxError",
    "NameError",
    "TypeError",
    "ValueError",
    "AttributeError",
    "KeyError",
    "IndexError",
    "ZeroDivisionError",
)


def detect_log_color(message):
    if any(p in message for p in _ERROR_PATTERNS):
        return "error"
    if message.startswith(">>>"):
        return "prompt"
    if message.startswith(">>"):
        return "input"
    return None


async def broadcast_log(message, clients):
    color = detect_log_color(message)
    payload = json.dumps({"type": "foxdot_log", "data": message, "color": color})
    for client in clients:
        await client.send(payload)


async def handle_websocket(websocket, _path, foxdot_process, clients):
    print("New client connected")
    clients.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if data["type"] == "evaluate_code":
                code = data["code"]
                await broadcast_log(code, clients)
                foxdot_process.stdin.write(f"{code}\n\n".encode())
                foxdot_process.stdin.flush()
    finally:
        clients.remove(websocket)
        print("Client disconnected")


async def _read_stream(stream, clients, is_stderr=False):
    buffer = []
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, stream.readline)
        if not line:
            continue

        log_message = line.decode()
        if "^" not in log_message or not log_message.replace("^", "").isspace():
            log_message = log_message.strip()
        print(log_message)

        buffer.append(log_message)
        if (not log_message or log_message.endswith((">>>", "..."))) and buffer:
            await broadcast_log("\n".join(buffer), clients)
            buffer = []


async def read_foxdot_output(foxdot_process, clients):
    await asyncio.gather(
        _read_stream(foxdot_process.stdout, clients),
        _read_stream(foxdot_process.stderr, clients, is_stderr=True),
    )


async def main():
    try:
        foxdot_process = Popen(
            PROGRAM_CMD,
            cwd=PROGRAM_PATH,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        print(f"FoxDot started, pid: {foxdot_process.pid}")
    except Exception as e:
        print(f"Error starting FoxDot: {e}")
        print(
            "Make sure FoxDot or Renardo is correctly installed and the path is set in config.py"
        )
        return

    clients = set()
    _output_task = asyncio.create_task(read_foxdot_output(foxdot_process, clients))

    async with websockets.serve(
        lambda ws, path: handle_websocket(ws, path, foxdot_process, clients),
        HOST,
        WS_PORT,
    ):
        print(f"WebSocket server started on port {WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
