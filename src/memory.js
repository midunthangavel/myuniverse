/**
 * Personal Memory Engine
 * Syncs structured explicit memories, learned behavioral patterns,
 * graph entities, and routine constraints with the backend SQLite database.
 */

export class MemoryEngine {
  constructor() {
    this.storageKey = 'synapse_personal_memory_v1';
    this.memory = this.loadMemory();
    this.syncFromBackend();
    this.render();
  }

  async syncFromBackend() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/memory');
      if (res.ok) {
        const data = await res.json();
        if (data.explicit && data.explicit.length > 0) {
          this.memory = data;
          this.saveMemory();
        }
      }
      await this.updateFlywheelMetrics();
    } catch (e) {
      // Backend not yet reachable, keep local memory
    }
  }

  async updateFlywheelMetrics() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/learner/insights');
      if (res.ok) {
        const stats = await res.json();
        const statusEl = document.getElementById('flywheel-status-text');
        const effEl = document.getElementById('flywheel-efficiency-val');
        const obsEl = document.getElementById('f-total-obs');
        const habitsEl = document.getElementById('f-habits-count');
        const highConfEl = document.getElementById('f-high-conf-count');

        if (statusEl) statusEl.textContent = `Learning Momentum: ${stats.flywheel_status} 🚀`;
        if (effEl) effEl.textContent = stats.flywheel_efficiency;
        if (obsEl) obsEl.textContent = stats.total_observed_interactions;
        if (habitsEl) habitsEl.textContent = stats.active_learned_habits;
        if (highConfEl) highConfEl.textContent = stats.high_confidence_habits;
      }
    } catch (e) {}
  }

  getDefaultMemory() {
    return {
      explicit: [
        { id: 'exp_1', text: 'Dietary: Strictly Vegetarian (avoids non-veg & gelatin)', category: 'Food' },
        { id: 'exp_2', text: 'Movie Format: Prefers IMAX 70mm or Dolby Atmos', category: 'Entertainment' },
        { id: 'exp_3', text: 'Showtime Window: Evening slots between 7:30 PM – 9:30 PM', category: 'Entertainment' },
        { id: 'exp_4', text: 'Meeting Constraint: Never schedule meetings before 10:00 AM', category: 'Schedule' },
        { id: 'exp_5', text: 'Seating: Prefers center-back rows (E-H) in theatres', category: 'Preferences' }
      ],
      learned: [
        { id: 'lrn_1', text: 'Cinema Venue: PVR Inox Palladium', count: 8, confidence: '94%' },
        { id: 'lrn_2', text: 'Friday Dinner: Frequently orders Biryani from Paradise Spice', count: 6, confidence: '89%' },
        { id: 'lrn_3', text: 'Commute Preference: Takes Metro when city traffic > 30 min delay', count: 12, confidence: '84%' }
      ],
      entities: [
        { id: 'ent_1', name: 'John Vance', role: 'Colleague & Engineering Lead', priority: 'High' },
        { id: 'ent_2', name: 'Mom', role: 'Family (Immediate bypass for emergency calls)', priority: 'VIP' },
        { id: 'ent_3', name: 'Home', address: '402 Skyline Heights, Tech Corridor' },
        { id: 'ent_4', name: 'Office', address: 'Apex Innovation Center, Block 4' }
      ],
      routine: [
        { id: 'rtn_1', title: 'Work Day Routine', timing: '10:00 AM – 6:30 PM (Mon-Fri)' },
        { id: 'rtn_2', title: 'Focus Time Window', timing: '2:00 PM – 4:00 PM (Silent alerts)' },
        { id: 'rtn_3', title: 'Quiet Hours', timing: '11:00 PM – 7:30 AM' }
      ]
    };
  }

  loadMemory() {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.warn('Could not read memory from localStorage, using default profile');
    }
    return this.getDefaultMemory();
  }

  saveMemory() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.memory));
    } catch (e) {
      console.warn('Could not persist memory', e);
    }
    this.render();
  }

  async addExplicit(text, category = 'General') {
    const id = 'exp_' + Date.now();
    this.memory.explicit.push({ id, text, category });
    this.saveMemory();

    // Sync with backend
    try {
      await fetch('http://127.0.0.1:8000/api/memory/explicit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'user_default', category, text })
      });
    } catch (e) {}

    return id;
  }

  async remove(category, id) {
    if (this.memory[category]) {
      this.memory[category] = this.memory[category].filter(item => item.id !== id);
      this.saveMemory();

      // Sync with backend
      const tableMap = {
        explicit: 'explicit_preferences',
        learned: 'learned_habits',
        entities: 'entities',
        routine: 'routines'
      };
      const table = tableMap[category];
      if (table) {
        try {
          await fetch(`http://127.0.0.1:8000/api/memory/${table}/${id}`, { method: 'DELETE' });
        } catch (e) {}
      }
    }
  }

  // Contextual Semantic Retrieval for Agent Loop
  retrieveContextForIntent(intent, query) {
    const q = query.toLowerCase();
    const matches = [];

    // Food / dining queries
    if (q.includes('food') || q.includes('biryani') || q.includes('dinner') || q.includes('restaurant') || intent === 'order_food') {
      const diet = this.memory.explicit.find(m => m.text.toLowerCase().includes('vegetarian'));
      if (diet) matches.push({ type: 'EXPLICIT_PREFERENCE', text: diet.text });
      const foodHabit = this.memory.learned.find(m => m.text.toLowerCase().includes('biryani'));
      if (foodHabit) matches.push({ type: 'LEARNED_HABIT', text: `${foodHabit.text} (Confidence: ${foodHabit.confidence})` });
    }

    // Movie / cinema queries
    if (q.includes('movie') || q.includes('cinema') || q.includes('theatre') || intent === 'book_movie') {
      this.memory.explicit.forEach(m => {
        if (m.text.toLowerCase().includes('movie') || m.text.toLowerCase().includes('showtime') || m.text.toLowerCase().includes('seating')) {
          matches.push({ type: 'EXPLICIT_RULE', text: m.text });
        }
      });
      const cinemaHabit = this.memory.learned.find(m => m.text.toLowerCase().includes('cinema'));
      if (cinemaHabit) matches.push({ type: 'LEARNED_HABIT', text: `${cinemaHabit.text} (Confidence: ${cinemaHabit.confidence})` });
    }

    // Meeting / calendar / people queries
    if (q.includes('meeting') || q.includes('schedule') || q.includes('calendar') || q.includes('john') || intent === 'schedule_meeting') {
      const meetRule = this.memory.explicit.find(m => m.text.toLowerCase().includes('meeting'));
      if (meetRule) matches.push({ type: 'EXPLICIT_RULE', text: meetRule.text });
      if (q.includes('john')) {
        const john = this.memory.entities.find(e => e.name && e.name.toLowerCase().includes('john'));
        if (john) matches.push({ type: 'CONTACT_GRAPH', text: `${john.name}: ${john.role}` });
      }
      const focus = this.memory.routine.find(r => r.title.includes('Focus'));
      if (focus) matches.push({ type: 'SCHEDULE_CONSTRAINT', text: `${focus.title}: ${focus.timing}` });
    }

    // General fallback: return top 2 explicit rules
    if (matches.length === 0) {
      this.memory.explicit.slice(0, 2).forEach(m => {
        matches.push({ type: 'EXPLICIT_PREFERENCE', text: m.text });
      });
    }

    return matches;
  }

  render() {
    const explicitItems = this.memory.explicit || [];
    const learnedItems = this.memory.learned || [];
    const entitiesItems = this.memory.entities || [];
    const routineItems = this.memory.routine || this.memory.routines || [];

    // 1. Explicit list
    const expList = document.getElementById('explicit-memory-list');
    if (expList) {
      expList.innerHTML = explicitItems.map(item => `
        <li class="mem-item" data-id="${item.id}">
          <span class="mem-content"><strong>[${item.category}]</strong> ${item.text}</span>
          <button class="mem-delete-btn" data-cat="explicit" data-id="${item.id}" title="Delete memory">✕</button>
        </li>
      `).join('');
    }

    // 2. Learned list
    const lrnList = document.getElementById('learned-memory-list');
    if (lrnList) {
      lrnList.innerHTML = learnedItems.map(item => `
        <li class="mem-item" data-id="${item.id}">
          <span class="mem-content">${item.text}</span>
          <span class="mem-confidence">${item.confidence || '90%'}</span>
          <button class="mem-delete-btn" data-cat="learned" data-id="${item.id}" title="Delete memory">✕</button>
        </li>
      `).join('');
    }

    // 3. Entities list
    const entList = document.getElementById('entities-memory-list');
    if (entList) {
      entList.innerHTML = entitiesItems.map(item => `
        <li class="mem-item" data-id="${item.id}">
          <span class="mem-content"><strong>${item.name || ''}</strong> ${item.role || item.address || ''}</span>
          <button class="mem-delete-btn" data-cat="entities" data-id="${item.id}" title="Delete memory">✕</button>
        </li>
      `).join('');
    }

    // 4. Routine list
    const rtnList = document.getElementById('routine-memory-list');
    if (rtnList) {
      rtnList.innerHTML = routineItems.map(item => `
        <li class="mem-item" data-id="${item.id}">
          <span class="mem-content"><strong>${item.title}:</strong> ${item.schedule_rule || item.timing || ''}</span>
          <button class="mem-delete-btn" data-cat="routine" data-id="${item.id}" title="Delete memory">✕</button>
        </li>
      `).join('');
    }

    // Update memory badge count
    const totalCount = (this.memory.explicit ? this.memory.explicit.length : 0) +
                       (this.memory.learned ? this.memory.learned.length : 0) +
                       (this.memory.entities ? this.memory.entities.length : 0);
    const badge = document.getElementById('memory-count-badge');
    if (badge) badge.textContent = totalCount;

    // Attach delete listeners
    document.querySelectorAll('.mem-delete-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const cat = btn.getAttribute('data-cat');
        const id = btn.getAttribute('data-id');
        this.remove(cat, id);
      };
    });

    this.updateFlywheelMetrics();
  }
}
