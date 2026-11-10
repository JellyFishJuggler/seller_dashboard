const API_URL = localStorage.getItem('seller-assistant-api-url') || 'http://127.0.0.1:8000';
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const conversation = document.querySelector('#conversation');
const sendButton = document.querySelector('#send-button');
const hint = document.querySelector('#input-hint');
const newChatButton = document.querySelector('#new-chat');
const voiceBar = document.querySelector('.voice-bar');
const voiceStatus = document.querySelector('#voice-status');
const liveTranscript = document.querySelector('#live-transcript');
const startVoiceButton = document.querySelector('#start-voice');
const endVoiceButton = document.querySelector('#end-voice');

let sellerId = '';
let sessionId = createSessionId();
let waitingForSellerId = true;
let busy = false;
let voiceSocket = null;
let voiceStream = null;
let voiceAudioContext = null;
let voiceSource = null;
let voiceProcessor = null;
let voiceMutedGain = null;
let voiceActive = false;
let voiceStarting = false;
let voicePaused = false;
let voiceAssistantEnded = false;
let voiceAudioReceived = false;
let voicePlaybackPending = false;
let voicePlaybackActive = false;
let voiceEndTimer = null;
let voiceClosingByUser = false;
let voiceStartToken = 0;
let voiceReplyErrored = false;

