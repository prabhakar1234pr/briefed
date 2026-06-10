// Bot-page audio-render harness.
// Streams ref_24k.pcm to a page running the bot-page playback logic in REAL
// (headless) Chrome, captures what it actually renders via a ScriptProcessor
// tap, and writes the captured float32 PCM back to disk for analysis.
//
//   node harness.js <ctxRate>      e.g. node harness.js 24000 | 48000
const fs = require('fs');
const http = require('http');
const path = require('path');
const { WebSocketServer } = require('ws');
const puppeteer = require('puppeteer-core');

const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const CTX_RATE = parseInt(process.argv[2] || '24000', 10);
const SRC_RATE = 24000;
const CHUNK_BYTES = SRC_RATE * 2 * 60 / 1000; // 60ms @24k s16 = 2880
const SEND_INTERVAL_MS = 48;                  // backend pace (~0.9x real time)
const REF = fs.readFileSync(path.join(__dirname, 'ref_24k.pcm'));

const PAGE = (rate) => `<!doctype html><html><body><script>
// rate=0 → use the browser's native rate (don't force a context rate).
const FORCE_RATE=${rate}, SRC_RATE=${SRC_RATE}, PREBUFFER=0.30;
let ctx=null,next=0,cap=null,under=0,chunks=0;const captured=[];
function ensure(){ if(ctx)return ctx;
  ctx=FORCE_RATE ? new AudioContext({sampleRate:FORCE_RATE}) : new AudioContext();
  cap=ctx.createScriptProcessor(4096,1,1);
  cap.onaudioprocess=e=>captured.push(Float32Array.from(e.inputBuffer.getChannelData(0)));
  cap.connect(ctx.destination); next=ctx.currentTime+PREBUFFER; window.__rate=ctx.sampleRate; return ctx; }
function play(ab){ const c=ensure(); if(c.state==='suspended')c.resume();
  const i16=new Int16Array(ab); const f=new Float32Array(i16.length);
  for(let k=0;k<i16.length;k++) f[k]=i16[k]/0x8000;
  const b=c.createBuffer(1,f.length,SRC_RATE); b.copyToChannel(f,0);
  const s=c.createBufferSource(); s.buffer=b; s.connect(cap);
  const now=c.currentTime; let at;
  if(next<now){ under++; at=now+PREBUFFER; } else at=next;
  s.start(at); next=at+b.duration; chunks++; }
const ws=new WebSocket('ws://'+location.host+'/audio'); ws.binaryType='arraybuffer';
ws.onmessage=e=>{ if(typeof e.data==='string'){ if(e.data==='END'){
    // wait for the scheduled tail to render, then send capture back
    const tailMs=(next-ctx.currentTime)*1000+400;
    setTimeout(()=>{ let n=captured.reduce((a,x)=>a+x.length,0); const out=new Float32Array(n);
      let o=0; for(const x of captured){out.set(x,o);o+=x.length;}
      const meta=JSON.stringify({rate:window.__rate,under,chunks,samples:n});
      ws.send('META'+meta); ws.send(out.buffer); }, Math.max(500,tailMs)); } }
  else play(e.data); };
</script></body></html>`;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html' });
  res.end(PAGE(CTX_RATE));
});
const wss = new WebSocketServer({ server, path: '/audio' });
let capturedBuf = null, meta = null;

wss.on('connection', async (ws) => {
  ws.on('message', (data, isBinary) => {
    if (!isBinary) {
      const s = data.toString();
      if (s.startsWith('META')) meta = JSON.parse(s.slice(4));
    } else { capturedBuf = data; }
  });
  // stream the reference, paced like the backend
  for (let i = 0; i < REF.length; i += CHUNK_BYTES) {
    ws.send(REF.subarray(i, Math.min(i + CHUNK_BYTES, REF.length)));
    await new Promise(r => setTimeout(r, SEND_INTERVAL_MS));
  }
  ws.send('END');
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
  page.on('console', m => console.log('[page]', m.text()));
  await page.goto(`http://127.0.0.1:${port}/`);
  // wait until capture comes back
  const t0 = Date.now();
  while (!capturedBuf && Date.now() - t0 < 60000) await new Promise(r => setTimeout(r, 200));
  await browser.close(); server.close();
  if (!capturedBuf) { console.error('NO CAPTURE'); process.exit(1); }
  const outName = path.join(__dirname, `captured_${CTX_RATE}.f32`);
  fs.writeFileSync(outName, capturedBuf);
  console.log('META', JSON.stringify(meta));
  console.log('saved', outName, capturedBuf.length, 'bytes');
})().catch(e => { console.error('ERR', e.stack || e.message); process.exit(1); });
