/**
 * SalaryAI v2 — script.js
 * Handles prediction, history table, stats, search, pagination, delete
 * © 2026 SalaryAI
 */

'use strict';

const API = 'http://127.0.0.1:8000';
const PAGE_SIZE = 10;

/* ============================================================
   DOM REFS
   ============================================================ */
const form        = document.getElementById('salaryForm');
const predictBtn  = document.getElementById('predictBtn');
const resultBox   = document.getElementById('resultBox');
const salaryOutput = document.getElementById('salaryOutput');
const resultMeta  = document.getElementById('resultMeta');

const historyBody    = document.getElementById('historyBody');
const historyEmpty   = document.getElementById('historyEmpty');
const historyLoading = document.getElementById('historyLoading');
const historyCount   = document.getElementById('historyCount');
const historySearch  = document.getElementById('historySearch');
const btnRefresh     = document.getElementById('btnRefresh');
const pagination     = document.getElementById('pagination');
const btnPrev        = document.getElementById('btnPrev');
const btnNext        = document.getElementById('btnNext');
const pageInfo       = document.getElementById('pageInfo');

const statTotal = document.getElementById('statTotal');
const statAvg   = document.getElementById('statAvg');
const statMax   = document.getElementById('statMax');
const statMin   = document.getElementById('statMin');

const deleteModal   = document.getElementById('deleteModal');
const modalCancel   = document.getElementById('modalCancel');
const modalConfirm  = document.getElementById('modalConfirm');

/* ============================================================
   STATE
   ============================================================ */
let currentPage     = 0;          // 0-indexed offset pages
let totalRecords    = 0;
let searchQuery     = '';
let allRecords      = [];         // full local cache for search
let deleteTargetId  = null;

/* ============================================================
   TOAST
   ============================================================ */
function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toastMessage');
  toast.className = `toast show ${type}`;
  toastMsg.textContent = message;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 4000);
}

/* ============================================================
   CURRENCY FORMAT
   ============================================================ */
const fmt = (n) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);

/* ============================================================
   STATS
   ============================================================ */
async function loadStats() {
  try {
    const res = await fetch(`${API}/stats`);
    if (!res.ok) return;
    const d = await res.json();
    statTotal.textContent = d.total_predictions.toLocaleString();
    statAvg.textContent   = d.avg_salary   ? fmt(d.avg_salary)   : '—';
    statMax.textContent   = d.max_salary   ? fmt(d.max_salary)   : '—';
    statMin.textContent   = d.min_salary   ? fmt(d.min_salary)   : '—';
  } catch (_) { /* silently fail */ }
}

/* ============================================================
   HISTORY — LOAD FROM API
   ============================================================ */
