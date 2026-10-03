# frontend

The driver-facing web app, built with React. **Owners: Thomas and Kailesh.** This folder is intentionally empty until the app is created.

## What it should do
- Let a driver pick their vehicle class (Compact, Sedan, SUV, Full-Size) and reserve a slot.
- Show the assigned slot and live availability per size class.
- Show a map of the lot with the assigned slot highlighted.
- Show clear messages for the "lot full" and "no valid slot" cases.

## How it connects to the backend
- It talks to the backend only through the HTTP API described in [`../docs/api.md`](../docs/api.md).
- Keep the API address in one environment variable (for example `VITE_API_URL`), so switching from mock data to the real backend is a one-line change.
- Until the backend is ready, use mock data that follows the same response shapes.
