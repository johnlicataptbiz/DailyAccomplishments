# Daily Accomplishments home page crawl (2025-12-13)

- **URL:** https://dailyaccomplishments.up.railway.app/
- **Fetched:** 2025-12-13T17:36:00Z
- **Method:** `curl -L` to follow redirects.
- **Notes:** The page bootstraps the dashboard by injecting an iframe. It first tries to load a local `dashboard.html` copy and falls back to the raw GitHub version if the local asset fails to load.

## Saved assets
- `dailyaccomplishments-home-2025-12-13.html`: raw HTML response.

## Observed inline script (excerpt)
```
const t = Date.now();
const qs = window.location.search || "";
const join = qs.includes("?") && qs.length > 1 ? "&" : "?";

const local = `/dashboard.html${qs}${join}t=${t}`;
const raw = `https://raw.githubusercontent.com/johnlicataptbiz/DailyAccomplishments/main/dashboard.html${qs}${join}t=${t}`;

const f = document.createElement("iframe");
f.src = local;
f.onerror = () => { f.src = raw; };
document.body.appendChild(f);
```
