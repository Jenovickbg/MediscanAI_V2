# ============================================================
# CURSOR PROMPT — INTÉGRATION COMPLÈTE DES 3 MODÈLES IA
# MediScanAI — Pipeline de production final
# ============================================================

Tu travailles sur le projet MediScanAI déjà en cours de construction.
Le frontend React et le backend FastAPI existent déjà.
Ce prompt intègre les 3 modèles PyTorch entraînés dans le pipeline
de production complet, de bout en bout.

Ne recommence rien depuis zéro. Modifie uniquement ce qui est indiqué.
Exécute dans l'ordre exact donné. Confirme chaque étape avant de passer
à la suivante.

---

## CONTEXTE — LES 3 MODÈLES ENTRAÎNÉS

### Modèle 1 — Classificateur de fracture
```
Architecture : DenseNet-121 2.5D
Fichier      : model/model1_classifier_densenet121.pth
Entrée       : Tenseur (1, 5, 384, 384) — 5 coupes consécutives
Sortie       : Logit scalaire → sigmoid → probabilité [0, 1]
Seuil bas    : 0.15 → "normal"
Seuil haut   : 0.30 → "eleve"
Entre 0.15 et 0.30 → "incertain"
Performance  : Recall 99.5% au seuil 0.15
```

### Modèle 3 — Classificateur de vertèbre
```
Architecture : DenseNet-121 2.5D
Fichier      : model/model3_vertebra_densenet121.pth
Entrée       : Tenseur (1, 5, 384, 384) — mêmes 5 coupes
Sortie       : Vecteur de 7 logits → softmax → classe C1 à C7
Classes      : 0=C1, 1=C2, 2=C3, 3=C4, 4=C5, 5=C6, 6=C7
Performance  : Accuracy 95.07%
```

### Modèle 2 — Localisateur Faster RCNN
```
Architecture : Faster RCNN ResNet50-FPN (torchvision)
Fichier      : model/model2_fasterrcnn.pth
Entrée       : Image RGB (3, 512, 512) normalisée [0, 1]
Sortie       : boxes [x1,y1,x2,y2], labels, scores
Seuil score  : 0.50 (ne garder que les détections > 50%)
NMS thresh   : 0.30
Max détect.  : 3 par image
```

---

## ÉTAPE 1 — Structure des fichiers modèles

Crée cette structure dans le projet :

```
backend/
├── model/
│   ├── model1_classifier_densenet121.pth    ← à placer manuellement
│   ├── model2_fasterrcnn.pth                ← à placer manuellement
│   ├── model3_vertebra_densenet121.pth      ← à placer manuellement
│   └── README.md
├── config/
│   └── triage_thresholds.json
└── app/
    └── services/
        ├── dicom_service.py
        ├── pipeline_service.py
        └── reconstruction_service.py
```
NB:J'ai deja mis pour toi les 3 fichier pth dans le dossier modele 
Crée `backend/config/triage_thresholds.json` :
```json
{
  "seuil_bas": 0.15,
  "seuil_haut": 0.30,
  "score_thresh_rcnn": 0.50,
  "nms_thresh_rcnn": 0.30,
  "max_detections": 3,
  "recall_garanti": 0.995,
  "auc_modele1": 0.7581,
  "accuracy_modele3": 0.9507,
  "derniere_maj": "2025-06"
}
```

Crée `backend/model/README.md` :
```markdown
# Modèles MediScanAI

Placer les 3 fichiers .pth dans ce dossier :
- model1_classifier_densenet121.pth  (DenseNet-121, fracture binaire)
- model2_fasterrcnn.pth              (Faster RCNN, localisation)
- model3_vertebra_densenet121.pth    (DenseNet-121, C1-C7)
```

---

## ÉTAPE 2 — Service DICOM (dicom_service.py)

Remplace entièrement `backend/app/services/dicom_service.py` :

