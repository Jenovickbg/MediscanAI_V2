# Modèles MediScanAI

Placer les 3 fichiers `.pth` dans ce dossier :

| Fichier | Modèle |
|---------|--------|
| `model1_classifier_densenet121.pth` | DenseNet-121 2.5D — fracture binaire |
| `model2_fasterrcnn.pth` | Faster R-CNN — localisation |
| `model3_vertebra_densenet121.pth` | DenseNet-121 2.5D — classification C1–C7 |

L'alias `model3_vertebre_densenet121.pth` est aussi accepté.

Sans fichier `.pth`, le modèle correspondant tourne en **mode mock**.

Vérifier le chargement : `GET /api/health`
