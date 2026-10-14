/**
 * Phone OS Simulator
 * Simulates active phone apps (Home, Cinema, Foodie, Mail),
 * renders UI, and generates the Accessibility Node Hierarchy for screen grounding.
 */

const API_BASE = 'http://127.0.0.1:8000';
const API_KEY = 'synapse_api_sec_prod_9a2b8c4d1e7f0_2026';

async function fetchService(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn(`[PhoneSimulator] Fetch error ${endpoint}:`, e);
    return null;
  }
}

export class PhoneSimulator {
  constructor(viewportId) {
    this.viewport = document.getElementById(viewportId);
    this.currentApp = 'home';
    this.nodes = [];
    this.inspectMode = false;
    
    this.render();
  }

  setApp(appName) {
    this.currentApp = appName;
    this.render();
    this.updateActiveNavChip();
  }

  updateActiveNavChip() {
    document.querySelectorAll('.view-chip').forEach(chip => {
      chip.classList.remove('active');
    });
    const chipMap = {
      home: 'btn-nav-home',
      calendar: 'btn-nav-calendar',
      food: 'btn-nav-food',
      messages: 'btn-nav-messages',
      tasks: 'btn-nav-tasks',
      cinema: 'btn-nav-movies',
      mail: 'btn-nav-mail',
      rides: 'btn-nav-rides',
      maps: 'btn-nav-maps'
    };
    const activeId = chipMap[this.currentApp];
    if (activeId) {
      const activeEl = document.getElementById(activeId);
      if (activeEl) activeEl.classList.add('active');
    }
  }

  toggleInspector() {
    this.inspectMode = !this.inspectMode;
    const overlay = document.getElementById('screen-inspector-overlay');
    const btn = document.getElementById('btn-toggle-screen-inspector');
    
    if (overlay) {
      if (this.inspectMode) {
        overlay.classList.remove('hidden');
        this.renderAccessibilityBoxes();
      } else {
        overlay.classList.add('hidden');
      }
    }
    if (btn) {
      btn.classList.toggle('active', this.inspectMode);
    }
    return this.inspectMode;
  }

  renderAccessibilityBoxes() {
    const container = document.getElementById('node-bounding-boxes');
    if (!container) return;
    container.innerHTML = '';

    const viewportRect = this.viewport.getBoundingClientRect();

    this.nodes.forEach(node => {
      const el = document.getElementById(node.domId);
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const top = rect.top - viewportRect.top + 38; // 38px status bar offset
      const left = rect.left - viewportRect.left;
      const width = rect.width;
      const height = rect.height;

      const box = document.createElement('div');
      box.className = 'node-bounding-box';
      box.style.top = `${top}px`;
      box.style.left = `${left}px`;
      box.style.width = `${width}px`;
      box.style.height = `${height}px`;

      const tag = document.createElement('span');
      tag.className = 'node-tag-label';
      tag.textContent = `${node.role}#${node.id}`;
      box.appendChild(tag);

      container.appendChild(box);
    });
  }

  getNodeById(id) {
    return this.nodes.find(n => n.id === id);
  }

  getCurrentScreenContext() {
    return {
      app: this.currentApp,
      title: this.getAppTitle(),
      visibleNodes: this.nodes.map(n => ({
        id: n.id,
        role: n.role,
        text: n.text,
        clickable: n.clickable
      }))
    };
  }

  getAppTitle() {
    switch (this.currentApp) {
      case 'home': return 'Home Launcher';
      case 'calendar': return 'Synapse Calendar (Durable SQLite)';
      case 'food': return 'Synapse Food (Durable SQLite)';
      case 'messages': return 'Synapse Messages (Durable SQLite)';
      case 'tasks': return 'Synapse Tasks (Durable SQLite)';
      case 'cinema': return 'CinePass IMAX Booking';
      case 'mail': return 'Spark Mail — Inbox';
      case 'rides': return 'PulseRide — Live Ride Booking';
      case 'maps': return 'Orbit Maps — Live Navigation';
      default: return 'Active App';
    }
  }

