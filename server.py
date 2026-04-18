import asyncio
import json
import os
from subprocess import PIPE, Popen

import websockets

try:
    from config import PROGRAM_CMD, PROGRAM_PATH
except Exception:
    print(
        "Make sure to uncomment the correct PROGRAM_PATH and PROGRAM_CMD in config.py"
    )

HOST = "localhost"
WS_PORT = 1234


async def broadcast_log(message, clients):
    payload = json.dumps({"type": "foxdot_log", "data": message, "color": None})
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


async def read_foxdot_output(foxdot_process, clients):
    buffer = []
    while True:
        line = await asyncio.get_event_loop().run_in_executor(
            None, foxdot_process.stdout.readline
        )
        if not line:
            continue

        log_message = line.decode()
        if "^" not in log_message or not log_message.replace("^", "").isspace():
            log_message = line.decode().strip()
        print(log_message)

        buffer.append(log_message)
        if (not log_message or log_message.endswith((">>>", "..."))) and buffer:
            await broadcast_log("\n".join(buffer), clients)
            buffer = []


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
