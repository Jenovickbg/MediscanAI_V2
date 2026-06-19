# ============================================================
# CURSOR PROMPT — MediScanAI : Système Intelligent d'Aide
# au Diagnostic de Fractures Cervicales
# Prompt Ingénieur Logiciel Senior — Application Complète
# ============================================================

Tu es un ingénieur logiciel senior spécialisé dans les applications médicales d'imagerie.
Tu vas construire de A à Z l'application MediScanAI, un système professionnel d'aide
au diagnostic orthopédique basé sur l'intelligence artificielle, avec une interface
de niveau laboratoire médical (style OsiriX / 3D Slicer modernisé).

---

## CONTEXTE MÉDICAL ET TECHNIQUE DU PROJET

MediScanAI analyse des examens scanner (CT scan) de la colonne cervicale (C1–C7) au format
DICOM pour détecter des fractures vertébrales. Le pipeline IA est composé de :
- Un classificateur DenseNet-121 2.5D (5 coupes consécutives, recall 95.4%, AUC 0.746)
  qui prédit un score de fracture par coupe
- Un module Grad-CAM qui génère une carte d'activation visuelle sur les coupes positives
- Un module de localisation Faster RCNN (bounding box précise)
- Un générateur de rapport clinique structuré en langage naturel

Le modèle PyTorch est sauvegardé dans `model/final_best_densenet121_25d.pth`.
Les fichiers DICOM sont organisés en `data/train_images/{StudyInstanceUID}/*.dcm`.

---

## STACK TECHNOLOGIQUE — OBLIGATOIRE, NE PAS DÉVIER

### Frontend
- React 18 + TypeScript (strict mode)
- Vite comme bundler
- Tailwind CSS pour le styling
- Three.js (r128+) pour le rendu 3D de la colonne vertébrale
- Cornerstone.js (cornerstone-core + cornerstone-wado-image-loader) pour les vues DICOM
- Chart.js ou Recharts pour les graphiques de scores
- React Router v6 pour la navigation
- Zustand pour le state management global
- React Query (TanStack Query) pour les appels API
- Framer Motion pour les animations fluides
- Lucide React pour les icônes médicales

### Backend
- FastAPI (Python 3.11+) avec Uvicorn
- PyTorch 2.0+ + timm pour le modèle
- pydicom + pylibjpeg pour la lecture DICOM
- scikit-image pour le Marching Cubes (reconstruction 3D)
- scipy pour le resampling volumétrique
- SimpleITK pour le preprocessing médical avancé
- SQLite (via SQLAlchemy) pour la persistance
- Alembic pour les migrations
- Python-multipart pour l'upload de fichiers
- reportlab pour la génération PDF
- python-jose + passlib pour l'authentification JWT

### Structure du projet
```
mediscanai/
├── frontend/               # Application React
│   ├── src/
│   │   ├── components/     # Composants réutilisables
│   │   ├── pages/          # Pages principales
│   │   ├── store/          # Zustand stores
│   │   ├── hooks/          # Custom hooks React
│   │   ├── api/            # Clients API (React Query)
│   │   ├── types/          # TypeScript interfaces
│   │   └── utils/          # Fonctions utilitaires
│   ├── public/
│   └── package.json
├── backend/                # API FastAPI
│   ├── app/
│   │   ├── api/            # Routes FastAPI
│   │   ├── core/           # Config, sécurité, DB
│   │   ├── models/         # Modèles SQLAlchemy
│   │   ├── schemas/        # Schémas Pydantic
│   │   ├── services/       # Logique métier
│   │   └── ai/             # Pipeline IA
│   ├── model/              # Poids du modèle PyTorch
│   └── requirements.txt
└── docker-compose.yml      # Optionnel, si Docker disponible
```

---

## DESIGN SYSTEM — APPLIQUE RIGOUREUSEMENT