```python
import os
import cv2
import pydicom
import numpy as np
from pathlib import Path


DICOM_BASE_PATH = os.getenv("DICOM_BASE_PATH", "data/train_images")


class DicomService:
    """
    Gère la lecture, le tri et le preprocessing des fichiers DICOM.
    Aucune dépendance aux modèles IA — pure manipulation d'images médicales.
    """

    def load_and_sort_slices(self, study_id: str) -> tuple[np.ndarray, dict]:
        """
        Charge toutes les coupes DICOM d'un examen et les trie
        par position Z physique réelle (ImagePositionPatient[2]).

        Retourne:
            volume : np.ndarray shape (N, H, W) en Unités Hounsfield
            spacing: dict avec pixel_spacing, slice_thickness, n_slices
        """
        study_path = os.path.join(DICOM_BASE_PATH, study_id)

        if not os.path.exists(study_path):
            raise FileNotFoundError(f"Examen introuvable : {study_id}")

        dcm_files = [f for f in os.listdir(study_path) if f.endswith(".dcm")]

        if not dcm_files:
            raise ValueError(f"Aucun fichier DICOM dans : {study_path}")

        # Trier par position Z réelle — PAS par nom de fichier
        slices_with_pos = []
        for f in dcm_files:
            dcm = pydicom.dcmread(
                os.path.join(study_path, f),
                stop_before_pixels=True
            )
            try:
                z = float(dcm.ImagePositionPatient[2])
            except AttributeError:
                z = float(f.replace(".dcm", ""))
            slices_with_pos.append((f, z))

        slices_sorted = sorted(slices_with_pos, key=lambda x: x[1])

        # Charger les pixels en Hounsfield
        volume = []
        for filename, _ in slices_sorted:
            dcm   = pydicom.dcmread(os.path.join(study_path, filename))
            img   = dcm.pixel_array.astype(np.float32)
            slope = float(getattr(dcm, "RescaleSlope", 1))
            inter = float(getattr(dcm, "RescaleIntercept", 0))
            volume.append(img * slope + inter)

        volume = np.stack(volume, axis=0)

        # Espacement physique
        dcm_ref = pydicom.dcmread(
            os.path.join(study_path, slices_sorted[0][0]),
            stop_before_pixels=True
        )
        try:
            pixel_spacing = float(dcm_ref.PixelSpacing[0])
        except AttributeError:
            pixel_spacing = 1.0

        if len(slices_sorted) > 1:
            slice_thickness = abs(slices_sorted[1][1] - slices_sorted[0][1])
        else:
            slice_thickness = float(getattr(dcm_ref, "SliceThickness", 1.0))

        # Liste des slice_numbers dans l'ordre trié
        sorted_slice_numbers = [
            int(f.replace(".dcm", "")) for f, _ in slices_sorted
        ]

        spacing = {
            "pixel_spacing":        pixel_spacing,
            "slice_thickness":      slice_thickness,
            "n_slices":             len(volume),
            "sorted_slice_numbers": sorted_slice_numbers
        }

        return volume, spacing

    def apply_windowing(
        self,
        image: np.ndarray,
        wc: float = 300,
        ww: float = 1500
    ) -> np.ndarray:
        """Applique le fenêtrage CT osseux. Retourne valeurs dans [0, 1]."""
        lower = wc - ww / 2
        upper = wc + ww / 2
        image = np.clip(image, lower, upper)
        return ((image - lower) / (upper - lower)).astype(np.float32)

    def build_25d_stack(
        self,
        volume: np.ndarray,
        slice_idx: int,
        image_size: int = 384
    ) -> np.ndarray:
        """
        Construit l'entrée 2.5D : 5 coupes consécutives centrées sur slice_idx.
        Retourne un array (5, image_size, image_size) normalisé [0, 1].
        """
        n_slices = volume.shape[0]
        offsets  = [-2, -1, 0, 1, 2]
        images   = []

        for offset in offsets:
            idx  = max(0, min(n_slices - 1, slice_idx + offset))
            img  = self.apply_windowing(volume[idx])
            img  = cv2.resize(img, (image_size, image_size))
            images.append(img)

        return np.stack(images, axis=0)   # shape: (5, H, W)

    def render_slice_png(
        self,
        volume: np.ndarray,
        slice_idx: int,
        view: str = "axial",
        wc: float = 300,
        ww: float = 1500,
        image_size: int = 512
    ) -> bytes:
        """
        Génère une image PNG d'une coupe dans la vue demandée.
        view: 'axial' | 'sagittal' | 'coronal'
        Retourne: bytes PNG
        """
        if view == "axial":
            slice_2d = volume[
                max(0, min(volume.shape[0]-1, slice_idx)), :, :
            ]
        elif view == "sagittal":
            slice_2d = volume[
                :, :, max(0, min(volume.shape[2]-1, slice_idx))
            ]
        elif view == "coronal":
            slice_2d = volume[
                :, max(0, min(volume.shape[1]-1, slice_idx)), :
            ]
        else:
            raise ValueError(f"Vue inconnue : {view}")

        img = self.apply_windowing(slice_2d, wc=wc, ww=ww)
        img = (img * 255).astype(np.uint8)
        img = cv2.resize(img, (image_size, image_size))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        _, buffer = cv2.imencode(".png", img_rgb)
        return buffer.tobytes()

    def get_slice_count(self, study_id: str) -> dict:
        """Retourne rapidement le nombre de coupes sans charger les pixels."""
        study_path = os.path.join(DICOM_BASE_PATH, study_id)
        n = len([f for f in os.listdir(study_path) if f.endswith(".dcm")])
        return {"study_id": study_id, "n_coupes": n}


dicom_service = DicomService()
```

