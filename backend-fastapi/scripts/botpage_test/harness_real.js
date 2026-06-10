// Verify the REAL bot-page/index.html: serve it, mock the /ws/bot-bridge WS
// streaming ref_24k.pcm, tap the actual <audio> MediaStream (what Recall
// captures), and write the captured float32 back for analysis.
const fs = require('fs');
const http = require('http');
const path = require('path');
const { WebSocketServer } = require('ws');
const puppeteer = require('puppeteer-core');

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const SRC_RATE = 24000;
const CHUNK_BYTES = SRC_RATE * 2 * 60 / 1000;
const SEND_INTERVAL_MS = 48;
const BOTPAGE = fs.readFileSync(path.join(__dirname, '..', '..', '..', 'bot-page', 'index.html'), 'utf8');
const REF = fs.readFileSync(path.join(__dirname, 'ref_24k.pcm'));

const TAP = `
window.__cap=[]; window.__caprate=0;
const iv=setInterval(()=>{ const el=document.getElementById('output');
  if(el && el.srcObject && el.srcObject.getAudioTracks().length){ clearInterval(iv);
    const cc=new AudioContext(); const sn=cc.createMediaStreamSource(el.srcObject);
    const tap=cc.createScriptProcessor(4096,1,1);
    tap.onaudioprocess=e=>window.__cap.push(Float32Array.from(e.inputBuffer.getChannelData(0)));
    sn.connect(tap); tap.connect(cc.destination); window.__caprate=cc.sampleRate; }
},30);`;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end(BOTPAGE);
});
const wss = new WebSocketServer({ server });  // accept any path (/ws/bot-bridge/..)
wss.on('connection', async (ws) => {
  for (let i = 0; i < REF.length; i += CHUNK_BYTES) {
    if (ws.readyState !== ws.OPEN) break;
    ws.send(REF.subarray(i, Math.min(i + CHUNK_BYTES, REF.length)));
    await new Promise(r => setTimeout(r, SEND_INTERVAL_MS));
  }
});

(async () => {
  await new Promise(r => server.listen(0, r));
  const port = server.address().port;
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--autoplay-policy=no-user-gesture-required', '--no-sandbox',
           '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  });
  const page = await browser.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  await page.evaluateOnNewDocument(TAP);
  const params = `meeting_id=test&agent_name=Bora&backend_ws=ws://127.0.0.1:${port}&token=x`;
  await page.goto(`http://127.0.0.1:${port}/?${params}`);
  await new Promise(r => setTimeout(r, (REF.length / CHUNK_BYTES) * SEND_INTERVAL_MS + 2500));
  const out = await page.evaluate(() => {
    const n = window.__cap.reduce((a, x) => a + x.length, 0);
    const a = new Float32Array(n); let o = 0; for (const x of window.__cap) { a.set(x, o); o += x.length; }
    let bin = ''; const u8 = new Uint8Array(a.buffer);
    for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
    return { rate: window.__caprate, b64: btoa(bin) };
  });
  await browser.close(); server.close();
  console.log('pageerrors:', errs.length ? errs : 'none');
  console.log('capture rate:', out.rate);
  fs.writeFileSync(path.join(__dirname, 'captured_real.f32'), Buffer.from(out.b64, 'base64'));
  console.log('saved captured_real.f32');
})().catch(e => { console.error('ERR', e.stack || e.message); process.exit(1); });
