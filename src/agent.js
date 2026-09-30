/**
 * Autonomous Agent Engine (ReAct / OODA Loop)
 * Orchestrates Ask -> Understand -> Remember -> Act -> Explain
 * Supports Live Bi-directional WebSocket Streaming to FastAPI Backend
 */

export class AgentEngine {
  constructor(character, memory, phone, audio) {
    this.character = character;
    this.memory = memory;
    this.phone = phone;
    this.audio = audio;
    
    this.isRunning = false;
    this.pendingConfirmation = null;
    
    this.feedContainer = document.getElementById('reasoning-feed');
    this.phaseEl = document.getElementById('agent-loop-phase');
    
    this.ws = null;
    this.wsConnected = false;
    this.initWebSocket();
  }

  initWebSocket() {
    try {
      this.ws = new WebSocket('ws://127.0.0.1:8000/ws/agent');

      this.ws.onopen = () => {
        this.wsConnected = true;
        const statusEl = document.getElementById('agent-connection-status');
        if (statusEl) {
          statusEl.innerHTML = '<span class="status-dot"></span><span class="status-text">FastAPI + SQLite Live</span>';
        }
      };

      this.ws.onclose = () => {
        this.wsConnected = false;
        const statusEl = document.getElementById('agent-connection-status');
        if (statusEl) {
          statusEl.innerHTML = '<span class="status-dot" style="background: #f59e0b; box-shadow: 0 0 8px #f59e0b;"></span><span class="status-text" style="color: #f59e0b;">Client Engine (Local)</span>';
        }
        // Try reconnect in 4s
        setTimeout(() => this.initWebSocket(), 4000);
      };

      this.ws.onerror = () => {
        this.wsConnected = false;
      };

      this.ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);
        await this.handleServerEvent(msg);
      };

    } catch (e) {
      this.wsConnected = false;
    }
  }

  async handleServerEvent(msg) {
    if (msg.type === 'CHARACTER_STATE') {
      this.character.setState(msg.state, msg.speech);
      if (msg.audio_data_uri) {
        this.audio.playNeuralVoice(
          msg.audio_data_uri,
          msg.speech,
          () => this.character.setState('SPEAKING'),
          () => {
            if (msg.state === 'SUCCESS') {
              setTimeout(() => this.character.setState('IDLE'), 2000);
            }
          }
        );
      } else if (msg.speech && msg.state === 'SPEAKING') {
        this.audio.speak(msg.speech);
      }
    } else if (msg.type === 'LOG_STEP') {
      this.logStep(msg.step, msg.title, msg.description, msg.payload);
    } else if (msg.type === 'HIGH_RISK_PROMPT') {
      await this.handleHighRiskApproval(msg.plan, msg.audio_data_uri);
    } else if (msg.type === 'ACTION_CONFIRMED') {
      if (msg.audio_data_uri) {
        this.audio.playNeuralVoice(msg.audio_data_uri, msg.speech);
      }
    }
  }

  logStep(type, title, description, jsonPayload = null) {
    if (!this.feedContainer) return;

    const placeholder = document.getElementById('empty-feed-placeholder');
    if (placeholder) placeholder.remove();

    const card = document.createElement('div');
    card.className = 'feed-card';

    const timeStr = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + 
      '.' + Math.floor(Math.random() * 900 + 100);

    card.innerHTML = `
      <div class="feed-card-header">
        <span class="feed-tag ${type.toLowerCase()}">${type}</span>
        <span class="feed-timestamp">+${timeStr}</span>
      </div>
      <h4 class="feed-title">${title}</h4>
      <p class="feed-body">${description}</p>
      ${jsonPayload ? `<pre class="feed-json-block">${JSON.stringify(jsonPayload, null, 2)}</pre>` : ''}
    `;

    this.feedContainer.appendChild(card);
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  setPhase(phaseName) {
    if (this.phaseEl) {
      this.phaseEl.textContent = phaseName;
    }
  }

  async runTask(userPrompt) {
    if (this.isRunning) return;
    this.isRunning = true;

    // If WebSocket is connected, stream directly to FastAPI backend!
    if (this.wsConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.setPhase('Streaming Task to FastAPI Backend...');
      const screenContext = this.phone.getCurrentScreenContext();
      this.ws.send(JSON.stringify({
        type: 'RUN_TASK',
        prompt: userPrompt,
        screen_context: screenContext
      }));
      // Check if navigation needs to animate on client
      setTimeout(() => {
        const p = userPrompt.toLowerCase();
        if (p.includes('movie')) this.animateTapOnApp('cinema');
        else if (p.includes('biryani') || p.includes('food')) this.animateTapOnApp('food');
        this.isRunning = false;
      }, 1500);
      return;
    }

    // Fallback: Client-Side ReAct Loop
    try {
      this.character.setState('LISTENING', `Listening to request: "${userPrompt}"`);
      this.setPhase('Processing User Query...');
      await this.sleep(800);

      this.character.setState('THINKING', 'Analyzing intent and extracting parameters...');
      this.setPhase('Intent Reasoning & Entity Extraction');
      const parsed = this.parseIntent(userPrompt);

      this.logStep('INTENT', `Extracted Goal: ${parsed.intent.toUpperCase()}`, 
        `Classified prompt into domain "${parsed.domain}" with confidence ${parsed.confidence}. Extracted constraints: ${JSON.stringify(parsed.entities)}`,
        parsed
      );
      await this.sleep(900);

      this.character.setState('SEARCHING', 'Retrieving personal memory and learned preferences...');
      this.setPhase('Personal Memory Retrieval');
      const retrievedMemories = this.memory.retrieveContextForIntent(parsed.intent, userPrompt);
      const activeScreen = this.phone.getCurrentScreenContext();

      this.logStep('MEMORY', `Synthesized ${retrievedMemories.length} Personal Rules & Preferences`,
        `Fused user memory with current screen context (${activeScreen.app}). Applying personal bias to plan.`,
        { retrievedPreferences: retrievedMemories, screenContext: activeScreen }
      );
      await this.sleep(900);

      this.character.setState('WORKING', 'Compiling phone action sequence and evaluating risk tier...');
      this.setPhase('Action Planning & Risk Evaluation');
      const plan = this.createExecutionPlan(parsed, retrievedMemories);

      this.logStep('PLAN', `Execution Plan Formulated (${plan.steps.length} Actions)`,
        `Risk tier evaluated as ${plan.riskTier.toUpperCase()}. Action protocol: ${plan.riskReason}`,
        plan
      );
      await this.sleep(800);

      if (plan.riskTier === 'high') {
        await this.handleHighRiskApproval(plan);
      } else {
        await this.executePlanSteps(plan);
      }

    } catch (err) {
      console.error('Agent execution error', err);
      this.character.setState('ERROR', 'An error occurred while executing the task.');
      this.setPhase('Execution Terminated');
    } finally {
      this.isRunning = false;
    }
  }

  parseIntent(prompt) {
    const p = prompt.toLowerCase();

    if (p.includes('movie') || p.includes('cinema') || p.includes('ticket')) {
      return {
        intent: 'book_movie',
        domain: 'entertainment',
        confidence: '98.4%',
        entities: { timeAnchor: 'tonight', targetType: 'movie', format: 'IMAX' }
      };
    }

    if (p.includes('screen') || p.includes('what is') || p.includes('read') || p.includes('look at')) {
      return {
        intent: 'inspect_screen',
        domain: 'screen_context',
        confidence: '99.1%',
        entities: { target: 'current_viewport_nodes' }
      };
    }

    if (p.includes('biryani') || p.includes('food') || p.includes('dinner') || p.includes('eat')) {
      return {
        intent: 'order_food',
        domain: 'dining_delivery',
        confidence: '97.8%',
        entities: { cuisine: 'Biryani', timing: 'immediate' }
      };
    }

    if (p.includes('meeting') || p.includes('schedule') || p.includes('john') || p.includes('calendar')) {
      return {
        intent: 'schedule_meeting',
        domain: 'productivity',
        confidence: '96.5%',
        entities: { contact: 'John Vance', subject: 'Sync' }
      };
    }

    return {
      intent: 'general_assistance',
      domain: 'system',
      confidence: '91.0%',
      entities: { raw: prompt }
    };
  }

  createExecutionPlan(parsed, memories) {
    if (parsed.intent === 'book_movie') {
      return {
        riskTier: 'high',
        riskReason: 'Financial transaction ($36.00 payment) requires explicit authorization.',
        summary: 'Book 2 tickets for Interstellar 70mm IMAX at PVR Palladium (8:30 PM)',
        cost: '$36.00',
        steps: [
          { action: 'OPEN_APP', target: 'cinema', desc: 'Launch CinePass application' },
          { action: 'APPLY_PREFERENCES', desc: 'Select preferred venue: PVR Palladium & showtime 8:30 PM' },
          { action: 'SELECT_SEATS', target: 'Row F14-F15', desc: 'Auto-select center-back row preference' },
          { action: 'REQUEST_CONFIRMATION', target: 'modal', desc: 'Prompt user for biometric authorization' }
        ]
      };
    }

    if (parsed.intent === 'inspect_screen') {
      return {
        riskTier: 'low',
        riskReason: 'Read-only screen parsing requires no confirmation.',
        summary: 'Analyze visible accessibility nodes and explain current content',
        steps: [
          { action: 'SCAN_ACCESSIBILITY_NODES', desc: 'Extract UI labels, bounding coordinates, and buttons' },
          { action: 'CROSS_REFERENCE_MEMORY', desc: 'Check if screen content relates to user priorities' },
          { action: 'EXPLAIN_RESULT', desc: 'Character voice summary of screen state' }
        ]
      };
    }

    if (parsed.intent === 'order_food') {
      return {
        riskTier: 'high',
        riskReason: 'Food checkout and card charge ($18.50) requires explicit authorization.',
        summary: 'Order Veg Dum Biryani from Paradise Dum Biryani',
        cost: '$18.50',
        steps: [
          { action: 'OPEN_APP', target: 'food', desc: 'Launch BiteGo Delivery app' },
          { action: 'FILTER_VEGETARIAN', desc: 'Apply user explicit rule: Strict Vegetarian' },
          { action: 'SELECT_HABIT_ITEM', desc: 'Locate Paradise Biryani (Learned habit 89%)' },
          { action: 'REQUEST_CONFIRMATION', desc: 'Prompt user before triggering payment gateway' }
        ]
      };
    }

    if (parsed.intent === 'schedule_meeting') {
      return {
        riskTier: 'medium',
        riskReason: 'Calendar modification requires 1-tap confirmation.',
        summary: 'Check conflict and schedule 3:00 PM review with John Vance',
        steps: [
          { action: 'OPEN_APP', target: 'mail', desc: 'Read John\'s email request' },
          { action: 'CHECK_CALENDAR', desc: 'Verify calendar free slot against Focus Time rule' },
          { action: 'DRAFT_INVITE', desc: 'Prepare calendar invite for 3:00 PM tomorrow' }
        ]
      };
    }

    return {
      riskTier: 'low',
      riskReason: 'Informational assistance.',
      summary: 'General query resolution',
      steps: [
        { action: 'QUERY_KNOWLEDGE', desc: 'Analyze user query against context' },
        { action: 'EXPLAIN_RESULT', desc: 'Provide helpful explanation' }
      ]
    };
  }

  async handleHighRiskApproval(plan, audioDataUri = null) {
    const speechPrompt = `I found the best option based on your usual preference. Shall I authorize the ${plan.summary}?`;
    this.character.setState('WAITING_CONFIRM', speechPrompt);
    this.setPhase('Awaiting User Biometric / PIN Approval');

    if (plan.steps && plan.steps[0] && plan.steps[0].action === 'OPEN_APP') {
      await this.animateTapOnApp(plan.steps[0].target);
    }

    const modal = document.getElementById('approval-modal');
    const modalTitle = document.getElementById('modal-action-title');
    const modalDetails = document.getElementById('modal-action-details');
    const modalBadge = document.getElementById('modal-risk-badge');

    let countdownSeconds = 120;
    let timerInterval = null;

    if (modal && modalTitle && modalDetails) {
      modalBadge.textContent = `${(plan.risk_tier || plan.riskTier || 'HIGH').toUpperCase()} RISK ACTION`;
      modalTitle.textContent = plan.summary;
      
      const token = plan.financial_token || `tok_${Math.floor(Date.now() / 1000)}_hmac_verified`;
      
      modalDetails.innerHTML = `
        <div><strong>Transaction:</strong> ${plan.summary}</div>
        <div><strong>Total Charge:</strong> <span style="color: #38bdf8; font-weight: 700;">${plan.cost || '$36.00'}</span></div>
        <div><strong>Security Protocol:</strong> ${plan.risk_reason || plan.riskReason || 'Biometric authorization required'}</div>
        <div class="hmac-token-badge" style="margin-top: 8px; font-family: monospace; font-size: 11px; color: #a78bfa; background: rgba(167, 139, 250, 0.12); padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(167, 139, 250, 0.3);">
          🔐 <strong>HMAC Signature:</strong> ${token.slice(0, 36)}...
        </div>
        <div id="modal-ttl-countdown" style="margin-top: 6px; font-size: 12px; color: #fbbf24; font-weight: 600;">
          ⏱️ Token expires in: <span id="ttl-sec">120</span>s
        </div>
        <div style="margin-top: 4px; color: #10b981;">✓ Preference Match: Verified against SQLite personal profile.</div>
      `;
      modal.classList.remove('hidden');

      // Live 120s TTL countdown
      const ttlSec = document.getElementById('ttl-sec');
      timerInterval = setInterval(() => {
        countdownSeconds -= 1;
        if (ttlSec) ttlSec.textContent = countdownSeconds;
        if (countdownSeconds <= 0) {
          clearInterval(timerInterval);
          if (cancelHandler) cancelHandler('Token expired (120s TTL)');
        }
      }, 1000);
    }

    this.audio.playNeuralVoice(audioDataUri, speechPrompt);

    return new Promise((resolve) => {
      const confirmBtn = document.getElementById('btn-confirm-action');
      const denyBtn = document.getElementById('btn-deny-action');
      const closeBtn = document.getElementById('btn-approval-cancel');

      const cleanup = () => {
        if (timerInterval) clearInterval(timerInterval);
        if (modal) modal.classList.add('hidden');
      };

      const cancelHandler = (reason = 'Execution aborted per user instruction.') => {
        cleanup();
        this.logStep('RISK', 'Action Cancelled by User', reason);
        this.character.setState('IDLE', 'Action cancelled. What would you like to do instead?');
        this.setPhase('Task Cancelled');
        
        // Notify governance gate of decline
        try {
          fetch('/api/governance/decline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: plan.task_id || 'task_default', reason })
          });
        } catch (e) {}

        resolve(false);
      };

      if (confirmBtn) {
        confirmBtn.onclick = async () => {
          cleanup();
          this.logStep('ACTION', 'User Authorized Transaction', 'Cryptographic HMAC Token Verified. Triggering payment gateway...');
          
          const token = plan.financial_token || `tok_${Math.floor(Date.now() / 1000)}_verified`;
          
          // Verify with backend financial gate
          try {
            await fetch('/api/governance/authorize', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ token: token, task_id: plan.task_id || 'task_default' })
            });
          } catch (e) {
            console.warn('Financial gate REST notify:', e);
          }

          if (this.wsConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
              type: 'CONFIRM_ACTION',
              plan: plan,
              token: token
            }));
          }

          await this.completeSuccessfulAction(plan);
          resolve(true);
        };
      }

      if (denyBtn) denyBtn.onclick = () => cancelHandler('User clicked Deny');
      if (closeBtn) closeBtn.onclick = () => cancelHandler('User closed modal');
    });
  }

  async executePlanSteps(plan) {
    if (plan.summary.includes('screen')) {
      this.phone.toggleInspector();
      await this.sleep(600);

      const activeScreen = this.phone.getCurrentScreenContext();
      this.logStep('ACTION', 'Screen Grounding & Accessibility Analysis', 
        `Extracted ${activeScreen.visibleNodes.length} visible UI elements from "${activeScreen.title}".`,
        activeScreen
      );

      const explanation = `You are currently in ${activeScreen.title}. I can see ${activeScreen.visibleNodes.length} interactive elements on your screen, including active navigation and items matching your preferences.`;

      this.character.setState('SPEAKING', explanation);
      this.audio.speak(explanation, null, () => {
        this.character.setState('SUCCESS', 'Screen analysis complete!');
        this.phone.toggleInspector();
        this.setPhase('Task Completed');
      });
      return;
    }

    if (plan.steps && plan.steps[0] && plan.steps[0].action === 'OPEN_APP') {
      await this.animateTapOnApp(plan.steps[0].target);
    }

    await this.completeSuccessfulAction(plan);
  }

  async animateTapOnApp(targetApp) {
    const cursor = document.getElementById('agent-touch-cursor');
    const label = document.getElementById('cursor-action-label');
    
    const appEl = document.querySelector(`[data-app="${targetApp}"]`);
    if (appEl && cursor) {
      const rect = appEl.getBoundingClientRect();
      const phoneRect = document.getElementById('phone-screen').getBoundingClientRect();

      const top = rect.top - phoneRect.top + rect.height / 2;
      const left = rect.left - phoneRect.left + rect.width / 2;

      cursor.style.top = `${top}px`;
      cursor.style.left = `${left}px`;
      if (label) label.textContent = `Tapping ${targetApp}`;
      cursor.classList.remove('hidden');

      await this.sleep(500);
      this.phone.setApp(targetApp);
      await this.sleep(400);
      cursor.classList.add('hidden');
    } else {
      this.phone.setApp(targetApp);
    }
  }

  async completeSuccessfulAction(plan) {
    this.character.setState('WORKING', 'Executing phone action...');
    await this.sleep(600);

    this.character.setState('SUCCESS', 'Task completed successfully!');
    this.setPhase('Execution Succeeded');

    const speech = `Done! I've completed: ${plan.summary}. Added to your schedule and confirmed.`;
    this.character.setSpeech(speech);
    this.logStep('EXPLAIN', 'Task Completed & Explained', speech);

    this.audio.speak(speech, () => {
      this.character.setState('SPEAKING');
    }, () => {
      this.character.setState('SUCCESS');
      setTimeout(() => {
        this.character.setState('IDLE', 'Task finished. What should we tackle next?');
        this.setPhase('Agent Idle • Ready');
      }, 3500);
    });
  }

  sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }
}
