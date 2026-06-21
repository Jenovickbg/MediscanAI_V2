# ============================================================
# CURSOR PROMPT — MISE À JOUR MediScanAI
# Intégration du pipeline IA à 3 modèles + reconstruction 3D
# À envoyer en complément du prompt initial déjà fourni à Cursor
# ============================================================

Ce prompt met à jour et complète l'architecture IA de MediScanAI déjà en cours de
construction. Ne recommence pas le projet depuis zéro — intègre ces changements dans
le code existant, en particulier dans `backend/app/services/pipeline_service.py`.
Exécute les modifications dans l'ordre indiqué, étape par étape, et confirme chaque
étape terminée avant de passer à la suivante.

---

## CONTEXTE — CE QUI A CHANGÉ DEPUIS LE PROMPT INITIAL

Le pipeline IA n'est plus composé d'un seul modèle de classification. Il est désormais
composé de **trois modèles spécialisés**, plus deux composants de traitement classique
(sans IA) pour la visualisation. Chaque composant a un rôle précis et ne s'exécute que
quand c'est nécessaire.

---

## ÉTAPE 1 — Mettre à jour le Modèle 1 (classificateur de triage)

### Spécifications du modèle
```python
model_1 = timm.create_model(
    "densenet121",
    pretrained=False,
    in_chans=5,          # 5 coupes consécutives (2.5D)
    num_classes=1,
    drop_rate=0.0         # 0.0 en inférence, 0.3 pendant l'entraînement
)
# Poids : model/model1_classifier_densenet121.pth
# Target layer Grad-CAM : model.features.norm5
```

### Logique de triage à 3 niveaux — IMPORTANT, à implémenter comme une vraie fonction

Le modèle ne retourne pas juste un score brut. Il classe chaque coupe en 3 catégories
via un seuillage à deux niveaux :

```python
# backend/app/services/pipeline_service.py

class TriageThresholds:
    """
    Seuils de triage clinique du Modèle 1.
    NOTE : ces valeurs sont provisoires (issues de l'entraînement initial).
    Elles seront mises à jour après le réentraînement final avec
    early stopping — prévoir un fichier de config externe, pas une
    valeur codée en dur, pour pouvoir les ajuster sans redéployer.
    """
    SEUIL_BAS = 0.03    # < ce seuil : aucune fracture, pas d'alerte
    SEUIL_HAUT = 0.10   # >= ce seuil : haute confiance

def classifier_triage(probability: float) -> str:
    """
    Retourne : "normal" | "incertain" | "eleve"
    """
    if probability < TriageThresholds.SEUIL_BAS:
        return "normal"
    elif probability < TriageThresholds.SEUIL_HAUT:
        return "incertain"
    else:
        return "eleve"
```

