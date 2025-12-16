Sample extension to test robust chrome.runtime.onMessage handling

How to load and test locally:

1. Open Chrome/Edge and go to `chrome://extensions/` (or `edge://extensions/`).
2. Enable **Developer mode** (top-right).
3. Click **Load unpacked** and point to this folder:
   `workspaces/DailyAccomplishments/tools/sample_extension_test`
4. Once loaded, open this repository's local dashboard in a tab:
   `http://localhost:8000/dashboard.html?date=2025-12-04`
5. Check the page console (F12) — the content script will send a test message to the background and log the response.
6. Open the extension popup (click the extension action toolbar icon) and click **Send Async Message** to exercise the popup -> background flow.

This extension's background listener always calls `sendResponse` (or a timeout fallback) and wraps sendResponse in try/catch, preventing the "Unchecked runtime.lastError: A listener indicated an asynchronous response..." error when the sender remains active.

If you want me to produce a ZIP of this folder for easier loading, tell me and I will create an archive you can download.
