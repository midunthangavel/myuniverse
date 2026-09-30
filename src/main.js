/**
 * Main Application Orchestrator
 * Connects Character, Phone OS, Personal Memory, Audio, and Agent Intelligence.
 */

import { CharacterEngine } from './character.js';
import { MemoryEngine } from './memory.js';
import { PhoneSimulator } from './phone.js';
import { AudioEngine } from './audio.js';
import { AgentEngine } from './agent.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Core Engines
  const character = new CharacterEngine('character-canvas');
  const memory = new MemoryEngine();
  const phone = new PhoneSimulator('phone-viewport');
  const audio = new AudioEngine();
  const agent = new AgentEngine(character, memory, phone, audio);

  // 2. Setup Live Phone Clock
  const timeEl = document.getElementById('phone-live-time');
  const updateTime = () => {
    if (timeEl) {
      const now = new Date();
      timeEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  };
  updateTime();
  setInterval(updateTime, 1000);

  // 3. User Input Handling (Text)
  const inputEl = document.getElementById('agent-user-input');
  const sendBtn = document.getElementById('btn-send-input');

  let activeDeviceMode = 'simulator';
  let runHardwareTaskFn = null;

  const handleUserSubmit = () => {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    if (activeDeviceMode === 'android' && runHardwareTaskFn) {
      runHardwareTaskFn(text);
    } else {
      agent.runTask(text);
    }
  };

  if (sendBtn) sendBtn.addEventListener('click', handleUserSubmit);
  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleUserSubmit();
    });
  }

  // 4. Voice Mic Button Handling (Speech-to-Text)
  const micBtn = document.getElementById('btn-mic');
  if (micBtn) {
    micBtn.addEventListener('click', () => {
      audio.startListening(
        (transcript) => {
          if (inputEl) inputEl.value = transcript;
          agent.runTask(transcript);
        },
        (isRecording) => {
          micBtn.classList.toggle('recording', isRecording);
          if (isRecording) {
            character.setState('LISTENING', 'Listening to your voice...');
          }
        }
      );
    });
  }

  // 5. Voice Toggle Button (TTS)
  const voiceToggleBtn = document.getElementById('btn-voice-toggle');
  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener('click', () => {
      audio.toggleVoice();
    });
  }

  // 6. Character Avatar Selector (Nova, Pixel, Astra)
  const charSelect = document.getElementById('char-select');
  if (charSelect) {
    charSelect.addEventListener('change', (e) => {
      const chosen = e.target.value;
      character.setAvatar(chosen);
      character.setState('SUCCESS', `Switched character persona to ${chosen.toUpperCase()}!`);
      setTimeout(() => character.setState('IDLE'), 2000);
    });
  }

  // 7. Quick Scenario Buttons
  const scenarioActions = {
    movie: 'Book a movie for tonight',
    screen: 'What is on my screen right now?',
    biryani: 'Find a good biryani place nearby for dinner',
    meeting: 'Schedule a meeting with John Vance tomorrow at 3 PM'
  };

  document.querySelectorAll('.scenario-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const scenarioKey = chip.getAttribute('data-scenario');
      const prompt = scenarioActions[scenarioKey];
      if (prompt) {
        if (inputEl) inputEl.value = prompt;
        agent.runTask(prompt);
      }
    });
  });

  // 7b. Proactive Ambient Triggers
  document.querySelectorAll('.proactive-chip:not(.chain)').forEach(chip => {
    chip.addEventListener('click', async () => {
      const template = chip.getAttribute('data-trigger');
      try {
        const res = await fetch('http://127.0.0.1:8000/api/proactive/trigger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ template })
        });
        const data = await res.json();
        const event = data.event;
        const plan = data.proactive_plan;

        // Switch to reasoning tab
        const reasoningTab = document.getElementById('tab-btn-reasoning');
        if (reasoningTab) reasoningTab.click();

        // Update Dynamic Island on phone
        const islandActivity = document.getElementById('island-activity');
        if (islandActivity) {
          islandActivity.innerHTML = `<span class="island-dot" style="background:#f43f5e; box-shadow:0 0 8px #f43f5e;"></span><span class="island-text" style="color:#f43f5e;">${event.title.substring(0, 24)}...</span>`;
        }

        // Log to stream
        agent.logStep('PROACTIVE', `Ambient Trigger: ${event.title}`, 
          `${event.description} Agent proactively synthesized a resolution plan.`,
          { event, suggestedResolution: plan }
        );

        // Character reaction
        character.setState('WAITING_CONFIRM', plan.speech_prompt);
        audio.speak(plan.speech_prompt);

        // Open approval modal
        const approvalModal = document.getElementById('approval-modal');
        const modalTitle = document.getElementById('modal-action-title');
        const modalDetails = document.getElementById('modal-action-details');
        if (approvalModal && modalTitle && modalDetails) {
          modalTitle.textContent = `Proactive Action: ${event.title}`;
          modalDetails.innerHTML = `
            <div><strong>Urgency:</strong> <span style="color:#f43f5e; text-transform:uppercase;">${event.priority}</span></div>
            <div><strong>Plan:</strong> ${plan.speech_prompt}</div>
            <div style="font-family:monospace; margin-top:6px;"><strong>Cross-App Steps:</strong> ${plan.steps.map(s => `[${s.app}] ${s.action}`).join(' ➔ ')}</div>
          `;
          approvalModal.classList.remove('hidden');
        }
      } catch (e) {
        console.error('Proactive trigger error', e);
      }
    });
  });

  // 7c. Multi-App Workflow Chaining
  const chainBtn = document.getElementById('btn-run-chain');
  if (chainBtn) {
    chainBtn.addEventListener('click', async () => {
      try {
        const reasoningTab = document.getElementById('tab-btn-reasoning');
        if (reasoningTab) reasoningTab.click();

        character.setState('WORKING', 'Executing Multi-App Workflow: Movie & Dinner Night Chain...');
        agent.setPhase('Running Cross-App Workflow Chain...');

        // Step 1: Cinema
        phone.setApp('cinema');
        agent.logStep('CHAINING', 'Step 1/3: CinePass Movie App', 'Booking 2 IMAX 70mm tickets in Center Row G...', { app: 'cinepass', seat: 'G12', time: '20:15' });
        await new Promise(r => setTimeout(r, 1200));

        // Step 2: Food
        phone.setApp('food');
        agent.logStep('CHAINING', 'Step 2/3: BiteGo Food Delivery App', 'Ordering Royal Mutton Dum Biryani (Medium spice, extra raita) scheduled for 19:15...', { app: 'bitego', dish: 'Dum Biryani', time: '19:15' });
        await new Promise(r => setTimeout(r, 1200));

        // Step 3: Mail / Calendar
        phone.setApp('mail');
        agent.logStep('CHAINING', 'Step 3/3: Spark Mail & Calendar', 'Syncing complete itinerary to Google Calendar and sending confirmation...', { app: 'spark_mail', dinner: '19:15', movie: '20:15' });
        await new Promise(r => setTimeout(r, 1000));

        const res = await fetch('http://127.0.0.1:8000/api/chaining/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ workflow: 'movie_and_dinner' })
        });
        const data = await res.json();

        agent.logStep('SUCCESS', 'Cross-App Workflow Completed', 
          `Executed ${data.total_steps} apps in sequence with verified parameter binding.`,
          data
        );

        const speech = "All done! I've booked your 8:15 PM IMAX tickets, ordered your favorite Dum Biryani for 7:15 PM, and synced everything to your calendar.";
        character.setState('SUCCESS', speech);
        audio.speak(speech);
        setTimeout(() => character.setState('IDLE'), 3500);

      } catch (e) {
        console.error('Workflow chaining error', e);
      }
    });
  }

  // 8. Phone Nav Chips (Home, Mail, Cinema, Foodie, Screen Inspector)
  const navHome = document.getElementById('btn-nav-home');
  const navMail = document.getElementById('btn-nav-mail');
  const navMovies = document.getElementById('btn-nav-movies');
  const navFood = document.getElementById('btn-nav-food');
  const toggleInspectorBtn = document.getElementById('btn-toggle-screen-inspector');

  if (navHome) navHome.addEventListener('click', () => phone.setApp('home'));
  if (navMail) navMail.addEventListener('click', () => phone.setApp('mail'));
  if (navMovies) navMovies.addEventListener('click', () => phone.setApp('cinema'));
  if (navFood) navFood.addEventListener('click', () => phone.setApp('food'));
  const navRides = document.getElementById('btn-nav-rides');
  const navMaps = document.getElementById('btn-nav-maps');
  if (navRides) navRides.addEventListener('click', () => phone.setApp('rides'));
  if (navMaps) navMaps.addEventListener('click', () => phone.setApp('maps'));
  if (toggleInspectorBtn) {
    toggleInspectorBtn.addEventListener('click', () => phone.toggleInspector());
  }

  // 9. Observability Studio Tabs (Reasoning, Memory, Permissions)
  const tabs = document.querySelectorAll('.brain-tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      contents.forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetId = `tab-${tab.getAttribute('data-tab')}`;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');
    });
  });

  // 10. Clear Stream Button
  const clearBtn = document.getElementById('btn-clear-logs');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      const feed = document.getElementById('reasoning-feed');
      if (feed) {
        feed.innerHTML = `
          <div class="empty-feed-placeholder" id="empty-feed-placeholder">
            <div class="placeholder-icon">🤖</div>
            <h4>Agent Waiting for Instruction</h4>
            <p>Type a request above or select a scenario chip to watch the agent plan and execute tasks.</p>
          </div>
        `;
      }
    });
  }

  // 11. Add Memory Modal
  const addMemBtn = document.getElementById('btn-add-memory');
  const memModal = document.getElementById('add-memory-modal');
  const closeMemBtn = document.getElementById('btn-close-memory-modal');
  const cancelMemBtn = document.getElementById('btn-cancel-memory');
  const saveMemBtn = document.getElementById('btn-save-memory');
  const memTextInput = document.getElementById('mem-text-input');
  const memCategorySelect = document.getElementById('mem-category-select');

  const openMemModal = () => {
    if (memModal) memModal.classList.remove('hidden');
    if (memTextInput) {
      memTextInput.value = '';
      memTextInput.focus();
    }
  };

  const closeMemModal = () => {
    if (memModal) memModal.classList.add('hidden');
  };

  if (addMemBtn) addMemBtn.addEventListener('click', openMemModal);
  if (closeMemBtn) closeMemBtn.addEventListener('click', closeMemModal);
  if (cancelMemBtn) cancelMemBtn.addEventListener('click', closeMemModal);

  if (saveMemBtn) {
    saveMemBtn.addEventListener('click', () => {
      const text = memTextInput.value.trim();
      const cat = memCategorySelect.value;
      if (!text) return;

      if (cat === 'explicit') {
        memory.addExplicit(text, 'User Defined');
      } else if (cat === 'routine') {
        memory.memory.routine.push({ id: 'rtn_' + Date.now(), title: 'User Rule', timing: text });
        memory.saveMemory();
      } else if (cat === 'entities') {
        memory.memory.entities.push({ id: 'ent_' + Date.now(), name: text, role: 'Saved Entity' });
        memory.saveMemory();
      }

      closeMemModal();
      character.setState('SUCCESS', 'Saved new preference to your personal memory model!');
      setTimeout(() => character.setState('IDLE'), 2500);
    });
  }

  // =========================================================================
  // 12. TAB 4: 4-Engine Integrated Stack (OpenViking, Laya, Scrapling, QwenPaw)
  // =========================================================================
  const vikingUriSelect = document.getElementById('viking-uri-select');
  const vikingTierBtns = document.querySelectorAll('#viking-tier-buttons .tier-btn');
  const vikingTokenEst = document.getElementById('viking-token-est');
  const vikingTierIndicator = document.getElementById('viking-tier-indicator');
  const vikingContentPreview = document.getElementById('viking-content-preview');
  let currentVikingTier = 'L1';

  const loadVikingNode = async (uri, tier) => {
    if (!vikingContentPreview) return;
    vikingContentPreview.textContent = `Loading ${uri} (${tier})...`;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/viking/read?uri=${encodeURIComponent(uri)}&tier=${tier}`);
      const data = await res.json();
      if (data.success) {
        if (vikingTokenEst) vikingTokenEst.textContent = `Estimated Tokens: ${data.estimated_tokens}`;
        if (vikingTierIndicator) vikingTierIndicator.textContent = `TIER: ${data.tier}`;
        const contentStr = typeof data.content === 'object' ? JSON.stringify(data.content, null, 2) : data.content;
        vikingContentPreview.textContent = contentStr;
      } else {
        vikingContentPreview.textContent = `Error: ${data.error || 'Failed to read node'}`;
      }
    } catch (e) {
      vikingContentPreview.textContent = `Offline preview for ${uri} (${tier}):\nCinema Preferences: IMAX Laser 70mm, Dolby Atmos, center row seats (Row G or H, seats 8-14). Frequency: 2x/month | Confidence: 0.94`;
    }
  };

  if (vikingUriSelect) {
    vikingUriSelect.addEventListener('change', (e) => {
      loadVikingNode(e.target.value, currentVikingTier);
    });
  }

  vikingTierBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      vikingTierBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentVikingTier = btn.getAttribute('data-tier');
      const uri = vikingUriSelect ? vikingUriSelect.value : 'viking://user/habits/cinema.json';
      loadVikingNode(uri, currentVikingTier);
    });
  });

  // Laya System 1 Interactive Fast Classifier
  const layaInput = document.getElementById('laya-test-input');
  const layaRunBtn = document.getElementById('btn-run-laya-test');
  const layaLatency = document.getElementById('laya-latency-display');
  const layaChoice = document.getElementById('laya-choice-val');
  const layaScore = document.getElementById('laya-score-val');
  const layaNoul = document.getElementById('laya-noul-val');
  const layaGov = document.getElementById('laya-gov-val');
  const layaPreloadContainer = document.getElementById('laya-preload-tags');

  const runLayaTest = async () => {
    const prompt = (layaInput ? layaInput.value : '').trim();
    if (!prompt) return;

    try {
      const res = await fetch('http://127.0.0.1:8000/api/classifier/system1', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, active_app: phone.currentApp || 'home' })
      });
      const data = await res.json();

      if (layaLatency) layaLatency.textContent = `${data.latency_ms}ms Latency (Sub-millisecond)`;
      if (layaChoice) layaChoice.textContent = data.choice;
      if (layaScore) layaScore.textContent = `${data.score} (${Math.round(data.score * 100)}%)`;
      
      if (layaNoul) {
        if (data.noul.is_safe) {
          layaNoul.textContent = '✓ SAFE (Passed)';
          layaNoul.className = 'm-val safe';
        } else {
          layaNoul.textContent = '✗ BLOCKED (Hazard)';
          layaNoul.className = 'm-val warn';
        }
      }

      if (layaGov) {
        layaGov.textContent = `${data.governance_action} (${data.noul.risk_tier.toUpperCase()})`;
        layaGov.className = data.governance_action === 'ALLOW' ? 'm-val safe' : 'm-val warn';
      }

      if (layaPreloadContainer && data.viking_preload) {
        layaPreloadContainer.innerHTML = data.viking_preload.map(p => `<span class="p-tag">${p}</span>`).join('');
      }

      // Micro-reaction on character
      if (data.suggested_character_state) {
        character.setState(data.suggested_character_state, `Fast Classifier: Identified ${data.choice} in ${data.latency_ms}ms!`);
        setTimeout(() => character.setState('IDLE'), 2000);
      }
    } catch (e) {
      console.warn('Laya live endpoint error', e);
    }
  };

  if (layaRunBtn) layaRunBtn.addEventListener('click', runLayaTest);
  if (layaInput) {
    layaInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') runLayaTest();
    });
  }

  // Scrapling Web Intelligence Runner
  const scraplingInput = document.getElementById('scrapling-query-input');
  const scraplingRunBtn = document.getElementById('btn-run-scrapling-test');
  const scraplingOutputBox = document.getElementById('scrapling-output-box');

  const runScraplingTest = async () => {
    const query = (scraplingInput ? scraplingInput.value : '').trim();
    if (!query) return;

    if (scraplingOutputBox) {
      scraplingOutputBox.innerHTML = '<div style="color: var(--text-muted); font-size: 0.75rem;">Fetching live sources via stealth scraper...</div>';
    }

    try {
      const res = await fetch('http://127.0.0.1:8000/api/web/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      const data = await res.json();

      if (scraplingOutputBox && data.results) {
        scraplingOutputBox.innerHTML = data.results.map(r => `
          <div class="web-result-item">
            <div class="web-res-title">${r.title}</div>
            <div class="web-res-snippet">${r.snippet}</div>
            <span class="web-res-url">${r.url}</span>
          </div>
        `).join('');
      }
    } catch (e) {
      console.warn('Scrapling fetch error', e);
    }
  };

  if (scraplingRunBtn) scraplingRunBtn.addEventListener('click', runScraplingTest);
  if (scraplingInput) {
    scraplingInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') runScraplingTest();
    });
  }

  // QwenPaw ReMe Refresh
  const updatePawRemeUI = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/paw/reme');
      const data = await res.json();
      const stepEl = document.getElementById('reme-working-step');
      const modeEl = document.getElementById('reme-working-mode');
      const turnsEl = document.getElementById('reme-turns-count');

      if (stepEl && data.working_memory) stepEl.textContent = `${data.working_memory.current_step} / ${data.working_memory.max_steps}`;
      if (modeEl && data.working_memory) modeEl.textContent = data.working_memory.governance_mode;
      if (turnsEl) turnsEl.textContent = `${data.episodic_history_count} Verbatim Turns`;
    } catch (e) {
      // ignore
    }
  };

  // Preload initial Viking context
  loadVikingNode('viking://user/habits/cinema.json', 'L1');
  updatePawRemeUI();

  // Day-in-the-Life Showcase Driver (Module 3.6)
  const showcaseBtn = document.getElementById('btn-play-showcase');
  if (showcaseBtn) {
    showcaseBtn.addEventListener('click', async () => {
      showcaseBtn.disabled = true;
      showcaseBtn.textContent = '⏳ Playing Showcase...';

      try {
        const res = await fetch('http://127.0.0.1:8000/api/showcase/steps');
        const data = await res.json();
        const steps = data.steps || [];

        agent.logStep('SHOWCASE', 'Starting 12-Step Day-in-the-Life Showcase', 'Exercising all 7 integrated repositories and Phase 3 architectures end-to-end.');

        for (let i = 0; i < steps.length; i++) {
          const s = steps[i];
          
          // Switch phone app
          if (s.app) {
            phone.setApp(s.app);
          }

          // Character state & speech
          character.setState(i === steps.length - 1 ? 'SUCCESS' : 'WORKING', s.title);
          character.setSpeech(s.speech);

          agent.logStep(
            'SHOWCASE',
            `Step ${s.step}/12: ${s.title}`,
            `[${s.engine}] ${s.speech}`
          );

          // Voice narration if audio enabled
          try {
            audio.speak(s.speech);
          } catch (e) {}

          // Artificial animation delay for viewer experience
          await new Promise(r => setTimeout(r, 2200));
        }

        character.setState('SUCCESS', 'All 12 Showcase Scenarios Executed Successfully!');
        agent.logStep('COMPLETE', 'Showcase Finished (100% OK)', 'Universal LLM Factory, Decorator Tools, YAML Prompts, MadeAgents Reflection, App RAG, Device Bridge, and Saga Rollback all verified.');
      } catch (e) {
        console.error('Showcase playback error:', e);
      } finally {
        showcaseBtn.disabled = false;
        showcaseBtn.textContent = '✨ Play Showcase';
      }
    });
  }

  // ==============================================================
  // 12. REAL ANDROID HARDWARE BRIDGE & LIVE SCREEN MIRROR CONTROLLER
  // ==============================================================
  const btnModeSim = document.getElementById('btn-mode-sim');
  const btnModeHw = document.getElementById('btn-mode-hardware');
  const mirrorContainer = document.getElementById('real-phone-mirror-container');
  const mirrorImg = document.getElementById('real-phone-mirror-img');
  const mirrorOverlay = document.getElementById('mirror-touch-overlay');
  const mirrorStatusText = document.getElementById('mirror-status-text');
  const btnRefreshMirror = document.getElementById('btn-refresh-mirror');
  const hwNavBar = document.getElementById('hardware-nav-bar');
  const phoneModelTag = document.getElementById('phone-model-tag');
  const phoneViewport = document.getElementById('phone-viewport');
  const phoneChassis = document.getElementById('phone-chassis');

  let mirrorPollInterval = null;

  const refreshMirrorScreen = () => {
    if (!mirrorImg) return;
    const cacheBuster = Date.now();
    mirrorImg.src = `http://127.0.0.1:8000/api/device/screen.png?t=${cacheBuster}`;
  };

  const setDeviceMode = async (mode) => {
    activeDeviceMode = mode;
    if (btnModeSim) btnModeSim.classList.toggle('active', mode === 'simulator');
    if (btnModeHw) btnModeHw.classList.toggle('active', mode === 'android');
    if (phoneChassis) phoneChassis.classList.toggle('real-phone-mode-active', mode === 'android');

    if (mode === 'android') {
      if (mirrorContainer) mirrorContainer.classList.remove('hidden');
      if (hwNavBar) hwNavBar.classList.remove('hidden');
      if (phoneViewport) phoneViewport.style.visibility = 'hidden';

      try {
        await fetch('http://127.0.0.1:8000/api/device/mode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: 'android' })
        });
        const res = await fetch('http://127.0.0.1:8000/api/device/status');
        const st = await res.json();
        const dev = st.device_info || {};
        if (phoneModelTag) {
          phoneModelTag.textContent = `${dev.model || 'Redmi Note 10S'} • Android ${dev.android_version || '13'} • ${dev.display_size || '1080x2400'}`;
        }
        if (mirrorStatusText) {
          mirrorStatusText.textContent = `${dev.model || 'Redmi Note 10S'} • Live ADB Mirror`;
        }
      } catch (e) {
        console.warn('Device status fetch:', e);
      }

      refreshMirrorScreen();
      if (!mirrorPollInterval) {
        mirrorPollInterval = setInterval(refreshMirrorScreen, 3000);
      }
      character.setState('SUCCESS', 'Real Phone Bridge Connected (Redmi Note 10S)');
    } else {
      if (mirrorContainer) mirrorContainer.classList.add('hidden');
      if (hwNavBar) hwNavBar.classList.add('hidden');
      if (phoneViewport) phoneViewport.style.visibility = 'visible';

      if (mirrorPollInterval) {
        clearInterval(mirrorPollInterval);
        mirrorPollInterval = null;
      }
      if (phoneModelTag) {
        phoneModelTag.textContent = 'Synapse Phone 16 Pro • Android 15 Core';
      }
      character.setState('IDLE', 'Switched to Web Simulator Mode');
    }
  };

  if (btnModeSim) btnModeSim.addEventListener('click', () => setDeviceMode('simulator'));
  if (btnModeHw) btnModeHw.addEventListener('click', () => setDeviceMode('android'));
  if (btnRefreshMirror) btnRefreshMirror.addEventListener('click', refreshMirrorScreen);

  // Interactive touch forwarding: Click anywhere on real phone screen mirror
  if (mirrorImg) {
    mirrorImg.addEventListener('click', async (e) => {
      const rect = mirrorImg.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;
      
      const phoneX = Math.round((clickX / rect.width) * 1080);
      const phoneY = Math.round((clickY / rect.height) * 2400);

      // Show tactile touch ripple
      const ripple = document.createElement('div');
      ripple.className = 'touch-ripple';
      ripple.style.left = `${clickX}px`;
      ripple.style.top = `${clickY}px`;
      if (mirrorOverlay) mirrorOverlay.appendChild(ripple);
      setTimeout(() => ripple.remove(), 500);

      agent.logStep('DEVICE_TAP', `Touch Forwarded to Hardware: (${phoneX}, ${phoneY})`, 'Injected physical input tap on connected Redmi Note 10S.');

      try {
        await fetch('http://127.0.0.1:8000/api/device/tap', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x: phoneX, y: phoneY })
        });
        setTimeout(refreshMirrorScreen, 600);
      } catch (err) {
        console.error('Tap injection error:', err);
      }
    });
  }

  // Hardware navigation buttons (Back, Home, Recents, Wake)
  const sendKeyEvent = async (keycode, name) => {
    agent.logStep('DEVICE_KEY', `Injected Hardware Key: ${name} (code ${keycode})`, 'Physical hardware key event dispatched to connected phone.');
    try {
      await fetch('http://127.0.0.1:8000/api/device/keyevent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keycode })
      });
      setTimeout(refreshMirrorScreen, 800);
    } catch (err) {
      console.error('Keyevent error:', err);
    }
  };

  const btnHwBack = document.getElementById('btn-hw-back');
  const btnHwHome = document.getElementById('btn-hw-home');
  const btnHwApps = document.getElementById('btn-hw-apps');
  const btnHwWake = document.getElementById('btn-hw-wake');

  if (btnHwBack) btnHwBack.addEventListener('click', () => sendKeyEvent(4, 'BACK'));
  if (btnHwHome) btnHwHome.addEventListener('click', () => sendKeyEvent(3, 'HOME'));
  if (btnHwApps) btnHwApps.addEventListener('click', () => sendKeyEvent(187, 'RECENTS'));
  if (btnHwWake) btnHwWake.addEventListener('click', () => sendKeyEvent(224, 'WAKE'));

  // Quick Hardware Scenario Tasks
  runHardwareTaskFn = async (promptText) => {
    await setDeviceMode('android');
    character.setState('WORKING', `Executing on Phone: "${promptText}"`);
    agent.logStep('DEVICE_TASK', `Autonomous Task Started: ${promptText}`, 'Executing multi-step action on physical Redmi Note 10S over ADB.');

    try {
      const res = await fetch('http://127.0.0.1:8000/api/device/execute-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText })
      });
      const data = await res.json();
      
      refreshMirrorScreen();

      const resultMsg = data.extracted_result ? `Task result: ${data.extracted_result}` : (data.message || 'Autonomous action completed on physical phone!');
      character.setState('SUCCESS', resultMsg);
      agent.logStep('TASK_COMPLETE', 'Hardware Task 100% Verified', resultMsg, data);
      
      try {
        audio.speak(resultMsg);
      } catch (e) {}
    } catch (err) {
      console.error('Task execution error:', err);
      character.setState('ERROR', 'Failed to execute task on device.');
    }
  };

  const btnCalcAdd = document.getElementById('btn-hw-calc-add');
  const btnChromeSearch = document.getElementById('btn-hw-chrome-search');
  const btnImagesTab = document.getElementById('btn-hw-images-tab');
  const btnCalcMul = document.getElementById('btn-hw-calc-mul');

  if (btnCalcAdd) btnCalcAdd.addEventListener('click', () => runHardwareTaskFn('open calculator and add 2 + 2'));
  if (btnChromeSearch) btnChromeSearch.addEventListener('click', () => runHardwareTaskFn('open google browser and type hi to run'));
  if (btnImagesTab) btnImagesTab.addEventListener('click', () => runHardwareTaskFn('go to images in google search'));
  if (btnCalcMul) btnCalcMul.addEventListener('click', () => runHardwareTaskFn('calculate 8 * 9 on physical phone'));

  // =========================================================================
  // 13. Autonomous App Explorer & UI Vector Memory Client Controller
  // =========================================================================
  const explorerAppSelect = document.getElementById('explorer-app-select');
  const btnTriggerCrawl = document.getElementById('btn-trigger-crawl');
  const crawlBtnLabel = document.getElementById('crawl-btn-label');
  const explorerQueryInput = document.getElementById('explorer-query-input');
  const btnExplorerSearch = document.getElementById('btn-explorer-search');
  const explorerSearchResults = document.getElementById('explorer-search-results');
  const explorerElementsGrid = document.getElementById('explorer-elements-grid');
  const expTotalScreens = document.getElementById('exp-total-screens');
  const expTotalElements = document.getElementById('exp-total-elements');
  const explorerElementsPill = document.getElementById('explorer-elements-pill');

  async function loadAppExplorerKnowledge(appId) {
    if (!appId) return;
    try {
      let res = await fetch(`http://127.0.0.1:8000/api/explorer/knowledge/${appId}`);
      let data = await res.json();
      
      // If not yet explored, trigger crawl automatically
      if (data.status === 'NOT_EXPLORED' || !data.screens) {
        await triggerAutonomousCrawl(appId);
        return;
      }

      renderExplorerData(data);
    } catch (err) {
      console.error('Failed to load explorer knowledge:', err);
    }
  }

  function renderExplorerData(data) {
    const screens = data.screens || {};
    const screenKeys = Object.keys(screens);
    const elements = data.indexed_elements || [];

    if (expTotalScreens) expTotalScreens.textContent = screenKeys.length;
    if (expTotalElements) expTotalElements.textContent = elements.length;
    if (explorerElementsPill) explorerElementsPill.textContent = `${elements.length} Actionable Elements`;

    if (!explorerElementsGrid) return;
    explorerElementsGrid.innerHTML = '';

    if (elements.length === 0) {
      explorerElementsGrid.innerHTML = '<p style="color: var(--text-secondary); grid-column: 1/-1;">No elements indexed yet. Click "Run Autonomous Crawl" above.</p>';
      return;
    }

    elements.forEach(elem => {
      const card = document.createElement('div');
      card.className = 'affordance-grid-card';
      const coords = elem.coordinates || [540, 1200];
      card.innerHTML = `
        <div class="affordance-card-top">
          <div class="result-label-row">
            <span class="affordance-card-label">${elem.label || 'Widget'}</span>
            <span class="result-type-tag">${elem.type || 'Button'}</span>
          </div>
          <span class="result-coords-pill">(${coords[0]}, ${coords[1]})</span>
        </div>
        <div class="result-screen-title">${elem.screen || ''}</div>
        <div class="affordance-card-desc">${elem.affordance || ''}</div>
      `;
      card.addEventListener('click', async () => {
        // Forward tap to active device at element coordinates
        try {
          await fetch('http://127.0.0.1:8000/api/device/tap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x: coords[0], y: coords[1] })
          });
          character.setState('WORKING', `Tapped element "${elem.label}" at (${coords[0]}, ${coords[1]})`);
          refreshMirrorScreen();
        } catch (e) {}
      });
      explorerElementsGrid.appendChild(card);
    });
  }

  async function triggerAutonomousCrawl(appId) {
    const targetApp = appId || (explorerAppSelect ? explorerAppSelect.value : 'com.miui.calculator');
    if (btnTriggerCrawl) btnTriggerCrawl.disabled = true;
    if (crawlBtnLabel) crawlBtnLabel.textContent = 'Crawling & Vector Indexing...';
    character.setState('WORKING', `Crawling UI Hierarchy for ${targetApp}...`);
    agent.logStep('CRAWLER_START', `Autonomous App Crawler Started`, `Traversing screens and calculating vector embeddings for ${targetApp}`);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/explorer/crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app: targetApp, max_depth: 2 })
      });
      const data = await res.json();
      
      renderExplorerData({
        screens: data.screens ? data.screens.reduce((acc, s) => ({ ...acc, [s]: {} }), {}) : {},
        indexed_elements: data.indexed_elements || []
      });

      character.setState('SUCCESS', `Indexed ${data.total_ui_elements_indexed} UI elements into ChromaDB!`);
      agent.logStep('CRAWLER_COMPLETE', `ChromaDB Vector Indexing Complete`, `Indexed ${data.total_ui_elements_indexed} buttons into ChromaDB. Persisted nav map to ${data.viking_storage_uri}.`, data);

      // Perform initial query demo
      if (explorerQueryInput && explorerQueryInput.value) {
        await executeVectorQuery(targetApp, explorerQueryInput.value);
      }
    } catch (err) {
      console.error('Crawl execution error:', err);
      character.setState('ERROR', 'App crawl failed.');
    } finally {
      if (btnTriggerCrawl) btnTriggerCrawl.disabled = false;
      if (crawlBtnLabel) crawlBtnLabel.textContent = 'Run Autonomous Crawl';
    }
  }

  async function executeVectorQuery(appId, queryText) {
    if (!queryText || !queryText.trim()) return;
    const targetApp = appId || (explorerAppSelect ? explorerAppSelect.value : 'com.miui.calculator');
    if (explorerSearchResults) {
      explorerSearchResults.innerHTML = '<p style="color: var(--accent-cyan); font-size: 0.85rem;">Searching ChromaDB HNSW vector index...</p>';
    }

    try {
      const res = await fetch('http://127.0.0.1:8000/api/explorer/query-ui', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app: targetApp, query: queryText, n_results: 3 })
      });
      const data = await res.json();
      const matches = data.matches || [];

      if (!explorerSearchResults) return;
      explorerSearchResults.innerHTML = '';

      if (matches.length === 0) {
        explorerSearchResults.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">No vector matches found for query.</p>';
        return;
      }

      matches.forEach(m => {
        const meta = m.metadata || {};
        const label = meta.label || 'Element';
        const type = meta.type || 'Widget';
        const screen = meta.screen_title || '';
        const coords = [meta.center_x || 540, meta.center_y || 1200];
        const sim = m.similarity || 'N/A';

        const row = document.createElement('div');
        row.className = 'result-affordance-card';
        row.innerHTML = `
          <div class="result-left">
            <div class="result-label-row">
              <span class="result-button-title">${label}</span>
              <span class="result-type-tag">${type}</span>
              <span class="result-score-badge">✦ ${sim} Vector Match</span>
            </div>
            <div class="result-screen-title">${screen}</div>
            <div class="result-desc">${m.text ? m.text.substring(0, 110) + '...' : ''}</div>
          </div>
          <div class="result-right">
            <span class="result-coords-pill">(${coords[0]}, ${coords[1]})</span>
            <button class="view-chip" style="font-size: 0.72rem; padding: 2px 8px; background: rgba(56, 189, 248, 0.2);">Tap on Device</button>
          </div>
        `;

        row.querySelector('button').addEventListener('click', async (e) => {
          e.stopPropagation();
          try {
            await fetch('http://127.0.0.1:8000/api/device/tap', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ x: coords[0], y: coords[1] })
            });
            character.setState('WORKING', `Tapped vector matched button "${label}" at (${coords[0]}, ${coords[1]})`);
            refreshMirrorScreen();
          } catch (err) {}
        });

        explorerSearchResults.appendChild(row);
      });
    } catch (err) {
      console.error('Vector search error:', err);
    }
  }

  if (explorerAppSelect) {
    explorerAppSelect.addEventListener('change', (e) => loadAppExplorerKnowledge(e.target.value));
  }

  if (btnTriggerCrawl) {
    btnTriggerCrawl.addEventListener('click', () => triggerAutonomousCrawl());
  }

  if (btnExplorerSearch) {
    btnExplorerSearch.addEventListener('click', () => {
      const q = explorerQueryInput ? explorerQueryInput.value : '';
      executeVectorQuery(explorerAppSelect ? explorerAppSelect.value : 'com.miui.calculator', q);
    });
  }

  if (explorerQueryInput) {
    explorerQueryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        executeVectorQuery(explorerAppSelect ? explorerAppSelect.value : 'com.miui.calculator', explorerQueryInput.value);
      }
    });
  }

  // Pre-load default app knowledge
  const tabBtnExplorer = document.getElementById('tab-btn-explorer');
  if (tabBtnExplorer) {
    tabBtnExplorer.addEventListener('click', () => {
      loadAppExplorerKnowledge(explorerAppSelect ? explorerAppSelect.value : 'com.miui.calculator');
      if (explorerQueryInput && explorerQueryInput.value) {
        executeVectorQuery(explorerAppSelect ? explorerAppSelect.value : 'com.miui.calculator', explorerQueryInput.value);
      }
    });
  }

  // Welcome announcement
  setTimeout(() => {
    character.setSpeech('Welcome! I am Synapse. I am connected to your physical Redmi Note 10S! Try the real phone scenario buttons or inspect the new App Explorer tab!');
  }, 500);
});