async function loadHistory(page = 0) {
  historyLoading.hidden = false;
  historyEmpty.hidden   = true;
  historyBody.innerHTML = '';
  pagination.hidden     = true;

  try {
    const offset = page * PAGE_SIZE;
    const res    = await fetch(`${API}/history?limit=${PAGE_SIZE}&offset=${offset}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    totalRecords = data.total;
    allRecords   = data.records;    // cache for search
    currentPage  = page;

    renderRows(data.records);
    updatePagination();
    historyCount.textContent = `${totalRecords.toLocaleString()} record${totalRecords !== 1 ? 's' : ''}`;

  } catch (err) {
    historyBody.innerHTML = `
      <tr><td colspan="9" style="text-align:center;padding:2rem;color:#e03e3e;">
        <i class="fas fa-exclamation-triangle"></i>
        Could not load history — is the API running?
      </td></tr>`;
    console.error('[SalaryAI] History load error:', err);
  } finally {
    historyLoading.hidden = true;
  }
}

/* ============================================================
   RENDER TABLE ROWS
   ============================================================ */
function renderRows(records) {
  historyBody.innerHTML = '';

  const filtered = searchQuery
    ? records.filter(r =>
        r.job_role.toLowerCase().includes(searchQuery) ||
        r.location.toLowerCase().includes(searchQuery) ||
        r.education_level.toLowerCase().includes(searchQuery)
      )
    : records;

  if (filtered.length === 0) {
    historyEmpty.hidden = false;
    return;
  }
  historyEmpty.hidden = true;

  const offset = currentPage * PAGE_SIZE;

  filtered.forEach((r, i) => {
    const dt = new Date(r.created_at);
    const dateStr = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    const timeStr = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    const tr = document.createElement('tr');
    tr.style.animationDelay = `${i * 0.03}s`;
    tr.innerHTML = `
      <td class="cell-id">${offset + i + 1}</td>
      <td class="cell-salary">${fmt(r.predicted_salary)}</td>
      <td>${r.years_experience} yrs</td>
      <td>${r.age}</td>
      <td><span class="chip chip--edu">${r.education_level}</span></td>
      <td><span class="chip chip--role">${r.job_role}</span></td>
      <td><span class="chip chip--loc">${r.location}</span></td>
      <td>
        <span style="display:block;line-height:1.2">
          <span style="font-weight:600">${dateStr}</span><br>
          <span style="font-size:0.75rem;color:var(--text-light)">${timeStr}</span>
        </span>
      </td>
      <td>
        <button class="btn-delete" data-id="${r.id}" title="Delete record">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    `;
    historyBody.appendChild(tr);
  });

  // Attach delete listeners
  historyBody.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', () => {
      deleteTargetId = parseInt(btn.dataset.id);
      deleteModal.hidden = false;
    });
  });
}

/* ============================================================
   PAGINATION
   ============================================================ */
function updatePagination() {
  const totalPages = Math.ceil(totalRecords / PAGE_SIZE);
  if (totalPages <= 1) { pagination.hidden = true; return; }

  pagination.hidden = false;
  btnPrev.disabled  = currentPage === 0;
  btnNext.disabled  = currentPage >= totalPages - 1;
  pageInfo.textContent = `Page ${currentPage + 1} of ${totalPages}`;
}

btnPrev.addEventListener('click', () => {
  if (currentPage > 0) loadHistory(currentPage - 1);
});
btnNext.addEventListener('click', () => {
  loadHistory(currentPage + 1);
});

/* ============================================================
   SEARCH (client-side on cached page)
   ============================================================ */
let searchDebounce;
historySearch.addEventListener('input', () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    searchQuery = historySearch.value.trim().toLowerCase();
    renderRows(allRecords);
  }, 250);
});

/* ============================================================
   REFRESH BUTTON
   ============================================================ */
btnRefresh.addEventListener('click', async () => {
  btnRefresh.classList.add('spinning');
  await Promise.all([loadHistory(currentPage), loadStats()]);
  btnRefresh.classList.remove('spinning');
});

/* ============================================================
   DELETE MODAL
   ============================================================ */
modalCancel.addEventListener('click', () => {
  deleteModal.hidden = true;
  deleteTargetId = null;
});

modalConfirm.addEventListener('click', async () => {
  if (!deleteTargetId) return;
  deleteModal.hidden = true;

  try {
    const res = await fetch(`${API}/history/${deleteTargetId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast('Record deleted.', 'success');
    await Promise.all([loadHistory(currentPage), loadStats()]);
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  } finally {
    deleteTargetId = null;
  }
});

// Close modal clicking overlay
deleteModal.addEventListener('click', (e) => {
  if (e.target === deleteModal) {
    deleteModal.hidden = true;
    deleteTargetId = null;
  }
});

/* ============================================================
   PREDICTION FORM
   ============================================================ */
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const payload = {
    years_experience: parseFloat(document.getElementById('experience').value),
    age:              parseInt(document.getElementById('age').value),
    education_level:  document.getElementById('education').value,
    job_role:         document.getElementById('role').value,
    location:         document.getElementById('location').value,
  };

  // Basic validation
  if (isNaN(payload.years_experience) || isNaN(payload.age)) {
    showToast('Please fill in all fields correctly.', 'error');
    return;
  }

  // Loading state
  predictBtn.disabled = true;
  predictBtn.innerHTML = '<div class="spinner"></div><span>Predicting…</span>';
  resultBox.classList.remove('show');

  try {
    const res = await fetch(`${API}/predict`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    const result = await res.json();

    if (res.ok) {
      salaryOutput.textContent = fmt(result.predicted_salary);
      resultMeta.textContent   =
        `${payload.job_role} · ${payload.education_level} · ${payload.location} · ${payload.years_experience} yrs exp`;
      resultBox.classList.add('show');

      const savedNote = result.saved ? ' & saved to database' : '';
      showToast(`Prediction complete${savedNote}! 🎉`, 'success');

      // Refresh history + stats after a short delay (let DB commit)
      setTimeout(() => Promise.all([loadHistory(0), loadStats()]), 600);

    } else {
      showToast('Error: ' + (result.detail || 'Unknown error'), 'error');
    }

  } catch (err) {
    showToast('Cannot connect to API. Is it running at port 8000?', 'error');
    console.error('[SalaryAI] Predict error:', err);
  } finally {
    predictBtn.disabled = false;
    predictBtn.innerHTML = '<span>Predict Salary</span><i class="fas fa-arrow-right"></i>';
  }
});

/* ============================================================
   INIT ON PAGE LOAD
   ============================================================ */
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadHistory(0);
});