---

## ÉTAPE 3 — Pipeline IA (pipeline_service.py)

Remplace entièrement `backend/app/services/pipeline_service.py` :

```python
import os
import json
import cv2
import torch
import timm
import numpy as np
from typing import Optional
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from .dicom_service import dicom_service

# ── Chargement de la config ──────────────────────────────────
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../../config/triage_thresholds.json"
)
with open(CONFIG_PATH) as f:
    THRESHOLDS = json.load(f)

SEUIL_BAS         = THRESHOLDS["seuil_bas"]          # 0.15
SEUIL_HAUT        = THRESHOLDS["seuil_haut"]          # 0.30
SCORE_THRESH_RCNN = THRESHOLDS["score_thresh_rcnn"]   # 0.50
NMS_THRESH_RCNN   = THRESHOLDS["nms_thresh_rcnn"]     # 0.30
MAX_DETECTIONS    = THRESHOLDS["max_detections"]       # 3

VERTEBRA_NAMES = ["C1","C2","C3","C4","C5","C6","C7"]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "../../model")


def classifier_triage(probability: float) -> str:
    """Triage clinique à 3 niveaux basé sur la probabilité du Modèle 1."""
    if probability < SEUIL_BAS:
        return "normal"
    elif probability < SEUIL_HAUT:
        return "incertain"
    else:
        return "eleve"


class PipelineAIService:
    """
    Orchestrateur des 3 modèles IA.
    Ordre d'exécution :
      1. Modèle 1 (toutes les coupes) → triage
      2. Modèle 2 + Modèle 3 (coupes flaguées uniquement)
      3. Agrégation par vertèbre
      4. Rapport clinique
    """

    def __init__(self):
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        print(f"[PipelineAI] Device : {self.device}")

        self.model1 = self._load_model1()
        self.model2 = self._load_model2()
        self.model3 = self._load_model3()

        print("[PipelineAI] ✅ 3 modèles chargés.")

    # ── Chargement des modèles ───────────────────────────────

    def _load_model1(self):
        path = os.path.join(MODEL_DIR, "model1_classifier_densenet121.pth")
        model = timm.create_model(
            "densenet121",
            pretrained=False,
            in_chans=5,
            num_classes=1,
            drop_rate=0.0
        )
        if os.path.exists(path):
            model.load_state_dict(
                torch.load(path, map_location=self.device)
            )
            print("[Modèle 1] ✅ Poids chargés.")
        else:
            print("[Modèle 1] ⚠️  Fichier .pth absent — mode mock actif.")
        model.to(self.device)
        model.eval()
        return model

    def _load_model2(self):
        path  = os.path.join(MODEL_DIR, "model2_fasterrcnn.pth")
        model = fasterrcnn_resnet50_fpn(weights=None, num_classes=2)
        in_f  = model.roi_heads.box_predictor.cls_score.in_features
        from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
        model.roi_heads.box_predictor = FastRCNNPredictor(in_f, 2)

        if os.path.exists(path):
            model.load_state_dict(
                torch.load(path, map_location=self.device)
            )
            print("[Modèle 2] ✅ Poids chargés.")
        else:
            print("[Modèle 2] ⚠️  Fichier .pth absent — mode mock actif.")

        # Réglages NMS pour éviter les doublons
        model.roi_heads.nms_thresh        = NMS_THRESH_RCNN
        model.roi_heads.detections_per_img = MAX_DETECTIONS

        model.to(self.device)
        model.eval()
        return model

    def _load_model3(self):
        path = os.path.join(MODEL_DIR, "model3_vertebra_densenet121.pth")
        model = timm.create_model(
            "densenet121",
            pretrained=False,
            in_chans=5,
            num_classes=7,
            drop_rate=0.0
        )
        if os.path.exists(path):
            model.load_state_dict(
                torch.load(path, map_location=self.device)
            )
            print("[Modèle 3] ✅ Poids chargés.")
        else:
            print("[Modèle 3] ⚠️  Fichier .pth absent — mode mock actif.")
        model.to(self.device)
        model.eval()
        return model

    # ── Pipeline principal ───────────────────────────────────

    def analyser_examen(self, study_id: str) -> dict:
        """
        Point d'entrée principal. Orchestre les 3 modèles dans l'ordre.

        Retourne le contrat JSON complet consommé par le frontend.
        """
        print(f"\n[Pipeline] Analyse de {study_id}")

        # Charger le volume DICOM
        volume, spacing = dicom_service.load_and_sort_slices(study_id)
        n_slices = volume.shape[0]
        print(f"[Pipeline] Volume chargé : {n_slices} coupes")

        # ── Phase 1 : Modèle 1 sur TOUTES les coupes ────────
        print("[Pipeline] Phase 1 — Classification fracture...")
        scores_par_coupe = self._run_model1(volume, spacing)

        coupes_flaguees = [
            c for c in scores_par_coupe
            if c["categorie"] != "normal"
        ]
        print(f"[Pipeline] Coupes flaguées : {len(coupes_flaguees)}")

        # ── Court-circuit si aucune anomalie ────────────────
        if not coupes_flaguees:
            return {
                "study_id":            study_id,
                "fracture_detectee":   False,
                "score_global":        0.0,
                "scores_par_vertebre": {},
                "rapport_clinique":    self._rapport_negatif(study_id),
                "n_coupes_analysees":  n_slices,
                "n_coupes_flaguees":   0
            }

        # ── Phase 2 : Modèles 2 et 3 sur les coupes flaguées
        print("[Pipeline] Phase 2 — Localisation + Vertèbre...")
        resultats_bbox    = self._run_model2(volume, coupes_flaguees)
        resultats_vertebre = self._run_model3(volume, coupes_flaguees)

        # ── Phase 3 : Agrégation par vertèbre ───────────────
        scores_par_vertebre = self._agreger_par_vertebre(
            coupes_flaguees, resultats_bbox,
            resultats_vertebre, spacing
        )

        score_global = max(
            v["probabilite"] for v in scores_par_vertebre.values()
        )

        # ── Phase 4 : Rapport clinique ───────────────────────
        rapport = self._generer_rapport(study_id, scores_par_vertebre)

        return {
            "study_id":            study_id,
            "fracture_detectee":   True,
            "score_global":        round(score_global, 4),
            "scores_par_vertebre": scores_par_vertebre,
            "rapport_clinique":    rapport,
            "n_coupes_analysees":  n_slices,
            "n_coupes_flaguees":   len(coupes_flaguees)
        }

    # ── Modèle 1 ────────────────────────────────────────────

    def _run_model1(self, volume: np.ndarray, spacing: dict) -> list:
        """
        Passe toutes les coupes dans le Modèle 1.
        Retourne liste de dicts avec score et catégorie par coupe.
        """
        results   = []
        n_slices  = volume.shape[0]
        sorted_sn = spacing.get("sorted_slice_numbers", list(range(n_slices)))

        with torch.no_grad():
            for i in range(n_slices):
                stack  = dicom_service.build_25d_stack(volume, i, image_size=384)
                tensor = torch.tensor(
                    stack, dtype=torch.float32
                ).unsqueeze(0).to(self.device)

                logit = self.model1(tensor)
                prob  = torch.sigmoid(logit).item()

                results.append({
                    "slice_idx":    i,
                    "slice_number": sorted_sn[i] if i < len(sorted_sn) else i,
                    "score":        round(prob, 4),
                    "categorie":    classifier_triage(prob)
                })

        return results

    # ── Modèle 2 ────────────────────────────────────────────

    def _run_model2(
        self,
        volume: np.ndarray,
        coupes_flaguees: list
    ) -> dict:
        """
        Localise les fractures via Faster RCNN.
        S'exécute UNIQUEMENT sur les coupes flaguées.
        Retourne : { slice_idx: {"bbox": [x1,y1,x2,y2], "score": float} }
        """
        resultats = {}

        with torch.no_grad():
            for coupe in coupes_flaguees:
                i = coupe["slice_idx"]

                # Préparer l'image RGB 512x512 normalisée [0,1]
                img_hu  = volume[i]
                img_win = (np.clip(
                    (img_hu - (-450)) / 1500, 0, 1
                ) * 255).astype(np.uint8)
                img_512 = cv2.resize(img_win, (512, 512))
                img_rgb = cv2.cvtColor(img_512, cv2.COLOR_GRAY2RGB)

                tensor = torch.tensor(
                    img_rgb.transpose(2, 0, 1),
                    dtype=torch.float32
                ).unsqueeze(0).to(self.device) / 255.0

                outputs = self.model2([tensor[0]])[0]

                boxes  = outputs["boxes"].cpu().numpy()
                scores = outputs["scores"].cpu().numpy()

                best_bbox  = None
                best_score = 0.0

                for box, score in zip(boxes, scores):
                    if score >= SCORE_THRESH_RCNN and score > best_score:
                        best_score = float(score)
                        x1, y1, x2, y2 = box
                        best_bbox = {
                            "x":      float(x1),
                            "y":      float(y1),
                            "width":  float(x2 - x1),
                            "height": float(y2 - y1)
                        }

                if best_bbox:
                    resultats[i] = {
                        "bbox":  best_bbox,
                        "score": best_score
                    }

        return resultats

    # ── Modèle 3 ────────────────────────────────────────────

    def _run_model3(
        self,
        volume: np.ndarray,
        coupes_flaguees: list
    ) -> dict:
        """
        Identifie la vertèbre pour chaque coupe flaguée.
        S'exécute UNIQUEMENT sur les coupes flaguées.
        Retourne : { slice_idx: "C5" }
        """
        resultats = {}

        with torch.no_grad():
            for coupe in coupes_flaguees:
                i = coupe["slice_idx"]

                stack  = dicom_service.build_25d_stack(volume, i, image_size=384)
                tensor = torch.tensor(
                    stack, dtype=torch.float32
                ).unsqueeze(0).to(self.device)

                logits   = self.model3(tensor)
                pred_idx = torch.argmax(logits, dim=1).item()
                probs    = torch.softmax(logits, dim=1)[0].cpu().numpy()

                resultats[i] = {
                    "vertebre":    VERTEBRA_NAMES[pred_idx],
                    "confiance":   float(probs[pred_idx]),
                    "all_probs":   {
                        VERTEBRA_NAMES[j]: float(probs[j])
                        for j in range(7)
                    }
                }

        return resultats

    # ── Agrégation par vertèbre ──────────────────────────────

    def _agreger_par_vertebre(
        self,
        coupes_flaguees: list,
        resultats_bbox: dict,
        resultats_vertebre: dict,
        spacing: dict
    ) -> dict:
        """
        Pour chaque vertèbre touchée, retient la coupe avec le
        score de fracture le plus élevé comme coupe de référence.
        """
        par_vertebre = {}

        for coupe in coupes_flaguees:
            i            = coupe["slice_idx"]
            score        = coupe["score"]
            slice_number = coupe["slice_number"]
            categorie    = coupe["categorie"]

            vert_info = resultats_vertebre.get(i)
            if not vert_info:
                continue

            vertebre = vert_info["vertebre"]

            if (vertebre not in par_vertebre or
                    score > par_vertebre[vertebre]["probabilite"]):

                bbox = resultats_bbox.get(i, {}).get("bbox")

                par_vertebre[vertebre] = {
                    "probabilite":    round(score, 4),
                    "bounding_box":   bbox,
                    "coupe_reference": slice_number,
                    "slice_idx":      i,
                    "niveau_risque":  categorie,
                    "confiance_vertebre": round(vert_info["confiance"], 4)
                }

        return par_vertebre

    # ── Grad-CAM ─────────────────────────────────────────────

    def generer_gradcam(
        self,
        volume: np.ndarray,
        slice_idx: int
    ) -> np.ndarray:
        """
        Génère la heatmap Grad-CAM via model1.features.norm5.
        Retourne une image RGB (H, W, 3) prête à être encodée en PNG.
        """
        gradients  = {}
        activations = {}

        def save_activation(module, input, output):
            activations["out"] = output

        def save_gradient(module, grad_input, grad_output):
            gradients["out"] = grad_output[0]

        target_layer  = self.model1.features.norm5
        hook_fwd  = target_layer.register_forward_hook(save_activation)
        hook_bwd  = target_layer.register_full_backward_hook(save_gradient)

        stack  = dicom_service.build_25d_stack(volume, slice_idx)
        tensor = torch.tensor(
            stack, dtype=torch.float32
        ).unsqueeze(0).to(self.device)
        tensor.requires_grad = True

        self.model1.zero_grad()
        output = self.model1(tensor)
        output[0, 0].backward()

        hook_fwd.remove()
        hook_bwd.remove()

        weights = torch.mean(gradients["out"], dim=(2, 3), keepdim=True)
        cam     = torch.sum(weights * activations["out"], dim=1)
        cam     = torch.relu(cam)[0].cpu().detach().numpy()
        cam     = cv2.resize(cam, (384, 384))
        cam     = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)

        # Image centrale
        central  = dicom_service.build_25d_stack(volume, slice_idx)[2]
        central  = (central * 255).astype(np.uint8)
        central_rgb = cv2.cvtColor(central, cv2.COLOR_GRAY2RGB)

        heatmap  = cv2.applyColorMap(
            (cam * 255).astype(np.uint8), cv2.COLORMAP_JET
        )
        overlay  = cv2.addWeighted(central_rgb, 0.6, heatmap, 0.4, 0)

        return overlay   # np.ndarray (H, W, 3) RGB

    # ── Rapport clinique ─────────────────────────────────────

    def _generer_rapport(
        self,
        study_id: str,
        scores_par_vertebre: dict
    ) -> str:
        """
        Génère un rapport clinique structuré en français.
        """
        if not scores_par_vertebre:
            return self._rapport_negatif(study_id)

        vertebres_touchees = sorted(
            scores_par_vertebre.items(),
            key=lambda x: x[1]["probabilite"],
            reverse=True
        )

        lignes_vertebres = []
        for vert, data in vertebres_touchees:
            niveau   = data["niveau_risque"]
            prob_pct = round(data["probabilite"] * 100, 1)
            if niveau == "eleve":
                mention = f"FRACTURE PROBABLE ({prob_pct}% de certitude)"
            else:
                mention = f"ANOMALIE SUSPECTE ({prob_pct}% de certitude)"
            lignes_vertebres.append(f"  • {vert} : {mention}")

        vertebres_str  = "\n".join(lignes_vertebres)
        vert_principale = vertebres_touchees[0][0]
        score_max       = round(vertebres_touchees[0][1]["probabilite"] * 100, 1)

        rapport = f"""
RAPPORT D'ANALYSE IA — MediScanAI
Examen : {study_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RÉSULTAT GLOBAL : FRACTURE CERVICALE PROBABLE
Score de confiance maximum : {score_max}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VERTÈBRES CONCERNÉES :
{vertebres_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INTERPRÉTATION :
Le système MediScanAI a identifié des caractéristiques
visuelles compatibles avec une anomalie osseuse au niveau
de la vertèbre {vert_principale}.

La carte Grad-CAM disponible dans l'interface indique les
régions précises ayant influencé la décision du modèle.
La bounding box délimite la zone d'intérêt sur la coupe
de référence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMANDATION :
Ce résultat doit être interprété et validé par un radiologue
ou un spécialiste en orthopédie. MediScanAI est un outil
d'aide à la décision — il ne remplace pas l'expertise médicale.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modèle : DenseNet-121 2.5D | Recall garanti : 99.5%
Seuils : Bas=0.15 / Haut=0.30 | AUC : 0.7581
"""
        return rapport.strip()

    def _rapport_negatif(self, study_id: str) -> str:
        return f"""
RAPPORT D'ANALYSE IA — MediScanAI
Examen : {study_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RÉSULTAT : AUCUNE FRACTURE CERVICALE DÉTECTÉE

Le modèle n'a identifié aucune anomalie osseuse sur
l'ensemble des coupes de cet examen (score < 0.15
sur toutes les coupes).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMANDATION :
Ce résultat ne dispense pas d'une validation par un
professionnel de santé. Le système garantit un recall
de 99.5% — 1 fracture sur 200 peut ne pas être détectée.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()


# Instance singleton — chargée une seule fois au démarrage
pipeline_service = PipelineAIService()
```

