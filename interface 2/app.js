let port = null;
let reader = null;
let inputDone = null;
let outputStream = null;

const logEl = document.getElementById('log');
const connStatus = document.getElementById('conn-status');
const lastLetterEl = document.getElementById('last-letter');
const btnStateEl = document.getElementById('btn-state');
const btnPort = document.getElementById('btn-port');
const btnConnect = document.getElementById('btn-connect');
const baudSel = document.getElementById('baud');
const manualInput = document.getElementById('manual-input');
const btnSend = document.getElementById('btn-send');

function appendLog(txt) {
  const ts = new Date().toLocaleTimeString();
  logEl.innerHTML += `<div>[${ts}] ${txt}</div>`;
  logEl.scrollTop = logEl.scrollHeight;
}

btnPort.addEventListener('click', async () => {
  try {
    port = await navigator.serial.requestPort();
    appendLog('Port selected');
  } catch (e) {
    appendLog('Port selection canceled');
  }
});

btnConnect.addEventListener('click', async () => {
  if (!port) {
    appendLog('No port selected');
    return;
  }
  if (btnConnect.textContent === 'Connect') {
    try {
      const baud = Number(baudSel.value || 115200);
      await port.open({ baudRate: baud });
      appendLog('Port opened at ' + baud);
      connStatus.textContent = 'Connected';
      connStatus.style.background = '#113322';
      connStatus.style.color = '#8df0a3';
      btnConnect.textContent = 'Disconnect';

      // setup reader
      const decoder = new TextDecoderStream();
      inputDone = port.readable.pipeTo(decoder.writable);
      reader = decoder.readable.getReader();

      readLoop();

      // setup writer
      outputStream = port.writable;
    } catch (e) {
      appendLog('Open failed: ' + e);
    }
  } else {
    await disconnect();
  }
});

btnSend.addEventListener('click', async () => {
  const t = (manualInput.value || '').toUpperCase().trim();
  if (!/^[A-Z]$/.test(t)) { appendLog('Invalid manual letter'); return; }
  if (!outputStream) { appendLog('Not connected'); return; }
  const writer = outputStream.getWriter();
  await writer.write(t + '\n');
  writer.releaseLock();
  appendLog('Manually sent: ' + t);
});

async function disconnect() {
  if (reader) {
    await reader.cancel();
    await inputDone.catch(() => {});
    reader = null;
    inputDone = null;
  }
  if (port) {
    await port.close();
    port = null;
  }
  outputStream = null;
  connStatus.textContent = 'Disconnected';
  connStatus.style.background = '';
  connStatus.style.color = '#ff6b6b';
  btnConnect.textContent = 'Connect';
  appendLog('Disconnected');
}

async function readLoop() {
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    if (value) {
      const lines = value.split('\n');
      for (let l of lines) {
        l = l.trim();
        if (!l) continue;
        appendLog(l);
        // parse Sent 'X'
        const m = l.match(/Sent\s+'([A-Z])'/);
        if (m) { lastLetterEl.textContent = 'Last sent letter: ' + m[1]; }
        // parse level_at_isr= or level=
        const ml = l.match(/level_at_isr=(\d)/) || l.match(/level=(\d)/);
        if (ml) { btnStateEl.textContent = (ml[1]==='1') ? 'Button state: HIGH (3.3V)' : 'Button state: LOW (GND)'; }
      }
    }
  }
}

// Matrix background for the web UI
(function createMatrixBackground(){
  const canvas = document.createElement('canvas');
  canvas.style.position = 'fixed';
  canvas.style.left = '0';
  canvas.style.top = '0';
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.zIndex = '-1';
  canvas.style.pointerEvents = 'none';
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  let width, height, cols, fontSize=14, drops;
  function resize(){
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    cols = Math.floor(width / fontSize);
    drops = new Array(cols).fill(0).map(()=>Math.floor(Math.random()*height/fontSize));
  }
  window.addEventListener('resize', resize);
  resize();
  const chars = '01';
  function draw(){
    ctx.fillStyle = 'rgba(0,0,0,0.06)';
    ctx.fillRect(0,0,width,height);
    ctx.font = fontSize + 'px monospace';
    for(let i=0;i<cols;i++){
      const text = chars[(i + drops[i]) % chars.length];
      ctx.fillStyle = '#8CFF8C';
      ctx.fillText(text, i*fontSize, drops[i]*fontSize);
      if(Math.random() > 0.975) drops[i]=0; else drops[i]++;
    }
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
})();

appendLog('Web UI ready');
