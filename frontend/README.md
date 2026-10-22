# frontend

The driver-facing web app, built with React and Vite. **Owners: Thomas and Kailesh.**

| File             | What it does |
|------------------|--------------|
| `src/App.jsx`    | The page: availability cards, reserve form, your reservation with step-by-step directions and the moving dot, and the lot. Refreshes every 5 seconds. |
| `src/LotMap.jsx` | Draws the lot as an SVG map: one-way roads with arrows, gates, trees, bays, parked cars, the blue route and the moving dot. |
| `src/api.js`     | One small function per backend URL in [`docs/api.md`](../docs/api.md). |
| `src/App.css`    | The styles. |
| `src/main.jsx`   | Starts React. |
| `vite.config.js` | While developing, forwards API calls to the backend on port 8000. |

## Installable app (PWA)
The site can be installed on a phone like an app. Files in `public/`:

| File                    | What it does |
|-------------------------|--------------|
| `manifest.webmanifest`  | App name, colours, icons, and `display: standalone` (opens full-screen, no browser bar). |
| `sw.js`                 | Service worker. Keeps a copy of the page so the app opens offline. It never saves parking data; that always comes live from the server. |
| `icon-*.png`, `apple-touch-icon.png`, `favicon.png` | App icons. |

Installing needs the deployed `https` address:
- **iPhone (Safari):** Share button, then **Add to Home Screen**.
- **Android (Chrome):** menu, then **Install app** (or **Add to Home screen**).

## Run while developing
Start the backend first (see the main README), then:

```bash
cd frontend
npm install
npm run dev        # opens http://localhost:5173
```

To point at a different backend, set `VITE_API_URL` (for example `VITE_API_URL=https://my-backend.example.com npm run dev`). If it is not set, the app calls the same server that served the page.

## Build
`npm run build` creates the `dist/` folder. The backend serves it automatically, so the whole app runs from one server.
