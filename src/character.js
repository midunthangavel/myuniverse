/**
 * Character Engine — Realtime Procedural Canvas Character System
 * Supports: Nova (Holo-AI), Pixel (CyberBot), Astra (Quantum Orb)
 * States: IDLE, LISTENING, THINKING, SEARCHING, WORKING, SPEAKING, WAITING_CONFIRM, SUCCESS, ERROR
 */

export class CharacterEngine {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    
    this.avatarType = 'nova'; // 'nova' | 'pixel' | 'astra'
    this.currentState = 'IDLE';
    this.targetState = 'IDLE';
    
    // Animation timing & state
    this.time = 0;
    this.blinkTimer = 0;
    this.isBlinking = false;
    this.mouthOpen = 0;
    this.headTilt = 0;
    
    // Mouse tracking for gaze
    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    
    // State aura colors
    this.stateColors = {
      IDLE: { primary: '#38bdf8', secondary: '#0284c7', aura: 'rgba(56, 189, 248, 0.25)' },
      LISTENING: { primary: '#10b981', secondary: '#059669', aura: 'rgba(16, 185, 129, 0.35)' },
      THINKING: { primary: '#a855f7', secondary: '#7c3aed', aura: 'rgba(168, 85, 247, 0.35)' },
      SEARCHING: { primary: '#3b82f6', secondary: '#1d4ed8', aura: 'rgba(59, 130, 246, 0.35)' },
      WORKING: { primary: '#f59e0b', secondary: '#d97706', aura: 'rgba(245, 158, 11, 0.35)' },
      SPEAKING: { primary: '#06b6d4', secondary: '#0891b2', aura: 'rgba(6, 182, 212, 0.4)' },
      WAITING_CONFIRM: { primary: '#f59e0b', secondary: '#b45309', aura: 'rgba(245, 158, 11, 0.45)' },
      SUCCESS: { primary: '#22c55e', secondary: '#15803d', aura: 'rgba(34, 197, 94, 0.45)' },
      ERROR: { primary: '#ef4444', secondary: '#b91c1c', aura: 'rgba(239, 68, 68, 0.4)' },
    };

