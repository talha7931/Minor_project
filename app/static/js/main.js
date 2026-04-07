/* GateANPR — Main JavaScript */
'use strict';

// ---- Theme (light/dark) ----
const THEME_STORAGE_KEY = 'gateanpr_theme';
const rootEl = document.documentElement;
const themeToggle = document.getElementById('themeToggle');
const themeToggleLabel = document.getElementById('themeToggleLabel');

function preferredTheme() {
  const saved = window.localStorage ? window.localStorage.getItem(THEME_STORAGE_KEY) : null;
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  rootEl.setAttribute('data-theme', theme);
  if (themeToggle) {
    themeToggle.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
  }
  if (themeToggleLabel) {
    themeToggleLabel.textContent = theme === 'dark' ? 'Dark' : 'Light';
  }
}

applyTheme(preferredTheme());

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const current = rootEl.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    try {
      window.localStorage && window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch (e) {
      // If storage is blocked, we still apply the theme for this session.
    }
    applyTheme(next);
  });
}

// ---- Sidebar toggle ----
const sidebar = document.getElementById('sidebar');
const sidebarOpen = document.getElementById('sidebarOpen');
const sidebarClose = document.getElementById('sidebarClose');
const overlay = document.getElementById('sidebarOverlay');

function openSidebar() {
  sidebar && sidebar.classList.add('open');
  overlay && overlay.classList.add('active');
}

function closeSidebar() {
  sidebar && sidebar.classList.remove('open');
  overlay && overlay.classList.remove('active');
}

sidebarOpen && sidebarOpen.addEventListener('click', openSidebar);
sidebarClose && sidebarClose.addEventListener('click', closeSidebar);
overlay && overlay.addEventListener('click', closeSidebar);

// ---- Clock ----
const clock = document.getElementById('topbarClock');
function updateClock() {
  if (!clock) return;
  const now = new Date();
  clock.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
updateClock();
setInterval(updateClock, 1000);

// ---- Auto-dismiss flash alerts ----
const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
document.querySelectorAll('#toastContainer .alert').forEach(el => {
  setTimeout(() => {
    el.style.opacity = '0';
    if (!reduceMotion) el.style.transition = 'opacity 0.35s';
    setTimeout(() => el.remove(), reduceMotion ? 0 : 350);
  }, 4500);
});

// ---- Uppercase plate inputs ----
document.querySelectorAll('input[style*="text-transform:uppercase"], input[style*="text-transform: uppercase"]').forEach(inp => {
  inp.addEventListener('input', () => { inp.value = inp.value.toUpperCase(); });
});

// ---- Confirm dialogs ----
// Add `data-confirm="Your message"` on links/buttons that need confirmation.
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', (e) => {
    const msg = el.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) {
      e.preventDefault();
      e.stopPropagation();
    }
  });
});

// ---- Confirm dialogs (premium, accessible) ----
// Use: add data-confirm="Message" to <a> or <button type="submit">.
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', (e) => {
    const msg = el.getAttribute('data-confirm');
    if (!msg) return;
    // Keep it lightweight: use native confirm for now; styled modal can be added later.
    if (!window.confirm(msg)) {
      e.preventDefault();
      e.stopPropagation();
    }
  });
});
