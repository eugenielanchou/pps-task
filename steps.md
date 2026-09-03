# Guide de passation PPS-Task avec LSL

## Phase 0 : Préparation matérielle

### Matériel à vérifier avant de commencer

- ✓ Amplificateur EEG **g.HIamp** : branché en USB et en alimentation électrique
- ✓ Électrodes EEG : bien positionnées et vérifiées
- ✓ Câble audio stéréo : connecté aux enceintes (droite = near/proche, gauche = far/loin)
- ✓ Arduino (stimulateur tactile) : branché et port COM configuré dans `config_local.py`
- ✓ Ordinateur allumé et connecté au réseau (pour LSL sur localhost)

---

## Phase 1 : Démarrage de gNEEDaccess (vérification impédances EEG)

**Objectif :** Vérifier que tous les électrodes ont une bonne impédance avant de commencer l'enregistrement.

### Étapes

1. **Ouvre l'explorateur Windows** et navigue vers :
   ```
   C:\LSL\gNEEDaccess\
   ```

2. **Double-clique sur** `gNEEDaccess.exe`

3. **Interface gNEEDaccess :**
   - Sélectionne l'amplificateur **g.HIamp** s'il n'est pas déjà sélectionné
   - Clique sur le bouton d'acquisition (play/record) pour mesurer les impédances
   - Observe la grille des électrodes : ✓ vert = bon, ✗ rouge = mauvais contact
   - **Ajuste les électrodes si nécessaire** jusqu'à ce que tout soit vert

4. **Une fois OK :** laisse gNEEDaccess ouvert en arrière-plan (pas besoin de le fermer)

---

## Phase 2 : Lancer LabRecorder (enregistrement LSL)

**Objectif :** Démarrer l'enregistrement des streams LSL (EEG, ECG, markers) dans un fichier `.xdf`.

### Étapes

1. **Ouvre l'explorateur Windows** et navigue vers :
   ```
   C:\LSL\LabRecorder\
   ```

2. **Double-clique sur** `LabRecorder.exe`

3. **Interface LabRecorder :**
   - Clique sur le bouton **"Refresh"** ou **"Discover Streams"** (en haut à gauche)
   - Attends quelques secondes : tu devrais voir apparaître les streams disponibles
   - **Sélectionne tous les streams :** coches les cases pour EEG, ECG, et tout autre stream
   - Vérifie que le **dossier de destination** est défini (normalement `CurrentStudy/sub-P{N}/ses-S001/eeg/`)

4. **Clique sur "Record"** (bouton rouge en haut)
   - Le fichier `.xdf` commence à être écrit
   - Tu devrais voir un indicateur "Recording..." ou similaire
   - **Note l'heure de démarrage** pour synchroniser avec les logs

5. **Laisse LabRecorder tourner** (ne le ferme pas pendant la passation)

---

## Phase 3 : Lancer la tâche PPS (pps-task.py)

**Objectif :** Démarrer la tâche et envoyer les markers EEG via LSL.

### Étapes

1. **Ouvre PowerShell** sur ton ordinateur
   - Clique sur le menu Démarrer → tape `PowerShell`
   - Ou : `Win + R`, tape `powershell`, Entrée

2. **Navigue vers le dossier du projet :**
   ```powershell
   cd C:\Users\eduwell\Documents\Workspace\pps-task
   ```

3. **Lance le script Python :**
   ```powershell
   python pps-task.py
   ```

4. **Interface PPS-Task :**
   - Suis les consignes à l'écran
   - Saisis le groupe (E = expert, C = contrôle)
   - Saisis le numéro du participant
   - Choisis la condition (M = méditation ou V = vigilance)
   - La tâche va afficher des consignes au participant
   - **Les markers LSL sont envoyés automatiquement** lors de chaque essai PPS

5. **Une fois la tâche terminée :**
   - Le script s'arrête
   - **Retour immédiat à LabRecorder** (voir Phase 4)

---

## Phase 4 : Arrêter LabRecorder et exporter

**Objectif :** Finaliser l'enregistrement et générer le fichier `.xdf`.

### Étapes

1. **Dans la fenêtre LabRecorder :**
   - Clique sur le bouton **"Stop"** (carré rouge)
   - L'enregistrement s'arrête
   - Le fichier `.xdf` est finalisé dans :
     ```
     C:\LSL\CurrentStudy\sub-P{N}\ses-S001\eeg\
     ```

