# CLAUDE.md

## Qui je suis

Je suis Eugénie. Je suis en thèse de neurosciences cognitives au CRNL (Centre de Recherche en Neurosciences de Lyon), encadrée par Antoine Lutz. Je suis également co-supervisée à l'EPFL par Olaf Blanke.

## Contexte du projet

Je développe une tâche d'espace péripersonnel (PPS, peripersonal space). Le projet s'inspire de l'article **Bertoni et al., 2026**, publié récemment, dans lequel les auteurs ont fait passer une tâche PPS à des patients présentant des troubles de la conscience ainsi qu'à des participants endormis. Il s'agit d'un PPS qui ne nécessite pas de réponse motrice (pas de report comportemental), uniquement un marquage EEG via les triggers.

Mon objectif est de répliquer ce paradigme chez des **méditants**, avec deux groupes de participants :
- des personnes qui méditent régulièrement,
- des personnes n'ayant jamais pratiqué la méditation.

Les deux groupes passent la même pps-task, avec deux conditions :
1. **Condition méditation (M)** : les méditants méditent réellement ; les non-méditants reçoivent des consignes méditatives similaires (pour avoir une condition comparable sans pratique réelle de méditation).
2. **Condition vigilance/absorption (V)** : tâche de comptage du nombre de fraises qui défilent à l'écran, destinée à capter l'attention et empêcher tout état méditatif pendant cette condition.

Pendant les deux conditions, les stimulations PPS (auditives/tactiles, proches/lointaines) continuent d'être délivrées et marquées en EEG, comme dans le paradigme PPS classique sans réponse motrice.

## Stack technique

- Tâche codée en **Python**, avec **PsychoPy**.
- **Python 3.10**, environnement géré avec **uv**.
- IDE : **Positron** sur Windows.
- Triggers EEG envoyés via **LSL** (Lab Streaming Layer), vers un système **g.HIamp** (g.tec).
- Stimulation tactile possible via port série (MMBT-S / Digitimer).

## Style de code et de communication

- **Code et commentaires en anglais** : le code doit être compréhensible et réutilisable par d'autres chercheurs.
- **Communication avec moi en français** : merci d'échanger avec moi en français dans les réponses, même si le code reste en anglais.
- **Pas d'emoji dans le code** : aucun emoji dans les print/logs/commentaires du code.

## Conventions établies dans pps-task.py (à respecter pour la suite)

- **Réglages spécifiques à la machine** (nom du périphérique audio, port COM du MMBT-S) : ne jamais les coder en dur dans `pps-task.py`. Ils vivent dans `config_local.py` (non suivi par git) ; `config_local.example.py` (suivi par git) sert de modèle avec les instructions pour les retrouver sur une nouvelle machine.
- **Nommage `condition_task` vs `condition_trial`** : `condition_task` = M (méditation) ou V (vigilance), au niveau de la session. `condition_trial` = T/AN/AF/ANT/AFT/P3A, au niveau de l'essai PPS. Ne pas réutiliser le nom générique `condition` pour l'un ou l'autre, ça avait créé un vrai bug de log (la colonne `condition` du CSV essai-par-essai enregistrait le mauvais niveau d'information).
- **Placement des enceintes** : "near" (AN/ANT) sort sur le canal droit, "far" (AF/AFT) sur le canal gauche → enceinte droite devant/proche du participant, enceinte gauche derrière/loin.
- **Groupe E/C** : E = méditant expert, C = contrôle. Saisi par l'expérimentateur, jamais explicité à l'écran pour le participant.
- **Pattern d'interface pour les écrans de saisie/consignes** (groupe, condition, numéro participant, resting state, consignes M/V) : titre clair et grand en haut, aide en petit et en italique en bas via `draw_hint()` / `show_instruction_space()` / `select_single_key()`. Garder cette cohérence pour tout nouvel écran.
- **Resting state** : 2 minutes de fixation de croix, une seule fois par session, juste **avant** la consigne de la première condition choisie (pas répété pour la deuxième condition).

## À faire

Avant toute chose, lire [ToDo.md](ToDo.md) (alimenté via le skill `/todo`) pour voir ce qu'Eugénie a prévu pour la prochaine session, et le signaler en début de conversation.

## Préférences pour `/memory`

Quand tu utilises le skill `/memory` pour résumer une session :
- Inclure le travail substantiel (découvertes, bugs trouvés, décisions importantes)
- **NE PAS inclure** : les todos qu'on a ajoutés, les modifications apportées à CLAUDE.md (ces métadonnées administratives ne font pas partie du "travail réel")

## LSL Setup (ordre d'exécution)

Pour chaque passation, respecter cet ordre :
1. Lance **gNEEDaccess** (C:\LSL\gNEEDaccess\gNEEDaccess.exe) → configure et vérifie impédances EEG
2. Lance **LabRecorder** en enregistrement (C:\LSL\LabRecorder\...\LabRecorder.exe) → sélectionne tous les streams, clique "Record"
3. Lance **pps-task.py** → envoie les markers via LSL
4. Arrête LabRecorder quand c'est fini → génère le .xdf dans CurrentStudy/

Les fichiers sont organisés en BIDS : CurrentStudy/sub-P{N}/ses-S001/eeg/*.xdf

## À surveiller

- ⚠️ `DURATION_RESTING_STATE` est actuellement à `1` (seconde) pour faciliter les tests — **bien remettre à `120` (2 minutes) avant toute vraie passation**.
- `setup_lsl()` n'a pas encore de `try/except` autour de la création du `StreamOutlet` (contrairement à `setup_mmbt()`) — c'est un chantier qu'Eugénie est encore en train de finaliser de son côté, ne pas y toucher sans lui demander.
