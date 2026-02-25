/**
 * Mana — AI Voice Bot Frontend
 * Handles: Onboarding, Chat UI, Voice Recording, Waveform, Session Management
 */

// ═══════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════

const state = {
    sessionId: null,
    language: 'en',
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    audioContext: null,
    analyser: null,
    animationId: null,
    isProcessing: false,
};

// ═══════════════════════════════════════════════════════════
// DOM References
// ═══════════════════════════════════════════════════════════

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Screens
    onboarding: $('#onboarding-screen'),
    chat: $('#chat-screen'),

    // Onboarding
    consentCheckbox: $('#consent-checkbox'),
    startBtn: $('#start-btn'),
    langBtns: $$('.lang-btn'),

    // Chat
    messagesContainer: $('#messages-container'),
    messagesInner: $('#messages-inner'),
    textInput: $('#text-input'),
    sendBtn: $('#send-btn'),
    micBtn: $('#mic-btn'),
    statusText: $('#status-text'),
    emotionIcon: $('#emotion-icon'),
    emotionLabel: $('#emotion-label'),
    emotionBadge: $('#emotion-badge'),
    langBadge: $('#lang-badge'),
    waveformContainer: $('#waveform-container'),
    waveformCanvas: $('#waveform-canvas'),
    endSessionBtn: $('#end-session-btn'),
    crisisHelpBtn: $('#crisis-help-btn'),

    // Modal
    crisisModal: $('#crisis-modal'),
    crisisModalClose: $('#crisis-modal-close'),
};

// ═══════════════════════════════════════════════════════════
// Emotion Map
// ═══════════════════════════════════════════════════════════

const emotionMap = {
    neutral: { icon: '😊', label: 'Neutral', color: '#94A3B8' },
    anxious: { icon: '😰', label: 'Anxious', color: '#FCD34D' },
    sad: { icon: '😢', label: 'Sad', color: '#7DD3FC' },
    angry: { icon: '😤', label: 'Angry', color: '#FB7185' },
    frustrated: { icon: '😩', label: 'Frustrated', color: '#F9A8D4' },
    positive: { icon: '😌', label: 'Positive', color: '#86EFAC' },
    crisis: { icon: '🆘', label: 'Crisis', color: '#FB7185' },
};

// ═══════════════════════════════════════════════════════════
// Onboarding Logic
// ═══════════════════════════════════════════════════════════

function initOnboarding() {
    // Consent checkbox
    dom.consentCheckbox.addEventListener('change', () => {
        dom.startBtn.disabled = !dom.consentCheckbox.checked;
    });

    // Language selection
    dom.langBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
            dom.langBtns.forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            state.language = btn.dataset.lang;
        });
    });

    // Start button
    dom.startBtn.addEventListener('click', startSession);
}

async function startSession() {
    // Create session
    try {
        const res = await fetch('/session/create', { method: 'POST' });
        const data = await res.json();
        state.sessionId = data.session_id;
    } catch (e) {
        // Fallback: generate client-side ID
        state.sessionId = crypto.randomUUID();
    }

    // Transition screens
    dom.onboarding.classList.remove('active');
    setTimeout(() => {
        dom.chat.classList.add('active');
        updateLangBadge();
        addBotOpening();
    }, 300);
}

function addBotOpening() {
    const openings = {
        en: "Hi there! I'm Mana — your friendly companion for a moment of calm. I'm here to listen, not judge. Is it okay if we talk for a bit?",
        hi: "Namaste! Main Mana hoon — aapki baat sunne ke liye yahan hoon. Koi judgment nahi, bas sunna. Kya hum thodi der baat kar sakte hain?",
        'hi-en': "Hey! Main Mana hoon. I'm here to listen — koi judgment nahi. Kya aap thoda share karna chahenge?",
    };

    addMessage('assistant', openings[state.language] || openings.en);
}

// ═══════════════════════════════════════════════════════════
// Chat Logic
// ═══════════════════════════════════════════════════════════

function initChat() {
    // Text send
    dom.sendBtn.addEventListener('click', sendTextMessage);
    dom.textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendTextMessage();
        }
    });

    // Mic button
    dom.micBtn.addEventListener('click', toggleRecording);

    // End session
    dom.endSessionBtn.addEventListener('click', endSession);

    // Crisis modal
    dom.crisisHelpBtn.addEventListener('click', () => {
        dom.crisisModal.classList.add('active');
    });
    dom.crisisModalClose.addEventListener('click', () => {
        dom.crisisModal.classList.remove('active');
    });
    dom.crisisModal.addEventListener('click', (e) => {
        if (e.target === dom.crisisModal) {
            dom.crisisModal.classList.remove('active');
        }
    });
}

