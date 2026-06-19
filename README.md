# MediScanAI v1.0

Système intelligent d'aide au diagnostic de **fractures cervicales (C1–C7)** à partir d'examens **CT DICOM**, avec inférence IA, visualisation 2D/3D, Grad-CAM et rapports cliniques.

> **Avertissement médical** — MediScanAI est un outil d'aide à la décision. Tout résultat doit être validé par un médecin qualifié avant toute décision clinique.

---

## Fonctionnalités

| Module | Description |
|--------|-------------|
| **Authentification** | JWT, rôles Admin / Médecin |
| **Import DICOM** | Upload par chunks, drag & drop, examen démo |
| **Pipeline IA** | DenseNet-121 2.5D ou mode mock si le modèle est absent |
| **Viewer 2D** | Cornerstone.js — coupes axiales, windowing, pan/zoom |
| **Grad-CAM** | Heatmap d'attention superposée sur les coupes |
| **Viewer 3D** | Reconstruction Marching Cubes + Three.js (C1–C7) |
| **Panels vertèbres** | Scores C1–C7 synchronisés (Zustand) entre toutes les vues |
| **Rapport clinique** | Page imprimable + export PDF (ReportLab) |
| **Dashboard** | Stats du jour / du mois, examens récents |
| **Historique** | Recherche, filtres, pagination |
| **Statistiques** | Graphiques Recharts (7 / 30 / 90 jours) |

---

## Prérequis

| Outil | Version |
|-------|---------|
| Node.js | 20+ |
| Python | 3.11+ |
| npm | 10+ |
| (Optionnel) CUDA | Pour inférence GPU PyTorch |

**Résolution minimale** : 1366×768 (écrans médicaux).

---

## Installation

### 1. Cloner et installer le frontend

```powershell
cd frontend
npm install
```

### 2. Créer l'environnement Python backend