function createSessionId() {
  return globalThis.crypto?.randomUUID?.() || `seller-chat-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function scrollToLatest() {
  requestAnimationFrame(() => {
    conversation.scrollTop = conversation.scrollHeight;
  });
}

function setVoiceState(state, message) {
  voiceBar.dataset.state = state;
  voiceStatus.textContent = message;
}

function addMessage(text, who, extraClass = '') {
  const row = document.createElement('div');
  row.className = `message-row ${who === 'assistant' ? 'assistant-row' : 'user-row'}`;
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.setAttribute('aria-hidden', 'true');
  avatar.textContent = who === 'assistant' ? '✳' : 'You';
  const bubble = document.createElement('div');
  bubble.className = `message ${who === 'assistant' ? 'assistant-message' : ''} ${extraClass}`.trim();
  bubble.textContent = text;
  row.append(avatar, bubble);
  conversation.append(row);
  scrollToLatest();
  return bubble;
}

function setBusy(value) {
  busy = value;
  sendButton.disabled = value;
  input.disabled = value;
  sendButton.setAttribute('aria-label', value ? 'Waiting for response' : 'Send message');
}

function resizeInput() {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
}

function sendVoicePcm(pcm) {
  if (voiceActive && !voicePaused && voiceSocket?.readyState === WebSocket.OPEN) {
    voiceSocket.send(pcm.buffer);
  }
}

function floatToPcm16(samples, sampleRate) {
  const ratio = sampleRate / 16000;
  const length = Math.max(1, Math.floor(samples.length / ratio));
  const pcm = new Int16Array(length);
  for (let i = 0; i < length; i += 1) {
    const position = i * ratio;
    const left = Math.floor(position);
    const fraction = position - left;
    const first = samples[Math.min(left, samples.length - 1)] || 0;
    const second = samples[Math.min(left + 1, samples.length - 1)] || 0;
    const sample = Math.max(-1, Math.min(1, first + (second - first) * fraction));
    pcm[i] = sample < 0 ? sample * 32768 : sample * 32767;
  }
  return pcm;
}

async function connectMicrophone() {
  voiceStream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });

  try {
    voiceAudioContext = new AudioContext({ sampleRate: 16000 });
  } catch {
    voiceAudioContext = new AudioContext();
  }
  await voiceAudioContext.resume();
  voiceSource = voiceAudioContext.createMediaStreamSource(voiceStream);
  voiceMutedGain = voiceAudioContext.createGain();
  voiceMutedGain.gain.value = 0;

  const createScriptProcessorFallback = () => {
    voiceProcessor = voiceAudioContext.createScriptProcessor(4096, 1, 1);
    voiceProcessor.onaudioprocess = (event) => {
      const inputBuffer = event.inputBuffer;
      const frames = inputBuffer.length;
      const mono = new Float32Array(frames);
      for (let channel = 0; channel < inputBuffer.numberOfChannels; channel += 1) {
        const source = inputBuffer.getChannelData(channel);
        for (let i = 0; i < frames; i += 1) mono[i] += source[i] / inputBuffer.numberOfChannels;
      }
      sendVoicePcm(floatToPcm16(mono, voiceAudioContext.sampleRate));
      event.outputBuffer.getChannelData(0).fill(0);
    };
  };

  if (voiceAudioContext.audioWorklet) {
    const workletCode = `
      class SellerPcmProcessor extends AudioWorkletProcessor {
        constructor() {
          super();
          this.step = sampleRate / 16000;
          this.offset = 0;
          this.pending = [];
          this.chunkSize = 1600;
        }
        process(inputs, outputs) {
          const channels = inputs[0];
          const output = outputs[0];
          if (output) for (const channel of output) channel.fill(0);
          if (!channels || !channels.length) return true;
          const frames = channels[0].length;
          const mono = new Float32Array(frames);
          for (let frame = 0; frame < frames; frame++) {
            let sum = 0;
            for (const channel of channels) sum += channel[frame] || 0;
            mono[frame] = sum / channels.length;
          }
          while (this.offset < frames) {
            const left = Math.floor(this.offset);
            const fraction = this.offset - left;
            const a = mono[left] || 0;
            const b = mono[Math.min(left + 1, frames - 1)] || 0;
            this.pending.push(a + (b - a) * fraction);
            this.offset += this.step;
          }
          this.offset -= frames;
          while (this.pending.length >= this.chunkSize) {
            const pcm = new Int16Array(this.chunkSize);
            for (let i = 0; i < this.chunkSize; i++) {
              const sample = Math.max(-1, Math.min(1, this.pending[i]));
              pcm[i] = sample < 0 ? sample * 32768 : sample * 32767;
            }
            this.pending.splice(0, this.chunkSize);
            this.port.postMessage(pcm.buffer, [pcm.buffer]);
          }
          return true;
        }
      }
      registerProcessor('seller-pcm-processor', SellerPcmProcessor);
    `;
    const workletUrl = URL.createObjectURL(new Blob([workletCode], { type: 'text/javascript' }));
    try {
      try {
        await voiceAudioContext.audioWorklet.addModule(workletUrl);
      } catch {
        createScriptProcessorFallback();
      }
    } finally {
      URL.revokeObjectURL(workletUrl);
    }
    if (!voiceProcessor) {
      voiceProcessor = new AudioWorkletNode(voiceAudioContext, 'seller-pcm-processor', {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      voiceProcessor.port.onmessage = (event) => {
        sendVoicePcm(new Int16Array(event.data));
      };
    }
  } else {
    createScriptProcessorFallback();
  }

  voiceSource.connect(voiceProcessor);
  voiceProcessor.connect(voiceMutedGain);
  voiceMutedGain.connect(voiceAudioContext.destination);
}

async function startVoice() {
  if (voiceActive || voiceStarting) return;
  if (!navigator.mediaDevices?.getUserMedia || !('WebSocket' in window)) {
    setVoiceState('error', 'This browser does not support microphone voice chat.');
    return;
  }

  const attempt = ++voiceStartToken;
  voiceStarting = true;
  startVoiceButton.disabled = true;
  setVoiceState('connecting', 'Requesting microphone access…');
  try {
    await connectMicrophone();
    if (attempt !== voiceStartToken) {
      cleanupVoiceResources();
      return;
    }
    const socketUrl = `${API_URL.replace(/^http/, 'ws').replace(/\/$/, '')}/voice/${encodeURIComponent(sessionId)}`;
    const socket = new WebSocket(socketUrl);
    voiceSocket = socket;
    socket.binaryType = 'arraybuffer';
    socket.onmessage = (event) => handleVoiceMessage(event);
    socket.onerror = () => {
      if (voiceActive || voiceStarting) setVoiceState('error', 'Voice connection failed. Check that the API is running.');
    };
    socket.onclose = () => {
      const wasActive = voiceActive;
      cleanupVoiceResources();
      if (wasActive) setVoiceState('error', 'Voice connection closed. Start a new call to reconnect.');
      else if (!voiceClosingByUser) setVoiceState('error', 'Voice connection closed.');
      voiceClosingByUser = false;
      voiceSocket = null;
    };
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Timed out connecting to the voice service.')), 10000);
      socket.addEventListener('open', () => { clearTimeout(timeout); resolve(); }, { once: true });
      socket.addEventListener('error', () => { clearTimeout(timeout); reject(new Error('Could not connect to the voice service.')); }, { once: true });
      socket.addEventListener('close', () => { clearTimeout(timeout); reject(new Error('The voice service closed the connection.')); }, { once: true });
    });
    voiceActive = true;
    voicePaused = false;
    voiceClosingByUser = false;
    startVoiceButton.disabled = true;
    endVoiceButton.disabled = false;
    liveTranscript.hidden = false;
    liveTranscript.textContent = 'Microphone connected. Start speaking when ready.';
    setVoiceState('listening', 'Listening…');
  } catch (error) {
    cleanupVoiceResources();
    if (voiceSocket && voiceSocket.readyState < WebSocket.CLOSING) voiceSocket.close();
    voiceSocket = null;
    if (attempt === voiceStartToken) {
      startVoiceButton.disabled = false;
      endVoiceButton.disabled = true;
      const denied = error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError';
      setVoiceState('error', denied ? 'Microphone permission was denied.' : (error.message || 'Could not start voice chat.'));
    }
  } finally {
    if (attempt === voiceStartToken) voiceStarting = false;
  }
}

function cleanupVoiceResources() {
  voiceActive = false;
  voicePaused = false;
  clearTimeout(voiceEndTimer);
  voiceEndTimer = null;
  if (voiceProcessor) {
    voiceProcessor.disconnect();
    if (voiceProcessor.port) voiceProcessor.port.onmessage = null;
    if ('onaudioprocess' in voiceProcessor) voiceProcessor.onaudioprocess = null;
  }
  voiceSource?.disconnect();
  voiceMutedGain?.disconnect();
  voiceStream?.getTracks().forEach((track) => track.stop());
  if (voiceAudioContext && voiceAudioContext.state !== 'closed') voiceAudioContext.close();
  voiceProcessor = null;
  voiceSource = null;
  voiceMutedGain = null;
  voiceStream = null;
  voiceAudioContext = null;
  voicePlaybackPending = false;
  voicePlaybackActive = false;
  voiceAudioReceived = false;
  voiceAssistantEnded = false;
  startVoiceButton.disabled = false;
  endVoiceButton.disabled = true;
}

function endVoice() {
  if (!voiceActive && !voiceStarting) return;
  voiceStartToken += 1;
  voiceStarting = false;
  voiceClosingByUser = true;
  const socket = voiceSocket;
  if (socket && socket.readyState < WebSocket.CLOSING) socket.close(1000, 'Call ended');
  voiceSocket = null;
  cleanupVoiceResources();
  liveTranscript.hidden = true;
  setVoiceState('idle', 'Voice call ended');
}

function handleVoiceMessage(event) {
  if (typeof event.data !== 'string') {
    voiceAudioReceived = true;
    voicePlaybackPending = false;
    playVoiceAudio(event.data);
    return;
  }

  let data;
  try {
    data = JSON.parse(event.data);
  } catch {
    setVoiceState('error', 'Received an unreadable message from the voice service.');
    return;
  }

  if (data.type === 'partial_transcript') {
    liveTranscript.hidden = false;
    liveTranscript.textContent = data.text || 'Listening…';
    setVoiceState('listening', 'Listening…');
  } else if (data.type === 'assistant_start') {
    voicePaused = true;
    voiceAssistantEnded = false;
    voiceAudioReceived = false;
    voicePlaybackPending = true;
    voiceReplyErrored = false;
    liveTranscript.hidden = true;
    if (data.transcript) addMessage(data.transcript, 'user');
    setVoiceState('processing', 'Assistant is thinking…');
  } else if (data.type === 'assistant_reply') {
    if (data.text) addMessage(data.text, 'assistant');
    setVoiceState('speaking', 'Assistant is speaking…');
  } else if (data.type === 'assistant_end') {
    voiceAssistantEnded = true;
    if (voiceReplyErrored) {
      finishVoiceTurn();
    } else if (voiceAudioReceived || voicePlaybackActive || voicePlaybackPending) {
      resumeVoiceAfterReply();
    } else {
      clearTimeout(voiceEndTimer);
      voiceEndTimer = setTimeout(() => {
        if (voiceAssistantEnded && !voiceAudioReceived && !voicePlaybackActive) finishVoiceTurn();
      }, 4000);
    }
  } else if (data.type === 'error') {
    voicePaused = false;
    voicePlaybackPending = false;
    voiceAssistantEnded = true;
    voiceReplyErrored = true;
    addMessage(`Voice assistant error: ${data.message || 'Unknown backend error.'}`, 'assistant', 'error-message');
    setVoiceState('error', data.message || 'The voice service returned an error.');
  }
}

async function playVoiceAudio(audioData) {
  if (!voiceAudioContext) return;
  voicePlaybackActive = true;
  voicePlaybackPending = false;
  setVoiceState('speaking', 'Assistant is speaking…');
  try {
    await voiceAudioContext.resume();
    let audioBuffer;
    const bytes = audioData instanceof Blob ? await audioData.arrayBuffer() : audioData;
    try {
      audioBuffer = await voiceAudioContext.decodeAudioData(bytes.slice(0));
    } catch {
      const view = new DataView(bytes);
      const samples = new Float32Array(Math.floor(bytes.byteLength / 2));
      for (let i = 0; i < samples.length; i += 1) samples[i] = view.getInt16(i * 2, true) / 32768;
      audioBuffer = voiceAudioContext.createBuffer(1, samples.length, 16000);
      audioBuffer.copyToChannel(samples, 0);
    }
    const source = voiceAudioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(voiceAudioContext.destination);
    source.onended = () => {
      voicePlaybackActive = false;
      if (voiceAssistantEnded) finishVoiceTurn();
      else setVoiceState('processing', 'Finishing response…');
    };
    source.start();
  } catch (error) {
    voicePlaybackActive = false;
    voicePaused = false;
    addMessage(`Could not play the assistant audio: ${error.message || 'unsupported audio format.'}`, 'assistant', 'error-message');
    setVoiceState('error', 'Audio playback failed; microphone resumed.');
    if (voiceAssistantEnded) finishVoiceTurn();
  }
}

function resumeVoiceAfterReply() {
  clearTimeout(voiceEndTimer);
  if (voicePlaybackActive || voicePlaybackPending) {
    setVoiceState('speaking', 'Assistant is speaking…');
    return;
  }
  if (voiceAssistantEnded) finishVoiceTurn();
}

function finishVoiceTurn() {
  clearTimeout(voiceEndTimer);
  voicePlaybackPending = false;
  voicePaused = false;
  if (voiceActive) setVoiceState('listening', 'Listening…');
}

async function sendQuery(query) {
  setBusy(true);
  const bubble = addMessage('Thinking', 'assistant', 'typing');
  try {
    const response = await fetch(`${API_URL.replace(/\/$/, '')}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, seller_id: sellerId, message: query }),
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error(`The API returned an unreadable response (HTTP ${response.status}).`);
    }
    if (!response.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data);
      throw new Error(detail || `Request failed (HTTP ${response.status}).`);
    }
    bubble.classList.remove('typing');
    bubble.textContent = data.message || 'I didn’t receive a response. Please try again.';
  } catch (error) {
    bubble.classList.remove('typing');
    bubble.classList.add('error-message');
    bubble.textContent = `${error.message || 'Could not reach the API.'} Make sure the Seller API is running at ${API_URL}.`;
  } finally {
    setBusy(false);
    input.focus();
    scrollToLatest();
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  resizeInput();
  addMessage(text, 'user');

  if (waitingForSellerId) {
    sellerId = text;
    waitingForSellerId = false;
    input.placeholder = 'Ask about your store…';
    hint.textContent = `Connected for this chat as ${sellerId}. Ask a question about your store.`;
    addMessage(`Thanks! I’m ready to help with seller ${sellerId}. What would you like to know?`, 'assistant');
    return;
  }

  await sendQuery(text);
});

input.addEventListener('input', resizeInput);
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

newChatButton.addEventListener('click', () => {
  endVoice();
  sessionId = createSessionId();
  sellerId = '';
  waitingForSellerId = true;
  conversation.replaceChildren();

  const welcome = document.createElement('div');
  welcome.className = 'welcome-block';
  welcome.innerHTML = '<span class="welcome-icon" aria-hidden="true">✳</span><h2>Let’s get started.</h2><p>Your seller data is just a question away.</p>';
  conversation.append(welcome);
  addMessage('Hi! To get started, what’s your seller ID or unique ID?', 'assistant');
  input.placeholder = 'Enter your seller ID…';
  hint.textContent = 'Your seller ID connects the assistant to your store.';
  input.value = '';
  resizeInput();
  input.focus();
});

startVoiceButton.addEventListener('click', startVoice);
endVoiceButton.addEventListener('click', endVoice);