  render() {
    if (!this.viewport) return;

    switch (this.currentApp) {
      case 'home':
        this.renderHome();
        break;
      case 'calendar':
        this.renderCalendar();
        break;
      case 'food':
        this.renderFood();
        break;
      case 'messages':
        this.renderMessages();
        break;
      case 'tasks':
        this.renderTasks();
        break;
      case 'cinema':
        this.renderCinema();
        break;
      case 'mail':
        this.renderMail();
        break;
      case 'rides':
        this.renderRides();
        break;
      case 'maps':
        this.renderMaps();
        break;
      default:
        this.renderHome();
    }

    // Refresh inspection boxes if enabled
    if (this.inspectMode) {
      setTimeout(() => this.renderAccessibilityBoxes(), 50);
    }
  }

  // 1. HOME SCREEN
  renderHome() {
    this.nodes = [
      { id: 'widget_weather', domId: 'el-widget-weather', role: 'widget', text: '74° Sunny, Tech Corridor', clickable: true },
      { id: 'widget_schedule', domId: 'el-widget-schedule', role: 'widget', text: '3:00 PM: Sync with John', clickable: true },
      { id: 'app_cinema', domId: 'el-app-cinema', role: 'app_icon', text: 'CinePass', clickable: true },
      { id: 'app_food', domId: 'el-app-food', role: 'app_icon', text: 'BiteGo', clickable: true },
      { id: 'app_rides', domId: 'el-app-rides', role: 'app_icon', text: 'PulseRide', clickable: true },
      { id: 'app_maps', domId: 'el-app-maps', role: 'app_icon', text: 'Orbit Maps', clickable: true },
      { id: 'app_mail', domId: 'el-app-mail', role: 'app_icon', text: 'Mail', clickable: true },
      { id: 'app_calendar', domId: 'el-app-calendar', role: 'app_icon', text: 'Calendar', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="home-screen">
        <div class="home-widget-row">
          <div class="home-widget" id="el-widget-weather">
            <div class="widget-header">
              <span>Weather</span>
              <span>☀️</span>
            </div>
            <div class="widget-main-value">74°</div>
            <div class="widget-subtext">Sunny • Air: Good</div>
          </div>

          <div class="home-widget" id="el-widget-schedule">
            <div class="widget-header">
              <span>Next Up</span>
              <span>📅</span>
            </div>
            <div class="widget-main-value">3:00 PM</div>
            <div class="widget-subtext">Product Sync w/ John</div>
          </div>
        </div>

        <div class="home-apps-grid">
          <div class="app-icon-item" id="el-app-cinema" data-app="cinema">
            <div class="app-squircle cinema">🎬</div>
            <span class="app-name">CinePass</span>
          </div>

          <div class="app-icon-item" id="el-app-food" data-app="food">
            <div class="app-squircle food">🍛</div>
            <span class="app-name">BiteGo</span>
          </div>

          <div class="app-icon-item" id="el-app-mail" data-app="mail">
            <div class="app-squircle mail">✉️</div>
            <span class="app-name">Spark Mail</span>
          </div>

          <div class="app-icon-item" id="el-app-calendar" data-app="calendar">
            <div class="app-squircle calendar">📅</div>
            <span class="app-name">Calendar</span>
          </div>

          <div class="app-icon-item" id="el-app-rides" data-app="rides">
            <div class="app-squircle rides">🚗</div>
            <span class="app-name">PulseRide</span>
          </div>

          <div class="app-icon-item" id="el-app-maps" data-app="maps">
            <div class="app-squircle maps">📍</div>
            <span class="app-name">Orbit Maps</span>
          </div>

          <div class="app-icon-item" data-app="notes">
            <div class="app-squircle notes">📝</div>
            <span class="app-name">Notes</span>
          </div>

          <div class="app-icon-item" data-app="bank">
            <div class="app-squircle bank">💳</div>
            <span class="app-name">Vault Pay</span>
          </div>

          <div class="app-icon-item" data-app="settings">
            <div class="app-squircle settings">⚙️</div>
            <span class="app-name">Settings</span>
          </div>
        </div>
      </div>
    `;

    // Click handler for app icons
    this.viewport.querySelectorAll('.app-icon-item').forEach(item => {
      item.onclick = () => {
        const app = item.getAttribute('data-app');
        if (['cinema', 'food', 'mail', 'rides', 'maps'].includes(app)) {
          this.setApp(app);
        }
      };
    });
  }

  // 2. CINEMA APP
  renderCinema() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-cine-back', role: 'button', text: 'Back', clickable: true },
      { id: 'text_theater_name', domId: 'el-cine-theater', role: 'text', text: 'PVR INOX Palladium IMAX', clickable: false },
      { id: 'slot_showtime_830', domId: 'el-slot-830', role: 'button', text: '8:30 PM IMAX (Preferred)', clickable: true },
      { id: 'btn_book_tickets', domId: 'el-cine-book-btn', role: 'button', text: 'Book 2 Seats ($36)', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-cinema">
        <div class="app-nav-bar">
          <button class="view-chip" id="el-cine-back">← Home</button>
          <span class="app-title-text">CinePass IMAX</span>
          <span class="app-tag">Tonight</span>
        </div>

        <div class="movie-hero-card" id="el-movie-card">
          <div class="movie-poster-mock">🚀</div>
          <div class="movie-info">
            <h4 class="movie-title">Interstellar 70mm IMAX</h4>
            <p class="movie-meta">Sci-Fi • 2h 49m • ⭐ 8.9/10</p>
            <div class="theater-badge" id="el-cine-theater">
              <span>📍 PVR INOX Palladium IMAX</span>
            </div>
            
            <div class="showtimes-row">
              <span class="time-chip" id="el-slot-530">5:15 PM</span>
              <span class="time-chip preferred active" id="el-slot-830">8:30 PM ⭐</span>
              <span class="time-chip" id="el-slot-1015">10:45 PM</span>
            </div>
          </div>
        </div>

        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 10px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #94a3b8; margin-bottom: 6px;">
            <span>Selected Row: Center (Row F14-F15)</span>
            <span style="color: #38bdf8; font-weight: 600;">Dolby Atmos 7.1</span>
          </div>
          <button class="btn primary" id="el-cine-book-btn" style="width: 100%; padding: 8px; font-size: 0.78rem;">
            Book 2 Seats ($36.00)
          </button>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-cine-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');
  }

  // 2. CALENDAR APP (Synapse Calendar - Durable SQLite)
  async renderCalendar() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-cal-back', role: 'button', text: 'Back', clickable: true },
      { id: 'btn_add_event_test', domId: 'el-btn-add-event', role: 'button', text: 'Quick Event', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-calendar" style="padding: 12px; color: #f8fafc; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div class="app-nav-bar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <button class="view-chip" id="el-cal-back" style="cursor: pointer;">← Home</button>
          <span style="font-weight: 700; color: #38bdf8;">📅 Synapse Calendar</span>
          <span class="app-tag" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem;">Live SQLite</span>
        </div>

        <div id="calendar-content-body">
          <div style="font-size: 0.75rem; color: #94a3b8; text-align: center; padding: 20px;">Loading confirmed events from SQLite...</div>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-cal-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');

    const events = await fetchService('/api/services/calendar/events') || [];
    const container = document.getElementById('calendar-content-body');
    if (!container) return;

    if (events.length === 0) {
      container.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed rgba(255,255,255,0.15); border-radius: 10px; padding: 18px; text-align: center;">
          <span style="font-size: 1.5rem;">📅</span>
          <p style="font-size: 0.75rem; color: #94a3b8; margin: 6px 0 10px 0;">No calendar events yet.</p>
          <button class="btn secondary" id="el-btn-add-event" style="padding: 6px 12px; font-size: 0.72rem; cursor: pointer;">
            + Test Add Event
          </button>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Confirmed Schedule (${events.length})</span>
          <button class="btn secondary" id="el-btn-add-event" style="padding: 4px 8px; font-size: 0.7rem; cursor: pointer;">+ Add</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${events.map(ev => `
            <div style="background: rgba(15, 23, 42, 0.7); border-left: 3px solid #38bdf8; border-radius: 8px; padding: 10px; font-size: 0.75rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
              <div style="font-weight: 700; color: #f8fafc; font-size: 0.8rem;">${ev.title}</div>
              <div style="color: #38bdf8; font-size: 0.72rem; margin: 3px 0;">⏰ ${ev.start_time.replace('T', ' ')} (${ev.duration_minutes || 60}m)</div>
              ${ev.location ? `<div style="color: #94a3b8; font-size: 0.7rem;">📍 ${ev.location}</div>` : ''}
              ${ev.attendees && ev.attendees.length > 0 ? `<div style="color: #64748b; font-size: 0.68rem; margin-top: 4px;">👥 ${ev.attendees.join(', ')}</div>` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    const addBtn = document.getElementById('el-btn-add-event');
    if (addBtn) {
      addBtn.onclick = async () => {
        addBtn.textContent = '⏳ Saving...';
        await fetchService('/api/services/calendar/events', {
          method: 'POST',
          body: JSON.stringify({
            title: 'Team Product Sync',
            start_time: '2026-10-16T14:30:00',
            duration_minutes: 45,
            location: 'Main Conference Room',
            attendees: ['sam@synapse.ai', 'alex@synapse.ai']
          })
        });
        this.renderCalendar();
      };
    }
  }

  // 3. FOOD APP (Synapse Food - Durable SQLite)
  async renderFood() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-food-back', role: 'button', text: 'Back', clickable: true },
      { id: 'btn_order_sushi', domId: 'el-btn-order-sushi', role: 'button', text: 'Order Sushi Zen', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-food" style="padding: 12px; color: #f8fafc; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div class="app-nav-bar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <button class="view-chip" id="el-food-back" style="cursor: pointer;">← Home</button>
          <span style="font-weight: 700; color: #f97316;">🍣 Synapse Food</span>
          <span class="app-tag" style="background: rgba(249, 115, 22, 0.2); color: #fb923c; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem;">Durable SQLite</span>
        </div>

        <div id="food-content-body">
          <div style="font-size: 0.75rem; color: #94a3b8; text-align: center; padding: 20px;">Loading orders & kitchens...</div>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-food-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');

    const orders = await fetchService('/api/services/food/orders') || [];
    const container = document.getElementById('food-content-body');
    if (!container) return;

    let ordersHtml = '';
    if (orders.length > 0) {
      ordersHtml = `
        <div style="margin-bottom: 14px;">
          <h5 style="font-size: 0.72rem; text-transform: uppercase; color: #10b981; margin: 0 0 6px 0;">Confirmed Orders (${orders.length})</h5>
          ${orders.slice(0, 3).map(o => `
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 8px; margin-bottom: 6px; font-size: 0.72rem;">
              <div style="display: flex; justify-content: space-between; font-weight: 600;">
                <span style="color: #38bdf8;">${o.restaurant_name}</span>
                <span style="color: #10b981;">$${Number(o.total).toFixed(2)}</span>
              </div>
              <div style="color: #94a3b8; margin-top: 2px; font-size: 0.7rem;">
                ${o.items.map(i => `${i.quantity}x ${i.name}`).join(', ')}
              </div>
              <div style="color: #64748b; font-size: 0.65rem; margin-top: 3px;">
                Status: <span style="color: #10b981; font-weight: 600;">${o.status}</span> • ID: ${o.order_id}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    container.innerHTML = `
      ${ordersHtml}
      <h5 style="font-size: 0.72rem; text-transform: uppercase; color: #94a3b8; margin: 0 0 6px 0;">Available Kitchens</h5>
      <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 10px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; font-size: 0.82rem;">Sushi Zen</span>
          <span style="color: #fbbf24; font-size: 0.75rem;">⭐ 4.9 (Japanese)</span>
        </div>
        <p style="font-size: 0.7rem; color: #94a3b8; margin: 4px 0 8px 0;">Omakase selection, fresh yellowfin roll, miso</p>
        <button class="btn primary" id="el-btn-order-sushi" style="width: 100%; padding: 6px; font-size: 0.72rem; background: #f97316; border: none; border-radius: 6px; color: white; cursor: pointer;">
          Order 2x Omakase Platter ($101.19)
        </button>
      </div>
    `;

    const sushiBtn = document.getElementById('el-btn-order-sushi');
    if (sushiBtn) {
      sushiBtn.onclick = async () => {
        sushiBtn.textContent = '⏳ Checking Out...';
        await fetchService('/api/services/food/cart', {
          method: 'POST',
          body: JSON.stringify({ item_id: 'sushi_omakase', quantity: 2 })
        });
        await fetchService('/api/services/food/checkout', {
          method: 'POST',
          body: JSON.stringify({ address: '742 Evergreen Terrace', restaurant_name: 'Sushi Zen' })
        });
        this.renderFood();
      };
    }
  }

  // 4. MESSAGES APP (Synapse Messages - Durable SQLite)
  async renderMessages() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-msg-back', role: 'button', text: 'Back', clickable: true },
      { id: 'btn_send_test_msg', domId: 'el-btn-send-msg', role: 'button', text: 'Send Message', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-messages" style="padding: 12px; color: #f8fafc; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div class="app-nav-bar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <button class="view-chip" id="el-msg-back" style="cursor: pointer;">← Home</button>
          <span style="font-weight: 700; color: #8b5cf6;">💬 Synapse Messages</span>
          <span class="app-tag" style="background: rgba(139, 92, 246, 0.2); color: #a78bfa; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem;">Durable SQLite</span>
        </div>

        <div id="messages-content-body">
          <div style="font-size: 0.75rem; color: #94a3b8; text-align: center; padding: 20px;">Loading threads from SQLite...</div>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-msg-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');

    const threads = await fetchService('/api/services/messages/threads') || [];
    const container = document.getElementById('messages-content-body');
    if (!container) return;

    if (threads.length === 0) {
      container.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed rgba(255,255,255,0.15); border-radius: 10px; padding: 18px; text-align: center;">
          <span style="font-size: 1.5rem;">💬</span>
          <p style="font-size: 0.75rem; color: #94a3b8; margin: 6px 0 10px 0;">No messages yet.</p>
          <button class="btn secondary" id="el-btn-send-msg" style="padding: 6px 12px; font-size: 0.72rem; cursor: pointer;">
            + Send Test Message
          </button>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${threads.map(t => {
            const lastMsg = t.messages && t.messages.length > 0 ? t.messages[t.messages.length - 1] : {};
            return `
              <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 8px; padding: 10px; font-size: 0.75rem;">
                <div style="display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 3px;">
                  <span style="color: #c084fc;">👤 ${t.recipient}</span>
                  <span style="color: #64748b; font-size: 0.65rem;">${t.count} msg(s)</span>
                </div>
                <div style="color: #cbd5e1; font-size: 0.72rem; background: rgba(30, 41, 59, 0.5); border-radius: 6px; padding: 6px; margin: 4px 0;">
                  "${lastMsg.body || ''}"
                </div>
                <div style="color: #10b981; font-size: 0.65rem; text-align: right;">
                  ${lastMsg.status || 'DELIVERED'} ✓✓
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    const testBtn = document.getElementById('el-btn-send-msg');
    if (testBtn) {
      testBtn.onclick = async () => {
        testBtn.textContent = '⏳ Dispatching...';
        await fetchService('/api/services/messages/send', {
          method: 'POST',
          body: JSON.stringify({
            recipient: 'Team Lead',
            body: 'Hey, I will be attending the Friday Strategy Lunch.'
          })
        });
        this.renderMessages();
      };
    }
  }

  // 5. TASKS APP (Synapse Tasks - Durable SQLite)
  async renderTasks() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-tasks-back', role: 'button', text: 'Back', clickable: true },
      { id: 'btn_add_task', domId: 'el-btn-add-task', role: 'button', text: 'Add Task', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-tasks" style="padding: 12px; color: #f8fafc; font-family: 'Plus Jakarta Sans', sans-serif;">
        <div class="app-nav-bar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <button class="view-chip" id="el-tasks-back" style="cursor: pointer;">← Home</button>
          <span style="font-weight: 700; color: #10b981;">✅ Synapse Tasks</span>
          <span class="app-tag" style="background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem;">Durable SQLite</span>
        </div>

        <div id="tasks-content-body">
          <div style="font-size: 0.75rem; color: #94a3b8; text-align: center; padding: 20px;">Loading tasks from SQLite...</div>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-tasks-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');

    const tasks = await fetchService('/api/services/tasks') || [];
    const container = document.getElementById('tasks-content-body');
    if (!container) return;

    if (tasks.length === 0) {
      container.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed rgba(255,255,255,0.15); border-radius: 10px; padding: 18px; text-align: center;">
          <span style="font-size: 1.5rem;">✅</span>
          <p style="font-size: 0.75rem; color: #94a3b8; margin: 6px 0 10px 0;">No active tasks.</p>
          <button class="btn secondary" id="el-btn-add-task" style="padding: 6px 12px; font-size: 0.72rem; cursor: pointer;">
            + Add First Task
          </button>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.72rem; color: #94a3b8; text-transform: uppercase;">Active Todos (${tasks.length})</span>
          <button class="btn secondary" id="el-btn-add-task" style="padding: 4px 8px; font-size: 0.7rem; cursor: pointer;">+ Add</button>
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${tasks.map(t => {
            const priorityColor = t.priority === 'HIGH' ? '#f43f5e' : t.priority === 'URGENT' ? '#ef4444' : '#fbbf24';
            return `
              <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 10px; display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <input type="checkbox" ${t.completed ? 'checked disabled' : ''} data-task-id="${t.id}" class="task-toggle-checkbox" style="cursor: pointer;" />
                  <span style="${t.completed ? 'text-decoration: line-through; color: #64748b;' : 'color: #f8fafc; font-weight: 500;'}">
                    ${t.title}
                  </span>
                </div>
                <span style="font-size: 0.65rem; color: ${priorityColor}; font-weight: 700; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">
                  ${t.priority}
                </span>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    // Bind checkboxes to complete task endpoint
    container.querySelectorAll('.task-toggle-checkbox').forEach(chk => {
      chk.onchange = async () => {
        const taskId = chk.getAttribute('data-task-id');
        if (taskId) {
          await fetchService(`/api/services/tasks/${taskId}/complete`, { method: 'POST' });
          this.renderTasks();
        }
      };
    });

    const addBtn = document.getElementById('el-btn-add-task');
    if (addBtn) {
      addBtn.onclick = async () => {
        addBtn.textContent = '⏳ Saving...';
        await fetchService('/api/services/tasks', {
          method: 'POST',
          body: JSON.stringify({
            title: 'Review team feedback on Q4 roadmap',
            priority: 'HIGH'
          })
        });
        this.renderTasks();
      };
    }
  }

  // 4. MAIL APP
  renderMail() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-mail-back', role: 'button', text: 'Back', clickable: true },
      { id: 'mail_item_john', domId: 'el-mail-john', role: 'list_item', text: 'John Vance: Q4 Product Strategy Alignment', clickable: true },
      { id: 'mail_item_cinepass', domId: 'el-mail-cine', role: 'list_item', text: 'Cineplex: Tonight 8:30 PM Premiere Reminder', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-mail">
        <div class="app-nav-bar">
          <button class="view-chip" id="el-mail-back">← Home</button>
          <span class="app-title-text">Spark Mail</span>
          <span class="app-tag" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa;">2 Unread</span>
        </div>

        <div class="mail-item unread" id="el-mail-john">
          <div class="mail-header-row">
            <span class="sender-name">John Vance</span>
            <span class="mail-time">10:14 AM</span>
          </div>
          <div class="mail-subject">Urgent: Reschedule Q4 Review Tomorrow?</div>
          <div class="mail-preview">
            "Hey! Can we move tomorrow's review to 3:00 PM? Let me know if that conflicts with your focus time."
          </div>
        </div>

        <div class="mail-item" id="el-mail-cine">
          <div class="mail-header-row">
            <span class="sender-name">PVR IMAX Box Office</span>
            <span class="mail-time">Yesterday</span>
          </div>
          <div class="mail-subject">Interstellar 70mm re-release shows open</div>
          <div class="mail-preview">
            "Your favorite venue PVR Palladium has evening showtimes available starting tonight at 8:30 PM."
          </div>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-mail-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');
  }

  // 5. RIDES APP (Uber-Style: PulseRide)
  renderRides() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-rides-back', role: 'button', text: 'Back', clickable: true },
      { id: 'input_pickup', domId: 'el-pickup-loc', role: 'input', text: 'Pickup: Tech Corridor (Tower 4)', clickable: true },
      { id: 'input_dest', domId: 'el-dest-loc', role: 'input', text: 'Destination: Downtown Convention Center', clickable: true },
      { id: 'tier_pulse_x', domId: 'el-tier-x', role: 'card', text: 'Pulse X: $18.50 (4 mins away)', clickable: true },
      { id: 'tier_pulse_comfort', domId: 'el-tier-comfort', role: 'card', text: 'Pulse Comfort: $24.00 (6 mins away, extra legroom)', clickable: true },
      { id: 'tier_pulse_black', domId: 'el-tier-black', role: 'card', text: 'Pulse Black: $38.00 (3 mins away, VIP driver)', clickable: true },
      { id: 'btn_request_ride', domId: 'el-request-ride-btn', role: 'button', text: 'Confirm Pulse Comfort ($24.00)', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-rides">
        <div class="app-nav-bar">
          <button class="view-chip" id="el-rides-back">← Home</button>
          <span class="app-title-text">PulseRide</span>
          <span class="app-tag" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">Active GPS</span>
        </div>

        <div class="rides-location-card">
          <div class="loc-row">
            <span class="loc-dot start">●</span>
            <div class="loc-text" id="el-pickup-loc">Tech Corridor (Tower 4)</div>
          </div>
          <div class="loc-divider"></div>
          <div class="loc-row">
            <span class="loc-dot end">◼</span>
            <div class="loc-text" id="el-dest-loc">Downtown Convention Center</div>
          </div>
        </div>

        <div class="rides-tier-list">
          <div class="ride-tier-card" id="el-tier-x">
            <div class="tier-icon">🚗</div>
            <div class="tier-info">
              <div class="tier-name">Pulse X <span class="tier-eta">4 mins away</span></div>
              <div class="tier-sub">Affordable, everyday rides</div>
            </div>
            <div class="tier-price">$18.50</div>
          </div>

          <div class="ride-tier-card selected" id="el-tier-comfort">
            <div class="tier-icon">✨</div>
            <div class="tier-info">
              <div class="tier-name">Pulse Comfort <span class="tier-badge-top">Top Match</span></div>
              <div class="tier-sub">Top rated drivers • Extra legroom</div>
            </div>
            <div class="tier-price">$24.00</div>
          </div>

          <div class="ride-tier-card" id="el-tier-black">
            <div class="tier-icon">🎩</div>
            <div class="tier-info">
              <div class="tier-name">Pulse Black <span class="tier-eta">3 mins away</span></div>
              <div class="tier-sub">Premium luxury sedan</div>
            </div>
            <div class="tier-price">$38.00</div>
          </div>
        </div>

        <button class="ride-confirm-btn" id="el-request-ride-btn">
          Request Pulse Comfort ($24.00)
        </button>
      </div>
    `;

    const backBtn = document.getElementById('el-rides-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');
  }

  // 6. NAVIGATION APP (Orbit Maps)
  renderMaps() {
    this.nodes = [
      { id: 'btn_back_home', domId: 'el-maps-back', role: 'button', text: 'Back', clickable: true },
      { id: 'text_eta_status', domId: 'el-eta-status', role: 'text', text: '22 min (11.4 mi) • Fastest Route', clickable: false },
      { id: 'btn_start_nav', domId: 'el-start-nav-btn', role: 'button', text: 'Start Turn-by-Turn Navigation', clickable: true },
      { id: 'btn_reroute_transit', domId: 'el-reroute-btn', role: 'button', text: 'Reroute via Express Transit', clickable: true }
    ];

    this.viewport.innerHTML = `
      <div class="app-view-maps">
        <div class="app-nav-bar">
          <button class="view-chip" id="el-maps-back">← Home</button>
          <span class="app-title-text">Orbit Maps</span>
          <span class="app-tag" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">I-95 Heavy</span>
        </div>

        <div class="maps-viewport-canvas" id="el-map-canvas">
          <svg class="map-vector-svg" viewBox="0 0 320 200" fill="none">
            <path d="M 30 160 Q 90 100 160 120 T 290 30" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" />
            <path d="M 120 115 L 180 150" stroke="#f43f5e" stroke-width="4" stroke-linecap="round" />
            <circle cx="30" cy="160" r="7" fill="#10b981" />
            <circle cx="290" cy="30" r="7" fill="#f43f5e" />
            <text x="30" y="185" fill="#94a3b8" font-size="9" font-family="sans-serif">Tech Corridor</text>
            <text x="235" y="22" fill="#f8fafc" font-size="9" font-weight="bold" font-family="sans-serif">Downtown</text>
            <circle cx="95" cy="105" r="4" fill="#38bdf8" />
            <circle cx="95" cy="105" r="10" stroke="#38bdf8" stroke-width="1.5" opacity="0.6" />
          </svg>
          <div class="map-traffic-alert-pill">⚠️ +15m traffic delay on I-95</div>
        </div>

        <div class="maps-guidance-card">
          <div class="guidance-instruction-row">
            <span class="turn-icon">↱</span>
            <div class="instruction-text">
              <strong>In 400m, take Exit 24B</strong>
              <span>toward Downtown Metro Center</span>
            </div>
          </div>
          <div class="guidance-meta" id="el-eta-status">
            <span class="g-eta">22 min</span>
            <span class="g-dist">11.4 mi</span>
            <span class="g-arr">ETA 3:22 PM</span>
          </div>
        </div>

        <div class="maps-action-row">
          <button class="map-action-btn secondary" id="el-reroute-btn">Transit Reroute</button>
          <button class="map-action-btn primary" id="el-start-nav-btn">Start Navigation</button>
        </div>
      </div>
    `;

    const backBtn = document.getElementById('el-maps-back');
    if (backBtn) backBtn.onclick = () => this.setApp('home');
  }
}
