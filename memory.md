# Memory
Résumés courts de chaque session de travail (les plus récentes en premier). Alimenté via le skill `/memory`. Les éléments à retenir systématiquement vivent dans [CLAUDE.md](CLAUDE.md), pas ici.

### 2026-06-24
- LSL fonctionne. Ordre : gNEEDaccess → LabRecorder (record) → pps-task.py. Tout sync en .xdf.
- Scripts : `visualize_eeg.py` (offline MNE), `stream_live.py` (live monitoring, import pylsl bug).
- Impédances EEG : 505kΩ sans bonnet, changent avec bonnet (ajouter gel).


### 2026-06-23
- Travail sur LSL (augmentation du nombre de triggers et vérification du code)

### 2026-06-22
- Revue complète de `pps-task.py` : correction de 3 bugs (double affichage des consignes/EXP_START pour la 1ère condition, bug de log où la colonne `condition` du CSV essai-par-essai enregistrait le type d'essai PPS au lieu de M/V, `pyproject.toml` sans dépendances) + un typo dans la consigne participant.
- Réglages spécifiques à la machine (nom du device audio, port COM du MMBT-S) sortis du code en dur vers `config_local.py` / `config_local.example.py`.
- Renommage `condition` → `condition_task` (M/V) et `condition_trial` (T/AN/AF/ANT/AFT/P3A) pour éviter la confusion entre les deux niveaux.
- Refonte des écrans de saisie (groupe, condition, numéro participant) 
- Ajout du resting state 
- Création des skills `/memory` et `/todo`.
