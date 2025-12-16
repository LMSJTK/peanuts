const defaultState = {
  teamName: 'Peanuts Club',
  lineup: [
    { name: 'Ivy Sparks', position: 'CF' },
    { name: 'Gale Torres', position: 'SS' },
    { name: 'Kip Lantern', position: 'RF' },
    { name: 'River Ocho', position: '1B' },
    { name: 'Juniper Vail', position: 'LF' },
    { name: 'Hani Croft', position: '3B' },
    { name: 'Marlow Quinn', position: '2B' },
    { name: 'Tamsin Reed', position: 'C' },
    { name: 'Noah Calder', position: 'DH' },
  ],
  rotation: [
    { name: 'Cy Lumen', role: 'SP' },
    { name: 'Rosa Hallow', role: 'SP' },
    { name: 'Dylan Ash', role: 'SP' },
    { name: 'Mia Cortez', role: 'RP' },
    { name: 'Khalil Snow', role: 'RP' },
  ],
  economics: {
    ticketPrice: 24,
    promotions: {
      fireworks: true,
      kidsDay: false,
      themeNight: true,
      giveaway: false,
    },
    concessions: {
      Peanuts: 6.0,
      Crackerjacks: 7.5,
      Soda: 4.0,
      "Local Brew": 8.0,
    },
  },
};

const REQUIRED_POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'];
const MIN_LINEUP_SIZE = 9;
const ROTATION_RULES = { starters: 3, relievers: 2 };
const PROMOTION_COSTS = {
  fireworks: 15000,
  kidsDay: 5000,
  themeNight: 8000,
  giveaway: 12000,
};
const BASE_CASH = 250000;

const lineupList = document.getElementById('lineupList');
const rotationList = document.getElementById('rotationList');
const ticketInput = document.getElementById('ticketPrice');
const ticketDisplay = document.getElementById('ticketDisplay');
const promotionList = document.getElementById('promotionList');
const concessionsList = document.getElementById('concessionsList');
const downloadButton = document.getElementById('downloadState');
const uploadInput = document.getElementById('uploadState');
const validationStatus = document.getElementById('managementStatus');
const syncStatus = document.getElementById('syncStatus');

const clone = (value) =>
  typeof structuredClone === 'function'
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value));

let state = clone(defaultState);

async function bootstrapState() {
  const [fileState, localState] = await Promise.all([
    loadBridgeFile(),
    Promise.resolve(loadLocalState()),
  ]);

  state = mergeState(defaultState, fileState || localState || defaultState);
  renderAll();
  updateValidation();
  setSyncStatus('Ready for sync. Download to share with the simulator.', 'info');
}

function mergeState(base, incoming) {
  const merged = {
    ...clone(base),
    ...clone(incoming),
    economics: {
      ...clone(base.economics),
      ...clone(incoming.economics || {}),
      promotions: {
        ...clone(base.economics.promotions),
        ...clone(incoming.economics?.promotions || {}),
      },
      concessions: {
        ...clone(base.economics.concessions),
        ...clone(incoming.economics?.concessions || {}),
      },
    },
  };
  return merged;
}

function loadLocalState() {
  try {
    const raw = localStorage.getItem('managerState');
    if (!raw) return null;
    return mergeState(defaultState, JSON.parse(raw));
  } catch (err) {
    console.warn('Unable to load manager state, using defaults', err);
    return null;
  }
}

async function loadBridgeFile() {
  try {
    const response = await fetch('manager_state.json', { cache: 'no-store' });
    if (!response.ok) return null;
    const payload = await response.json();
    return normalizeBridgePayload(payload);
  } catch (err) {
    console.warn('Unable to fetch bridge file, falling back to local state', err);
    return null;
  }
}

function persist() {
  localStorage.setItem('managerState', JSON.stringify(state));
  setSyncStatus('Local changes pending simulator sync', 'warning');
  updateValidation();
}

function renderLineup() {
  lineupList.innerHTML = '';
  const positions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH'];

  state.lineup.forEach((entry, idx) => {
    const row = document.createElement('div');
    row.className = 'manager-row';

    const order = document.createElement('span');
    order.textContent = `${idx + 1}`;
    order.className = 'order';

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.value = entry.name;
    nameInput.className = 'text-input';
    nameInput.addEventListener('input', (e) => {
      state.lineup[idx].name = e.target.value;
      persist();
    });

    const positionSelect = document.createElement('select');
    positionSelect.className = 'select-input';
    positions.forEach((pos) => {
      const option = document.createElement('option');
      option.value = pos;
      option.textContent = pos;
      option.selected = pos === entry.position;
      positionSelect.appendChild(option);
    });
    positionSelect.addEventListener('change', (e) => {
      state.lineup[idx].position = e.target.value;
      persist();
    });

    row.append(order, nameInput, positionSelect);
    lineupList.appendChild(row);
  });
}