### Palette de couleurs (thème médical sombre professionnel)
```css
--bg-primary:     #0A0F1E  /* fond principal - bleu nuit profond */
--bg-secondary:   #0F1629  /* panneaux latéraux */
--bg-tertiary:    #141D35  /* cartes, modales */
--bg-elevated:    #1C2540  /* éléments surélevés */
--border:         #243056  /* bordures subtiles */
--border-light:   #2E3D6B  /* bordures actives */
--accent-blue:    #378ADD  /* couleur principale d'action */
--accent-cyan:    #00C6FF  /* highlights, données actives */
--accent-green:   #00E5A0  /* indicateurs positifs / OK */
--text-primary:   #E8EDF7  /* texte principal */
--text-secondary: #7B8DB8  /* texte secondaire */
--text-muted:     #4A5880  /* texte désactivé */
--danger:         #FF4757  /* fracture / alerte */
--warning:        #FFA048  /* risque modéré */
--safe:           #00E5A0  /* aucune fracture */

/* Couleurs vertèbres par niveau de risque */
--risk-low:    #00E5A0  /* 0–30% */
--risk-medium: #FFA048  /* 30–60% */
--risk-high:   #FF4757  /* 60–100% */
```

### Typographie
- Font principale : Inter (Google Fonts)
- Font monospace (scores, données) : JetBrains Mono
- Taille de base : 14px
- Hiérarchie : 24px (titres) / 16px (sous-titres) / 14px (body) / 12px (labels)

### Composants de base à créer dans `components/ui/`
- `Button` (variantes: primary, ghost, danger, icon-only)
- `Badge` (variantes: success, warning, danger, info, neutral)
- `Card` (avec header, body, footer slots)
- `Tooltip`
- `Modal` (avec backdrop blur)
- `Slider` (style médical, range bleu)
- `ProgressBar`
- `LoadingSpinner` (animation pulse bleu)
- `Divider`

---

## PAGES ET ROUTES

### Route `/login` — Page d'authentification
Interface minimaliste et professionnelle :
- Logo MediScanAI (icône cervicale + texte) centré
- Tagline : "Système Intelligent d'Aide au Diagnostic Orthopédique"
- Champs : Email, Mot de passe (avec toggle affichage)
- Bouton de connexion avec animation de chargement
- Message d'erreur inline si mauvais identifiants
- Fond : gradient radial subtil `#0A0F1E` vers `#141D35`
- Comptes par défaut à créer : `admin@mediscanai.cd / Admin2025!` (Administrateur)
  et `dr.kabila@mediscanai.cd / Medecin2025!` (Médecin)

### Route `/dashboard` — Tableau de bord principal
Layout : sidebar gauche fixe (260px) + zone principale
**Sidebar (permanente) :**
- Logo + version en haut
- Navigation verticale avec icônes :
  * 🏠 Tableau de bord
  * 📁 Nouvel examen
  * 📋 Historique
  * 📊 Statistiques
  * ⚙️ Paramètres
  * 👤 Profil
- Indicateur de statut du modèle IA (point vert animé + "Modèle chargé")
- Informations utilisateur connecté en bas

**Zone principale :**
- Header : "Bonjour Dr. [Nom]" + date + heure en temps réel
- Cartes de statistiques (4 colonnes) :
  * Examens analysés aujourd'hui
  * Fractures détectées (ce mois)
  * Taux de détection moyen
  * Temps de traitement moyen
- Tableau des examens récents (10 derniers) avec colonnes :
  PatientID | Date | Vertèbres | Score | Résultat | Actions
- Chaque ligne : badge coloré (Fracture/Normal), bouton "Voir" → redirige vers /viewer
- Bouton principal CTA : "+ Importer un examen DICOM"

### Route `/import` — Import d'examen DICOM
**Zone de drag & drop :**
- Zone centrale pointillée avec icône de téléchargement
- Texte : "Glissez vos fichiers DICOM ici ou cliquez pour parcourir"
- Sous-texte : "Formats acceptés : .dcm | Tout un dossier d'examen"
- Support du drag & drop de dossier entier (studyInstanceUID/)
- Progress bar pendant l'upload (fichier par fichier avec compteur "127 / 352 fichiers")
- Après upload : aperçu de 3 coupes axiales + métadonnées extraites
  (PatientID, date examen, nombre de coupes, dimensions)
- Bouton "Analyser cet examen" → lance le pipeline IA → redirige vers /viewer/:studyId

### Route `/viewer/:studyId` — Viewer principal (CŒUR DE L'APPLICATION)

C'est la page la plus importante. Layout à 3 zones :