2. **Vérifie le fichier généré :**
   - Ouvre l'explorateur Windows
   - Navigue vers le dossier ci-dessus
   - Vérifie que le fichier `.xdf` est présent et contient des données

3. **Ferme LabRecorder** (optionnel, tu peux le garder ouvert pour la passation suivante)

---

## Phase 5 (optionnelle) : Monitoring en temps réel avec App-SigVisualizer

**Objectif :** Visualiser les signaux EEG/ECG en temps réel pendant la tâche (optionnel, pour debug).

### Étapes

1. **Ouvre PowerShell** et navigue vers :
   ```powershell
   cd C:\LSL\App-SigVisualizer
   ```

2. **Active le virtual environment :**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Tu devrais voir `(.venv)` au début du prompt.

3. **Lance l'app :**
   ```powershell
   python sigvisualizer.py
   ```

4. **Interface App-SigVisualizer :**
   - Une fenêtre s'ouvre avec un panneau "Streams" vide
   - Clique sur **"Update Streams"**
   - Les streams LSL disponibles (EEG, ECG, markers) apparaissent dans la liste
   - Clique sur un stream pour le visualiser en temps réel
   - **Laisse l'app ouverte** pendant la tâche pour surveiller la qualité du signal

5. **Ferme l'app** quand tu as fini (elle n'affecte pas l'enregistrement)

---

## Checklist complète pour une passation

### Avant le participant

- [ ] Vérifier que le g.HIamp est branché (USB + alimentation)
- [ ] Ouvrir et tester gNEEDaccess (tous les électrodes au vert)
- [ ] Ouvrir LabRecorder et vérifier le dossier de destination
- [ ] Préparer PowerShell pour lancer pps-task.py
- [ ] (Optionnel) Ouvrir App-SigVisualizer pour monitoring

### Pendant la passation (ordre strict)

1. **LabRecorder :** clique sur "Record" ← **À faire d'abord**
2. **PowerShell :** lance `python pps-task.py`
3. **Participant :** suit les consignes et fait la tâche
4. **pps-task.py :** se termine toute seule
5. **LabRecorder :** clique sur "Stop"
6. Vérifie que le fichier `.xdf` a été créé

### Après la passation

- [ ] Fermer gNEEDaccess
- [ ] Fermer LabRecorder
- [ ] Fermer pps-task.py (si encore ouvert)
- [ ] Fermer App-SigVisualizer (si ouvert)
- [ ] Vérifier les fichiers générés dans `CurrentStudy/sub-P{N}/ses-S001/eeg/`

---

## Troubleshooting rapide

| Problème | Solution |
|----------|----------|
| LabRecorder ne détecte pas l'ampli | Vérifie que g.HIamp est branché et allumé, clique "Refresh" |
| Les streams n'apparaissent pas dans App-SigVisualizer | Lance pps-task.py, puis clique "Update Streams" dans l'app |
| pps-task.py crash au démarrage | Vérifie que `config_local.py` a les bons réglages (port COM, device audio) |
| Fichier `.xdf` vide ou très petit | L'enregistrement n'a peut-être pas démarré ; vérifier que LabRecorder dit "Recording" |
| Les électrodes sont au rouge dans gNEEDaccess | Réajuste les électrodes ou ajoute du gel conducteur |

---

## Notes importantes à retenir

⚠️ **ORDRE CRITIQUE :** LabRecorder **AVANT** pps-task.py (sinon les markers ne sont pas enregistrés)

⚠️ **DURÉE RESTING STATE :** Vérifier que `DURATION_RESTING_STATE` dans `pps-task.py` est à **120 secondes** (2 min), pas 1 seconde (qui est actuellement le réglage pour les tests)

⚠️ **Config locale :** Les réglages spécifiques à ta machine (port COM, device audio) sont dans `config_local.py`, pas dans `pps-task.py`

⚠️ **Sauvegarde EEG :** Les fichiers `.xdf` sont précieux — fais une copie de sauvegarde après chaque passation

---

## Chemins importants à connaître

```
C:\LSL\gNEEDaccess\gNEEDaccess.exe          ← Vérification impédances
C:\LSL\LabRecorder\LabRecorder.exe          ← Enregistrement LSL
C:\LSL\App-SigVisualizer\sigvisualizer.py   ← Monitoring (optionnel)
C:\LSL\CurrentStudy\                        ← Dossier de sortie des .xdf
C:\Users\eduwell\Documents\Workspace\pps-task\pps-task.py  ← La tâche
C:\Users\eduwell\Documents\Workspace\pps-task\config_local.py  ← Réglages locaux
```
