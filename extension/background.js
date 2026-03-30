// YT Research Flagger - Background Service Worker
// Uses Native Messaging to write flagged videos directly to the local queue file.
// No server required — Edge launches native_host.py on demand.

const HOST_NAME = 'com.ytresearch.flagger';

// Seed flagged video IDs into storage on install/update
chrome.runtime.onInstalled.addListener(() => {
  chrome.runtime.sendNativeMessage(HOST_NAME, { type: 'LOAD_ALL' }, (response) => {
    if (chrome.runtime.lastError) {
      console.warn('Could not seed flagged videos:', chrome.runtime.lastError.message);
      return;
    }
    if (response && response.status === 'ok') {
      chrome.storage.local.set({ flaggedVideos: response.videos });
    }
  });
});

// Handle messages from content.js
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'FLAG_VIDEO') {
    flagViaNativeMessaging(message)
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (message.type === 'CHECK_VIDEO') {
    chrome.storage.local.get('flaggedVideos', (data) => {
      const flagged = data.flaggedVideos || {};
      const status = flagged[message.videoId] || null;
      sendResponse({ flagged: status });
    });
    return true;
  }
});

// Handle keyboard command (Alt+S) fired by the browser
chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'flag-video') {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && tab.url.includes('youtube.com/watch')) {
      chrome.tabs.sendMessage(tab.id, { type: 'TRIGGER_FLAG' });
    }
  }
});

async function flagViaNativeMessaging({ videoId, title, url }) {
  const payload = {
    video_id: videoId,
    title: title || '',
    url: url,
    flagged_at: new Date().toISOString(),
  };

  return new Promise((resolve) => {
    chrome.runtime.sendNativeMessage(HOST_NAME, payload, (response) => {
      if (chrome.runtime.lastError) {
        const err = chrome.runtime.lastError.message;
        // Provide a helpful message if setup hasn't been run yet
        const hint = err.includes('not found') || err.includes('Specified native')
          ? 'Run: python pipeline/install_host.py <your-extension-id>'
          : err;
        resolve({ success: false, error: hint });
        return;
      }

      if (response && (response.status === 'queued' || response.status === 'already_queued')) {
        // Sync to storage for fast content-script lookups
        chrome.storage.local.get('flaggedVideos', (data) => {
          const flagged = data.flaggedVideos || {};
          flagged[payload.video_id] = 'pending';
          chrome.storage.local.set({ flaggedVideos: flagged });
        });
        resolve({ success: true, data: response });
      } else {
        resolve({ success: false, error: response?.error || 'Unknown response from host' });
      }
    });
  });
}