async function sendTextMessage() {
    const text = dom.textInput.value.trim();
    if (!text || state.isProcessing) return;

    dom.textInput.value = '';
    addMessage('user', text);
    await processUserMessage(text);
}

async function processUserMessage(text) {
    state.isProcessing = true;
    setStatus('Thinking...');
    showTypingIndicator();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: state.sessionId,
                language: state.language,
            }),
        });

        const data = await res.json();
        removeTypingIndicator();

        // Update emotion display
        updateEmotion(data.emotion);

        // Update language if server detected different
        if (data.language && data.language !== state.language) {
            state.language = data.language;
            updateLangBadge();
        }

        // Handle crisis
        if (data.is_crisis) {
            addMessage('assistant', data.response, true);
            dom.crisisModal.classList.add('active');
        } else {
            addMessage('assistant', data.response);
        }

        // Optional: play TTS
        if (data.response) {
            playTTS(data.response, data.language || state.language);
        }

    } catch (e) {
        removeTypingIndicator();
        addMessage('assistant', "I'm sorry, I'm having trouble connecting right now. Please try again in a moment.");
        console.error('[Chat] Error:', e);
    }

    state.isProcessing = false;
    setStatus('Listening...');
}

// ═══════════════════════════════════════════════════════════
// Message Rendering
// ═══════════════════════════════════════════════════════════

function addMessage(role, content, isCrisis = false) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const avatarContent = role === 'user' ? '👤' : '🧠';

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}${isCrisis ? ' crisis' : ''}`;
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarContent}</div>
        <div>
            <div class="message-bubble">${escapeHtml(content)}</div>
            <span class="message-time">${timeStr}</span>
        </div>
    `;

    dom.messagesInner.appendChild(messageDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'message assistant';
    typing.id = 'typing-indicator';
    typing.innerHTML = `
        <div class="message-avatar">🧠</div>
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    dom.messagesInner.appendChild(typing);
    scrollToBottom();
}

function removeTypingIndicator() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        dom.messagesContainer.scrollTop = dom.messagesContainer.scrollHeight;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════
// Voice Recording
// ═══════════════════════════════════════════════════════════

async function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Set up audio context for waveform
        state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = state.audioContext.createMediaStreamSource(stream);
        state.analyser = state.audioContext.createAnalyser();
        state.analyser.fftSize = 256;
        source.connect(state.analyser);

        // Set up recorder
        state.mediaRecorder = new MediaRecorder(stream, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm',
        });

        state.audioChunks = [];
        state.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) state.audioChunks.push(e.data);
        };

        state.mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
            await processAudio(audioBlob);
            stream.getTracks().forEach((t) => t.stop());
        };

        state.mediaRecorder.start(100);
        state.isRecording = true;
        dom.micBtn.classList.add('recording');
        dom.waveformContainer.classList.add('active');
        setStatus('Recording...');

        // Start waveform animation
        drawWaveform();

    } catch (e) {
        console.error('[Recording] Error:', e);
        alert('Microphone access is needed for voice input. Please allow microphone access.');
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
        state.mediaRecorder.stop();
    }

    state.isRecording = false;
    dom.micBtn.classList.remove('recording');
    dom.waveformContainer.classList.remove('active');
    setStatus('Processing...');

    if (state.animationId) {
        cancelAnimationFrame(state.animationId);
        state.animationId = null;
    }

    if (state.audioContext) {
        state.audioContext.close();
        state.audioContext = null;
    }
}

async function processAudio(audioBlob) {
    state.isProcessing = true;
    showTypingIndicator();

    try {
        // Send audio for STT
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        formData.append('language', state.language);

        const sttRes = await fetch('/stt', {
            method: 'POST',
            body: formData,
        });

        const sttData = await sttRes.json();
        removeTypingIndicator();

        if (sttData.transcript) {
            addMessage('user', sttData.transcript);

            // Update language based on STT detection
            if (sttData.language) {
                state.language = sttData.language;
                updateLangBadge();
            }

            await processUserMessage(sttData.transcript);
        } else {
            addMessage('assistant', "I couldn't quite catch that. Could you try again?");
            state.isProcessing = false;
            setStatus('Listening...');
        }

    } catch (e) {
        removeTypingIndicator();
        addMessage('assistant', "I'm having trouble hearing right now. Try typing instead.");
        console.error('[STT] Error:', e);
        state.isProcessing = false;
        setStatus('Listening...');
    }
}

// ═══════════════════════════════════════════════════════════
// TTS Playback
// ═══════════════════════════════════════════════════════════

async function playTTS(text, language) {
    try {
        const res = await fetch('/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, language }),
        });

        if (res.ok) {
            const audioBlob = await res.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            setStatus('Speaking...');
            audio.addEventListener('ended', () => {
                setStatus('Listening...');
                URL.revokeObjectURL(audioUrl);
            });

            audio.play().catch((e) => {
                console.warn('[TTS] Autoplay blocked:', e);
                setStatus('Listening...');
            });
        }
    } catch (e) {
        console.error('[TTS] Playback error:', e);
    }
}

// ═══════════════════════════════════════════════════════════
// Waveform Visualization
// ═══════════════════════════════════════════════════════════

function drawWaveform() {
    if (!state.analyser || !state.isRecording) return;

    const canvas = dom.waveformCanvas;
    const ctx = canvas.getContext('2d');
    const bufferLength = state.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    // Set canvas size
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);

    function draw() {
        if (!state.isRecording) return;
        state.animationId = requestAnimationFrame(draw);

        state.analyser.getByteFrequencyData(dataArray);

        const width = canvas.offsetWidth;
        const height = canvas.offsetHeight;

        ctx.clearRect(0, 0, width, height);

        const barCount = 60;
        const barWidth = (width / barCount) * 0.6;
        const gap = (width / barCount) * 0.4;
        const centerY = height / 2;

        for (let i = 0; i < barCount; i++) {
            const dataIndex = Math.floor((i / barCount) * bufferLength);
            const value = dataArray[dataIndex] / 255;
            const barHeight = Math.max(2, value * centerY * 0.9);

            const x = i * (barWidth + gap);

            // Gradient color from purple to blue
            const ratio = i / barCount;
            const r = Math.floor(167 * (1 - ratio) + 125 * ratio);
            const g = Math.floor(139 * (1 - ratio) + 211 * ratio);
            const b = Math.floor(250 * (1 - ratio) + 252 * ratio);

            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.4 + value * 0.6})`;
            ctx.beginPath();
            ctx.roundRect(x, centerY - barHeight, barWidth, barHeight * 2, barWidth / 2);
            ctx.fill();
        }
    }

    draw();
}

