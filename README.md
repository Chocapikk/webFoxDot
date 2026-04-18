# WebFoxDot

WebFoxDot is a web-based interface for the FoxDot or Renardo live coding music environment. It allows you to write and send code to a local FoxDot or Renardo program running on your computer.

> [!Note]
> WebFoxDoT IS NOT a full web-based version of FoxDot or Renardo. You still need to have FoxDot or Renardo installed on your computer to use WebFoxDot.

## 👀 How does it look?

![WebFoxDot](./webFoxdot.png)

## 🤔 Why WebFoxDot?
We first made WebTroop to replace the old Troop interface, we did it our way so that it was effective and reliable live. As the work was already done, we decided to make a WebFoxDot interface for the live coding community, something more generic that anyone can use. 

We know that there are already some people using IDEs like Pulsar or Vim with FoxDot, but we wanted to make something more user-friendly, more visual and focus on the live aspect of FoxDot. 

## 🚩 Known issues
- WebFoxDot is not working with Chrome or other Chromium based browser (Vivaldi, Edge, Brave, Opera, ... ), some shortcuts are not recognized
- Not tested yet on Safari or other web browsers
- Some shortcuts may not work because we don't have tested all configurations (Windows, Linux, MacOs, different browser, different key mapping...)
- Beta tested with Renardo

> [!WARNING]
> This version is in test with Renardo, everything may not work as expected. See the Renardo compatibility section for more information.

## ✅ Requirements
- a fully working FoxDot or Renardo installation
- a working SuperCollider installation
- a modern web browser (for now it works only with Firefox)
- the websocket package for Python (install it with `pip install websockets`)

## ✨ Features
- Code editor with Python syntax highlighting
- Responsive interface with resizable panel and console logs
- Customizable font family, code font size and interface font size
- Dozens of code themes and interface themes available
- Console log with color-coded output (errors in red, prompts in green, input in blue)
- Info panel showing BPM, Scale, Root, CPU usage, Timer, beat modulo, active players, and available Loops/Synths/Fx
- Active player list with synth name, duration (color transitions from green to orange to red), and click-to-stop
- Solo players highlighted
- Piano roll based on current scale and root with click-to-insert notes (`Alt-P` or click `Root`)
- Auto-completion with synth/fx descriptions shown in the dropdown
- Line markers for visual annotation (Alt+1/2/3 for Red/Green/Blue, Alt+4 to reset)
- Comment and stop/start a player with `Alt-x`
- WebSocket auto-reconnect on connection loss
- WebSocket origin check to prevent cross-origin code injection
- Unified startup file supporting both FoxDot and Renardo
- Auto-detection of Python executable (python3/python)


## 🐍 Installation with Python

### Clone the repository and go to the directory:
```bash
git clone git@github.com:CrashServer/webFoxDot.git
cd webFoxDot
```

### Rename the config file and edit the foxdot path:
```bash
cp config.py.sample config.py
nano config.py

Change the FOXDOT_PATH to your foxdot path
```

### Copy the content of this startup.py file to your FoxDot startup file:
```text
Your startup file is located in the FoxDot directory:
/FoxDot/lib/Custom/startup.py
```

### Start SuperCollider as usual

### Run Foxdot with a server:
```python
python server.py
```

> [!WARNING]
> You don't need to run FoxDot/Renardo manually, the server will start FoxDot/Renardo for you. 
> Also, make sure you have something like this 3 lines printed in your terminal, if not restart from the beginning:
> ```python
> FoxDot started, pid: 79311
> WebSocket server started on port 1234
> Start FoxDot WebSocket server at ws://localhost:20000
> ```

### Start a http server to serve the web interface:
```python
cd dist
python -m http.server
```

> [!WARNING] 
> Make sure that your running the server in the `dist` directory because it's a compiled version of the web interface. For running in development mode, see the `Installation with Node.js` section.

### Open your browser and go to `http://localhost:8000`

## 📉 Sending the CPU usage to the web interface

If you want to send the Supercollider CPU usage to the web interface, follow these steps and go for a crash server (notice how the interface reacts to server load): 

