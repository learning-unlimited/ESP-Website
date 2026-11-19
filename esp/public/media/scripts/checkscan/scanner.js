// Digital Check SSX1 (network firmware 25.07, "SecureLink 2.0") client, run in the browser.
// The scanner answers CORS requests from any origin; over HTTPS it uses a self-signed cert, so each
// computer must accept that cert once (open https://192.168.2.1/ and click through the warning).
import * as openpgp from './vendor/openpgp-6.3.2.min.mjs';
import { apiUrl } from './common.js';

export const DEFAULT_HOST = 'https://192.168.2.1';
const DPI = 200;
const MICR_BAND_IN = 0.45;         // MICR characters sit ~0.19-0.31" above the bottom edge; margin for skew
const sleep = ms => new Promise(r => setTimeout(r, ms));

export class SecureLink {
  constructor(host = DEFAULT_HOST) { this.host = host; this.mid = 0; this.sid = null; }

  async cmd(command, extra = {}) {
    const body = { Command: command, MessageId: String(++this.mid), ...extra };
    if (this.sid && !('SessionId' in body)) body.SessionId = this.sid;
    const r = await fetch(this.host + '/securelink', {
      method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify(body) });
    return r.json();
  }

  // Sessionless read-only status (works without Connect on 25.07 firmware).
  async status() {
    const r = await this.cmd('GetParameters', { Params: ['TisState', 'TransportState', 'FeederEmpty', 'JammedDocument', 'CartridgeInstalled'] });
    return r.Params || {};
  }

  // exclusive: the scanner refuses every other session (another tab or computer) until this one disconnects.
  async connect(exclusive = false) {
    const c = await this.cmd('Connect', { Exclusive: exclusive ? 'true' : 'false' });
    if (c.Result === '29' || c.Result === '30') {
      throw new Error('The scanner is in use by another computer (or a scan there was cut off). Stop that scan, or wait a few ' +
                      'minutes for the scanner to drop the old session, then press Start again.');
    }
    if (c.Result !== '0') throw new Error('Connect failed: ' + c.ErrorInformation);
    this.sid = c.SessionId;
    return c;
  }

  async setParams(params) {
    const r = await this.cmd('SetParameters', { Params: params });
    if (r.Result !== '0') throw new Error('SetParameters failed: ' + r.ErrorInformation);
  }

  getDocument(timeoutMs = 5000) {
    return this.cmd('GetDocument', { IncludeImages: 'false', Timeout: String(timeoutMs) });
  }

  async image(side) {
    const r = await fetch(`${this.host}/sl20/${side}_image`);
    if (!r.ok) throw new Error(`image ${side}: HTTP ${r.status}`);
    return new Uint8Array(await r.arrayBuffer());
  }

  // Fire-and-forget StopFlow + Disconnect that survives the page unloading (keepalive requests).
  // Fire-and-forget StopFlow + Disconnect while the page is closing. sendBeacon is the one request the
  // browser reliably delivers during unload (a text/plain body needs no CORS preflight).
  release() {
    if (!this.sid) return;
    for (const Command of ['StopFlow', 'Disconnect']) {
      const body = JSON.stringify({ Command, MessageId: String(++this.mid), SessionId: this.sid });
      let sent = false;
      try { sent = navigator.sendBeacon(this.host + '/securelink', new Blob([body], { type: 'text/plain' })); } catch (e) { /* fall through */ }
      if (!sent) {
        try { fetch(this.host + '/securelink', { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body, keepalive: true }); } catch (e) { /* ignore */ }
      }
    }
    this.sid = null;
  }

  // End a session left behind by a tab that closed or crashed mid-scan (we only know its id).
  async releaseSession(sid) {
    for (const Command of ['StopFlow', 'Disconnect']) {
      try { await this.cmd(Command, { SessionId: sid }); } catch (e) { /* ignore */ }
    }
  }

  async stopFlow() { try { await this.cmd('StopFlow'); } catch (e) { /* ignore */ } }
  async disconnect() { try { await this.cmd('Disconnect'); } catch (e) { /* ignore */ } this.sid = null; }
}

export const SCAN_PARAMS = {
  GrayOrColorImageFormat: 'JPEG', fgsEnabled: 'true', rgsEnabled: 'true',
  fgsResolution: `${DPI}dpi`, rgsResolution: `${DPI}dpi`, fbwEnabled: 'false', rbwEnabled: 'false',
  FeedSource: 'main', FeedType: 'batch', RearEndorserEnabled: 'false',
};

// Continuous batch scanning: feeds until stop() is called. When the feeder runs empty it waits for
// more items instead of ending. Callbacks: onDocument({doc, front, rear}), onState(text), onError(msg).
export class BatchScanner {
  // onSession(sid | null): told when the scanner session opens and closes, so the page can remember it.
  constructor(sl, { onDocument, onState, onError, onSession = () => {} }) {
    Object.assign(this, { sl, onDocument, onState, onError, onSession });
    this.running = false;
  }

  stop() { this.running = false; this.onState('stopping…'); }