### Comportement attendu
Le Modèle 1 s'exécute sur **toutes les coupes** de l'examen (jusqu'à 352). Pour chaque
coupe, il produit une probabilité ET une catégorie de triage. Seules les coupes classées
`"incertain"` ou `"eleve"` seront transmises aux Modèles 2 et 3 à l'étape suivante.

Charge ces seuils depuis un fichier `backend/config/triage_thresholds.json` plutôt que
de les coder en dur, car ils seront recalibrés après un prochain entraînement :
```json
{ "seuil_bas": 0.03, "seuil_haut": 0.10, "derniere_maj": "PLACEHOLDER" }
```

---

## ÉTAPE 2 — Implémenter le Modèle 2 (localisation Faster RCNN)

### Spécifications
```python
import torchvision
model_2 = torchvision.models.detection.fasterrcnn_resnet50_fpn(
    weights=None,
    num_classes=2   # fond + fracture (1 seule classe positive)
)
# Poids : model/model2_fasterrcnn.pth
```

### Comportement attendu — RÈGLE CRITIQUE
Le Modèle 2 ne s'exécute **jamais** sur les 352 coupes. Il s'exécute **uniquement**
sur les coupes que le Modèle 1 a classées `"incertain"` ou `"eleve"`. C'est une
contrainte de performance et de conception, pas une optimisation facultative.

```python
def run_model_2(volume, coupes_a_traiter: list[int]) -> dict:
    """
    coupes_a_traiter = uniquement les indices retournés par le triage
    du Modèle 1 (catégorie != "normal")
    Retourne : { slice_idx: {"bbox": [x,y,w,h], "confidence": float} }
    """
```

---

## ÉTAPE 3 — Implémenter le Modèle 3 (classification de vertèbre)

### Spécifications
```python
model_3 = timm.create_model(
    "densenet121",
    pretrained=False,
    in_chans=5,
    num_classes=8,        # C1 à C7 + classe "hors zone cervicale"
    drop_rate=0.0
)
# Poids : model/model3_vertebre_densenet121.pth
# Entraîné sur ~87 patients avec masques NIfTI RSNA (~30 000 coupes)
# Loss utilisée à l'entraînement : CrossEntropyLoss (pas de Focal Loss ici,
# car les classes vertébrales sont anatomiquement équilibrées)

VERTEBRA_CLASSES = ["hors_zone", "C1", "C2", "C3", "C4", "C5", "C6", "C7"]
```

### Comportement attendu
Comme le Modèle 2, le Modèle 3 ne s'exécute que sur les coupes flaguées par le
Modèle 1 — pas sur les 352 coupes.

```python
def run_model_3(volume, coupes_a_traiter: list[int]) -> dict:
    """
    Retourne : { slice_idx: "C5" }  (ou autre vertèbre prédite)
    """
```

---

## ÉTAPE 4 — Orchestrateur complet (PipelineAIService)

Remplace entièrement la classe `PipelineAIService` existante par cette version
qui orchestre les 3 modèles dans le bon ordre :

```python
class PipelineAIService:

    def __init__(self):
        self.model_1 = self._load_model_1()
        self.model_2 = self._load_model_2()
        self.model_3 = self._load_model_3()
        self.thresholds = self._load_thresholds()  # depuis triage_thresholds.json

    def analyser_examen(self, study_id: str) -> dict:
        """
        Point d'entrée principal. Orchestration complète des 3 modèles.
        """
        volume, spacing = dicom_service.load_and_sort_slices(study_id)

        # --- Phase 1 : Modèle 1 sur TOUTES les coupes ---
        scores_par_coupe = []
        for slice_idx in range(volume.shape[0]):
            stack_25d = self._build_25d_stack(volume, slice_idx)
            proba = self.model_1.predict(stack_25d)
            categorie = classifier_triage(proba)
            scores_par_coupe.append({
                "slice": slice_idx,
                "score": proba,
                "categorie": categorie
            })

        coupes_flaguees = [
            c["slice"] for c in scores_par_coupe
            if c["categorie"] != "normal"
        ]

        # --- Cas où rien n'est détecté : court-circuit ---
        if not coupes_flaguees:
            return {
                "study_id": study_id,
                "fracture_detectee": False,
                "scores_par_vertebre": {},
                "rapport_clinique": "Aucune anomalie détectée sur l'ensemble de l'examen."
            }

        # --- Phase 2 : Modèles 2 et 3 UNIQUEMENT sur les coupes flaguées ---
        resultats_bbox = self.model_2.run(volume, coupes_flaguees)
        resultats_vertebre = self.model_3.run(volume, coupes_flaguees)

        # --- Phase 3 : Agrégation par vertèbre ---
        scores_par_vertebre = self._agreger_par_vertebre(
            scores_par_coupe, resultats_bbox, resultats_vertebre
        )

        # --- Phase 4 : Génération du rapport clinique ---
        rapport = self._generer_rapport_clinique(scores_par_vertebre)

        return {
            "study_id": study_id,
            "fracture_detectee": True,
            "scores_par_vertebre": scores_par_vertebre,
            "rapport_clinique": rapport
        }

    def _agreger_par_vertebre(self, scores_coupe, bbox, vertebre) -> dict:
        """
        Pour chaque vertèbre détectée, retient la coupe avec le score
        de fracture le plus élevé comme coupe de référence.
        """
        par_vertebre = {}
        for slice_idx, vlabel in vertebre.items():
            if vlabel == "hors_zone":
                continue
            score = next(c["score"] for c in scores_coupe if c["slice"] == slice_idx)
            if vlabel not in par_vertebre or score > par_vertebre[vlabel]["probabilite"]:
                par_vertebre[vlabel] = {
                    "probabilite": score,
                    "bounding_box": bbox.get(slice_idx, {}).get("bbox"),
                    "coupe_reference": slice_idx,
                    "niveau_risque": classifier_triage(score)
                }
        return par_vertebre
```

### Contrat JSON final — utilisé par le frontend (viewer 3D + rapport)
```json
{
  "study_id": "1.2.826.0.1.3680...",
  "fracture_detectee": true,
  "scores_par_vertebre": {
    "C5": {
      "probabilite": 0.97,
      "bounding_box": {"x": 245, "y": 180, "w": 32, "h": 28},
      "coupe_reference": 187,
      "niveau_risque": "eleve"
    }
  },
  "rapport_clinique": "Texte généré..."
}
```

Cette structure exacte doit être respectée — c'est elle que `SpineViewer3D.tsx`,
le panneau de score par vertèbre, et le générateur de rapport consomment tous les trois.

---

## ÉTAPE 5 — Reconstruction 3D (Marching Cubes) — RAPPEL IMPORTANT

**Ceci n'est PAS un modèle d'IA.** Ne pas le placer dans `PipelineAIService`. C'est un
algorithme géométrique classique (Lorensen & Cline, 1987), sans entraînement, sans poids
à charger. Garde-le dans `ReconstructionService`, complètement indépendant des 3 modèles.

```python
class ReconstructionService:

    def build_mesh(self, study_id: str, threshold_hu: int = 200) -> dict:
        """
        S'exécute sur le volume COMPLET (toutes les coupes), peu importe
        ce que les modèles IA ont détecté. Aucune dépendance au pipeline IA.
        """
        volume, spacing = dicom_service.load_and_sort_slices(study_id)
        volume_lisse = scipy.ndimage.gaussian_filter(volume, sigma=0.6)
        verts, faces, normals, _ = skimage.measure.marching_cubes(
            volume_lisse, level=threshold_hu, step_size=2
        )
        return {"vertices": verts.tolist(), "faces": faces.tolist()}

    def colorize_mesh(self, vertices, scores_par_vertebre: dict) -> list:
        """
        ICI seulement les résultats des modèles IA interviennent —
        en post-traitement, pour colorer un maillage déjà construit.
        Pas avant, pas pendant la reconstruction géométrique.
        """
```

L'ordre d'exécution réel : reconstruction du maillage (géométrie pure) → ensuite,
seulement si `scores_par_vertebre` existe, on colore le maillage déjà construit.

---

## ÉTAPE 6 — Vues MPR axiale / sagittale / coronale — RAPPEL IMPORTANT

**Pas un modèle non plus.** C'est un simple ré-échantillonnage du même volume numpy
déjà chargé pour la reconstruction 3D — aucun calcul ni modèle supplémentaire.

```python
def get_mpr_slice(volume: np.ndarray, view: str, index: int) -> np.ndarray:
    if view == "axial":
        return volume[index, :, :]
    elif view == "sagittal":
        return volume[:, :, index]
    elif view == "coronal":
        return volume[:, index, :]
    else:
        raise ValueError(f"Vue inconnue : {view}")
```

Endpoint à ajouter si absent :
```
GET /api/images/{study_id}/mpr/{view}/{index}
  view: axial | sagittal | coronal
  Returns: image/png
```

---

## ORDRE D'EXÉCUTION — SUIS CET ORDRE EXACTEMENT

1. Mets à jour `PipelineAIService` avec la classe `TriageThresholds` et la fonction
   `classifier_triage()` (Étape 1). Crée `backend/config/triage_thresholds.json`.
2. Ajoute le chargement du Modèle 2 (Faster RCNN) avec mock si les poids ne sont pas
   encore disponibles dans `model/model2_fasterrcnn.pth` (Étape 2).
3. Ajoute le chargement du Modèle 3 (vertèbre) avec mock si les poids ne sont pas
   encore disponibles dans `model/model3_vertebre_densenet121.pth` (Étape 3).
4. Réécris `analyser_examen()` selon l'orchestration complète à 4 phases (Étape 4).
   Vérifie que le contrat JSON final correspond exactement à la structure donnée.
5. Vérifie que `ReconstructionService` reste totalement indépendant de
   `PipelineAIService` — aucun import croisé entre les deux (Étape 5).
6. Ajoute l'endpoint MPR s'il n'existe pas encore, en réutilisant le volume déjà
   chargé par `dicom_service` plutôt que de le recharger (Étape 6).
7. Mets à jour le endpoint `GET /api/analyse/{study_id}/resultats` pour qu'il retourne
   exactement le nouveau contrat JSON à 3 modèles.
8. Vérifie que le frontend (`VertebraScorePanel.tsx`, `SpineViewer3D.tsx`,
   `ClinicalReportGenerator.tsx`) consomme bien `niveau_risque` ("normal" /
   "incertain" / "eleve") pour la colorisation, et pas un score brut à seuil unique.
9. Confirme chaque étape terminée avant de passer à la suivante.

---

## NOTES IMPORTANTES POUR L'EXÉCUTION

1. Tant que `model2_fasterrcnn.pth` et `model3_vertebre_densenet121.pth` ne sont pas
   fournis, utilise des mocks réalistes pour ces deux modèles (comme prévu pour le
   Modèle 1 dans le prompt initial) afin que l'interface reste testable.
2. `model1_classifier_densenet121.pth` est en cours de réentraînement (early stopping
   sur Val Loss) — utilise le mock pour ce modèle aussi tant que le fichier final
   n'est pas livré, même si une version antérieure existe déjà.
3. Les valeurs de `triage_thresholds.json` sont provisoires et seront mises à jour
   après la fin du réentraînement — ne les code jamais en dur ailleurs dans le projet.
4. Respecte strictement la règle de performance : Modèles 2 et 3 ne s'exécutent
   jamais sur des coupes classées `"normal"` par le Modèle 1.
