# Campus Customs Ops Desk (frontend)

React + Vite + TypeScript dashboard for the Campus Customs agent team. It talks to the backend at `http://localhost:8000`.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check and build to dist/
```

Start the backend first (from the project root):

```bash
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
```

Design notes are in `../output/design.md`.