function renderRotation() {
  rotationList.innerHTML = '';
  state.rotation.forEach((entry, idx) => {
    const row = document.createElement('div');
    row.className = 'manager-row';

    const order = document.createElement('span');
    order.textContent = idx < 3 ? `SP ${idx + 1}` : `RP ${idx - 2}`;
    order.className = 'order';

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.value = entry.name;
    nameInput.className = 'text-input';
    nameInput.addEventListener('input', (e) => {
      state.rotation[idx].name = e.target.value;
      persist();
    });

    const roleSelect = document.createElement('select');
    roleSelect.className = 'select-input';
    ['SP', 'RP', 'CP'].forEach((role) => {
      const option = document.createElement('option');
      option.value = role;
      option.textContent = role;
      option.selected = entry.role === role;
      roleSelect.appendChild(option);
    });
    roleSelect.addEventListener('change', (e) => {
      state.rotation[idx].role = e.target.value;
      persist();
    });

    row.append(order, nameInput, roleSelect);
    rotationList.appendChild(row);
  });
}

function renderTicketPrice() {
  const value = Number(state.economics.ticketPrice || ticketInput.min);
  ticketInput.value = value;
  ticketDisplay.textContent = `$${value.toFixed(0)}`;
}

function renderPromotions() {
  promotionList.innerHTML = '';
  const entries = Object.entries(state.economics.promotions);
  entries.forEach(([promoKey, isActive]) => {
    const label = document.createElement('label');
    label.className = `chip ${isActive ? 'active' : ''}`;
    label.title = 'Toggle promotion';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = isActive;
    checkbox.addEventListener('change', (e) => {
      state.economics.promotions[promoKey] = e.target.checked;
      label.classList.toggle('active', e.target.checked);
      persist();
    });

    const text = document.createElement('span');
    text.textContent = promoLabel(promoKey);

    label.append(checkbox, text);
    promotionList.appendChild(label);
  });
}

function renderConcessions() {
  concessionsList.innerHTML = '';
  Object.entries(state.economics.concessions).forEach(([item, price]) => {
    const row = document.createElement('div');
    row.className = 'concession-row';

    const label = document.createElement('span');
    label.textContent = item;

    const input = document.createElement('input');
    input.type = 'number';
    input.min = '1';
    input.max = '50';
    input.step = '0.5';
    input.value = price;
    input.className = 'number-input';
    input.addEventListener('input', (e) => {
      state.economics.concessions[item] = Number(e.target.value);
      persist();
    });

    row.append(label, input);
    concessionsList.appendChild(row);
  });
}

function promoLabel(key) {
  const labels = {
    fireworks: 'Fireworks Night',
    kidsDay: 'Kids Run the Bases',
    themeNight: 'Theme Night',
    giveaway: 'Giveaway',
  };
  return labels[key] || key;
}

function exposeInterface() {
  window.managerInterface = {
    getState() {
      return JSON.parse(JSON.stringify(state));
    },
    setLineup(lineup) {
      state.lineup = lineup.map((entry) => ({
        name: entry.name,
        position: entry.position,
      }));
      persist();
      renderLineup();
    },
    setRotation(rotation) {
      state.rotation = rotation.map((entry) => ({
        name: entry.name,
        role: entry.role || 'SP',
      }));
      persist();
      renderRotation();
    },
    setEconomicPlan(plan) {
      if (plan.ticketPrice !== undefined) {
        state.economics.ticketPrice = Number(plan.ticketPrice);
        renderTicketPrice();
      }
      if (plan.promotions) {
        state.economics.promotions = {
          ...state.economics.promotions,
          ...plan.promotions,
        };
        renderPromotions();
      }
      if (plan.concessions) {
        state.economics.concessions = {
          ...state.economics.concessions,
          ...plan.concessions,
        };
        renderConcessions();
      }
      persist();
    },
    getBridgePayload,
  };
}

function bindEvents() {
  ticketInput.addEventListener('input', (e) => {
    state.economics.ticketPrice = Number(e.target.value);
    renderTicketPrice();
    persist();
  });

  downloadButton.addEventListener('click', () => {
    downloadBridgePayload();
  });

  uploadInput.addEventListener('change', async (event) => {
    const [file] = event.target.files;
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      const incoming = normalizeBridgePayload(parsed);
      if (incoming) {
        state = mergeState(defaultState, incoming);
        persist();
        renderAll();
        setSyncStatus('Bridge file loaded. Local changes pending sync.', 'info');
      }
    } catch (err) {
      setValidationStatus(`Unable to read file: ${err.message}`, 'error');
    } finally {
      uploadInput.value = '';
    }
  });
}

function renderAll() {
  renderLineup();
  renderRotation();
  renderTicketPrice();
  renderPromotions();
  renderConcessions();
}

