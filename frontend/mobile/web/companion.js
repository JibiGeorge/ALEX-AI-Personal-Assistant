/**
 * Alex Mobile Companion - Web Client
 * Duplex 16kHz Audio Streaming & Encrypted Chat
 */

(function () {
  'use strict';

  // DOM Elements
  const statusEl = document.getElementById('status');
  const feedEl = document.getElementById('feed');
  const micBtn = document.getElementById('micBtn');
  const textInput = document.getElementById('textInput');
  const sendBtn = document.getElementById('sendBtn');
  const approvalModal = document.getElementById('approvalModal');
  const approvalActionName = document.getElementById('approvalActionName');
  const approvalParams = document.getElementById('approvalParams');
  const approvalDenyBtn = document.getElementById('approvalDenyBtn');
  const approvalApproveBtn = document.getElementById('approvalApproveBtn');

  let currentApprovalRequestId = null;

  // Network State
  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname || 'localhost';
  const port = window.location.port || '8766';
  const apiBase = `${protocol}//${host}:${port}/api/v1/mobile`;
  const wsUrlBase = `${wsProtocol}//${host}:${port}/api/v1/mobile/ws/audio`;

  let sessionToken = localStorage.getItem('alex_mobile_session_token') || null;
  let socket = null;
  let audioContext = null;
  let mediaStream = null;
  let processorNode = null;
  let isRecording = false;

  function setStatus(text, className) {
    statusEl.textContent = text;
    statusEl.className = 'status-badge ' + (className || '');
  }

  function appendBubble(text, sender) {
    const bubble = document.createElement('div');
    bubble.className = `bubble ${sender}`;
    bubble.textContent = text;
    feedEl.appendChild(bubble);
    feedEl.scrollTop = feedEl.scrollHeight;
  }

  // --- Pairing Flow ---
  async function pair(code) {
    setStatus('PAIRING...', 'pending');
    try {
      const res = await fetch(`${apiBase}/pair`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pairing_code: code.trim().toUpperCase(),
          device_name: 'Web Companion',
          device_platform: 'Web',
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Pairing failed' }));
        throw new Error(err.detail || 'Pairing rejected');
      }

      const data = await res.json();
      sessionToken = data.session_token;
      localStorage.setItem('alex_mobile_session_token', sessionToken);
      setStatus('PAIRED', 'ready');
      appendBubble('Pairing successful! Connecting audio stream...', 'alex');
      connectWebSocket();
    } catch (err) {
      setStatus('ERROR', 'error');
      appendBubble(`Pairing error: ${err.message}. Tap here to retry.`, 'alex');
      sessionToken = null;
      localStorage.removeItem('alex_mobile_session_token');
    }
  }

  function ensurePaired() {
    if (!sessionToken) {
      const code = window.prompt('Enter the 8-character pairing code from Alex Desktop:');
      if (code) {
        pair(code);
      } else {
        setStatus('UNPAIRED', 'error');
      }
    } else {
      connectWebSocket();
    }
  }

  // --- WebSocket Connection ---
  function connectWebSocket() {
    if (!sessionToken) return;
    setStatus('CONNECTING...', 'pending');

    const wsUrl = `${wsUrlBase}?token=${encodeURIComponent(sessionToken)}`;
    socket = new WebSocket(wsUrl);
    socket.binaryType = 'arraybuffer';

    socket.onopen = () => {
      setStatus('READY', 'ready');
      appendBubble('Connected to Alex Mobile Gateway over LAN.', 'alex');
    };

    socket.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data);
          handleServerMessage(msg);
        } catch (e) {
          console.error('Failed to parse WebSocket JSON message:', e);
        }
      } else if (event.data instanceof ArrayBuffer) {
        // Binary audio response from Piper TTS (24kHz PCM or WAV)
        playBinaryAudio(event.data);
      }
    };

    socket.onerror = (err) => {
      console.warn('WebSocket error:', err);
      setStatus('WS ERROR', 'error');
    };

    socket.onclose = () => {
      setStatus('DISCONNECTED', 'error');
      // Reconnect after 3 seconds if session exists
      setTimeout(() => {
        if (sessionToken) connectWebSocket();
      }, 3000);
    };
  }

  function handleServerMessage(msg) {
    if (msg.type === 'transcript') {
      appendBubble(msg.text, 'user');
      setStatus('THINKING...', 'pending');
    } else if (msg.type === 'response') {
      appendBubble(msg.text, 'alex');
      setStatus('READY', 'ready');
    } else if (msg.type === 'audio' && msg.audio_base64) {
      playBase64Audio(msg.audio_base64, msg.sample_rate || 24000);
    } else if (msg.type === 'error') {
      appendBubble(`Error: ${msg.message || 'Unknown server error'}`, 'alex');
      setStatus('READY', 'ready');
    } else if (msg.type === 'action_approval_required') {
      currentApprovalRequestId = msg.request_id;
      approvalActionName.textContent = msg.action || 'Unknown Action';
      approvalParams.textContent = JSON.stringify(msg.params || {}, null, 2);
      approvalModal.style.display = 'flex';
      setStatus('APPROVAL NEEDED', 'active');
      appendBubble(`⚠️ Action authorization requested: ${msg.action}`, 'alex');
    } else if (msg.type === 'action_approval_ack') {
      approvalModal.style.display = 'none';
      currentApprovalRequestId = null;
      setStatus('READY', 'ready');
    }
  }

  // --- Audio Recording (16kHz 16-bit PCM Mono) ---
  async function startRecording() {
    if (isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      mediaStream = stream;
      audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
      });

      const source = audioContext.createMediaStreamSource(stream);
      // Buffer size 4096 gives ~250ms chunks at 16kHz
      processorNode = audioContext.createScriptProcessor(4096, 1, 1);

      processorNode.onaudioprocess = (e) => {
        if (!isRecording || !socket || socket.readyState !== WebSocket.OPEN) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(inputData);
        socket.send(pcm16.buffer);
      };

      source.connect(processorNode);
      processorNode.connect(audioContext.destination);

      isRecording = true;
      micBtn.classList.add('active');
      setStatus('LISTENING...', 'active');
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'audio_start' }));
      }
    } catch (err) {
      console.error('Microphone access denied or failed:', err);
      alert('Could not access microphone: ' + err.message);
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    micBtn.classList.remove('active');
    setStatus('PROCESSING...', 'pending');

    if (processorNode) {
      processorNode.disconnect();
      processorNode = null;
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close().catch(() => {});
      audioContext = null;
    }

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'audio_end' }));
    }
  }

  function floatTo16BitPCM(float32Array) {
    const int16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16;
  }

  // --- Audio Playback ---
  function playBinaryAudio(arrayBuffer) {
    try {
      const playbackCtx = new (window.AudioContext || window.webkitAudioContext)();
      playbackCtx.decodeAudioData(
        arrayBuffer.slice(0),
        (audioBuffer) => {
          const source = playbackCtx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(playbackCtx.destination);
          source.start(0);
          setStatus('SPEAKING...', 'active');
          source.onended = () => {
            setStatus('READY', 'ready');
            playbackCtx.close();
          };
        },
        (decodeErr) => {
          // If raw PCM rather than WAV, play via raw buffer
          playRawPcm(arrayBuffer, 24000);
        }
      );
    } catch (err) {
      console.warn('Audio playback failed:', err);
    }
  }

  function playRawPcm(arrayBuffer, sampleRate) {
    try {
      const playbackCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate });
      const int16 = new Int16Array(arrayBuffer);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0;
      }
      const buffer = playbackCtx.createBuffer(1, float32.length, sampleRate);
      buffer.copyToChannel(float32, 0);
      const source = playbackCtx.createBufferSource();
      source.buffer = buffer;
      source.connect(playbackCtx.destination);
      source.start(0);
      setStatus('SPEAKING...', 'active');
      source.onended = () => {
        setStatus('READY', 'ready');
        playbackCtx.close();
      };
    } catch (e) {
      console.error('Raw PCM playback error:', e);
    }
  }

  function playBase64Audio(b64, sampleRate) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    playBinaryAudio(bytes.buffer);
  }

  // --- Text Input Handling ---
  function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text) return;
    textInput.value = '';
    appendBubble(text, 'user');
    setStatus('THINKING...', 'pending');

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'text', text: text }));
    } else {
      // Fallback to HTTP POST /turn
      fetch(`${apiBase}/turn`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Mobile-Session': sessionToken || '',
        },
        body: JSON.stringify({ text: text }),
      })
        .then((res) => res.json())
        .then((data) => {
          appendBubble(data.reply || data.text || 'No response', 'alex');
          setStatus('READY', 'ready');
          if (data.audio_base64) {
            playBase64Audio(data.audio_base64, data.sample_rate || 24000);
          }
        })
        .catch((err) => {
          appendBubble(`Failed to send message: ${err.message}`, 'alex');
          setStatus('ERROR', 'error');
        });
    }
  }

  // Event Listeners
  micBtn.addEventListener('click', () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  sendBtn.addEventListener('click', sendTextMessage);
  textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendTextMessage();
  });

  function resolveApprovalUI(approved) {
    if (!currentApprovalRequestId) return;
    const reqId = currentApprovalRequestId;
    approvalModal.style.display = 'none';
    currentApprovalRequestId = null;
    setStatus('READY', 'ready');

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'action_approval',
        request_id: reqId,
        approved: approved,
      }));
    } else {
      fetch(`${apiBase}/approvals/${reqId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Mobile-Session': sessionToken || '',
        },
        body: JSON.stringify({ approved: approved }),
      }).catch((e) => console.error('Approval submission failed:', e));
    }
    appendBubble(`Action ${approved ? 'Authorized ✅' : 'Denied ❌'}`, 'user');
  }

  if (approvalApproveBtn) {
    approvalApproveBtn.addEventListener('click', () => resolveApprovalUI(true));
  }
  if (approvalDenyBtn) {
    approvalDenyBtn.addEventListener('click', () => resolveApprovalUI(false));
  }

  // Start initialization
  ensurePaired();
})();

