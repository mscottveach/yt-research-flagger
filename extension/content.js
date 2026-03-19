// YT Research Flagger - Content Script
// Injects a flag button into YouTube video pages and handles Alt+S shortcut

const BUTTON_ID = 'yt-research-flag-btn';
const TOAST_ID = 'yt-research-toast';

function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('v');
}

function getVideoTitle() {
  // Try multiple selectors since YouTube's DOM changes
  const selectors = [
    'h1.ytd-watch-metadata yt-formatted-string',
    'h1.title.ytd-video-primary-info-renderer',
    '#title h1 yt-formatted-string',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.textContent.trim()) return el.textContent.trim();
  }
  return document.title.replace(' - YouTube', '').trim();
}

function showToast(message, isError = false) {
  let toast = document.getElementById(TOAST_ID);
  if (toast) toast.remove();

  toast = document.createElement('div');
  toast.id = TOAST_ID;
  toast.textContent = message;
  Object.assign(toast.style, {
    position: 'fixed',
    bottom: '80px',
    right: '24px',
    background: isError ? '#cc0000' : '#065fd4',
    color: '#fff',
    padding: '10px 18px',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: 'Roboto, sans-serif',
    fontWeight: '500',
    zIndex: '99999',
    boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
    transition: 'opacity 0.3s ease',
    opacity: '1',
  });
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

function flagCurrentVideo() {
  const videoId = getVideoId();
  if (!videoId) {
    showToast('No video detected on this page', true);
    return;
  }

  const title = getVideoTitle();
  const url = window.location.href;

  // Send to background service worker, which will POST to Flask
  chrome.runtime.sendMessage(
    { type: 'FLAG_VIDEO', videoId, title, url },
    (response) => {
      if (chrome.runtime.lastError) {
        showToast('Extension error: ' + chrome.runtime.lastError.message, true);
        return;
      }
      if (response && response.success) {
        showToast('Flagged for research');
      } else {
        const msg = response && response.error ? response.error : 'Could not reach server (is it running?)';
        showToast(msg, true);
      }
    }
  );
}

function injectButton() {
  if (document.getElementById(BUTTON_ID)) return;

  // Target the YouTube action buttons row
  const actionsRow = document.querySelector('#actions-inner #menu');
  if (!actionsRow) return;

  const btn = document.createElement('button');
  btn.id = BUTTON_ID;
  btn.title = 'Flag for research (Alt+S)';
  btn.textContent = '🔖 Flag';
  Object.assign(btn.style, {
    background: 'none',
    border: '1px solid #3ea6ff',
    borderRadius: '18px',
    color: '#3ea6ff',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    fontFamily: 'Roboto, sans-serif',
    padding: '6px 14px',
    marginLeft: '8px',
    verticalAlign: 'middle',
    lineHeight: '1',
  });

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    flagCurrentVideo();
  });

  // Insert before the first child of the menu row
  actionsRow.insertBefore(btn, actionsRow.firstChild);
}

// YouTube is a SPA — watch for DOM changes to re-inject button after navigation
const observer = new MutationObserver(() => {
  if (window.location.pathname === '/watch') {
    injectButton();
  }
});

observer.observe(document.body, { childList: true, subtree: true });

// Also try on initial load
injectButton();

// Keyboard shortcut: Alt+S
document.addEventListener('keydown', (e) => {
  if (e.altKey && (e.key === 's' || e.key === 'S') && !e.ctrlKey && !e.metaKey) {
    // Make sure we're not in a text input
    const tag = document.activeElement && document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    e.preventDefault();
    flagCurrentVideo();
  }
});

// Listen for messages from the background worker (e.g., command shortcut fired)
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'TRIGGER_FLAG') {
    flagCurrentVideo();
  }
});