// ═══════════════════════════════════════════════════════════
// UI Updates
// ═══════════════════════════════════════════════════════════

function setStatus(text) {
    dom.statusText.textContent = text;
}

function updateEmotion(emotion) {
    const data = emotionMap[emotion] || emotionMap.neutral;
    dom.emotionIcon.textContent = data.icon;
    dom.emotionLabel.textContent = data.label;
    dom.emotionBadge.style.borderColor = `${data.color}40`;
    dom.emotionBadge.style.background = `${data.color}15`;
}

function updateLangBadge() {
    const labels = { en: 'EN', hi: 'HI', 'hi-en': 'HI-EN' };
    dom.langBadge.textContent = labels[state.language] || 'EN';
}

async function endSession() {
    if (!state.sessionId) return;

    try {
        await fetch(`/session/${state.sessionId}/close`, { method: 'POST' });
    } catch (e) {
        console.error('[Session] Close error:', e);
    }

    // Add farewell
    const farewells = {
        en: "Take care of yourself. Remember, I'm here whenever you need a moment of calm. 💙",
        hi: "Apna khayal rakhein. Jab chahein, main yahan hoon. 💙",
        'hi-en': "Take care! Jab bhi mann kare, main yahan hoon. 💙",
    };
    addMessage('assistant', farewells[state.language] || farewells.en);

    // Reset after delay
    setTimeout(() => {
        dom.chat.classList.remove('active');
        dom.messagesInner.innerHTML = '';
        state.sessionId = null;
        dom.consentCheckbox.checked = false;
        dom.startBtn.disabled = true;
        setTimeout(() => dom.onboarding.classList.add('active'), 300);
    }, 3000);
}

// ═══════════════════════════════════════════════════════════
// Initialize
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initOnboarding();
    initChat();
});
