const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() {
    this.dataset = {};
    this.classList = { toggle() {} };
    this.children = [];
    this.lastChild = { textContent: '' };
    this.disabled = false;
    this.hidden = false;
    this.value = '';
  }

  addEventListener() {}
  append(...children) { this.children.push(...children); }
  connect() {}
  disconnect() {}
  focus() {}
  remove() {}
  replaceChildren(...children) { this.children = children; }
  setAttribute() {}
  querySelector() { return null; }
}

class FakeAudioContext {
  constructor() {
    this.sampleRate = 16000;
    this.state = 'running';
  }

  async resume() {}
  async close() { this.state = 'closed'; }
  createMediaStreamSource() { return new Element(); }
  createGain() { const gain = new Element(); gain.gain = {}; return gain; }
  createScriptProcessor() { return new Element(); }
}

class FakeWebSocket {
  static OPEN = 1;
  static CLOSING = 2;
  static instances = [];

  constructor(url) {
    this.url = url;
    this.sent = [];
    this.readyState = 0;
    this.listeners = {};
    FakeWebSocket.instances.push(this);
    setTimeout(() => {
      this.readyState = 1;
      this.listeners.open?.();
    }, 0);
  }

  addEventListener(type, callback) {
    this.listeners[type] = callback;
  }

  send(payload) {
    this.sent.push(payload);
  }

  close(code = 1000) {
    if (code !== 1000 && (code < 3000 || code > 4999)) {
      throw new Error('Invalid WebSocket close code');
    }
    this.closeCode = code;
    this.readyState = 3;
    this.onclose?.();
  }
}

const elements = new Map();
const document = {
  querySelector(selector) {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  },
  createElement() { return new Element(); },
};

const fetchState = { calls: [], response: { ok: true, body: {} } };

async function fetchStub(url, options = {}) {
  fetchState.calls.push({
    url,
    method: options.method || 'GET',
    body: options.body,
  });
  const configured = fetchState.response;
  return {
    ok: configured.ok !== false,
    status: configured.status || 200,
    json: async () => configured.body,
  };
}

const fakeTimers = { intervals: [] };
const localValues = new Map();

function fakeSetInterval(callback, delay) {
  const handle = { callback, delay, cleared: false };
  fakeTimers.intervals.push(handle);
  return handle;
}

function fakeClearInterval(handle) {
  if (handle && typeof handle === 'object') handle.cleared = true;
}

const context = vm.createContext({
  assert,
  document,
  window: { WebSocket: FakeWebSocket, isSecureContext: true },
  WebSocket: FakeWebSocket,
  FakeWebSocket,
  AudioContext: FakeAudioContext,
  fetch: fetchStub,
  fetchState,
  navigator: {
    mediaDevices: {
      async getUserMedia() {
        const track = { readyState: 'live', addEventListener() {}, stop() {} };
        return { getTracks: () => [track], getAudioTracks: () => [track] };
      },
    },
  },
  localStorage: {
    getItem: (key) => localValues.get(key) || '',
    setItem: (key, value) => localValues.set(key, value),
  },
  requestAnimationFrame: (callback) => callback(),
  setTimeout,
  clearTimeout,
  setInterval: fakeSetInterval,
  clearInterval: fakeClearInterval,
  fakeTimers,
  console,
  URL,
  URLSearchParams,
  Math,
  Date,
});

