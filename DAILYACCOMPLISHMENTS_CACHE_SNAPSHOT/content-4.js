// content.js
// Sends a test message to the background service worker once the page loads.

window.addEventListener('DOMContentLoaded', () => {
  console.log('[sample ext content] sending test message to background');
  chrome.runtime.sendMessage({ action: 'doSomethingAsync', payload: { page: location.href } }, (resp) => {
    if (chrome.runtime.lastError) {
      console.warn('[sample ext content] runtime.lastError:', chrome.runtime.lastError.message);
      return;
    }
    console.log('[sample ext content] got response:', resp);
  });
});
