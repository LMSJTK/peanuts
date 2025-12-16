const canvas = document.getElementById('field');
const ctx = canvas.getContext('2d');
const logEl = document.getElementById('log');
const energyBar = document.getElementById('energyBar');
const energyValue = document.getElementById('energyValue');
const playPauseBtn = document.getElementById('playPause');
const stepBtn = document.getElementById('step');
const skipBtn = document.getElementById('skip');
const speedInput = document.getElementById('speed');
const statusEl = document.getElementById('feedStatus');

const FEED_PATH = 'replay.json';
const POLL_INTERVAL_MS = 4000;

let events = [];
let currentIndex = 0;
let playing = true;
let lastTick = 0;
let tickDelay = Number(speedInput.value);
let feedVersion = null;

const palette = {
  grass: '#1b8a5a',
  dirt: '#c27b37',
  chalk: '#eae7db',
  sky: '#1a2f61',
  accent: '#8ce6ff',
  text: '#e8f2ff',
};

function drawDiamond(state) {
  ctx.fillStyle = palette.sky;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = palette.grass;
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2, 40);
  ctx.lineTo(canvas.width - 60, canvas.height / 2);
  ctx.lineTo(canvas.width / 2, canvas.height - 40);
  ctx.lineTo(60, canvas.height / 2);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = palette.dirt;
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2, canvas.height / 2 - 80);
  ctx.lineTo(canvas.width / 2 + 80, canvas.height / 2);
  ctx.lineTo(canvas.width / 2, canvas.height / 2 + 80);
  ctx.lineTo(canvas.width / 2 - 80, canvas.height / 2);
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle = palette.chalk;
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2 - 80, canvas.height / 2);
  ctx.lineTo(canvas.width / 2 - 200, canvas.height - 40);
  ctx.moveTo(canvas.width / 2 + 80, canvas.height / 2);
  ctx.lineTo(canvas.width / 2 + 200, canvas.height - 40);
  ctx.stroke();

  drawBases(state);
  drawScoreboard(state);
  drawCrowd(state);
}

function drawBases(state) {
  const basePositions = [
    { x: canvas.width / 2 + 110, y: canvas.height - 70 },
    { x: canvas.width / 2 - 110, y: canvas.height - 70 },
    { x: canvas.width / 2, y: canvas.height / 2 - 110 },
  ];

  basePositions.forEach((pos, idx) => {
    ctx.save();
    ctx.translate(pos.x, pos.y);
    ctx.rotate(Math.PI / 4);
    ctx.fillStyle = state.bases[idx] ? palette.accent : palette.chalk;
    ctx.fillRect(-12, -12, 24, 24);
    ctx.restore();
  });

  ctx.fillStyle = palette.chalk;
  ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height - 32, 12, 0, Math.PI * 2);
  ctx.fill();
}

function drawScoreboard(state) {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
  ctx.fillRect(16, 16, 240, 90);
  ctx.strokeStyle = palette.accent;
  ctx.lineWidth = 3;
  ctx.strokeRect(16, 16, 240, 90);

  ctx.fillStyle = palette.text;
  ctx.font = '12px "Press Start 2P"';
  ctx.fillText(`Pitch ${state.number}/${events.length}`, 26, 38);
  ctx.fillText(`Count ${state.count}`, 26, 58);
  ctx.fillText(`Outs ${state.outs}`, 26, 78);
  ctx.fillText(`Runs ${state.runs}`, 26, 98);
}

function drawCrowd(state) {
  const intensity = Math.min(1, state.crowdEnergy / 100);
  ctx.fillStyle = `rgba(140, 230, 255, ${0.08 + 0.3 * intensity})`;
  ctx.fillRect(0, 0, canvas.width, 26);
  ctx.fillRect(0, canvas.height - 26, canvas.width, 26);
}

function render(event) {
  const state = {
    number: event.number,
    count: `${event.balls_after}-${event.strikes_after}`,
    outs: event.outs_after,
    bases: event.bases_after,
    runs: event.total_runs,
    crowdEnergy: event.crowd_energy_after,
  };

  drawDiamond(state);
  paintPlayText(event);
  updateLog(event);
  updateEnergy(state.crowdEnergy, event.crowd_modifiers);
}

function paintPlayText(event) {
  ctx.fillStyle = palette.text;
  ctx.font = '13px "Press Start 2P"';
  ctx.fillText(`${event.batter} vs Pitch ${event.number}`, 280, 48);
  ctx.font = '11px "Press Start 2P"';
  ctx.fillText(`${event.outcome.toUpperCase()} — ${event.detail}`, 280, 70);
}

function updateLog(event) {
  const basesBefore = event.bases_before.map((b) => (b ? '1' : '-')).join('');
  const basesAfter = event.bases_after.map((b) => (b ? '1' : '-')).join('');
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.innerHTML = `<strong>#${event.number}</strong> ${event.batter}: ${event.outcome} (${event.balls_before}-${event.strikes_before} → ${event.balls_after}-${event.strikes_after}), bases ${basesBefore} → ${basesAfter}`;
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;
}

function updateEnergy(value, modifiers) {
  energyBar.style.width = `${Math.min(100, value).toFixed(0)}%`;
  energyValue.textContent = `${value.toFixed(1)} energy`;

  energyBar.style.boxShadow = `0 0 12px rgba(140, 230, 255, ${Math.max(0.25, value / 120)})`;

  const tooltip = Object.entries(modifiers)
    .map(([k, v]) => `${k}: ${v.toFixed(3)}`)
    .join('\n');
  energyBar.title = tooltip;
}

