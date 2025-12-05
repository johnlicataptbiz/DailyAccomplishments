// background.js (service worker)

// Example async operation used by the listener
async function someAsyncOperation(payload) {
  // Simulate async work (e.g., fetch or DB op)
  await new Promise(r => setTimeout(r, 800));
  return { echo: payload, time: new Date().toISOString() };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[sample ext] onMessage received:', message, 'from', sender?.tab?.id ?? 'popup');
  let responded = false;

  const safeRespond = (payload) => {
    if (responded) return;
    responded = true;
    try {
      sendResponse(payload);
    } catch (err) {
      // Port may be closed; log and continue
      console.warn('[sample ext] sendResponse failed (port closed?):', err && err.message);
    }
  };

  const timeout = setTimeout(() => {
    if (!responded) {
      safeRespond({ ok: false, error: 'timeout' });
    }
  }, 4000);

  (async () => {
    try {
      if (message?.action === 'doSomethingAsync') {
        const result = await someAsyncOperation(message.payload || {});
        clearTimeout(timeout);
        safeRespond({ ok: true, result });
        return;
      }

      if (message?.action === 'getSync') {
        clearTimeout(timeout);
        safeRespond({ ok: true, data: { now: new Date().toISOString() } });
        return;
      }

      clearTimeout(timeout);
      safeRespond({ ok: false, error: 'unknown_action' });
    } catch (err) {
      clearTimeout(timeout);
      safeRespond({ ok: false, error: err?.message || String(err) });
    }
  })();

  // We will call sendResponse asynchronously
  return true;
});