function normalizeBridgePayload(payload) {
  if (!payload || typeof payload !== 'object') return null;
  const economics = payload.finance || payload.economics || {};
  const team = payload.team || {};

  return {
    teamName: team.name || payload.teamName || defaultState.teamName,
    lineup: Array.isArray(team.lineup)
      ? team.lineup.map((entry) => ({ name: entry.name, position: entry.position }))
      : clone(defaultState.lineup),
    rotation: Array.isArray(team.rotation)
      ? team.rotation.map((entry) => ({ name: entry.name, role: entry.role || 'SP' }))
      : clone(defaultState.rotation),
    economics: {
      ticketPrice: Number(economics.ticket_price ?? economics.ticketPrice ?? defaultState.economics.ticketPrice),
      promotions: Object.assign(
        {},
        clone(defaultState.economics.promotions),
        Object.fromEntries((economics.promotions || []).map((key) => [key, true]))
      ),
      concessions: economics.concessions_pricing || economics.concessions || clone(defaultState.economics.concessions),
    },
  };
}

function estimatedBudget() {
  const activePromos = Object.entries(state.economics.promotions).filter(([, isOn]) => isOn);
  const promoSpend = activePromos.reduce((sum, [key]) => sum + (PROMOTION_COSTS[key] || 0), 0);
  const averageConcession =
    Object.values(state.economics.concessions).reduce((sum, value) => sum + Number(value || 0), 0) /
    Math.max(Object.keys(state.economics.concessions).length, 1);
  const ticketRevenue = Number(state.economics.ticketPrice || 0) * 5000;
  const concessionsRevenue = averageConcession * 1800;

  const estimatedRevenue = Math.round(ticketRevenue + concessionsRevenue);
  const net = BASE_CASH + estimatedRevenue - promoSpend;

  return { promoSpend, estimatedRevenue, net };
}

function validateState() {
  const issues = [];
  const warnings = [];

  if (!state.lineup || state.lineup.length < MIN_LINEUP_SIZE) {
    issues.push(`Lineup must include ${MIN_LINEUP_SIZE} players`);
  }

  const positions = new Set(state.lineup.map((entry) => entry.position));
  REQUIRED_POSITIONS.forEach((pos) => {
    if (!positions.has(pos)) issues.push(`Missing ${pos} in lineup`);
  });

  const starterCount = state.rotation.filter((p) => p.role === 'SP').length;
  const relieverCount = state.rotation.filter((p) => p.role !== 'SP').length;
  if (starterCount < ROTATION_RULES.starters) {
    warnings.push(`Rotation light on starters (need ${ROTATION_RULES.starters})`);
  }
  if (relieverCount < ROTATION_RULES.relievers) {
    warnings.push(`Rotation light on relief (${ROTATION_RULES.relievers}+ suggested)`);
  }

  const { promoSpend, estimatedRevenue, net } = estimatedBudget();
  if (promoSpend > estimatedRevenue) {
    warnings.push('Promotions exceed projected revenue; expect a cash hit');
  }
  if (net < BASE_CASH * 0.5) {
    issues.push('Budget risk: cash would fall dangerously low with current plan');
  }

  return { issues, warnings };
}

function setValidationStatus(message, level) {
  validationStatus.textContent = message;
  validationStatus.className = `status status-${level}`;
}

function setSyncStatus(message, level) {
  syncStatus.textContent = message;
  syncStatus.className = `status status-${level}`;
}

function updateValidation() {
  const { issues, warnings } = validateState();

  if (issues.length) {
    setValidationStatus(issues.join(' • '), 'error');
    return;
  }

  if (warnings.length) {
    setValidationStatus(warnings.join(' • '), 'warning');
    return;
  }

  setValidationStatus('Lineup, rotation, and budget checks look solid.', 'success');
}

function getBridgePayload() {
  const promoEntries = Object.entries(state.economics.promotions).filter(([, active]) => active);
  const finance = {
    ticket_price: Number(state.economics.ticketPrice || 0),
    promotions: promoEntries.map(([key]) => key),
    concessions_pricing: Object.fromEntries(
      Object.entries(state.economics.concessions).map(([item, price]) => [item, Number(price || 0)])
    ),
    cash_on_hand: BASE_CASH,
    revenue: { gate: Number(state.economics.ticketPrice || 0) * 5000 },
    expenses: {
      promotions: promoEntries.reduce((sum, [key]) => sum + (PROMOTION_COSTS[key] || 0), 0),
    },
  };

  return {
    version: '1.0.0',
    team: {
      id: 'peanuts-user-club',
      name: state.teamName,
      lineup: clone(state.lineup),
      rotation: clone(state.rotation),
    },
    finance,
  };
}

function downloadBridgePayload() {
  try {
    const payload = getBridgePayload();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'manager_state.json';
    anchor.click();
    URL.revokeObjectURL(url);
    setSyncStatus('Synced: manager_state.json downloaded for the simulator.', 'success');
  } catch (err) {
    setValidationStatus(`Unable to export sync file: ${err.message}`, 'error');
  }
}

renderAll();
bindEvents();
exposeInterface();
bootstrapState();
