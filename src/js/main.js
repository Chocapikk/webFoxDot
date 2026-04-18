import CodeMirror from 'codemirror';
import { setupConfigPanel, updateHelpPanel } from './configPanel.js';
import { EventEmitter } from './eventBus.js';

import 'codemirror/addon/dialog/dialog.js'
import 'codemirror/keymap/sublime'
import 'codemirror/keymap/vim'
import 'codemirror/addon/edit/matchbrackets'
import 'codemirror/addon/edit/closebrackets'
import 'codemirror/addon/comment/comment'
import 'codemirror/addon/hint/show-hint'
import 'codemirror/addon/selection/active-line.js'
import 'codemirror/addon/scroll/annotatescrollbar.js'
import 'codemirror/addon/search/searchcursor.js'
import 'codemirror/addon/search/search.js'
import 'codemirror/addon/search/jump-to-line.js'
import 'codemirror/addon/search/matchesonscrollbar.js'
import 'codemirror/mode/python/python.js'

import { logsUtils } from './logs.js';
import { functionUtils } from './functionUtils.js';
import { foxdotAutocomplete } from './foxdotAutocomplete.js';

import 'codemirror/lib/codemirror.css'
import 'codemirror/addon/hint/show-hint.css'
import 'codemirror/addon/dialog/dialog.css'
import '../css/style.css'
import '../css/configPanel.css'
import '../css/panel.css'

