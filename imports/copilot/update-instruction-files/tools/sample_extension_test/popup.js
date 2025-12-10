document.getElementById('btnAsync').addEventListener('click', () => {
  const resultEl = document.getElementById('result');
  resultEl.textContent = 'Sending...';
  chrome.runtime.sendMessage({ action: 'doSomethingAsync', payload: { from: 'popup' } }, (resp) => {
    if (chrome.runtime.lastError) {
      resultEl.textContent = `Error: ${chrome.runtime.lastError.message}`;
      return;
    }
    resultEl.textContent = `Response: ${JSON.stringify(resp)}`;
  });
});
