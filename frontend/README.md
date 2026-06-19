# MediScanAI — Frontend

Interface React de MediScanAI (viewer DICOM, pipeline IA, rapports cliniques).

La documentation complète du projet (installation, configuration, API, utilisation) se trouve dans le **[README principal](../README.md)**.

## Commandes

```powershell
npm install          # Installer les dépendances
npm run dev          # Dev server → http://localhost:5173
npm run build        # Build production → dist/
npm run lint         # ESLint
npm run preview      # Prévisualiser le build
```

## Stack

React 19 · TypeScript · Vite 8 · Tailwind v4 · Zustand · React Query · Cornerstone.js · Three.js · Recharts · Framer Motion

## Proxy API

En développement, les requêtes `/api/*` sont proxifiées vers `http://localhost:8000` (voir `vite.config.ts`). Le backend doit être lancé en parallèle.
