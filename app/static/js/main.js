/* GateANPR — Main JavaScript */
'use strict';

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
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 0.5s'; setTimeout(() => el.remove(), 500); }, 5000);
});

// ---- Uppercase plate inputs ----
document.querySelectorAll('input[style*="text-transform:uppercase"], input[style*="text-transform: uppercase"]').forEach(inp => {
  inp.addEventListener('input', () => { inp.value = inp.value.toUpperCase(); });
});
