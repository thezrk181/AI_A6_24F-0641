const gridEl = document.getElementById('grid');
const rowsInput = document.getElementById('rowsInput');
const colsInput = document.getElementById('colsInput');
const pitProbInput = document.getElementById('pitProbInput');
const newEpisodeBtn = document.getElementById('newEpisodeBtn');
const autoStepBtn = document.getElementById('autoStepBtn');
const inferenceStepsEl = document.getElementById('inferenceSteps');
const currentPerceptsEl = document.getElementById('currentPercepts');
const agentPositionEl = document.getElementById('agentPosition');
const statusMessageEl = document.getElementById('statusMessage');

let currentState = null;

function isAdjacent(a, b) {
  return Math.abs(a.r - b.r) + Math.abs(a.c - b.c) === 1;
}

function perceptText(percepts) {
  const active = [];
  if (percepts.breeze) active.push('Breeze');
  if (percepts.stench) active.push('Stench');
  return active.length ? active.join(', ') : 'None';
}

function updateDashboard(state) {
  inferenceStepsEl.textContent = state.inferenceSteps;
  currentPerceptsEl.textContent = perceptText(state.percepts);
  agentPositionEl.textContent = `(${state.agent.r},${state.agent.c})`;
  statusMessageEl.textContent = state.message || '';
}

function renderGrid(state) {
  gridEl.style.gridTemplateColumns = `repeat(${state.cols}, minmax(46px, 1fr))`;
  gridEl.innerHTML = '';

  for (let r = 0; r < state.rows; r += 1) {
    for (let c = 0; c < state.cols; c += 1) {
      const cell = state.grid[r][c];
      const div = document.createElement('button');
      div.className = `cell ${cell.status}${cell.agent ? ' agent' : ''}`;
      div.textContent = `${r},${c}`;
      div.title = `Cell (${r},${c})`; 

      const canAttemptMove = isAdjacent(state.agent, { r, c });
      if (canAttemptMove) {
        div.classList.add('clickable');
        div.addEventListener('click', () => moveAgent(r, c));
      } else {
        div.disabled = true;
      }

      gridEl.appendChild(div);
    }
  }
}

function applyState(state) {
  currentState = state;
  updateDashboard(state);
  renderGrid(state);
}

async function apiCall(url, method = 'GET', payload = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (payload) options.body = JSON.stringify(payload);

  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function startEpisode() {
  const payload = {
    rows: Number(rowsInput.value),
    cols: Number(colsInput.value),
    pitProbability: Number(pitProbInput.value),
  };
  const state = await apiCall('/api/new-episode', 'POST', payload);
  applyState(state);
}

async function autoStep() {
  const state = await apiCall('/api/auto-step', 'POST', {});
  applyState(state);
}

async function moveAgent(r, c) {
  const state = await apiCall('/api/move', 'POST', { r, c });
  applyState(state);
}

newEpisodeBtn.addEventListener('click', async () => {
  try {
    await startEpisode();
  } catch (err) {
    statusMessageEl.textContent = `Error: ${err.message}`;
  }
});

autoStepBtn.addEventListener('click', async () => {
  try {
    await autoStep();
  } catch (err) {
    statusMessageEl.textContent = `Error: ${err.message}`;
  }
});

(async () => {
  try {
    const state = await apiCall('/api/state');
    applyState(state);
  } catch (err) {
    statusMessageEl.textContent = `Error: ${err.message}`;
  }
})();