document.addEventListener('DOMContentLoaded', async () => {
	// DOM elements
	const chrono = document.getElementById('timer');

	// WebSocket with auto-reconnect
	let wsServer = null;

	function connectWsServer() {
		wsServer = new WebSocket(`ws://localhost:1234`);
		wsServer.onopen = () => console.log('Backend WebSocket connected');
		wsServer.onclose = () => {
			console.log('Backend WebSocket closed, reconnecting in 3s...');
			setTimeout(connectWsServer, 3000);
		};
		wsServer.onerror = () => wsServer.close();
		wsServer.onmessage = (event) => {
			try {
				const message = JSON.parse(event.data);
				if (message.type === 'foxdot_log') {
					logsUtils.appendLog(message.data, message.color);
				}
			} catch (error) {
				console.error('Error parsing WebSocket message:', error);
			}
		};
	}
	connectWsServer();

	// CodeMirror
	const editor = CodeMirror(document.getElementById('editor'), {
		mode: {	name: 'python',
				extra_builtins: ['PRand', 'PWhite', 'PxRand', 'PwRand', 'PChain', 'PZ12', 'PTree', 'PWalk', 'PDelta', 'PSquare', 'PIndex', 'PFibMod', 'PShuf', 'PAlt', 'PStretch', 'PPairs', 'PZip', 'PZip2', 'PStutter', 'PSq', 'P10', 'PStep', 'PSum', 'PRange', 'PTri', 'PSine', 'PEuclid', 'PEuclid2', 'PBern', 'PBeat', 'PDur', 'PDelay', 'PStrum', 'PQuicken', 'PRhythm', 'PJoin', 'linvar', 'var', 'expvar', 'sinvar', 'Pvar' ],
				extra_keywords: ["Clock", "Scale", "Root", "Server", "Group", "Samples", "now", "inf"],
		},
		theme: 'material',
		lineNumbers: true,
		autofocus: true,
		matchBrackets: true,
		autoCloseBrackets: {pairs: "()[]{}<>''\"\"", override: true},
		lineWrapping: true,
		singleCursorHeightPerLine: false,
		styleActiveLine: true,
		keyMap: 'sublime',
	});
    
	// Restore the code if it was stored
	const savedCode = localStorage.getItem('webFoxDotEditorContent');
    if (savedCode) {
        editor.setValue(savedCode);
    }
	// Store the code on change
	editor.on('change', () => {
        localStorage.setItem('webFoxDotEditorContent', editor.getValue());
    });

	setupConfigPanel(editor);

	// Init the logs panel
	logsUtils.initResize(editor);
	document.getElementById('clearLogsBtn').addEventListener('click', () => logsUtils.clear());

	// Line markers for visual annotation
	const activeMarkers = [];

	function setMarker(cm, color) {
		const cursor = cm.getCursor();
		const line = cursor.line;
		const className = `line${color}`;
		const existing = activeMarkers.findIndex(m => m.line === line);
		if (existing !== -1) {
			activeMarkers[existing].handle.clear();
			activeMarkers.splice(existing, 1);
		}
		const handle = cm.addLineClass(line, 'background', className);
		activeMarkers.push({ line, handle, color: className });
	}

	function resetMarkers(cm) {
		activeMarkers.forEach(m => cm.removeLineClass(m.handle, 'background', m.color));
		activeMarkers.length = 0;
	}

	function sendToServer(code) {
		if (wsServer && wsServer.readyState === WebSocket.OPEN) {
			wsServer.send(JSON.stringify({ type: 'evaluate_code', code }));
		}
	}

	EventEmitter.on('send_foxdot', sendToServer);

	// Reset timer on click
	chrono.addEventListener('click', () => sendToServer('ws_panel.time_init = time()'));

	// Evaluate the code and highlight the block with a flash
	function evaluateCode(cm, multi){
		const [blockCode, startLine, endLine] = functionUtils.getCodeAndCheckStop(cm, multi);
		sendToServer(blockCode);
		
		// Highlight the code
		for (let i = startLine; i <= endLine; i++) {
			const mark = editor.markText(
				{line: i, ch: 0},
				{line: i, ch: editor.getLine(i).length},
				{className: 'flash-highlight'}
			);
			setTimeout(() => mark.clear(), 200);
		}
	}

	editor.setOption('extraKeys', {
		'Ctrl-;': () => sendToServer('Clock.clear()'),
		'Ctrl-Space': 'autocomplete',
		'Ctrl-S': (cm) => functionUtils.saveEditorContent(cm),
		'Alt-X': (cm) => {
		  cm.toggleComment();
		  evaluateCode(cm, false);
		},
		'Ctrl-Alt-X': (cm) => {
		  const {startLine, endLine} = functionUtils.getBlock(cm, cm.getCursor().line);
		  cm.setSelection({line: startLine, ch: 0}, {line: endLine, ch: cm.getLine(endLine).length});
		  cm.toggleComment();
		  evaluateCode(cm, true);
		},
		'Alt-S': (cm) => {
			const player = functionUtils.getPlayer(cm.getRange(
				{line: cm.getCursor().line, ch: 0},
				{line: cm.getCursor().line, ch: cm.getLine(cm.getCursor().line).length}
			));
			if (player) sendToServer(`${player}.solo()`);
		},
		'Ctrl-Alt-S': () => sendToServer('unsolo()'),
		'Alt-1': (cm) => setMarker(cm, "Red"),
		'Alt-2': (cm) => setMarker(cm, "Green"),
		'Alt-3': (cm) => setMarker(cm, "Blue"),
		'Alt-4': (cm) => resetMarkers(cm),
		'Ctrl-Enter': (cm) => {evaluateCode(cm, false)},
		'Ctrl-Alt-Enter': (cm) => {evaluateCode(cm, true)},
		'Alt-F': "findPersistent",
		'Ctrl-G': "findNext",
		'Ctrl-Alt-Left': "goLineStart",
		'Ctrl-Alt-Right': "goLineEnd",
		'Ctrl-Left': (cm) => {functionUtils.goToPreviousComma(cm)},
		'Ctrl-Right': (cm) => {functionUtils.goToNextComma(cm)},
		'Alt-P': () => {document.getElementById('piano-roll').classList.toggle('hidden')},
		'Alt-=': (cm) => {functionUtils.incrementValue(cm, 1)},
		'Ctrl-Alt-=': (cm) => {functionUtils.incrementValue(cm, -1)},
	  });

	// autocomplete
	editor.setOption('hintOptions', {
		hint: (cm) => foxdotAutocomplete.hint(cm, CodeMirror),
	  });

	function connectFoxDotWs(){
		const foxdotWs = new WebSocket(`ws://localhost:20000`);
		foxdotWs.onopen = () => {
			foxdotWs.send(JSON.stringify({ type: 'get_autocomplete' }));
		};
		foxdotWs.onmessage = (event) => {
			try {
			const message = JSON.parse(event.data);
			if (message.type === 'autocomplete') {
				const { loops, fxList, synthList } = functionUtils.formatFoxDotAutocomplete(message);
				foxdotAutocomplete.loopList = loops;
				foxdotAutocomplete.fxList = fxList;
				foxdotAutocomplete.synths = synthList;

				updateHelpPanel(loops, fxList, synthList);

				if (loops.length === 0 || fxList.length === 0 || synthList.length === 0) {
				console.error(`Error on retrieving loops name (${loops.length}), effets (${fxList.length}), synths (${synthList.length})`);
				}
			}
			} catch (error) {
			console.error('Error on FoxDot message ', error);
			}
		};
		foxdotWs.onclose = () => {
			console.log('FoxDot WebSocket closed, reconnecting in 3s...');
			setTimeout(connectFoxDotWs, 3000);
		};
		foxdotWs.onerror = () => foxdotWs.close();
	}
	
	connectFoxDotWs();

	// piano insert at cursor
	document.querySelectorAll('#piano-roll .piano-key li').forEach(key => {
		key.addEventListener('click', (event) => {
			const index = event.currentTarget.dataset.index;
			if (index !== undefined) {
				insertAtCursor(index);
			}
		});
	  });
	
	  function insertAtCursor(index) {
		  // insert index text at cursor position
		  const cursor = editor.getCursor();
		  const line = cursor.line;
		  const ch = cursor.ch;
		  editor.replaceRange(index+',', {line, ch}, {line, ch});
	  }
})