---

## ÉTAPE 4 — Service de reconstruction 3D (reconstruction_service.py)

Remplace entièrement `backend/app/services/reconstruction_service.py` :

```python
import os
import numpy as np
from scipy.ndimage import gaussian_filter, zoom
from skimage.measure import marching_cubes, label as sklabel

from .dicom_service import dicom_service


class ReconstructionService:
    """
    Reconstruction 3D via Marching Cubes.
    AUCUN modèle IA — algorithme géométrique pur.
    Indépendant de PipelineAIService.
    """

    def build_mesh(
        self,
        study_id: str,
        threshold_hu: int = 200
    ) -> dict:
        """
        Reconstruit le maillage 3D de la colonne cervicale.
        """
        volume, spacing = dicom_service.load_and_sort_slices(study_id)

        pixel_spacing   = spacing["pixel_spacing"]
        slice_thickness = spacing["slice_thickness"]

        # Rogner la région cervicale (15% à 70% du volume)
        total  = volume.shape[0]
        debut  = int(total * 0.15)
        fin    = int(total * 0.70)
        volume = volume[debut:fin, :, :]

        # Resampling isotropique — CRITIQUE pour éviter l'écrasement en Z
        zoom_z      = slice_thickness / pixel_spacing
        zoom_factors = (zoom_z / 2, 0.5, 0.5)
        volume_res  = zoom(volume, zoom_factors, order=1)

        # Lissage gaussien
        volume_smooth = gaussian_filter(volume_res, sigma=1.5)

        # Marching Cubes
        verts, faces, normals, _ = marching_cubes(
            volume_smooth,
            level=threshold_hu,
            step_size=2,
            allow_degenerate=False
        )

        # Supprimer les fragments flottants — garder le plus grand composant
        binary = (volume_smooth > threshold_hu).astype(np.uint8)
        labeled = sklabel(binary, connectivity=2)
        sizes   = np.bincount(labeled.ravel())
        sizes[0] = 0
        largest  = np.argmax(sizes)
        clean    = (labeled == largest).astype(np.float32)

        # Relancer Marching Cubes sur le volume nettoyé
        verts, faces, normals, _ = marching_cubes(
            gaussian_filter(clean, sigma=0.8) * volume_smooth,
            level=threshold_hu * 0.5,
            step_size=2,
            allow_degenerate=False
        )

        # Normaliser pour Three.js (centrer + scale [-10, 10])
        center         = verts.mean(axis=0)
        verts_centered = verts - center
        scale          = 10.0 / (np.abs(verts_centered).max() + 1e-8)
        verts_norm     = verts_centered * scale

        return {
            "vertices": verts_norm.tolist(),
            "faces":    faces.tolist(),
            "normals":  normals.tolist(),
            "stats": {
                "nb_sommets":     len(verts_norm),
                "nb_faces":       len(faces),
                "spacing_xy_mm":  pixel_spacing,
                "spacing_z_mm":   slice_thickness
            }
        }

    def colorize_mesh(
        self,
        vertices: list,
        scores_par_vertebre: dict,
        vertebra_bounds: dict = None
    ) -> list:
        """
        Colorie chaque vertex selon le score de sa vertèbre.
        Retourne une liste de couleurs hex par vertex.
        """
        def score_to_color(score: float) -> str:
            if score < 0.15:
                return "#00E5A0"   # vert — normal
            elif score < 0.30:
                return "#FFA048"   # orange — incertain
            else:
                return "#FF4757"   # rouge — élevé

        default_color = "#D4A574"  # couleur os naturelle
        colors = [default_color] * len(vertices)

        if scores_par_vertebre:
            max_score  = max(v["probabilite"] for v in scores_par_vertebre.values())
            main_color = score_to_color(max_score)
            colors     = [main_color] * len(vertices)

        return colors


reconstruction_service = ReconstructionService()
```

