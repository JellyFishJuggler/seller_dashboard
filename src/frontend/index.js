const API_URL = localStorage.getItem('seller-assistant-api-url') || 'https://seller-dashboard-b7uw.onrender.com';
const conversation = document.querySelector('#conversation');
const newChatButton = document.querySelector('#new-chat');
const voiceBar = document.querySelector('.voice-bar');
const voiceStatus = document.querySelector('#voice-status');
const liveTranscript = document.querySelector('#live-transcript');
const startVoiceButton = document.querySelector('#start-voice');
const endVoiceButton = document.querySelector('#end-voice');
const connectionStatus = document.querySelector('#connection-status');
const connectionLabel = document.querySelector('#connection-label');
const transcriptLive = document.querySelector('#transcript-live');
const sellerIdInput = document.querySelector('#seller-id-input');
const loadSellerButton = document.querySelector('#load-seller');
const settingsToggle = document.querySelector('#settings-toggle');
const settingsDialog = document.querySelector('#settings-dialog');
const settingsForm = document.querySelector('#settings-form');
const settingsCancel = document.querySelector('#settings-cancel');
const settingsSave = document.querySelector('#settings-save');
const settingsClear = document.querySelector('#settings-clear');
const sarvamKeyInput = document.querySelector('#sarvam-key-input');
const sarvamKeyStatus = document.querySelector('#sarvam-key-status');

let sellerId = localStorage.getItem('seller-assistant-seller-id') || '';
let sessionId = createSessionId();
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
let voicePlaybackIsFinalization = false;
let voiceEndTimer = null;
let voiceClosingByUser = false;
let voiceStartToken = 0;
let voiceReplyErrored = false;
let voiceRecoverableError = false;
let voiceRecoverableMessage = '';
let voiceAudioChunksLogged = 0;
let voiceKeepaliveTimer = null;
let voiceCallFinalizing = false;
let voiceCallCompleted = false;

function voiceTextState(value) {
  if (value === null || value === undefined) return 'none';
  if (typeof value !== 'string') return 'invalid_type';
  if (value.length === 0) return 'empty';
  if (!value.trim()) return 'whitespace';
  return 'present';
}

function logVoiceBoundary(service, text = null, requestId = null, extra = {}) {
  const state = Object.prototype.hasOwnProperty.call(extra, 'audio_bytes')
    ? 'not_applicable' : voiceTextState(text);
  console.info('voice_boundary', {
    service,
    session_id: sessionId,
    text_exists: typeof text === 'string' && text.length > 0,
    text_length: typeof text === 'string' ? text.length : 0,
    text_state: state,
    request_id: requestId || 'unavailable',
    ...extra,
  });
}

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
  connectionStatus.dataset.state = state;
  transcriptLive.dataset.state = state;
  const labels = {
    idle: ['Voice ready', 'Ready'],
    connecting: ['Connecting…', 'Connecting'],
    listening: ['Voice connected', 'Listening'],
    processing: ['Voice connected', 'Thinking'],
    speaking: ['Voice connected', 'Speaking'],
    error: ['Connection issue', 'Issue'],
  };
  const [connectionText, transcriptText] = labels[state] || labels.idle;
  connectionLabel.textContent = connectionText;
  transcriptLive.lastChild.textContent = ` ${transcriptText}`;
}

function addMessage(text, who, extraClass = '') {
  document.querySelector('#transcript-empty')?.remove();
  const row = document.createElement('div');
  row.className = `message-row ${who === 'assistant' ? 'assistant-row' : 'user-row'}`;
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.setAttribute('aria-hidden', 'true');
  avatar.textContent = who === 'assistant' ? 'AI' : 'You';
  const content = document.createElement('div');
  content.className = 'message-content';
  const label = document.createElement('div');
  label.className = 'message-label';
  label.textContent = who === 'assistant' ? 'Seller Assistant' : 'You';
  const bubble = document.createElement('div');
  bubble.className = `message ${who === 'assistant' ? 'assistant-message' : ''} ${extraClass}`.trim();
  bubble.textContent = text;
  content.append(label, bubble);
  row.append(avatar, content);
  conversation.append(row);
  scrollToLatest();
  return bubble;
}

