import asyncio
import json
import os
import re
import threading
from time import sleep, time

import websockets

from synth_definitions import FX_DESCRIPTIONS, SYNTH_DESCRIPTIONS

loops = Samples.loops

# Renardo compatibility: FxList is named differently
try:
    FxList = effect_manager
except Exception:
    pass

# Resolve synth definition directory for both FoxDot and Renardo
try:
    _SYNTH_DIR = SYNTHDEF_DIR
except Exception:
    _SYNTH_DIR = os.path.join(FOXDOT_ROOT, "osc", "scsyndef")

_SYNTH_ARGS_IGNORE = {
    "amp",
    "sus",
    "gate",
    "pan",
    "freq",
    "mul",
    "bus",
    "atk",
    "decay",
    "rel",
    "level",
    "peak",
    "blur",
    "beat_dur",
    "buf",
    "vib",
    "fmod",
}


class WebFoxDotPanelWs:
    def __init__(self, ip="localhost", port=20000):
        self.is_running = False
        self.ip = ip
        self.port = port
        self.ws_clients = set()
        self.player_counter = {}
        self.time_init = time()

        self.bpm_time = 0.2
        self.beat_time = 0.1
        self.player_time = 1.0
        self.chrono_time = 1.0

        self._start_osc_server()
        self._start_websocket()
        self._start_bpm_sender()

        self._periodic_threads = [
            threading.Thread(
                target=self._send_loop,
                args=("scale", self._get_scale, self.bpm_time * 10),
                daemon=True,
            ),
            threading.Thread(
                target=self._send_loop,
                args=("root", self._get_root, self.bpm_time * 10),
                daemon=True,
            ),
            threading.Thread(
                target=self._send_loop,
                args=("beat", self._get_beat, self.beat_time),
                daemon=True,
            ),
            threading.Thread(target=self._send_player, daemon=True),
            threading.Thread(
                target=self._send_loop,
                args=("chrono", self._get_chrono, self.chrono_time),
                daemon=True,
            ),
        ]

        self.start()

    def _start_osc_server(self):
        self._osc_server = ThreadingOSCServer((self.ip, 2887))
        self._osc_server.addDefaultHandlers()
        self._osc_server.addMsgHandler("/CPU", self._receive_cpu)
        threading.Thread(target=self._osc_server.serve_forever, daemon=True).start()

    def _start_websocket(self):
        self._ws_event = threading.Event()
        threading.Thread(target=self._run_ws_server, daemon=True).start()
        self._ws_event.wait()

    def _start_bpm_sender(self):
        threading.Thread(target=self._send_bpm_periodically, daemon=True).start()

    def _receive_cpu(self, _address, _tags, contents, _source):
        cpu = round(float(contents[0]), 2)
        if cpu:
            asyncio.run(self._send_ws(json.dumps({"type": "cpu", "cpu": cpu})))

    async def _handle_ws_client(self, websocket):
        self.ws_clients.add(websocket)
        try:
            async for message in websocket:
                await asyncio.gather(*[c.send(message) for c in self.ws_clients])
                data = json.loads(message)
                if data["type"] == "get_autocomplete":
                    await self._send_autocomplete()
        except websockets.ConnectionClosed:
            pass
        finally:
            self.ws_clients.remove(websocket)

    async def _ws_main(self):
        async with websockets.serve(self._handle_ws_client, self.ip, self.port):
            self._ws_event.set()
            await asyncio.get_running_loop().create_future()

    def _run_ws_server(self):
        print(f"Start FoxDot WebSocket server at ws://{self.ip}:{self.port}")
        asyncio.run(self._ws_main())

    async def _send_ws(self, msg=""):
        try:
            uri = f"ws://{self.ip}:{self.port}"
            async with websockets.connect(uri) as ws:
                await ws.send(msg)
        except Exception as e:
            print(f"Error sending websocket message: {e}")

    def _send_bpm_periodically(self):
        while True:
            bpm = int(Clock.get_bpm())
            asyncio.run(self._send_ws(json.dumps({"type": "bpm", "bpm": bpm})))
            sleep(60 / bpm)

    # --- Data getters for periodic sends ---

    def _get_scale(self):
        return {"type": "scale", "scale": str(Scale.default.name)}

    def _get_root(self):
        return {"type": "root", "root": str(Root.default)}

    def _get_beat(self):
        return {"type": "beat", "beat": Clock.beat}

    def _get_chrono(self):
        return {"type": "chrono", "chrono": time() - self.time_init}

    def _send_loop(self, name, getter, interval):
        try:
            while self.is_running:
                asyncio.run(self._send_ws(json.dumps(getter())))
                sleep(interval)
        except Exception:
            pass

    def _send_player(self):
        try:
            while self.is_running:
                self._update_player_counter()
                solo_players = [p.name for p in Clock.solo.data]
                player_list = [
                    json.dumps(
                        {
                            "player": k.name,
                            "name": k.filename
                            if k.synthdef in ("loop", "stretch")
                            else k.synthdef,
                            "duration": f"{divmod(v, 60)[0]:02d}:{divmod(v, 60)[1]:02d}",
                            "solo": k.name in solo_players,
                        }
                    )
                    for k, v in self.player_counter.items()
                ]
                asyncio.run(
                    self._send_ws(
                        json.dumps({"type": "players", "players": player_list})
                    )
                )
                sleep(self.player_time)
        except Exception:
            pass

    def _update_player_counter(self):
        try:
            playing = Clock.playing
            for p in playing:
                self.player_counter[p] = self.player_counter.get(p, 0) + 1
            for k in [k for k in self.player_counter if k not in playing]:
                del self.player_counter[k]
        except Exception as err:
            print(f"_update_player_counter error: {err}")

    # --- Autocomplete ---

    async def _send_autocomplete(self):
        fx_list = await self._get_fx_list()
        synth_list = await self._get_synth_list()
        msg = json.dumps(
            {
                "type": "autocomplete",
                "autocomplete": {
                    "loopList": loops,
                    "fxList": fx_list,
                    "synthList": synth_list,
                },
            }
        )
        await self._send_ws(msg)

    async def _get_fx_list(self):
        result = []
        for fx_name in FxList.keys():
            defaults = FxList[fx_name].defaults
            filtered = {
                k: v
                for k, v in defaults.items()
                if not (k.endswith("_") or k.endswith("_d") or k == "sus")
            }
            result.append(
                {
                    "text": ", ".join(f"{k}={v}" for k, v in filtered.items()),
                    "displayText": fx_name + "_",
                    "description": FX_DESCRIPTIONS.get(fx_name, ""),
                }
            )
        return result

    async def _get_synth_list(self):
        result = []
        for syn in sorted(SynthDefs):
            if not syn:
                continue
            path = os.path.join(_SYNTH_DIR, syn + ".scd")
            with open(path) as f:
                content = "".join(line.strip() for line in f if line.strip())
            names = re.findall(r"SynthDef(?:\.new)?\(\\(\w+)", content)
            args = re.findall(r"{\|(.{3,})\|(?:var)", content)
            if names and args:
                filtered = ", ".join(
                    a.strip()
                    for a in args[0].split(", ")
                    if a.split("=")[0].strip() not in _SYNTH_ARGS_IGNORE
                )
                result.append(
                    {
                        "text": filtered,
                        "displayText": names[0],
                        "description": SYNTH_DESCRIPTIONS.get(names[0], ""),
                    }
                )
        return result

    # --- Control ---

    def send_once(self, txt, help_type=""):
        asyncio.run(
            self._send_ws(
                json.dumps({"type": "help", "helpType": help_type, "help": txt})
            )
        )

    def stop(self):
        self.is_running = False

    def start(self):
        self.is_running = True
        for t in self._periodic_threads:
            t.start()


try:
    ws_panel = WebFoxDotPanelWs()
except Exception as e:
    print(f"Error starting FoxDot WebSocket server: {e}")


def unsolo():
    for p in Clock.playing:
        p.solo(0)
