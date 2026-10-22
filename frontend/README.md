# frontend

The driver-facing web app, built with React and Vite. **Owners: Thomas and Kailesh.**

| File             | What it does |
|------------------|--------------|
| `src/App.jsx`    | The whole page: availability cards, reserve form, your reservation (arrive / leave / cancel), and the map of the lot. Refreshes every 5 seconds. |
| `src/api.js`     | One small function per backend URL in [`docs/api.md`](../docs/api.md). |
| `src/App.css`    | The styles. |
| `src/main.jsx`   | Starts React. |
| `vite.config.js` | While developing, forwards API calls to the backend on port 8000. |

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
