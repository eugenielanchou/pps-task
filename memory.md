# Memory

Résumés courts de chaque session de travail (les plus récentes en premier). Alimenté via le skill `/memory`. Les éléments à retenir systématiquement vivent dans [CLAUDE.md](CLAUDE.md), pas ici.

### 2026-06-22

- Revue complète de `pps-task.py` : correction de 3 bugs (double affichage des consignes/EXP_START pour la 1ère condition, bug de log où la colonne `condition` du CSV essai-par-essai enregistrait le type d'essai PPS au lieu de M/V, `pyproject.toml` sans dépendances) + un typo dans la consigne participant.
- Réglages spécifiques à la machine (nom du device audio, port COM du MMBT-S) sortis du code en dur vers `config_local.py` / `config_local.example.py`.
- Renommage `condition` → `condition_task` (M/V) et `condition_trial` (T/AN/AF/ANT/AFT/P3A) dans tout le fichier, pour éviter la confusion entre les deux niveaux.
- Refonte des écrans de saisie (groupe, condition, numéro participant) : titre net en haut + aide en petit italique en bas, lettre/chiffres tapés visibles avant validation par barre d'espace. Numéro participant accepte désormais lettres + chiffres (jusqu'à 10 caractères). Police des consignes agrandie (20 → 32).
- Ajout du resting state : 2 minutes de fixation de croix, une seule fois par session, juste avant la consigne de la première condition choisie, avec marqueurs LSL dédiés `RESTING_STATE_START`/`RESTING_STATE_END`.
- Création des skills `/memory` et `/todo`.