```powershell
cd ..\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> L'installation de PyTorch peut prendre plusieurs minutes. Sans GPU, le mode **mock** est activé automatiquement.

### 3. (Optionnel) Modèle IA entraîné

Placer le fichier de poids ici :

```
backend/model/final_best_densenet121_25d.pth
```

Sans ce fichier, le pipeline utilise des scores mock réalistes (C5 ~97 % en démo).

---

## Lancement

Ouvrir **deux terminaux** :

**Terminal 1 — API FastAPI**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend Vite**

```powershell
cd frontend
npm run dev
```

| Service | URL |
|---------|-----|
| Application | http://localhost:5173 |
| API | http://localhost:8000 |
| Docs OpenAPI | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/health |

Le proxy Vite redirige `/api/*` vers le backend (`frontend/vite.config.ts`).

### Docker (optionnel)

```powershell
docker compose up --build
```

---

## Comptes par défaut

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Administrateur | `admin@mediscanai.cd` | `Admin2025!` |
| Médecin | `dr.kabila@mediscanai.cd` | `Medecin2025!` |

Les comptes sont créés automatiquement au premier démarrage du backend.

---

## Utilisation

### Parcours rapide (démo)

1. Se connecter avec un compte médecin
2. Aller sur **Nouvel examen** (`/import`)
3. Cliquer **Charger un examen démo** (ou uploader des fichiers `.dcm`)
4. Cliquer **Analyser cet examen** → redirection vers le viewer
5. Explorer les onglets **Axiale** / **3D**, les scores C1–C7, le Grad-CAM
6. Ouvrir **Rapport clinique** ou **Exporter PDF** depuis le panneau gauche

### Import DICOM réel

- Glisser un dossier d'examen (fichiers `.dcm`) ou les sélectionner
- Saisir un **Patient ID** (ex. `PAT-2025-001`)
- L'upload se fait par paquets de 50 fichiers pour les gros examens
- Métadonnées extraites : Study UID, date, nombre de coupes, dimensions

---

## Routes de l'application

| Route | Description |
|-------|-------------|
| `/login` | Connexion |
| `/dashboard` | Tableau de bord |
| `/import` | Import DICOM |
| `/historique` | Examens archivés (recherche + filtres) |
| `/statistiques` | Graphiques analytiques |
| `/viewer/:studyId` | Viewer principal (2D + 3D + IA) |
| `/rapport/:studyId` | Rapport clinique imprimable |
| `/parametres` | Paramètres |
| `/profil` | Profil utilisateur |

---

## API principale

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/auth/login` | Authentification JWT |
| `GET` | `/api/auth/me` | Utilisateur courant |
| `POST` | `/api/examens/upload` | Upload DICOM (multipart) |
| `GET` | `/api/demo/load-sample` | Examen démo synthétique |
| `POST` | `/api/analyse/{study_id}` | Lancer l'analyse IA |
| `GET` | `/api/analyse/{study_id}/resultats` | Scores C1–C7 + rapport |
| `GET` | `/api/images/{study_id}/coupe/{n}` | Coupe PNG (axial/sagittal/coronal) |
| `GET` | `/api/images/{study_id}/gradcam/{n}` | Heatmap Grad-CAM |
| `GET` | `/api/images/{study_id}/reconstruction-3d` | Maillage 3D JSON |
| `GET` | `/api/images/{study_id}/export-pdf` | Rapport PDF |
| `GET` | `/api/stats/dashboard` | Stats tableau de bord |
| `GET` | `/api/stats/historique?period=30d` | Stats analytiques |

Documentation interactive : http://localhost:8000/docs

---

## Configuration

Variables d'environnement optionnelles (fichier `backend/.env`) :

```env
SECRET_KEY=votre-cle-secrete-en-production
DATABASE_URL=sqlite:///./mediscanai.db
DEBUG=false
MODEL_PATH=model/final_best_densenet121_25d.pth
```

| Variable | Défaut | Description |
|----------|--------|-------------|
| `SECRET_KEY` | *(dev)* | Clé JWT — **à changer en production** |
| `DATABASE_URL` | SQLite local | Base de données |
| `MODEL_PATH` | `model/final_best_densenet121_25d.pth` | Chemin relatif au dossier `backend/` |
| `CORS_ORIGINS` | `localhost:5173` | Origines autorisées |

---

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

**16 tests** couvrant le pipeline IA mock, les endpoints d'analyse, les images (Grad-CAM, 3D, PDF) et l'authentification.

---

## Structure du projet

```
MediscanAI_V2/
├── frontend/                 # React 18 + TypeScript + Vite + Tailwind v4
│   ├── src/
│   │   ├── api/              # Client Axios
│   │   ├── components/       # UI, viewer, dashboard, report…
│   │   ├── pages/            # Routes React
│   │   ├── store/            # Zustand (auth, viewer)
│   │   └── types/            # Interfaces TypeScript strictes
│   └── vite.config.ts        # Proxy /api → :8000
│
├── backend/
│   ├── app/
│   │   ├── api/              # Routes FastAPI
│   │   ├── models/           # SQLAlchemy (SQLite)
│   │   ├── schemas/          # Pydantic
│   │   └── services/         # DICOM, IA, reconstruction, rapport…
│   ├── model/                # Poids PyTorch (.pth)
│   ├── cache/                # Maillages 3D + uploads temporaires
│   └── tests/                # pytest
│
├── data/
│   ├── uploads/              # Examens DICOM importés
│   └── sample/               # PNG synthétiques pour la démo
│
├── docker-compose.yml
└── CURSOR_PROMPT_MEDISCANAI.md   # Spécification complète
```

---

## Stack technique

**Frontend** — React 19, TypeScript strict, Vite 8, Tailwind CSS v4, Zustand, React Query, Framer Motion, Cornerstone.js, Three.js, Recharts

**Backend** — FastAPI, SQLAlchemy + SQLite, PyTorch + timm (DenseNet-121), pydicom, scikit-image (Marching Cubes), ReportLab (PDF), bcrypt (JWT)

---

## Dépannage

| Problème | Solution |
|----------|----------|
| `401 Unauthorized` | Se reconnecter — token JWT expiré (60 min) |
| Analyse bloquée | Vérifier les logs backend ; relancer avec **Réessayer** |
| Mode **Mock** affiché | Normal si `final_best_densenet121_25d.pth` est absent |
| Erreur upload SQLite | Arrêter le serveur avant de supprimer `mediscanai.db` |
| Cornerstone ne charge pas | Vérifier que le backend tourne (proxy `/api`) |
| PowerShell `&&` | Utiliser `;` entre les commandes |

---

## Build production

```powershell
# Frontend
cd frontend
npm run build        # → frontend/dist/

# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Servir frontend/dist/ via nginx ou en statique
```

---

## Licence

Usage interne — projet médical de recherche et d'aide au diagnostic.

---

*MediScanAI v1.0 — Généré pour le diagnostic assisté de fractures cervicales C1–C7.*