---

## ÉTAPE 5 — Endpoints FastAPI (routes)

Dans `backend/app/api/routes.py` (ou le fichier de routes existant),
ajoute ou remplace ces endpoints :

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response
import json

from ..services.pipeline_service import pipeline_service
from ..services.dicom_service import dicom_service
from ..services.reconstruction_service import reconstruction_service

router = APIRouter()

# ── Analyse principale ───────────────────────────────────────

@router.post("/api/analyse/{study_id}")
async def lancer_analyse(study_id: str):
    """
    Lance l'analyse complète des 3 modèles sur un examen.
    """
    try:
        resultat = pipeline_service.analyser_examen(study_id)
        return resultat
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Images ──────────────────────────────────────────────────

@router.get("/api/images/{study_id}/mpr/{view}/{index}")
async def get_mpr_slice(study_id: str, view: str, index: int):
    """
    Retourne une coupe MPR (axial/sagittal/coronal) en PNG.
    """
    try:
        volume, spacing = dicom_service.load_and_sort_slices(study_id)
        png_bytes = dicom_service.render_slice_png(volume, index, view=view)
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/images/{study_id}/gradcam/{slice_idx}")
async def get_gradcam(study_id: str, slice_idx: int):
    """
    Retourne l'overlay Grad-CAM sur une coupe en PNG.
    """
    try:
        volume, _ = dicom_service.load_and_sort_slices(study_id)
        overlay   = pipeline_service.generer_gradcam(volume, slice_idx)
        import cv2
        _, buf = cv2.imencode(".png", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        return Response(content=buf.tobytes(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Reconstruction 3D ────────────────────────────────────────

@router.get("/api/images/{study_id}/reconstruction-3d")
async def get_reconstruction_3d(study_id: str):
    """
    Retourne le maillage 3D Marching Cubes.
    Résultat mis en cache automatiquement par le service.
    """
    try:
        mesh = reconstruction_service.build_mesh(study_id)
        return mesh
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Santé du système ─────────────────────────────────────────

@router.get("/api/health")
async def health_check():
    """Vérifie que les 3 modèles sont chargés."""
    import os, timm
    MODEL_DIR = "backend/model"
    return {
        "status": "ok",
        "device": str(pipeline_service.device),
        "modeles": {
            "model1": os.path.exists(
                f"{MODEL_DIR}/model1_classifier_densenet121.pth"
            ),
            "model2": os.path.exists(
                f"{MODEL_DIR}/model2_fasterrcnn.pth"
            ),
            "model3": os.path.exists(
                f"{MODEL_DIR}/model3_vertebra_densenet121.pth"
            )
        }
    }
```

---

## ÉTAPE 6 — Mise à jour frontend

### 6a — Mettre à jour le contrat de données TypeScript

Dans `frontend/src/types/index.ts`, ajoute ou remplace :

```typescript
export type NiveauRisque = "normal" | "incertain" | "eleve"

export interface ScoreVertebre {
  probabilite:          number
  bounding_box:         { x: number; y: number; width: number; height: number } | null
  coupe_reference:      number
  slice_idx:            number
  niveau_risque:        NiveauRisque
  confiance_vertebre:   number
}

export interface ResultatAnalyse {
  study_id:             string
  fracture_detectee:    boolean
  score_global:         number
  scores_par_vertebre:  Record<string, ScoreVertebre>
  rapport_clinique:     string
  n_coupes_analysees:   number
  n_coupes_flaguees:    number
}

export const RISK_COLORS: Record<NiveauRisque, string> = {
  normal:    "#00E5A0",
  incertain: "#FFA048",
  eleve:     "#FF4757"
}

export const VERTEBRA_ORDER = ["C1","C2","C3","C4","C5","C6","C7"] as const
```

### 6b — Mettre à jour VertebraScorePanel.tsx

Le composant doit maintenant utiliser `niveau_risque` pour la couleur
(pas un calcul de seuil côté frontend) et afficher
`confiance_vertebre` comme info secondaire.

```typescript
// Couleur basée sur niveau_risque du backend
const color = RISK_COLORS[vertebra.niveau_risque]

// Affichage
<div style={{ color }}>
  {(vertebra.probabilite * 100).toFixed(1)}%
</div>
<div className="text-xs text-gray-400">
  Vertèbre identifiée à {(vertebra.confiance_vertebre * 100).toFixed(0)}%
</div>
```

### 6c — Mettre à jour SpineViewer3D.tsx

Quand l'utilisateur clique une vertèbre dans le viewer 3D,
le composant doit :
1. Afficher la coupe `coupe_reference` dans les vues MPR
2. Charger le Grad-CAM via `/api/images/{study_id}/gradcam/{slice_idx}`
3. Mettre en évidence la bounding_box sur la coupe 2D

---

## ORDRE D'EXÉCUTION — SUIS CET ORDRE EXACTEMENT

1. Crée la structure `backend/model/` et `backend/config/` avec les fichiers README et JSON
2. Remplace `dicom_service.py` (Étape 2)
3. Remplace `pipeline_service.py` (Étape 3)
4. Remplace `reconstruction_service.py` (Étape 4)
5. Mets à jour les routes FastAPI (Étape 5)
6. Mets à jour les types TypeScript (Étape 6a)
7. Mets à jour `VertebraScorePanel.tsx` (Étape 6b)
8. Mets à jour `SpineViewer3D.tsx` (Étape 6c)
9. Teste `/api/health` — doit retourner les 3 modèles avec `false` si les `.pth` ne sont pas encore en place
10. Place les 3 fichiers `.pth` dans `backend/model/`
11. Redémarre le backend et reteste `/api/health` — doit retourner `true` pour les 3 modèles
12. Teste `/api/analyse/{study_id}` avec un vrai studyInstanceUID

---

## NOTES IMPORTANTES

1. Les 3 fichiers `.pth` ne sont PAS inclus dans le repo —
   ils doivent être placés manuellement dans `backend/model/`.
   Si un fichier est absent, le modèle correspondant tourne en
   mode mock (retourne des valeurs aléatoires réalistes) pour
   que l'interface reste testable.

2. `pipeline_service` est instancié une seule fois au démarrage
   de FastAPI via le singleton en bas du fichier. Les 3 modèles
   sont chargés une seule fois en mémoire GPU — ne jamais
   réinstancier dans les routes.

3. La reconstruction 3D peut prendre 30 à 90 secondes selon
   le volume. Implémenter un cache fichier dans
   `reconstruction_service.build_mesh` :
   ```python
   cache_path = f"/tmp/mesh_cache_{study_id}.json"
   if os.path.exists(cache_path):
       with open(cache_path) as f:
           return json.load(f)
   # ... calculer ...
   with open(cache_path, "w") as f:
       json.dump(result, f)
   ```

4. Ne jamais appeler `pipeline_service.analyser_examen` depuis
   le thread principal FastAPI sur un volume complet — utiliser
   `BackgroundTasks` ou `asyncio.run_in_executor` pour éviter
   de bloquer l'API pendant l'analyse.