**Zone gauche — Sidebar d'informations (280px)**
```
┌─────────────────────────────┐
│  🔬 MediScanAI              │
│  ─────────────────────────  │
│  Patient : [ID]             │
│  Examen  : [Date]           │
│  Coupes  : 352              │
│  ─────────────────────────  │
│  RÉSULTAT GLOBAL            │
│  ┌──────────────────────┐   │
│  │  ⚠️ FRACTURE DÉTECTÉE │   │
│  │  Score : 97.6%       │   │
│  └──────────────────────┘   │
│  ─────────────────────────  │
│  VERTÈBRES                  │
│  C1  ░░░░░░░░░░  8%  ●     │
│  C2  ████░░░░░░  23% ●     │
│  C3  ░░░░░░░░░░  5%  ●     │
│  C4  ███████░░░  67% ⚠     │
│  C5  ██████████  97% ✗     │
│  C6  ████░░░░░░  31% ⚠     │
│  C7  ░░░░░░░░░░  12% ●     │
│  ─────────────────────────  │
│  [📋 Rapport clinique]      │
│  [⬇️  Exporter PDF]         │
└─────────────────────────────┘
```
Chaque vertèbre est cliquable → sélectionne cette vertèbre dans toutes les vues.

**Zone centrale — Viewer principal (flexible)**
Onglets en haut : [3D] [Axiale] [Sagittale] [Coronale] [Multi-plan]