function sendVoicePcm(pcm) {
  if (pcm?.byteLength && voiceActive && !voicePaused && !voiceCallFinalizing && voiceSocket?.readyState === WebSocket.OPEN) {
    voiceSocket.send(pcm.buffer);
    voiceAudioChunksLogged += 1;
    if (voiceAudioChunksLogged === 1 || voiceAudioChunksLogged % 50 === 0) {
      logVoiceBoundary('Browser PCM -> FastAPI WebSocket', null, null, {
        audio_bytes: pcm.byteLength,
        chunks_sent: voiceAudioChunksLogged,
      });
    }
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
  try {
    voiceAudioContext = new AudioContext({ sampleRate: 16000 });
  } catch {
    voiceAudioContext = new AudioContext();
  }
  // Start the context during the button gesture, before the permission prompt
  // can consume the browser's transient user activation.
  const resumeAudio = voiceAudioContext.resume().catch(() => undefined);
  voiceStream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  await resumeAudio;
  if (voiceAudioContext.state !== 'running') {
    await voiceAudioContext.resume();
  }
  if (voiceAudioContext.state !== 'running') {
    throw new Error('The browser audio system is paused. Allow microphone audio and try again.');
  }

  const microphoneTrack = voiceStream.getAudioTracks()[0];
  if (!microphoneTrack || microphoneTrack.readyState !== 'live') {
    throw new Error('No active microphone was found. Check your microphone and try again.');
  }
  microphoneTrack.addEventListener('ended', () => {
    if (!voiceActive || voiceCallFinalizing) return;
    voiceRecoverableError = true;
    voiceRecoverableMessage = 'The microphone disconnected. Check it, then start voice again.';
    voicePaused = true;
    setVoiceState('error', voiceRecoverableMessage);
    if (voiceSocket?.readyState === WebSocket.OPEN) {
      voiceSocket.close(1012, 'Microphone disconnected');
    }
  }, { once: true });

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
  if (!window.isSecureContext) {
    setVoiceState('error', 'Microphone access requires HTTPS or localhost. Open the portal using a secure connection.');
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !('WebSocket' in window)) {
    setVoiceState('error', 'This browser does not support microphone voice chat.');
    return;
  }

  const attempt = ++voiceStartToken;
  voiceRecoverableError = false;
  voiceRecoverableMessage = '';
  voiceStarting = true;
  startVoiceButton.disabled = true;
  setVoiceState('connecting', 'Requesting microphone access…');
  try {
    await connectMicrophone();
    if (attempt !== voiceStartToken) {
      cleanupVoiceResources();
      return;
    }
    setVoiceState('connecting', 'Connecting to voice service…');
    // Bind the loaded seller to the voice session so the assistant answers
    // from this seller's data right away instead of asking for a seller ID.
    const sellerParam = sellerId ? `?seller_id=${encodeURIComponent(sellerId)}` : '';
    const socketUrl = `${API_URL.replace(/^http/, 'ws').replace(/\/$/, '')}/voice/${encodeURIComponent(sessionId)}${sellerParam}`;
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
      if (voiceCallCompleted) setVoiceState('idle', 'Call completed and saved');
      else if (voiceRecoverableError) setVoiceState('error', voiceRecoverableMessage);
      else if (wasActive) setVoiceState('error', 'Voice connection closed. Start a new call to reconnect.');
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
    voiceCallFinalizing = false;
    voiceCallCompleted = false;
    voiceAudioChunksLogged = 0;
    logVoiceBoundary('Browser microphone capture started');
    voicePaused = false;
    voiceClosingByUser = false;
    startVoiceKeepalive();
    startVoiceButton.disabled = true;
    endVoiceButton.disabled = false;
    liveTranscript.hidden = false;
    liveTranscript.textContent = 'Microphone ready. Connecting speech recognition…';
    setVoiceState('connecting', 'Microphone ready. Connecting speech recognition…');
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

function startVoiceKeepalive() {
  stopVoiceKeepalive();
  // Hosted proxies (e.g. Render) drop WebSocket connections that carry no
  // data for about a minute. While the assistant is thinking or speaking the
  // microphone is paused, so nothing flows; a small periodic message keeps
  // the connection alive. The backend ignores unknown control messages.
  voiceKeepaliveTimer = setInterval(() => {
    if (voiceSocket?.readyState !== WebSocket.OPEN || !voiceActive) return;
    if (!voicePaused && !voiceCallFinalizing) return; // live mic audio already flows
    try {
      voiceSocket.send(JSON.stringify({ type: 'keepalive' }));
    } catch {
      // A failed keepalive is picked up by the socket's close handling.
    }
  }, 20000);
}

function stopVoiceKeepalive() {
  if (voiceKeepaliveTimer) {
    clearInterval(voiceKeepaliveTimer);
    voiceKeepaliveTimer = null;
  }
}

function cleanupVoiceResources() {
  voiceActive = false;
  voicePaused = false;
  stopVoiceKeepalive();
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
  voicePlaybackIsFinalization = false;
  voiceAudioReceived = false;
  voiceAssistantEnded = false;
  voiceCallFinalizing = false;
  startVoiceButton.disabled = false;
  endVoiceButton.disabled = true;
  liveTranscript.hidden = true;
}

function endVoice() {
  if (!voiceActive && !voiceStarting) return;
  if (voiceSocket?.readyState === WebSocket.OPEN) {
    voiceCallFinalizing = true;
    voicePaused = true;
    endVoiceButton.disabled = true;
    setVoiceState('processing', 'Saving your call…');
    voiceSocket.send(JSON.stringify({ type: 'end_call' }));
    return;
  }
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
    logVoiceBoundary('FastAPI WebSocket -> Browser TTS audio', null, null, {
      audio_bytes: event.data?.byteLength ?? event.data?.size ?? 0,
    });
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

  if (data.type === 'stt_ready') {
    voicePaused = false;
    liveTranscript.hidden = false;
    liveTranscript.textContent = 'Speech recognition connected. Start speaking.';
    setVoiceState('listening', 'Listening…');
  } else if (data.type === 'partial_transcript') {
    logVoiceBoundary('FastAPI WebSocket -> Browser partial transcript', data.text, data.request_id);
    liveTranscript.hidden = false;
    liveTranscript.textContent = data.text || 'Listening…';
    setVoiceState('listening', 'Listening…');
  } else if (data.type === 'assistant_start') {
    logVoiceBoundary('FastAPI WebSocket -> Browser final transcript', data.transcript, data.request_id);
    voicePaused = true;
    voiceAssistantEnded = false;
    voiceAudioReceived = false;
    voicePlaybackPending = true;
    voiceReplyErrored = false;
    liveTranscript.hidden = true;
    if (data.transcript) addMessage(data.transcript, 'user');
    setVoiceState('processing', 'Assistant is thinking…');
  } else if (data.type === 'call_finalizing') {
    voiceCallFinalizing = true;
    voicePaused = true;
    clearTimeout(voiceEndTimer);
    setVoiceState('processing', 'Preparing your call summary…');
  } else if (data.type === 'finalization_in_progress') {
    voiceCallFinalizing = true;
    voicePaused = true;
    setVoiceState('processing', data.message || 'Your call is already being finalized…');
  } else if (data.type === 'assistant_reply') {
    logVoiceBoundary('FastAPI WebSocket -> Browser assistant text', data.text, data.request_id);
    voicePlaybackIsFinalization = voiceCallFinalizing;
    if (data.text) addMessage(data.text, 'assistant');
    setVoiceState('speaking', 'Assistant is speaking…');
  } else if (data.type === 'assistant_end') {
    voiceAssistantEnded = true;
    if (voiceCallFinalizing) {
      voicePaused = true;
      setVoiceState('speaking', 'Playing your closing message…');
    } else if (voiceReplyErrored) {
      finishVoiceTurn();
    } else if (voiceAudioReceived || voicePlaybackActive || voicePlaybackPending) {
      resumeVoiceAfterReply();
    } else {
      clearTimeout(voiceEndTimer);
      voiceEndTimer = setTimeout(() => {
        if (voiceAssistantEnded && !voiceAudioReceived && !voicePlaybackActive) finishVoiceTurn();
      }, 4000);
    }
  } else if (data.type === 'call_ended') {
    voiceCallCompleted = data.status === 'completed';
    voiceCallFinalizing = false;
    voicePaused = true;
    endVoiceButton.disabled = true;
    setVoiceState('idle', voiceCallCompleted ? 'Call completed and saved' : 'Call ended');
  } else if (data.type === 'error') {
    logVoiceBoundary(`FastAPI WebSocket error: ${data.code || 'voice_error'}`, data.message, data.request_id);
    if (data.recoverable && ['stt_connection_closed', 'stt_quota_exceeded', 'stt_auth_failed'].includes(data.code)) {
      if (voiceCallFinalizing) {
        voicePaused = true;
        setVoiceState('processing', data.message || 'Speech recognition disconnected while saving the call.');
        return;
      }
      voiceRecoverableError = true;
      voiceRecoverableMessage = data.message || 'Speech recognition disconnected. Tap Start voice to retry.';
      voicePaused = true;
      setVoiceState('error', voiceRecoverableMessage);
      if (voiceSocket?.readyState === WebSocket.OPEN) {
        voiceSocket.close(1012, 'Speech recognition unavailable');
      }
      return;
    }
    if (data.code === 'empty_transcript') {
      // Speech that could not be transcribed is a gentle nudge in the voice
      // status line, not a red error bubble in the conversation.
      voicePaused = false;
      setVoiceState('listening', data.message || 'I did not catch that. Please say it again.');
      return;
    }
    voicePaused = false;
    voicePlaybackPending = false;
    voiceAssistantEnded = true;
    voiceReplyErrored = true;
    if (voiceCallFinalizing) {
      voiceCallFinalizing = false;
      voicePaused = false;
      voiceAssistantEnded = false;
      voiceReplyErrored = false;
      endVoiceButton.disabled = false;
    }
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
      if (voiceSocket?.readyState === WebSocket.OPEN) {
        voiceSocket.send(JSON.stringify({
          type: voicePlaybackIsFinalization ? 'playback_complete' : 'turn_playback_complete',
        }));
      }
      if (voiceCallFinalizing) {
        voicePaused = true;
        setVoiceState('processing', 'Confirming call completion…');
      } else if (voiceAssistantEnded) finishVoiceTurn();
      else setVoiceState('processing', 'Finishing response…');
    };
    source.start();
  } catch (error) {
    voicePlaybackActive = false;
    if (!voiceCallFinalizing) voicePaused = false;
    if (voiceSocket?.readyState === WebSocket.OPEN) {
      voiceSocket.send(JSON.stringify({
        type: voicePlaybackIsFinalization ? 'playback_failed' : 'turn_playback_failed',
      }));
    }
    addMessage(`Could not play the assistant audio: ${error.message || 'unsupported audio format.'}`, 'assistant', 'error-message');
    setVoiceState('error', voiceCallFinalizing
      ? 'Closing audio failed; waiting for retry.'
      : 'Audio playback failed.');
    if (!voiceCallFinalizing && voiceAssistantEnded) finishVoiceTurn();
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
  if (voiceCallFinalizing) {
    voicePaused = true;
    return;
  }
  voicePaused = false;
  if (voiceActive) setVoiceState('listening', 'Listening…');
}

function formatPercent(value) {
  const percentage = Number(value);
  if (!Number.isFinite(percentage)) return 'Change unavailable';
  return `${percentage > 0 ? '+' : ''}${percentage.toFixed(1)}% vs. last month`;
}

function showMetricChange(element, value) {
  const percentage = Number(value);
  element.textContent = formatPercent(value);
  element.classList.toggle('positive', Number.isFinite(percentage) && percentage > 0);
  element.classList.toggle('negative', Number.isFinite(percentage) && percentage < 0);
}

async function loadSellerMetrics() {
  const requestedSellerId = sellerIdInput.value.trim();
  if (!requestedSellerId) {
    setVoiceState('error', 'Enter a seller ID to load your account metrics.');
    sellerIdInput.focus();
    return;
  }

  sellerId = requestedSellerId;
  localStorage.setItem('seller-assistant-seller-id', sellerId);
  loadSellerButton.disabled = true;
  loadSellerButton.textContent = 'Loading…';
  try {
    const response = await fetch(`${API_URL.replace(/\/$/, '')}/dashboard/${encodeURIComponent(sellerId)}`);
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.message || data.error || `Could not load seller metrics (HTTP ${response.status}).`);
    }

    document.querySelector('#sales-value').textContent = data.this_month?.sales_display || '—';
    document.querySelector('#orders-value').textContent = Number.isFinite(Number(data.this_month?.orders))
      ? Number(data.this_month.orders).toLocaleString('en-IN') : '—';
    document.querySelector('#price-value').textContent = data.this_month?.avg_selling_price_display || '—';
    showMetricChange(document.querySelector('#sales-change'), data.changes?.sales_pct);
    showMetricChange(document.querySelector('#orders-change'), data.changes?.orders_pct);
    showMetricChange(document.querySelector('#price-change'), data.changes?.avg_selling_price_pct);
    sellerIdInput.value = data.seller_id || sellerId;
    setVoiceState(voiceActive ? 'listening' : 'idle', `Account loaded: ${data.seller_id || sellerId}`);
  } catch (error) {
    document.querySelector('#sales-value').textContent = '—';
    document.querySelector('#orders-value').textContent = '—';
    document.querySelector('#price-value').textContent = '—';
    document.querySelector('#sales-change').textContent = error.message || 'Could not load seller metrics';
    document.querySelector('#orders-change').textContent = 'Check the seller ID and try again';
    document.querySelector('#price-change').textContent = 'Dashboard connection unavailable';
    setVoiceState('error', error.message || 'Could not load seller metrics.');
  } finally {
    loadSellerButton.disabled = false;
    loadSellerButton.textContent = 'Load';
  }
}

function clearTranscript() {
  conversation.replaceChildren();
  const empty = document.createElement('div');
  empty.className = 'transcript-empty';
  empty.id = 'transcript-empty';
  empty.innerHTML = '<span class="empty-icon" aria-hidden="true">◌</span><p>Your conversation will appear here.</p><span>Start speaking to ask your first question.</span>';
  conversation.append(empty);
}

function startNewSession() {
  endVoice();
  sessionId = createSessionId();
  clearTranscript();
  liveTranscript.hidden = true;
  setVoiceState('idle', 'Tap to start speaking');
}

function setSarvamKeyStatus(message, state = '') {
  sarvamKeyStatus.textContent = message;
  sarvamKeyStatus.dataset.state = state;
}

async function loadSarvamKeyStatus() {
  setSarvamKeyStatus('Checking…');
  settingsClear.disabled = true;
  try {
    const response = await fetch(`${API_URL.replace(/\/$/, '')}/settings/sarvam-key`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Could not read the API key status.');
    if (data.source === 'custom') {
      setSarvamKeyStatus('Custom API key configured. Saving a new key replaces it.', 'success');
      settingsClear.disabled = false;
    } else if (data.source === 'env') {
      setSarvamKeyStatus('Using the default key from .env. Enter a custom key to override it.');
    } else {
      setSarvamKeyStatus('No Sarvam API key is configured.', 'error');
    }
  } catch (error) {
    setSarvamKeyStatus(error.message || 'Could not read the API key status.', 'error');
  }
}

function openSettings() {
  sarvamKeyInput.value = '';
  loadSarvamKeyStatus();
  if (typeof settingsDialog.showModal === 'function' && !settingsDialog.open) {
    settingsDialog.showModal();
  } else {
    settingsDialog.setAttribute('open', '');
  }
}

function closeSettings() {
  if (typeof settingsDialog.close === 'function') settingsDialog.close();
  else settingsDialog.removeAttribute('open');
}

async function saveSarvamKey(event) {
  event.preventDefault();
  const apiKey = sarvamKeyInput.value.trim();
  if (!apiKey) {
    // An accidental empty submit must never clear the saved custom key.
    setSarvamKeyStatus('Enter a key to save, or use “Clear custom key” to return to the .env key.', 'error');
    sarvamKeyInput.focus();
    return;
  }
  settingsSave.disabled = true;
  setSarvamKeyStatus('Saving…');
  try {
    const response = await fetch(`${API_URL.replace(/\/$/, '')}/settings/sarvam-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Could not save the API key.');
    sarvamKeyInput.value = '';
    if (data.source === 'custom') {
      setSarvamKeyStatus('Custom key saved. LLM, speech recognition and text-to-speech now use it.', 'success');
      settingsClear.disabled = false;
    } else if (data.source === 'env') {
      setSarvamKeyStatus('Custom key cleared. Using the .env key.', 'success');
      settingsClear.disabled = true;
    } else {
      setSarvamKeyStatus('No Sarvam API key is configured.', 'error');
    }
    if (!voiceActive && !voiceStarting && voiceBar.dataset.state === 'error') {
      liveTranscript.hidden = true;
      setVoiceState('idle', 'API key updated. Tap to start speaking.');
    }
  } catch (error) {
    setSarvamKeyStatus(error.message || 'Could not save the API key.', 'error');
  } finally {
    settingsSave.disabled = false;
  }
}

async function clearSarvamKey() {
  if (settingsClear.disabled) return;
  settingsClear.disabled = true;
  setSarvamKeyStatus('Clearing custom key…');
  try {
    const response = await fetch(`${API_URL.replace(/\/$/, '')}/settings/sarvam-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: '' }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Could not clear the custom key.');
    sarvamKeyInput.value = '';
    if (data.source === 'env') {
      setSarvamKeyStatus('Custom key cleared. Using the .env key.', 'success');
      settingsClear.disabled = true;
    } else if (data.source === 'custom') {
      setSarvamKeyStatus('Custom API key configured.', 'success');
      settingsClear.disabled = false;
    } else {
      setSarvamKeyStatus('No Sarvam API key is configured.', 'error');
      settingsClear.disabled = true;
    }
    if (!voiceActive && !voiceStarting && voiceBar.dataset.state === 'error') {
      liveTranscript.hidden = true;
      setVoiceState('idle', 'API key updated. Tap to start speaking.');
    }
  } catch (error) {
    setSarvamKeyStatus(error.message || 'Could not clear the custom key.', 'error');
    settingsClear.disabled = false;
  }
}

sellerIdInput.value = sellerId;
if (sellerId) loadSellerMetrics();
loadSellerButton.addEventListener('click', loadSellerMetrics);
sellerIdInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') loadSellerMetrics();
});
newChatButton.addEventListener('click', startNewSession);
startVoiceButton.addEventListener('click', startVoice);
endVoiceButton.addEventListener('click', endVoice);
settingsToggle.addEventListener('click', openSettings);
settingsCancel.addEventListener('click', closeSettings);
settingsClear.addEventListener('click', clearSarvamKey);
settingsForm.addEventListener('submit', saveSarvamKey);