function stepOnce() {
  if (currentIndex >= events.length) return;
  const event = events[currentIndex];
  render(event);
  currentIndex += 1;
  if (currentIndex >= events.length) {
    playing = false;
    playPauseBtn.textContent = 'Play';
  }
}

function loop(timestamp) {
  if (!lastTick) lastTick = timestamp;
  const delta = timestamp - lastTick;
  if (playing && delta >= tickDelay) {
    stepOnce();
    lastTick = timestamp;
  }
  requestAnimationFrame(loop);
}

playPauseBtn.addEventListener('click', () => {
  playing = !playing;
  playPauseBtn.textContent = playing ? 'Pause' : 'Play';
});

stepBtn.addEventListener('click', () => {
  playing = false;
  playPauseBtn.textContent = 'Play';
  stepOnce();
});

skipBtn.addEventListener('click', () => {
  playing = false;
  playPauseBtn.textContent = 'Play';
  while (currentIndex < events.length) {
    stepOnce();
  }
});

speedInput.addEventListener('input', () => {
  tickDelay = Number(speedInput.value);
});

function normalizeEvent(rawEvent, idx) {
  if (!rawEvent) return null;

  if (rawEvent.context && rawEvent.outcome) {
    const countBefore = rawEvent.context.count?.before || {};
    const countAfter = rawEvent.context.count?.after || {};
    const outs = rawEvent.context.outs || {};
    const bases = rawEvent.context.bases || {};
    const crowd = rawEvent.context.crowd || {};

    return {
      number: rawEvent.context.pitch_number ?? idx + 1,
      batter: rawEvent.context.batter || 'Unknown',
      outcome: rawEvent.outcome.result || 'unknown',
      detail: rawEvent.outcome.detail || '',
      balls_before: countBefore.balls ?? 0,
      strikes_before: countBefore.strikes ?? 0,
      outs_before: outs.before ?? 0,
      balls_after: countAfter.balls ?? countBefore.balls ?? 0,
      strikes_after: countAfter.strikes ?? countBefore.strikes ?? 0,
      outs_after: outs.after ?? outs.before ?? 0,
      bases_before: (bases.before || [false, false, false]).slice(0, 3),
      bases_after: (bases.after || [false, false, false]).slice(0, 3),
      runs_scored: rawEvent.outcome.runs_scored ?? 0,
      total_runs: rawEvent.outcome.total_runs ?? 0,
      contact_quality: rawEvent.outcome.contact_quality ?? 0,
      crowd_energy_before: crowd.energy_before ?? 0,
      crowd_energy_after: crowd.energy_after ?? 0,
      crowd_modifiers: rawEvent.modifiers?.crowd || {},
    };
  }

  return {
    number: rawEvent.number ?? idx + 1,
    batter: rawEvent.batter || 'Unknown',
    outcome: rawEvent.outcome || 'unknown',
    detail: rawEvent.detail || '',
    balls_before: rawEvent.balls_before ?? 0,
    strikes_before: rawEvent.strikes_before ?? 0,
    outs_before: rawEvent.outs_before ?? 0,
    balls_after: rawEvent.balls_after ?? rawEvent.balls_before ?? 0,
    strikes_after: rawEvent.strikes_after ?? rawEvent.strikes_before ?? 0,
    outs_after: rawEvent.outs_after ?? rawEvent.outs_before ?? 0,
    bases_before: (rawEvent.bases_before || [false, false, false]).slice(0, 3),
    bases_after: (rawEvent.bases_after || [false, false, false]).slice(0, 3),
    runs_scored: rawEvent.runs_scored ?? 0,
    total_runs: rawEvent.total_runs ?? 0,
    contact_quality: rawEvent.contact_quality ?? 0,
    crowd_energy_before: rawEvent.crowd_energy_before ?? 0,
    crowd_energy_after: rawEvent.crowd_energy_after ?? 0,
    crowd_modifiers: rawEvent.crowd_modifiers || {},
  };
}

function setStatus(message, state = 'info') {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `status status-${state}`;
}

function applyEvents(normalizedEvents) {
  events = normalizedEvents;
  logEl.innerHTML = '';
  currentIndex = 0;
  lastTick = 0;
  playing = true;
  playPauseBtn.textContent = 'Pause';
  if (!events.length) {
    setStatus('No events available in replay feed.', 'error');
    return;
  }
  setStatus(`Loaded ${events.length} pitches from replay feed.`, 'success');
  stepOnce();
}

async function fetchReplayPayload() {
  const response = await fetch(`${FEED_PATH}?t=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Replay feed unavailable (${response.status})`);
  }
  return response.json();
}

function versionFromPayload(payload) {
  return [payload.updated_at, payload.game_id, payload.events?.length].join('|');
}

async function loadEvents({ silent = false } = {}) {
  if (!silent) {
    setStatus('Loading replay feed…', 'loading');
  }

  try {
    const payload = await fetchReplayPayload();
    const version = versionFromPayload(payload);
    const normalizedEvents = (payload.events || [])
      .map((evt, idx) => normalizeEvent(evt, idx))
      .filter(Boolean);

    if (version && version === feedVersion && silent) {
      return;
    }

    feedVersion = version;
    applyEvents(normalizedEvents);
  } catch (error) {
    setStatus(`Failed to load feed: ${error.message}`, 'error');
    throw error;
  }
}

async function refreshLoop() {
  await loadEvents({ silent: true }).catch(() => null);
}

loadEvents();
setInterval(refreshLoop, POLL_INTERVAL_MS);
requestAnimationFrame(loop);