    this.particles = [];
    this.initParticles();
    this.bindEvents();
    this.startLoop();
  }

  bindEvents() {
    window.addEventListener('mousemove', (e) => {
      if (!this.canvas) return;
      const rect = this.canvas.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      
      const dx = (e.clientX - centerX) / (window.innerWidth / 2);
      const dy = (e.clientY - centerY) / (window.innerHeight / 2);
      
      this.mouse.targetX = Math.max(-1, Math.min(1, dx));
      this.mouse.targetY = Math.max(-1, Math.min(1, dy));
    });
  }

  initParticles() {
    this.particles = [];
    for (let i = 0; i < 18; i++) {
      this.particles.push({
        angle: Math.random() * Math.PI * 2,
        radius: 45 + Math.random() * 30,
        speed: 0.015 + Math.random() * 0.025,
        size: 1.5 + Math.random() * 2,
        opacity: 0.3 + Math.random() * 0.7
      });
    }
  }

  setState(newState, speechText = null) {
    if (!this.stateColors[newState]) return;
    this.currentState = newState;
    
    // Update aura ring in DOM
    const aura = document.getElementById('character-aura');
    if (aura) {
      aura.style.background = `radial-gradient(circle, ${this.stateColors[newState].aura} 0%, transparent 70%)`;
    }

    // Update state pill text & badge
    const stateNameEl = document.getElementById('character-state-name');
    const stateIconEl = document.getElementById('state-icon');
    if (stateNameEl) stateNameEl.textContent = newState.replace('_', ' ');
    if (stateIconEl) {
      stateIconEl.style.color = this.stateColors[newState].primary;
    }

    // Update speech bubble if provided
    if (speechText) {
      this.setSpeech(speechText);
    }
  }

  setSpeech(text) {
    const speechEl = document.getElementById('character-speech-text');
    if (speechEl) {
      speechEl.textContent = text;
    }
  }

  setAvatar(avatarType) {
    this.avatarType = avatarType;
  }

  startLoop() {
    const render = () => {
      this.update();
      this.draw();
      requestAnimationFrame(render);
    };
    requestAnimationFrame(render);
  }

  update() {
    this.time += 0.04;
    
    // Smooth mouse follow
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.1;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.1;

    // Blinking logic
    this.blinkTimer += 1;
    if (this.blinkTimer > 180 + Math.random() * 100) {
      this.isBlinking = true;
      if (this.blinkTimer > 195 + Math.random() * 100) {
        this.isBlinking = false;
        this.blinkTimer = 0;
      }
    }

    // Speaking mouth modulation
    if (this.currentState === 'SPEAKING') {
      this.mouthOpen = (Math.sin(this.time * 6) + 1) * 0.5;
    } else {
      this.mouthOpen *= 0.8;
    }

    // Thinking head tilt
    if (this.currentState === 'THINKING') {
      this.headTilt = Math.sin(this.time * 1.5) * 0.08 + 0.06;
    } else {
      this.headTilt *= 0.85;
    }
  }

  draw() {
    const { ctx, canvas } = this;
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    ctx.save();
    ctx.translate(width / 2, height / 2);

    if (this.avatarType === 'nova') {
      this.drawNova(ctx);
    } else if (this.avatarType === 'pixel') {
      this.drawPixel(ctx);
    } else if (this.avatarType === 'astra') {
      this.drawAstra(ctx);
    }

    ctx.restore();
  }

  // ==========================================
  // AVATAR 1: NOVA (Holographic AI Companion)
  // ==========================================
  drawNova(ctx) {
    const color = this.stateColors[this.currentState];
    const breath = Math.sin(this.time * 1.5) * 3;

    // Orbiting Synaptic Energy Particles
    this.particles.forEach((p) => {
      p.angle += p.speed * (this.currentState === 'THINKING' ? 3 : 1);
      const px = Math.cos(p.angle) * p.radius;
      const py = Math.sin(p.angle) * (p.radius * 0.6) + breath * 0.5;
      
      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fillStyle = color.primary;
      ctx.globalAlpha = p.opacity;
      ctx.shadowBlur = 8;
      ctx.shadowColor = color.primary;
      ctx.fill();
    });

    ctx.globalAlpha = 1.0;
    ctx.shadowBlur = 0;

    // Head base with subtle tilt and hover
    ctx.save();
    ctx.rotate(this.headTilt);
    ctx.translate(0, breath);

    // Outer Holographic Halo
    ctx.beginPath();
    ctx.arc(0, 0, 48, 0, Math.PI * 2);
    ctx.strokeStyle = color.primary;
    ctx.lineWidth = 1.8;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Head Pod Body (Glassy Cyber Sphere)
    const grad = ctx.createRadialGradient(-10, -15, 5, 0, 0, 42);
    grad.addColorStop(0, '#1e293b');
    grad.addColorStop(0.7, '#0f172a');
    grad.addColorStop(1, '#020617');

    ctx.beginPath();
    ctx.arc(0, 0, 40, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = color.primary;
    ctx.lineWidth = 2.2;
    ctx.shadowBlur = 14;
    ctx.shadowColor = color.primary;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Cyber Visor / Face Plate
    const visorGrad = ctx.createLinearGradient(0, -18, 0, 18);
    visorGrad.addColorStop(0, 'rgba(15, 23, 42, 0.95)');
    visorGrad.addColorStop(1, 'rgba(2, 6, 23, 0.98)');

    ctx.beginPath();
    ctx.roundRect(-28, -14, 56, 32, 12);
    ctx.fillStyle = visorGrad;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Expressive Holographic Eyes
    const eyeOffsetX = 12;
    const eyeOffsetY = -2;
    const gazeX = this.mouse.x * 3.5;
    const gazeY = this.mouse.y * 3.5;

    if (!this.isBlinking) {
      [-eyeOffsetX, eyeOffsetX].forEach((baseX) => {
        const ex = baseX + gazeX;
        const ey = eyeOffsetY + gazeY;

        ctx.beginPath();
        if (this.currentState === 'SUCCESS') {
          // Happy arch eye
          ctx.arc(ex, ey + 1, 4.5, Math.PI, 0, false);
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = color.primary;
          ctx.shadowBlur = 10;
          ctx.shadowColor = color.primary;
          ctx.stroke();
          ctx.shadowBlur = 0;
        } else if (this.currentState === 'WAITING_CONFIRM') {
          // Inquisitive wide eye
          ctx.arc(ex, ey, 4.5, 0, Math.PI * 2);
          ctx.fillStyle = color.primary;
          ctx.shadowBlur = 12;
          ctx.shadowColor = color.primary;
          ctx.fill();
          ctx.shadowBlur = 0;
        } else {
          // Normal oval eye
          ctx.ellipse(ex, ey, 4.2, 5.5, 0, 0, Math.PI * 2);
          ctx.fillStyle = color.primary;
          ctx.shadowBlur = 10;
          ctx.shadowColor = color.primary;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Pupil glint
          ctx.beginPath();
          ctx.arc(ex - 1.5, ey - 2, 1.2, 0, Math.PI * 2);
          ctx.fillStyle = '#fff';
          ctx.fill();
        }
      });
    } else {
      // Blinking slit
      [-eyeOffsetX, eyeOffsetX].forEach((baseX) => {
        ctx.beginPath();
        ctx.moveTo(baseX - 4, eyeOffsetY);
        ctx.lineTo(baseX + 4, eyeOffsetY);
        ctx.lineWidth = 2;
        ctx.strokeStyle = color.primary;
        ctx.stroke();
      });
    }

    // Mouth / Waveform
    const my = 8 + gazeY * 0.4;
    ctx.beginPath();
    if (this.currentState === 'SPEAKING') {
      const mh = Math.max(2, this.mouthOpen * 7);
      ctx.ellipse(0, my, 6, mh, 0, 0, Math.PI * 2);
      ctx.fillStyle = color.primary;
      ctx.fill();
    } else if (this.currentState === 'SUCCESS') {
      ctx.arc(0, my - 2, 7, 0.1 * Math.PI, 0.9 * Math.PI, false);
      ctx.lineWidth = 2;
      ctx.strokeStyle = color.primary;
      ctx.stroke();
    } else {
      // Gentle calm smile
      ctx.moveTo(-5, my);
      ctx.quadraticCurveTo(0, my + 3, 5, my);
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = color.primary;
      ctx.stroke();
    }

    // Floating Ear Pods
    [-46, 46].forEach((ex, idx) => {
      const earOffset = idx === 0 ? -1 : 1;
      const earY = Math.sin(this.time * 2 + idx) * 2;
      ctx.beginPath();
      ctx.arc(ex, earY, 6, 0, Math.PI * 2);
      ctx.fillStyle = '#1e293b';
      ctx.fill();
      ctx.strokeStyle = color.primary;
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // Soundwave pulse if listening
      if (this.currentState === 'LISTENING') {
        ctx.beginPath();
        ctx.arc(ex + earOffset * 6, earY, 8 + (this.time % 2) * 5, -Math.PI / 2, Math.PI / 2, idx === 0);
        ctx.strokeStyle = color.primary;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });

    ctx.restore();
  }

  // ==========================================
  // AVATAR 2: PIXEL (Playful CyberBot)
  // ==========================================
  drawPixel(ctx) {
    const color = this.stateColors[this.currentState];
    const breath = Math.sin(this.time * 2) * 2.5;

    ctx.save();
    ctx.rotate(this.headTilt);
    ctx.translate(0, breath);

    // Antenna
    ctx.beginPath();
    ctx.moveTo(0, -38);
    ctx.lineTo(0, -56);
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#475569';
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(0, -60, 6, 0, Math.PI * 2);
    ctx.fillStyle = color.primary;
    ctx.shadowBlur = 12;
    ctx.shadowColor = color.primary;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Robot Head Chassis (Squircle)
    ctx.beginPath();
    ctx.roundRect(-42, -38, 84, 76, 18);
    ctx.fillStyle = '#1e2430';
    ctx.fill();
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Dark OLED Screen
    ctx.beginPath();
    ctx.roundRect(-34, -28, 68, 54, 12);
    ctx.fillStyle = '#0a0d14';
    ctx.fill();
    ctx.strokeStyle = color.primary;
    ctx.lineWidth = 1.5;
    ctx.shadowBlur = 8;
    ctx.shadowColor = color.primary;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Pixel Eyes
    const gazeX = this.mouse.x * 4;
    const gazeY = this.mouse.y * 3;

    if (!this.isBlinking) {
      [-14, 14].forEach((bx) => {
        const ex = bx + gazeX;
        const ey = -4 + gazeY;

        ctx.fillStyle = color.primary;
        ctx.shadowBlur = 10;
        ctx.shadowColor = color.primary;

        if (this.currentState === 'WAITING_CONFIRM') {
          // Question mark eye / alert
          ctx.fillRect(ex - 4, ey - 5, 8, 3);
          ctx.fillRect(ex, ey - 2, 4, 6);
          ctx.fillRect(ex, ey + 6, 4, 3);
        } else if (this.currentState === 'SUCCESS') {
          // ^ ^ happy eyes
          ctx.beginPath();
          ctx.moveTo(ex - 5, ey + 2);
          ctx.lineTo(ex, ey - 4);
          ctx.lineTo(ex + 5, ey + 2);
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = color.primary;
          ctx.stroke();
        } else {
          // Digital pixel block eye
          ctx.fillRect(ex - 5, ey - 5, 10, 10);
        }
        ctx.shadowBlur = 0;
      });
    }

    // Mouth
    ctx.fillStyle = color.primary;
    const my = 12;
    if (this.currentState === 'SPEAKING') {
      const mh = Math.max(3, this.mouthOpen * 8);
      ctx.fillRect(-8, my - mh / 2, 16, mh);
    } else {
      ctx.fillRect(-10, my, 20, 3);
    }

    ctx.restore();
  }

  // ==========================================
  // AVATAR 3: ASTRA (Quantum Bioluminescent Orb)
  // ==========================================
  drawAstra(ctx) {
    const color = this.stateColors[this.currentState];
    const spin = this.time * (this.currentState === 'WORKING' ? 4 : 1.5);
    const pulse = Math.sin(this.time * 2.5) * 4;

    ctx.save();

    // Quantum Ring 1
    ctx.save();
    ctx.rotate(spin * 0.5);
    ctx.beginPath();
    ctx.ellipse(0, 0, 52, 22, Math.PI / 4, 0, Math.PI * 2);
    ctx.strokeStyle = color.primary;
    ctx.lineWidth = 1.8;
    ctx.stroke();
    ctx.restore();

    // Quantum Ring 2
    ctx.save();
    ctx.rotate(-spin * 0.7);
    ctx.beginPath();
    ctx.ellipse(0, 0, 52, 22, -Math.PI / 4, 0, Math.PI * 2);
    ctx.strokeStyle = color.secondary;
    ctx.lineWidth = 1.8;
    ctx.stroke();
    ctx.restore();

    // Central Plasma Core
    const grad = ctx.createRadialGradient(0, 0, 2, 0, 0, 34 + pulse);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.3, color.primary);
    grad.addColorStop(0.8, color.secondary);
    grad.addColorStop(1, 'transparent');

    ctx.beginPath();
    ctx.arc(0, 0, 34 + pulse, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.shadowBlur = 24;
    ctx.shadowColor = color.primary;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Core Eye / Consciousness Lens
    const gx = this.mouse.x * 6;
    const gy = this.mouse.y * 5;
    ctx.beginPath();
    ctx.arc(gx, gy, 8, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.shadowBlur = 14;
    ctx.shadowColor = '#fff';
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.restore();
  }
}