const source = fs.readFileSync('src/frontend/index.js', 'utf8');
const test = new vm.Script(`${source}
  ;(async () => {
    await startVoice();
    const firstSocket = voiceSocket;
    assert.equal(voiceActive, true);

    handleVoiceMessage({ data: JSON.stringify({
      type: 'error',
      code: 'stt_connection_closed',
      recoverable: true,
      message: 'Speech recognition disconnected. Start voice again to continue.',
    }) });

    assert.equal(firstSocket.readyState, 3);
    assert.equal(firstSocket.closeCode, 1000);
    assert.equal(voiceActive, false);
    assert.equal(startVoiceButton.disabled, false);
    assert.equal(voiceBar.dataset.state, 'error');
    assert.match(voiceStatus.textContent, /Start voice again to continue/);

    await startVoice();
    assert.equal(FakeWebSocket.instances.length, 2);
    assert.equal(voiceActive, true);

    handleVoiceMessage({ data: JSON.stringify({ type: 'stt_ready' }) });
    assert.equal(voiceStatus.textContent, 'Listening…');

    handleVoiceMessage({ data: JSON.stringify({
      type: 'error',
      code: 'stt_quota_exceeded',
      recoverable: true,
      message: 'Speech recognition quota reached. Please check the API plan.',
    }) });

    assert.equal(voiceActive, false);
    assert.equal(startVoiceButton.disabled, false);
    assert.match(voiceStatus.textContent, /quota reached/i);

    await startVoice();
    assert.equal(FakeWebSocket.instances.length, 3);
    assert.equal(voiceActive, true);

    voiceSocket.close();
    assert.equal(voiceActive, false);
    assert.equal(startVoiceButton.disabled, false);
    assert.match(voiceStatus.textContent, /Restart voice/i);

    await startVoice();
    assert.equal(FakeWebSocket.instances.length, 4);
    assert.equal(voiceActive, true);
    console.log('Frontend STT readiness, quota message, disconnect, and retry path verified.');
    voiceSocket.close();
    for (const handle of fakeTimers.intervals) handle.cleared = true;

    // --- Seller binding, keepalive frames, and soft empty-transcript hint ---

    function firePendingIntervals() {
      for (const handle of fakeTimers.intervals) {
        if (!handle.cleared) handle.callback();
      }
    }

    // The loaded seller ID travels with the voice WebSocket URL so the
    // backend can bind the session to that seller from the first turn.
    sellerId = 'SD-48213';
    await startVoice();
    assert.equal(FakeWebSocket.instances.length, 5);
    assert.ok(FakeWebSocket.instances[4].url.includes('/voice/'));
    assert.ok(FakeWebSocket.instances[4].url.includes('seller_id=SD-48213'));
    assert.ok(FakeWebSocket.instances[4].url.includes('client_id='));
    const keepaliveSocket = voiceSocket;
    assert.equal(keepaliveSocket.readyState, FakeWebSocket.OPEN);
    const keepaliveHandles = fakeTimers.intervals.filter((handle) => !handle.cleared);
    assert.ok(keepaliveHandles.length >= 1);
    assert.equal(keepaliveHandles[keepaliveHandles.length - 1].delay, 20000);

    // While an assistant turn pauses the mic, the interval sends data frames
    // so hosted proxies keep the connection open.
    keepaliveSocket.sent.length = 0;
    handleVoiceMessage({ data: JSON.stringify({
      type: 'assistant_start',
      transcript: 'namaste',
      request_id: 'keepalive-turn-1',
    }) });
    assert.equal(voicePaused, true);
    firePendingIntervals();
    assert.equal(keepaliveSocket.sent.length, 1);
    assert.equal(keepaliveSocket.sent[0], JSON.stringify({ type: 'keepalive' }));

    // While the mic is live, the interval stays quiet: mic audio already flows.
    keepaliveSocket.sent.length = 0;
    handleVoiceMessage({ data: JSON.stringify({ type: 'stt_ready' }) });
    assert.equal(voicePaused, false);
    firePendingIntervals();
    assert.equal(keepaliveSocket.sent.length, 0);

    // An untranscribed utterance is a gentle voice-bar hint in listening
    // state, never a red error bubble in the conversation transcript.
    const chatChildrenBefore = conversation.children.length;
    handleVoiceMessage({ data: JSON.stringify({
      type: 'error',
      code: 'empty_transcript',
      recoverable: true,
      message: 'I could not understand that. Please try again.',
    }) });
    assert.equal(voiceBar.dataset.state, 'listening');
    assert.ok(voiceStatus.textContent.includes('understand'));
    assert.equal(conversation.children.length, chatChildrenBefore);
    assert.equal(voicePaused, false);

    // Closing the call clears the keepalive interval.
    voiceSocket.close();
    assert.equal(fakeTimers.intervals.every((handle) => handle.cleared), true);
    sellerId = '';
    console.log('Voice seller binding, paused-mic keepalive, and soft empty-transcript hint verified.');

    // --- Settings: custom Sarvam key UI behaviour ---
    const settingsInput = document.querySelector('#sarvam-key-input');
    const settingsStatus = document.querySelector('#sarvam-key-status');
    const settingsClearButton = document.querySelector('#settings-clear');

    // A configured custom key shows only a masked status and enables Clear.
    fetchState.calls.length = 0;
    fetchState.response = { ok: true, body: { configured: true, source: 'custom', masked: '********' } };
    await loadSarvamKeyStatus();
    assert.equal(fetchState.calls.length, 1);
    assert.equal(fetchState.calls[0].method, 'GET');
    assert.match(settingsStatus.textContent, /custom API key is configured/i);
    assert.equal(settingsClearButton.disabled, false);
    assert.ok(!settingsStatus.textContent.includes('sk_'));

    // The key input is never prefilled, not even with a saved value.
    settingsInput.value = 'sk-should-never-appear';
    openSettings();
    assert.equal(settingsInput.value, '');
    await loadSarvamKeyStatus();

    // An accidental empty submit must never clear the saved custom key.
    fetchState.calls.length = 0;
    settingsInput.value = '   ';
    await saveSarvamKey({ preventDefault() {} });
    assert.equal(fetchState.calls.length, 0);
    assert.match(settingsStatus.textContent, /enter a key/i);

    // Saving a replacement posts only the entered key.
    fetchState.calls.length = 0;
    fetchState.response = { ok: true, body: { configured: true, source: 'custom', masked: '********' } };
    settingsInput.value = 'sk-new-custom-key';
    await saveSarvamKey({ preventDefault() {} });
    assert.equal(fetchState.calls.length, 1);
    assert.equal(fetchState.calls[0].method, 'POST');
    assert.deepEqual(JSON.parse(fetchState.calls[0].body), {
      api_key: 'sk-new-custom-key',
      client_id: clientId,
    });
    assert.equal(settingsInput.value, '');
    assert.match(settingsStatus.textContent, /custom key saved/i);
    assert.equal(settingsClearButton.disabled, false);

    // Clearing posts an explicit empty key and re-disables the button.
    fetchState.calls.length = 0;
    fetchState.response = { ok: true, body: { configured: true, source: 'env', masked: '********' } };
    await clearSarvamKey();
    assert.equal(fetchState.calls.length, 1);
    assert.equal(fetchState.calls[0].method, 'POST');
    assert.deepEqual(JSON.parse(fetchState.calls[0].body), { api_key: '', client_id: clientId });
    assert.equal(settingsClearButton.disabled, true);
    assert.match(settingsStatus.textContent, /custom key cleared/i);

    // Status refresh with the .env key keeps Clear disabled.
    fetchState.calls.length = 0;
    fetchState.response = { ok: true, body: { configured: true, source: 'env', masked: '********' } };
    await loadSarvamKeyStatus();
    assert.equal(fetchState.calls[0].method, 'GET');
    assert.equal(settingsClearButton.disabled, true);
    assert.match(settingsStatus.textContent, /deployment default/i);

    // A page reload (status re-read) never replaces the saved custom key.
    fetchState.calls.length = 0;
    fetchState.response = { ok: true, body: { configured: true, source: 'custom', masked: '********' } };
    await loadSarvamKeyStatus();
    assert.equal(fetchState.calls.length, 1);
    assert.equal(fetchState.calls[0].method, 'GET');
    assert.equal(settingsClearButton.disabled, false);
    assert.match(settingsStatus.textContent, /custom API key is configured/i);
    console.log('Settings key status, empty-save guard, clear flow, and masked statuses verified.');
  })()
`);

Promise.resolve(test.runInContext(context)).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