  async run() {
    this.running = true;
    this.onState('connecting…');
    try {
      await this.sl.connect(true);
      this.onSession(this.sl.sid);
      await this.sl.setParams(SCAN_PARAMS);
      this.onState('scanning');
      while (this.running) {
        const g = await this.sl.getDocument(5000);
        if (g.Result === '0') {
          const front = await this.sl.image('fgs');
          const rear = await this.sl.image('rgs');
          this.onDocument({ doc: g, front, rear });
          continue;
        }
        await this.sl.stopFlow();
        const st = await this.sl.status();
        if (st.JammedDocument === 'true' || !(st.FeederEmpty === 'true' || /empty|time ?out/i.test(g.ErrorInformation || ''))) {
          this.onError(`Scanner stopped: ${g.ErrorInformation || 'error ' + g.Result}. Clear the track and press Start again.`);
          break;
        }
        this.onState('feeder empty — add checks to continue');
        while (this.running) {
          await sleep(1500);
          const s = await this.sl.status();
          if (s.FeederEmpty === 'false') { this.onState('scanning'); break; }
        }
      }
    } catch (e) {
      this.onError(e instanceof TypeError ? 'Lost contact with the scanner: ' + e.message : e.message);
    } finally {
      if (this.sl.sid) { await this.sl.stopFlow(); await this.sl.disconnect(); }
      this.onSession(null);
      this.running = false;
      this.onState('stopped');
    }
  }
}

// ---------------------------------------------------------------- MICR / check number

// Business checks carry the serial in the auxiliary on-us field (Fld7, zero padded); personal
// checks after the on-us symbol (Fld2). '*' marks a character the reader couldn't decode.
export function checkNumberFromMicr(m = {}) {
  const raw = m.RawMicr || '';
  const f7 = (m.Fld7 || '').replace(/^0+/, '');
  const f2 = m.Fld2 || '';
  let n = /^\d+$/.test(f7) ? f7 : /^\d+$/.test(f2) ? f2.replace(/^0+/, '') : '';
  return { checkNumber: n, complete: raw.trim() !== '' && !raw.includes('*') && n !== '' };
}

// ---------------------------------------------------------------- redact / encrypt / upload

export async function redactFront(jpegBytes) {
  const bmp = await createImageBitmap(new Blob([jpegBytes], { type: 'image/jpeg' }));
  const c = document.createElement('canvas');
  c.width = bmp.width; c.height = bmp.height;
  const ctx = c.getContext('2d');
  ctx.drawImage(bmp, 0, 0);
  const band = Math.round(MICR_BAND_IN * DPI);
  ctx.fillStyle = '#000';
  ctx.fillRect(0, c.height - band, c.width, band);
  return new Promise(res => c.toBlob(res, 'image/jpeg', 0.85));
}

let keyPromise = null;
export function treasurerKey() {
  keyPromise ??= (async () => {
    const r = await fetch(apiUrl('key'), { credentials: 'same-origin' });
    if (!r.ok) {   // the server answers with {"error": ...} (e.g. no key installed); show that, not a parse error
      let msg = `couldn't load the treasurer's public key (HTTP ${r.status})`;
      try { msg = (await r.json()).error || msg; } catch (e) { /* not JSON */ }
      throw new Error(msg);
    }
    return openpgp.readKey({ armoredKey: await r.text() });
  })();
  keyPromise.catch(() => { keyPromise = null; });   // don't remember a failure: retry once the key is installed
  return keyPromise;
}

export async function encrypt(bytes) {
  const key = await treasurerKey();
  const message = await openpgp.createMessage({ binary: bytes });
  return openpgp.encrypt({ message, encryptionKeys: key, format: 'binary' });
}

// Turn one scanned document into the upload form: everything sensitive is encrypted here, in the
// browser; the server only ever receives ciphertext + the redacted front.
export async function prepareUpload({ doc, front, rear }) {
  const { checkNumber, complete } = checkNumberFromMicr(doc.MicrFields);
  const micrJson = new TextEncoder().encode(JSON.stringify({
    MicrFields: doc.MicrFields, SequenceNumber: doc.SequenceNumber, Scanner: doc.Scanner,
    ScannedAt: new Date().toISOString() }));
  const [frontEnc, rearEnc, micrEnc, redacted] = await Promise.all([
    encrypt(front), encrypt(rear), encrypt(micrJson), redactFront(front)]);
  const f = new FormData();
  f.append('scanner_seq', doc.SequenceNumber || '');
  f.append('check_number', checkNumber);
  f.append('micr_complete', complete ? '1' : '0');
  f.append('front.jpg.gpg', new Blob([frontEnc]), 'front.jpg.gpg');
  f.append('rear.jpg.gpg', new Blob([rearEnc]), 'rear.jpg.gpg');
  f.append('micr.json.gpg', new Blob([micrEnc]), 'micr.json.gpg');
  f.append('front-redacted.jpg', redacted, 'front-redacted.jpg');
  f.append('rear.jpg', new Blob([rear], { type: 'image/jpeg' }), 'rear.jpg');   // kept unencrypted for review
  return f;
}
