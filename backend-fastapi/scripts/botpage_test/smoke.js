const puppeteer = require('puppeteer-core');
const CHROME = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--autoplay-policy=no-user-gesture-required', '--no-sandbox',
           '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  });
  const page = await browser.newPage();
  await page.goto('about:blank');
  const r = await page.evaluate(async () => {
    const out = {};
    const c24 = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    out.requested24000_got = c24.sampleRate;
    out.c24_state = c24.state;
    const md = c24.createMediaStreamDestination();
    out.mediaStream_trackRate = (md.stream.getAudioTracks()[0].getSettings() || {}).sampleRate || 'n/a';
    const cdef = new (window.AudioContext || window.webkitAudioContext)();
    out.default_rate = cdef.sampleRate;
    return out;
  });
  console.log(JSON.stringify(r, null, 2));
  await browser.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
