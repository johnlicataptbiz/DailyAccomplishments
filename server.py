import logging
import os
import re
from flask import Flask, send_from_directory, redirect
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.route("/healthz")

def healthz():
    return "ok", 200

SITE_DIR = os.environ.get("SITE_DIR", "site")

# Regex to match the legacy ActivityReport file format
report_pattern = re.compile(r'^ActivityReport-(\d{4}-\d{2}-\d{2})\.json$')

@app.route('/<path:path>')
def serve_static(path):
    """
    Serve static files from the SITE_DIR.
    Handles the redirection for legacy ActivityReport URLs.
    """
    # Check if the requested path matches the legacy report format
    match = report_pattern.match(path)
    if match:
        date = match.group(1)
        # Redirect to the new URL structure
        new_url = f'/reports/{date}/ActivityReport-{date}.json'
        logging.info(f"Redirecting legacy report URL: /{path} -> {new_url}")
        parsed = urlparse(new_url.replace('\\', ''))
        if not parsed.scheme and not parsed.netloc:
            return redirect(new_url, code=301)
        logging.warning(f"Unsafe redirect target ({new_url}), redirecting to root.")
        return redirect('/', code=302)
    
    # Serve the file from the static directory
    return send_from_directory(SITE_DIR, path)

@app.route('/')
def serve_root():
    """Serve the index.html from the root of the site."""
    return send_from_directory(SITE_DIR, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
