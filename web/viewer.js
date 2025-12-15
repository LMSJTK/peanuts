const canvas = document.getElementById('field');
const ctx = canvas.getContext('2d');
const logEl = document.getElementById('log');
const energyBar = document.getElementById('energyBar');
const energyValue = document.getElementById('energyValue');
const playPauseBtn = document.getElementById('playPause');
const stepBtn = document.getElementById('step');
const skipBtn = document.getElementById('skip');
const speedInput = document.getElementById('speed');

let events = [];
let currentIndex = 0;
let playing = true;
let lastTick = 0;
let tickDelay = Number(speedInput.value);

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
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.innerHTML = `<strong>#${event.number}</strong> ${event.batter}: ${event.outcome} (${event.balls_before}-${event.strikes_before} → ${event.balls_after}-${event.strikes_after}), bases ${event.bases_before.join('')} → ${event.bases_after.join('')}`;
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

async function loadEvents() {
  const response = await fetch('sample_events.json');
  events = await response.json();
  logEl.innerHTML = '';
  currentIndex = 0;
  lastTick = 0;
  playing = true;
  playPauseBtn.textContent = 'Pause';
  stepOnce();
}

loadEvents();
requestAnimationFrame(loop);

