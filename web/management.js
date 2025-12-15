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

const lineupList = document.getElementById('lineupList');
const rotationList = document.getElementById('rotationList');
const ticketInput = document.getElementById('ticketPrice');
const ticketDisplay = document.getElementById('ticketDisplay');
const promotionList = document.getElementById('promotionList');
const concessionsList = document.getElementById('concessionsList');

const clone = (value) =>
  typeof structuredClone === 'function'
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value));

const state = loadState();

function loadState() {
  try {
    const raw = localStorage.getItem('managerState');
    if (!raw) return clone(defaultState);
    const parsed = JSON.parse(raw);
    return {
      ...clone(defaultState),
      ...parsed,
      economics: {
        ...clone(defaultState.economics),
        ...parsed.economics,
        promotions: {
          ...clone(defaultState.economics.promotions),
          ...(parsed.economics?.promotions || {}),
        },
        concessions: {
          ...clone(defaultState.economics.concessions),
          ...(parsed.economics?.concessions || {}),
        },
      },
    };
  } catch (err) {
    console.warn('Unable to load manager state, using defaults', err);
    return clone(defaultState);
  }
}

function persist() {
  localStorage.setItem('managerState', JSON.stringify(state));
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
  };
}

function bindEvents() {
  ticketInput.addEventListener('input', (e) => {
    state.economics.ticketPrice = Number(e.target.value);
    renderTicketPrice();
    persist();
  });
}

function renderAll() {
  renderLineup();
  renderRotation();
  renderTicketPrice();
  renderPromotions();
  renderConcessions();
}

renderAll();
bindEvents();
exposeInterface();