**Onglet 3D :**
- Canvas Three.js plein écran (fond #0A0F1E)
- Maillage 3D de la colonne cervicale (Marching Cubes depuis le volume DICOM)
- Colorisation par score : vert → orange → rouge selon probabilité
- Chaque vertèbre sélectionnable par clic (glow effect sur la vertèbre cliquée)
- Contrôles : rotation par drag souris, scroll = zoom, double-clic = reset vue
- Bouton rotation automatique (tourne lentement quand actif)
- Labels flottants C1–C7 à côté de chaque vertèbre
- Marqueur 3D (sphère rouge pulsante) sur la zone de fracture détectée
- Lumières : ambientLight (0.6) + directionalLight (1.4) + backLight bleuté
- Mini-axes de référence (X/Y/Z) en bas à gauche du canvas

**Onglet Axiale / Sagittale / Coronale :**
- Canvas Cornerstone.js pour le rendu DICOM médical natif
- Slider vertical de navigation des coupes (1 → N)
- Numéro de coupe courant affiché
- Toggle "Grad-CAM" (superpose la heatmap sur la coupe actuelle)
- Toggle "Bounding Box" (affiche la boîte de localisation)
- Outils : zoom (molette), pan (clic droit), windowing (drag haut/bas = WW, gauche/droite = WC)
- Crosshairs synchronisés entre les 3 vues en mode Multi-plan

**Onglet Multi-plan (MPR) :**
- Grille 2x2 : Axiale | Sagittale | Coronale | 3D
- Toutes les vues synchronisées sur la même position anatomique
- Cliquer dans une vue 2D met à jour les croix dans les 3 autres
- Petit panneau de contrôle flottant : brightness, contrast, reset

**Zone droite — Panneau de contexte (300px)**
S'adapte à la vertèbre sélectionnée :
```
┌──────────────────────────────┐
│  C5 — 5ème vertèbre cervicale│
│  ────────────────────────    │
│  SCORE DE FRACTURE           │
│  ┌────────────────────────┐  │
│  │  97.6 %                │  │
│  │  ████████████████████░ │  │
│  └────────────────────────┘  │
│  RISQUE : ÉLEVÉ              │
│                              │
│  LOCALISATION                │
│  Arc vertébral postérieur    │
│  Pédicule droit              │
│                              │
│  COUPE DE RÉFÉRENCE          │
│  [miniature coupe + heatmap] │
│                              │
│  EXPLICATION IA              │
│  "Le modèle a focalisé son   │
│  attention sur une disconti- │
│  nuité osseuse dans la région│
│  postérieure de C5..."       │
│                              │
│  CONFIANCE GRAD-CAM          │
│  Score d'activation : 0.97   │
│                              │
└──────────────────────────────┘
```

### Route `/rapport/:studyId` — Rapport clinique
Page dédiée au rapport structuré, fond blanc pour l'impression :
- En-tête institutionnel (logo + nom de l'établissement)
- Section "Informations patient" (anonymisées)
- Section "Résumé de l'analyse" (résultat global + score)
- Section "Détail par vertèbre" (tableau C1–C7 avec scores + statut)
- Section "Explications du modèle" (texte clinique généré)
- Section "Images de référence" (captures des coupes + Grad-CAM côte à côte)
- Pied de page : "Rapport généré par MediScanAI v1.0 — [date/heure] — À valider par un médecin qualifié"
- Bouton "Imprimer / Exporter PDF" (utilise `window.print()` + CSS @media print)

### Route `/historique` — Liste des examens archivés
- Barre de recherche (PatientID, date, résultat)
- Filtres : Tous | Fracture détectée | Normal | Cette semaine | Ce mois
- Tableau paginé (20 par page) avec toutes les colonnes
- Clic sur une ligne → ouvre le viewer correspondant

### Route `/statistiques` — Dashboard analytique
- Graphique barres : examens analysés par jour (30 derniers jours)
- Donut chart : répartition Fractures vs Normal
- Graphique barres horizontales : fréquence de fracture par vertèbre (C1–C7)
- Carte score moyen par vertèbre
- Métriques clés du modèle (Recall, AUC, F1 du modèle entraîné)

---

## BACKEND — API FASTAPI COMPLÈTE

### Endpoints d'authentification
```
POST /api/auth/login
  Body: { email: string, password: string }
  Returns: { access_token: string, token_type: "bearer", user: UserSchema }

GET /api/auth/me
  Header: Authorization: Bearer {token}
  Returns: UserSchema
```

### Endpoints examens
```
POST /api/examens/upload
  Form-data: files (List[UploadFile]) + patient_id (string)
  Returns: { study_id: string, nb_coupes: int, metadata: dict }

GET /api/examens
  Query: page, limit, search, filter
  Returns: { items: List[ExamenSchema], total: int }

GET /api/examens/{study_id}
  Returns: ExamenSchema complet

DELETE /api/examens/{study_id}
  Returns: { success: true }
```

### Endpoints pipeline IA
```
POST /api/analyse/{study_id}
  Déclenche le pipeline complet de façon asynchrone
  Returns: { task_id: string }

GET /api/analyse/{study_id}/status
  Returns: { status: "pending"|"running"|"done"|"error", progress: 0-100 }

GET /api/analyse/{study_id}/resultats
  Returns: ResultatAnalyseSchema {
    study_id, score_global, fracture_detectee,
    scores_vertebres: [{ vertebre, probabilite, localisation, bounding_box }],
    rapport_clinique: string,
    date_analyse
  }
```

### Endpoints images
```
GET /api/images/{study_id}/coupes
  Returns: { nb_coupes: int, coupe_centrale: int }

GET /api/images/{study_id}/coupe/{numero}
  Query: view (axial|sagittal|coronal), window_center, window_width
  Returns: image/png (coupe DICOM rendue avec windowing)

GET /api/images/{study_id}/gradcam/{numero}
  Returns: image/png (coupe + heatmap Grad-CAM superposée)

GET /api/images/{study_id}/reconstruction-3d
  Returns: application/json { vertices, faces, normals, vertebrae_bounds }

GET /api/images/{study_id}/export-pdf
  Returns: application/pdf (rapport complet)
```

### Endpoints statistiques
```
GET /api/stats/dashboard
  Returns: { today_exams, month_fractures, avg_score, avg_time }

GET /api/stats/historique
  Query: period (7d|30d|90d)
  Returns: { daily_counts, vertebrae_distribution, recall_metrics }
```

---

## BACKEND — PIPELINE IA DETAILLÉ

### Service `DicomService` (`backend/app/services/dicom_service.py`)

```python
class DicomService:

    def load_and_sort_slices(self, study_path: str) -> Tuple[np.ndarray, dict]:
        """
        Charge et trie TOUS les fichiers .dcm par position Z réelle
        (ImagePositionPatient[2]), pas par nom de fichier.
        Applique RescaleSlope + RescaleIntercept pour obtenir les UH.
        Retourne: (volume_array, spacing_dict)
        volume_array shape: (n_slices, 512, 512) en int16 Hounsfield
        spacing_dict: { pixel_spacing, slice_thickness, slice_positions }
        """

    def apply_windowing(self, volume: np.ndarray,
                        wc: float = 300, ww: float = 1500) -> np.ndarray:
        """
        Applique le fenêtrage CT osseux sur le volume.
        Retourne les valeurs clippées et normalisées dans [0, 1].
        """

    def render_slice_to_image(self, volume: np.ndarray,
                               slice_idx: int, view: str,
                               wc: float = 300, ww: float = 1500) -> bytes:
        """
        Génère une image PNG d'une coupe dans la vue demandée.
        view: 'axial' | 'sagittal' | 'coronal'
        Retourne: bytes PNG
        """
```

### Service `ReconstructionService` (`backend/app/services/reconstruction_service.py`)

```python
class ReconstructionService:

    def build_mesh(self, volume: np.ndarray,
                   spacing: dict, threshold_hu: int = 200) -> dict:
        """
        1. Applique filtre gaussien (sigma=0.6) pour lisser les artefacts
        2. Crée masque binaire : voxels > threshold_hu
        3. Applique skimage.measure.marching_cubes()
        4. Retourne { vertices (List), faces (List), normals (List) }
        vertices en coordonnées physiques (mm), pas en voxels
        """

    def map_vertebrae_to_mesh(self, vertices: np.ndarray,
                               z_positions: list) -> List[int]:
        """
        Assigne chaque vertex à une vertèbre C1–C7 basé sur sa position Z.
        Utilise les segments NIfTI si disponibles, sinon division équidistante.
        Retourne un array d'indices vertèbre (0=C1, ..., 6=C7) par vertex.
        """

    def colorize_mesh(self, vertebra_indices: List[int],
                      scores: dict) -> List[str]:
        """
        Retourne une couleur hexadécimale par vertex basée sur le score
        de la vertèbre correspondante.
        < 0.30 → #00E5A0 (vert)
        0.30–0.60 → #FFA048 (orange)
        > 0.60 → #FF4757 (rouge)
        """
```

### Service `PipelineAIService` (`backend/app/services/pipeline_service.py`)

```python
class PipelineAIService:

    def __init__(self):
        # Charger DenseNet-121 une seule fois au démarrage
        self.model = timm.create_model(
            "densenet121", pretrained=False,
            in_chans=5, num_classes=1, drop_rate=0.0
        )
        state = torch.load("model/final_best_densenet121_25d.pth",
                            map_location="cpu")
        self.model.load_state_dict(state)
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        # Seuil optimal extrait lors de l'entraînement
        self.threshold = 0.03  # sera mis à jour par la valeur F2

    def predict_volume(self, volume: np.ndarray) -> dict:
        """
        Analyse toutes les coupes du volume.
        Groupe les résultats par vertèbre C1–C7.
        Retourne: {
          "scores_par_coupe": [(slice_idx, score), ...],
          "scores_par_vertebre": {"C1": 0.08, "C2": 0.23, ...},
          "coupes_positives": [slice_idx, ...],
          "fracture_detectee": bool,
          "score_global": float
        }
        """

    def load_25d_slice(self, volume: np.ndarray,
                        slice_idx: int) -> np.ndarray:
        """
        Extrait 5 coupes consécutives (N-2, N-1, N, N+1, N+2).
        Applique windowing osseux WC=300, WW=1500.
        Normalise dans [0, 1].
        Retourne: np.ndarray shape (5, 384, 384)
        """

    def generate_gradcam(self, volume: np.ndarray,
                          slice_idx: int) -> np.ndarray:
        """
        Génère la carte Grad-CAM via model.features.norm5.
        Superpose sur la coupe originale (70% original + 30% heatmap colorjet).
        Retourne: np.ndarray (H, W, 3) RGB
        """

    def generate_clinical_report(self, scores: dict,
                                   fracture_detectee: bool) -> str:
        """
        Génère un rapport clinique structuré basé sur les scores.
        Format :
        - Résumé (1 phrase conclusion)
        - Vertèbres concernées (liste avec score et localisation estimée)
        - Niveau de certitude (basé sur la calibration)
        - Recommandation (selon les guidelines radiologiques)
        Utilise des templates enrichis avec les données cliniques.
        """
```

---

## THREE.JS — VIEWER 3D DÉTAILLÉ

Composant `SpineViewer3D.tsx` :

```typescript
// Initialisation scène
const scene = new THREE.Scene()
scene.background = new THREE.Color(0x0A0F1E)
scene.fog = new THREE.Fog(0x0A0F1E, 15, 50)

// Caméra perspective
const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 200)
camera.position.set(0, 0, 14)

// Lumières médicales professionnelles
const ambientLight = new THREE.AmbientLight(0x3050A0, 0.8)
const mainLight = new THREE.DirectionalLight(0xFFFFFF, 1.5)
mainLight.position.set(5, 8, 6)
const fillLight = new THREE.DirectionalLight(0x4488FF, 0.5)
fillLight.position.set(-4, -3, -5)
const rimLight = new THREE.DirectionalLight(0x00C6FF, 0.3)
rimLight.position.set(0, -6, -4)

// Matériau osseux réaliste
const boneMaterial = new THREE.MeshPhongMaterial({
  color: vertebraColor,           // basé sur score
  shininess: 45,
  specular: new THREE.Color(0.25, 0.28, 0.35),
  side: THREE.DoubleSide,
  transparent: false,
})

// Interaction souris
// - mousedown + mousemove → rotation libre (OrbitControls-like manuel)
// - scroll → zoom
// - click → raycaster → sélection vertèbre
// - double-click → reset caméra

// Marqueur fracture (sphère animée)
// Sur les vertèbres avec score > 0.60 : ajouter une sphère rouge
// pulsante (scale oscillant entre 0.8 et 1.2 via Math.sin)
const fractureSphere = new THREE.Mesh(
  new THREE.SphereGeometry(0.15, 8, 8),
  new THREE.MeshBasicMaterial({
    color: 0xFF4757,
    transparent: true,
    opacity: 0.8
  })
)

// Labels HTML (via CSS2DRenderer ou div positionnés par projection)
// Chaque vertèbre a un label C1–C7 en blanc qui reste face caméra

// Export de la vue
// Bouton "Capturer" → canvas.toDataURL() → image PNG dans le rapport
```

---

## COMPOSANTS CRITIQUES À IMPLÉMENTER

### `GradCamOverlay.tsx`
- Props : `studyId`, `sliceNumber`, `vertebraId`, `active`
- Fetche l'endpoint `/api/images/{study_id}/gradcam/{numero}`
- Superpose l'image via CSS `mix-blend-mode: screen` sur le canvas Cornerstone
- Slider d'opacité pour contrôler l'intensité de l'overlay (0% → 100%)
- Toggle animé (Framer Motion) pour activer/désactiver

### `VertebraScorePanel.tsx`
- Affiche C1–C7 en liste verticale
- Barre de progression colorée par niveau de risque
- Clic → émet un event global (Zustand store) qui synchronise :
  le 3D viewer (highlight vertèbre), les vues MPR (navigation coupe centrale),
  le panneau de détail droite
- Animation de transition sur la sélection

### `ClinicalReportGenerator.tsx`
- Reçoit les résultats d'analyse
- Formate un rapport médical structuré
- Intègre : résumé, tableau des vertèbres, captures Grad-CAM, recommandation
- Bouton `<button onClick={() => window.print()}>Exporter PDF</button>`
- Style CSS @media print optimisé (fond blanc, texte noir, page A4)

### `DicomUploadZone.tsx`
- Drag & drop avec react-dropzone
- Accepte `.dcm` et dossiers entiers
- Chunked upload si > 50 fichiers
- Progress en temps réel via WebSocket ou polling `GET /api/examens/upload/status/{task_id}`

### `StatusIndicator.tsx` (dans la sidebar)
- Vérifie au démarrage que le modèle est chargé via `GET /api/health`
- Point vert animé (pulse) + "Modèle IA chargé" si OK
- Point rouge + "Modèle non disponible" si erreur

---

## BASE DE DONNÉES — SCHÉMA SQLALCHEMY

```python
class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id: int (PK), email: str (unique), hashed_password: str
    nom: str, role: Enum("medecin", "admin")
    created_at: datetime

class Patient(Base):
    __tablename__ = "patients"
    id: int (PK), patient_id: str (unique)
    created_at: datetime

class Examen(Base):
    __tablename__ = "examens"
    id: int (PK), study_instance_uid: str (unique)
    patient_id: str (FK → patients)
    date_examen: datetime, nb_coupes: int
    dicom_path: str, uploaded_at: datetime
    uploaded_by: int (FK → utilisateurs)

class ResultatAnalyse(Base):
    __tablename__ = "resultats_analyse"
    id: int (PK), study_instance_uid: str (FK → examens)
    fracture_detectee: bool, score_global: float
    rapport_clinique: text, date_analyse: datetime
    duree_analyse_sec: float, seuil_utilise: float

class ScoreVertebre(Base):
    __tablename__ = "scores_vertebres"
    id: int (PK), resultat_id: int (FK → resultats_analyse)
    vertebre: Enum("C1","C2","C3","C4","C5","C6","C7")
    probabilite: float, localisation: str
    bounding_box_x: float, bounding_box_y: float
    bounding_box_w: float, bounding_box_h: float
    coupe_reference: int
```

---

## ORDRE D'IMPLÉMENTATION — SUIS CET ORDRE EXACTEMENT

1. **Setup projet** : Vite + React + TS + Tailwind, FastAPI + SQLite, structure dossiers
2. **Design system** : variables CSS, composants UI de base (Button, Card, Badge)
3. **Authentification** : backend JWT + page login frontend
4. **Layout principal** : sidebar + routing React Router
5. **Upload DICOM** : endpoint FastAPI + composant frontend
6. **Pipeline IA** : DicomService + PipelineAIService (avec modèle mock si poids pas encore dispo)
7. **Viewer 2D** : intégration Cornerstone.js, navigation coupes axiales
8. **Grad-CAM overlay** : endpoint + composant frontend
9. **Reconstruction 3D** : ReconstructionService + SpineViewer3D Three.js
10. **Panel vertèbres** : scores + synchronisation Zustand
11. **Panel détail** : explication clinique par vertèbre
12. **Dashboard** : stats + tableau examens récents
13. **Rapport clinique** : génération + export PDF
14. **Historique** : liste + recherche + filtres
15. **Statistiques** : graphiques Recharts
16. **Polish** : animations Framer Motion, transitions, responsive
17. **Tests** : au moins des tests sur les endpoints IA critiques

---

## QUALITÉ DE CODE — STANDARDS OBLIGATOIRES

- TypeScript strict : toutes les interfaces typées dans `src/types/`
- Zero `any` dans le TypeScript
- Tous les endpoints FastAPI avec typage Pydantic complet
- Gestion d'erreur systématique : try/catch côté backend, error boundaries côté React
- Loading states sur tous les appels API (skeleton loaders, pas des spinners nus)
- Responsive : fonctionne sur 1366x768 minimum (résolution d'écrans médicaux)
- Commentaires en français sur la logique métier médicale
- README.md complet avec : prérequis, installation, configuration, utilisation

---

## NOTES IMPORTANTES

1. Le modèle PyTorch sera disponible dans `model/final_best_densenet121_25d.pth`
   pendant le développement. Créer un mock qui retourne des scores aléatoires
   réalistes si le fichier est absent, pour pouvoir tester l'interface.

2. Les fichiers DICOM réels ne sont pas tous disponibles. Créer un endpoint
   `GET /api/demo/load-sample` qui charge un examen d'exemple depuis
   `data/sample/` (quelques coupes fictives en PNG grises).

3. La reconstruction 3D est lourde (1–3 minutes). Implémenter un système de cache :
   si le mesh a déjà été calculé pour un studyId, le stocker en JSON dans `cache/`
   et le servir directement sans recalculer.

4. Sécurité : toutes les routes (sauf /login) nécessitent un JWT valide.
   Implémenter un refresh token automatique côté frontend (intercepteur Axios).

5. Performance 3D : limiter le mesh à 500 000 triangles maximum via
   `skimage.measure.marching_cubes(step_size=2)`. Si le mesh est plus grand,
   appliquer une décimation (open3d ou trimesh).

---

## LIVRABLE FINAL ATTENDU

Une application web complète, fonctionnelle, avec :
- Interface de niveau professionnel médical (pas une maquette, une vraie app)
- Pipeline IA intégré et fonctionnel avec le modèle PyTorch
- Viewer 3D interactif et impressionnant
- Rapport clinique exportable en PDF
- Code propre, commenté, maintenable
- README d'installation en 5 commandes maximum

L'objectif est qu'un radiologue puisse l'utiliser le jour J sans formation.