In the SuperCollider IDE, run the following code:
```supercollider
b = NetAddr.new("localhost", 20000); 

(
r = Routine {
	loop {
		b.sendMsg("/CPU", round(s.peakCPU,0.01));
	1.yield;
	};
}.play();
)

You can stop this routine with: 
r.stop()
```

## 🟩 Installation with Node.js
If you want to run the web interface in development mode, you need to have Node.js installed on your computer.

### Clone the repository and go to the directory:
```bash
git clone git@github.com:CrashServer/webFoxDot.git
cd webFoxDot
```

### Rename the config file and edit the foxdot path:
```bash
cp config.js.sample config.js
nano config.js

Change the FOXDOT_PATH to your foxdot path. Not yet fully compatible with Renardo, you have to change the spawn in `server.js` to the correct command. 
```

### Copy the content of this startup.py file to your FoxDot startup file:
```text
Your startup file is located in the FoxDot directory:
/FoxDot/lib/Custom/startup.py
```

### Start SuperCollider as usual

### Run the FoxDot/Renardo server:
```javascript
node server.js
```

> [!WARNING]
> You don't need to run FoxDot/Renardo manually, the server will start FoxDot/Renardo for you. 
> Also, make sure you have something like this 3 lines printed in your terminal, if not restart from the beginning:
> ```python
> FoxDot started, pid: 79311
> WebSocket server started on port 1234
> Start FoxDot WebSocket server at ws://localhost:20000
> ```

### Start a http server to serve the web interface:
```js
npm install
npm run dev
```

### Open your browser and go to `http://localhost:3000`


## 🦊 Renardo compatibility
In order to make WebFoxDot compatible with Renardo, here are the steps to follow:

Inject the websocket package dependency in the Renardo code:
```bash
pipx inject renardo websockets
```

Copy the content of `startup.py` to your Renardo startup file (the same `startup.py` now supports both FoxDot and Renardo):
```bash
This should be located in the Renardo directory, something like:
~/.local/pipx/venvs/renardo/lib/python3.13/site-packages/renardo_lib/Custom/startup.py
```


## 🚀 Usage
All things that work in FoxDot or Renardo will work in WebFoxDot. 

| Shortcut                    | Action                             |
| --------------------------- | ---------------------------------- |
| `Ctrl-Enter`                | Evaluate line                      |
| `Ctrl-Alt-Enter`            | Evaluate block                     |
| `Ctrl-;`                    | Stop all players                   |
| `Ctrl-Space`                | Auto-completion                    |
| `Alt-X`                     | Comment line and stop player       |
| `Ctrl-Alt-X`                | Comment block and stop players     |
| `Alt-P`                     | Toggle piano roll                  |
| `Alt-S`                     | Solo player                        |
| `Ctrl-Alt-S`                | Unsolo all players                 |
| `Alt-=`                     | Increment value under cursor       |
| `Ctrl-Alt-=`                | Decrement value under cursor       |
| `Alt-1` / `Alt-2` / `Alt-3` | Set Red / Green / Blue line marker |
| `Alt-4`                     | Reset all line markers             |
| `Alt-F`                     | Open search                        |
| `Ctrl-G`                    | Find next                          |
| `Ctrl-S`                    | Save code to file                  |

A full list of shortcuts is available in the config panel.

## 🧹 Linting

**Python** (requires [ruff](https://docs.astral.sh/ruff/)):
```bash
ruff check .
ruff format .
```

**JavaScript** (requires npm dependencies):
```bash
npm install
npx eslint src/js/
```

## 🗺️ Roadmap
- [ ] Add more interface themes
- [x] Add a vim mode
- [x] Clear console button
- [x] Renardo compatibility (unified startup.py)
- [x] Error detection and colored log output
- [x] Auto-detection of python executable
- [x] Synth/Fx descriptions in autocomplete
- [x] Line markers (Alt+1/2/3/4)

## 📝 License

Copyright © 2025-2026 [CrashServer](https://github.com/CrashServer).

This project is MIT licensed.

