const flagBtn = document.getElementById('flag-btn');
const queueCount = document.getElementById('queue-count');
const msg = document.getElementById('msg');

// Fetch current queue count from server
async function refreshStatus() {
  try {
    const res = await fetch('http://localhost:5123/status');
    if (res.ok) {
      const data = await res.json();
      queueCount.textContent = data.queued ?? '?';
    } else {
      queueCount.textContent = '?';
    }
  } catch {
    queueCount.textContent = '—';
    msg.textContent = 'Server offline';
  }
}

// Enable flag button only on YouTube watch pages
async function checkActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url && tab.url.includes('youtube.com/watch')) {
    flagBtn.disabled = false;
  }
}

flagBtn.addEventListener('click', async () => {
  flagBtn.disabled = true;
  msg.textContent = 'Flagging...';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    msg.textContent = 'No active tab found';
    flagBtn.disabled = false;
    return;
  }

  // Ask content script for the flag action
  chrome.tabs.sendMessage(tab.id, { type: 'TRIGGER_FLAG' });

  // Close popup after short delay
  setTimeout(() => window.close(), 800);
});

checkActiveTab();
refreshStatus();
