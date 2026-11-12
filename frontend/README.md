# frontend

The driver-facing website. **Owners: Thomas and Kailesh.**

It is one file, `index.html`, written in plain HTML, CSS and JavaScript. There is nothing to install or build: the backend serves this file, so start the backend and open http://localhost:8000.

Inside `index.html`, top to bottom:

| Part | What it does |
|------|--------------|
| `<style>` | How the page looks. |
| The HTML | The free-slot cards, the reserve form, your reservation (directions and buttons), and the empty map. |
| `api()` | Sends one request to the backend (the URLs are in [`../docs/api.md`](../docs/api.md)). |
| `refresh()` | Runs every 5 seconds: loads the slots and your reservation, then redraws the page. |
| `drawMap()` | Draws the lot as an SVG picture: one-way roads with arrows, gates, trees, bays, parked cars and your blue route. |
| `drawDot()` | Places the moving dot on the route and highlights the current direction. |
| The button handlers | Reserve, Start guidance, I have arrived, Cancel, I am leaving. |
