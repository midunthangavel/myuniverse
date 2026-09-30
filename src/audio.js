/**
 * Audio Engine — Speech Recognition, Server-Side Neural TTS, and Audio Visualizer
 */

export class AudioEngine {
  constructor() {
    this.voiceEnabled = true;
    this.recognition = null;
    this.isListening = false;
    this.synth = window.speechSynthesis || null;
    this.currentAudio = null;
    this.visualizerCanvas = document.getElementById('audio-visualizer-canvas');
    this.vCtx = this.visualizerCanvas ? this.visualizerCanvas.getContext('2d') : null;
    this.visualizerAnimId = null;

    this.initSpeechRecognition();
  }

  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-US';
    }
  }

  toggleVoice() {
    this.voiceEnabled = !this.voiceEnabled;
    const btn = document.getElementById('btn-voice-toggle');
    const label = document.getElementById('voice-label');
    if (btn && label) {
      if (this.voiceEnabled) {
        btn.classList.add('active');
        label.textContent = 'Voice ON';
      } else {
        btn.classList.remove('active');
        label.textContent = 'Voice MUTED';
        if (this.currentAudio) {
          this.currentAudio.pause();
          this.currentAudio = null;
        }
        if (this.synth) this.synth.cancel();
      }
    }
    return this.voiceEnabled;
  }

  playNeuralVoice(audioDataUri, fallbackText, onStart, onEnd) {
    if (!this.voiceEnabled) {
      if (onStart) onStart();
      setTimeout(() => { if (onEnd) onEnd(); }, 1500);
      return;
    }

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }

    if (audioDataUri) {
      const audio = new Audio(audioDataUri);
      this.currentAudio = audio;

      audio.onplay = () => {
        this.startVisualizer();
        if (onStart) onStart();
      };

      audio.onended = () => {
        this.stopVisualizer();
        this.currentAudio = null;
        if (onEnd) onEnd();
      };

      audio.onerror = () => {
        this.stopVisualizer();
        this.currentAudio = null;
        // Fallback to browser TTS if audio playback fails
        if (fallbackText) this.speak(fallbackText, onStart, onEnd);
        else if (onEnd) onEnd();
      };

      audio.play().catch(() => {
        // Autoplay policy or error, fallback to speak
        if (fallbackText) this.speak(fallbackText, onStart, onEnd);
      });
      return;
    }

    // Fallback if no audio URI
    if (fallbackText) {
      this.speak(fallbackText, onStart, onEnd);
    }
  }

  speak(text, onStart, onEnd) {
    if (!this.voiceEnabled || !this.synth) {
      if (onStart) onStart();
      setTimeout(() => { if (onEnd) onEnd(); }, 2000);
      return;
    }

    this.synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    const voices = this.synth.getVoices();
    const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => {
      this.startVisualizer();
      if (onStart) onStart();
    };

    utterance.onend = () => {
      this.stopVisualizer();
      if (onEnd) onEnd();
    };

    utterance.onerror = () => {
      this.stopVisualizer();
      if (onEnd) onEnd();
    };

    this.synth.speak(utterance);
  }

  startListening(onResult, onStateChange) {
    if (!this.recognition) {
      alert('Speech Recognition is not supported in this browser. You can type instructions in the input box below!');
      return;
    }

    if (this.isListening) {
      this.recognition.stop();
      this.isListening = false;
      if (onStateChange) onStateChange(false);
      this.stopVisualizer();
      return;
    }

    this.isListening = true;
    if (onStateChange) onStateChange(true);
    this.startVisualizer();

    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this.isListening = false;
      if (onStateChange) onStateChange(false);
      this.stopVisualizer();
      if (onResult) onResult(transcript);
    };

    this.recognition.onerror = (e) => {
      this.isListening = false;
      if (onStateChange) onStateChange(false);
      this.stopVisualizer();
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (onStateChange) onStateChange(false);
      this.stopVisualizer();
    };

    try {
      this.recognition.start();
    } catch (e) {
      console.warn('Recognition start exception:', e);
    }
  }

  startVisualizer() {
    if (!this.visualizerCanvas || !this.vCtx) return;
    this.visualizerCanvas.classList.remove('hidden');

    let wavePhase = 0;
    const renderWave = () => {
      wavePhase += 0.15;
      const { width, height } = this.visualizerCanvas;
      this.vCtx.clearRect(0, 0, width, height);

      this.vCtx.beginPath();
      this.vCtx.strokeStyle = '#38bdf8';
      this.vCtx.lineWidth = 2;

      const numPoints = 30;
      for (let i = 0; i <= numPoints; i++) {
        const x = (i / numPoints) * width;
        const amplitude = Math.sin(wavePhase + i * 0.4) * (height / 3);
        const y = height / 2 + amplitude;
        if (i === 0) this.vCtx.moveTo(x, y);
        else this.vCtx.lineTo(x, y);
      }
      this.vCtx.stroke();

      this.visualizerAnimId = requestAnimationFrame(renderWave);
    };

    renderWave();
  }

  stopVisualizer() {
    if (this.visualizerAnimId) {
      cancelAnimationFrame(this.visualizerAnimId);
      this.visualizerAnimId = null;
    }
    if (this.visualizerCanvas) {
      this.visualizerCanvas.classList.add('hidden');
    }
  }
}
