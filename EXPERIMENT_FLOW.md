# Flux Complet de l'Expérience PPS

## Phase 1 : Collecte d'informations

### Étape 1.1 - Sélection de la langue
- **Affichage** : `lang_select`  
- **Réponse attendue** : Lettre simple (F ou E), **pas de validation barre d'espace après**
- **Variable stockée** : `language` → "fr" ou "en"

### Étape 1.2 - Numéro du participant
- **Affichage** : `participant_heading`
- **Réponse attendue** : Texte libre
- **Validation** : Barre d'espace
- **Variable stockée** : `participant_id`

### Étape 1.3 - Groupe
- **Affichage** : `group_heading`
- **Réponse attendue** : Deux lettres (E = Expert ou C = Contrôle)
- **Pas de hint**
- **Variable stockée** : `group` → "E" ou "C"

### Étape 1.4 - Condition
- **Affichage** : `condition_heading`
- **Réponse attendue** : Deux lettres (M = Méditation ou V = Vigilance)
- **Pas de hint**
- **Variable stockée** : `condition` → "M" ou "V"

---

## Phase 2 : Familiarisation Audio

### Étape 2.1 - Introduction familiarisation
- **Affichage** : `famil_intro`
- **Hint** : `intro_hint` ("Cliquer sur la barre d'espace.")
- **Validation** : Barre d'espace

### Étape 2.2 - Séquence audio (4 répétitions)
Afficher la séquence suivante **4 fois de suite** :

1. **Son proche**
   - Affichage : `famil_near`
   - Hint : `famil_sound_hint`
   - Action : Jouer le son PROCHE
   - Validation : Barre d'espace

2. **Son lointain**
   - Affichage : `famil_far`
   - Hint : `famil_sound_hint`
   - Action : Jouer le son LOINTAIN
   - Validation : Barre d'espace

3. **Son proche** (répétition)
   - Affichage : `famil_near`
   - Hint : `famil_sound_hint`
   - Action : Jouer le son PROCHE
   - Validation : Barre d'espace

4. **Son lointain** (répétition)
   - Affichage : `famil_far`
   - Hint : `famil_sound_hint`
   - Action : Jouer le son LOINTAIN
   - Validation : Barre d'espace

### Étape 2.3 - Question de répétition audio
- **Affichage** : `famil_repeat_question`
- **Réponse attendue** : Y ou N
- **Pas de hint**
- **Logique** :
  - Si **Y** : retour à l'étape 2.2 (première itération)
  - Si **N** : passage à l'étape 3 (familiarisation tactile)

---

## Phase 3 : Familiarisation Tactile

### Étape 3.1 - Affichage tactile
- **Affichage** : `famil_tactile`
- **Hint** : `famil_tactile_hint`
- **Action** : Déclencher vibration (Arduino)
- **Validation** : Barre d'espace

### Étape 3.2 - Question de répétition tactile
- **Affichage** : `famil_repeat_question`
- **Réponse attendue** : Y ou N
- **Pas de hint**
- **Logique** :
  - Si **Y** : retour à l'étape 3.1
  - Si **N** : passage à l'étape 4

---

## Phase 4 : Introduction Tâche Principale

### Étape 4.1 - Intro tâche
- **Affichage** : `task_intro_start`
- **Hint** : `intro_hint`
- **Validation** : Barre d'espace

---

## Phase 5 : Boucle des Conditions (2 itérations)

### ⚠️ Avant Condition 2 (et seulement Condition 2)
- **Affichage** : `pause_condition_1` (après Condition 1) ou `pause_condition_2` (après Condition 2)
- **Hint** : `pause_entre_condition_1_hint` ou `pause_entre_condition_2_hint`
- **Validation** : Barre d'espace

---

## Pour chaque Condition (M ou V)

### Étape 5.X.1 - Affichage de la consigne

Afficher la consigne correspondant au groupe et à la condition :

| Groupe | Condition | Message              |
|--------|-----------|----------------------|
| E      | M         | `consigne_E_M`       |
| E      | V         | `consigne_E_V`       |
| C      | M         | `consigne_C_M`       |
| C      | V         | `consigne_V_C`       |

- **Hint** : `consigne_hint`
- **Validation** : Barre d'espace

### Étape 5.X.2 - Resting State

1. **Affichage du message**
   - Affichage : `resting_state_heading`
   - Durée : `DURATION_RESTING_STATE_MSG` = **3 secondes**

2. **Croix de fixation**
   - Affichage : Croix fixation
   - Durée : `DURATION_RESTING_STATE` = **120 secondes (2 minutes)**

3. **Message d'amorce**
   - Affichage : `task_will_start`
   - Durée : `DURATION_TASK_START_MSG` = **2 secondes**

---

## Étapes spécifiques par Condition

### Si Condition = M (Méditation)

**Boucle : 2 blocs**

#### Bloc [1/2] ou [2/2]

1. **Phase de méditation 1**
   - Affichage : `meditation_1`
   - Durée : `DURATION_MEDITATION_1` = **60 secondes**

2. **Phase de méditation 2**
   - Affichage : `meditation_2` ("Continuez, en fixant la croix.")
   - Durée : `DURATION_MEDITATION_2` = **1 seconde**

3. **Croix de fixation avant bloc**
   - Affichage : Croix fixation
   - Durée : `FIXATION_BEFORE_BLOCK` = **7 secondes**

4. **Lancer stimuli PPS**
   - Jouer les stimulations auditives/tactiles (proches/lointaines)
   - Envoyer triggers LSL
   - Durée : selon le bloc PPS

5. **Fin de bloc**
   - Affichage : `end_block` {bloc_actuel}/{nb_total_blocs}
   - Durée : `DURATION_END_BLOCK` = **1 seconde**

6. **Question phénomène (iPad)**
   - Affichage : `ipad_pheno`
   - Validation : Barre d'espace

7. **Message inter-bloc**
   - Affichage : `after_block_M`
   - Durée : `DURATION_AFTER_BLOCK` = **2 secondes**

8. **Croix de fixation (avant bloc suivant ou fin)**
   - Affichage : Croix fixation
   - Durée : `FIXATION_BEFORE_BLOCK` = **7 secondes**
   - *Si bloc 2 terminé : fin de la condition*

**Fin condition M** → Passage à pause (voir phase 5) ou RT block

---

### Si Condition = V (Vigilance/Vigilance)

**Boucle : 2 blocs**

#### Bloc [1/2] ou [2/2]

1. **Instruction vigilance**
   - Affichage : `vigilance_1` ("Fixer la croix, les fruits vont apparaitre sur la croix.")
   - Durée : `DURATION_VIGILANCE_1` = **1 seconde**

2. **Croix de fixation avant bloc**
   - Affichage : Croix fixation
   - Durée : `FIXATION_BEFORE_BLOCK` = **7 secondes**

3. **Lancer stimuli PPS + Fruits**
   - Jouer les stimulations auditives/tactiles (proches/lointaines)
   - Afficher les fruits (fraises) qui défilent sur la croix
   - Envoyer triggers LSL
   - Participant compte mentalement les fraises
   - Durée : selon le bloc PPS

4. **Fin de bloc**
   - Affichage : `end_block` {bloc_actuel}/{nb_total_blocs}
   - Durée : `DURATION_END_BLOCK` = **1 seconde**

5. **Question comptage**
   - Affichage : `question_fraise` ("Combien de fraises avez-vous vues ?")
   - Réponse attendue : 1 seul chiffre (0-9)
   - Pas de validation automatique : accept sur entrée numérique unique

6. **Feedback**
   - Calculer l'écart : `erreur = |réponse - nb_réel_fraises|`
   - Afficher `feedback_template` avec :
     - `{ans}` = réponse du participant
     - `{real}` = nombre réel de fraises
     - `{err}` = écart absolu
   - Ajouter message selon l'écart :
     - Si `erreur = 0` : `feedback_well_done` ("Très bien, continuez ainsi !")
     - Si `erreur ∈ [1, 2]` : `feedback_good` ("Presque!")
     - Si `erreur > 2` : `feedback_try_harder` ("Essayez de rester attentif à l'écran.")
   - Durée affichage feedback : `DURATION_FEEDBACK` = **1.5 secondes**

7. **Question phénomène (iPad)**
   - Affichage : `ipad_pheno`
   - Validation : Barre d'espace

8. **Message inter-bloc**
   - Affichage : `after_block_V`
   - Durée : `DURATION_AFTER_BLOCK` = **2 secondes**

9. **Croix de fixation (avant bloc suivant ou fin)**
   - Affichage : Croix fixation
   - Durée : `FIXATION_BEFORE_BLOCK` = **7 secondes**
   - *Si bloc 2 terminé : fin de la condition*

**Fin condition V** → Passage à pause (voir phase 5) ou RT block

---

## Phase 6 : Pause Entre Conditions

### Après Condition 1
- **Affichage** : `pause_condition_1`
- **Hint** : `pause_entre_condition_1_hint`
- **Validation** : Barre d'espace
- **Action suivante** : Condition 2 (retour à Étape 5.X.1)

### Après Condition 2
- **Affichage** : `pause_condition_2`
- **Hint** : `pause_entre_condition_2_hint`
- **Validation** : Barre d'espace
- **Action suivante** : Passage à Phase 7 (RT Block)

---

## Phase 7 : Bloc Reaction Time (RT Block)

### Étape 7.1 - Introduction RT
- **Affichage** : `rt_block_intro` ("Pour cette dernière partie, appuyez sur la barre d'espace dès que vous ressentez la vibration, aussi rapidement que possible.")
- **Hint** : `consigne_hint`
- **Validation** : Barre d'espace

### Étape 7.2 - Amorce tâche
- **Affichage** : `task_will_start`
- **Durée** : `DURATION_TASK_START_MSG` = **2 secondes**

### Étape 7.3 - Croix de fixation initiale
- **Affichage** : Croix fixation
- **Durée** : `FIXATION_BEFORE_BLOCK` = **7 secondes**

---

## Boucle RT : 2 blocs

### Bloc [1/2]

1. **Lancer stimuli RT**
   - Jouer les stimulations (auditives/tactiles)
   - Envoyer triggers LSL
   - **Mesurer le temps de réaction** (depuis trigger jusqu'à appui barre d'espace)
   - Valider réponse : Barre d'espace

2. **Message inter-bloc**
   - Affichage : `rt_between_blocks` ("Fin du bloc 1/2.")
   - Durée : `DURATION_END_BLOCK` = **1 seconde**

3. **Question phénomène (iPad)**
   - Affichage : `ipad_pheno`
   - Validation : Barre d'espace

4. **Message après bloc**
   - Affichage : `after_block_rt` ("La même tâche va reprendre.\n\nCliquer sur la barre d'espace quand vous sentez la vibration.")
   - Durée : `DURATION_AFTER_BLOCK` = **2 secondes**

5. **Croix de fixation**
   - Affichage : Croix fixation
   - Durée : `FIXATION_BEFORE_BLOCK` = **7 secondes**

### Bloc [2/2]

1. **Lancer stimuli RT**
   - Jouer les stimulations (auditives/tactiles)
   - Envoyer triggers LSL
   - **Mesurer le temps de réaction**
   - Valider réponse : Barre d'espace

2. **Fin RT block**
   - Affichage : `rt_block_end` ("Fin du bloc 2/2.")
   - Durée : `DURATION_END_BLOCK` = **1 seconde**

3. **Question phénomène (iPad)**
   - Affichage : `ipad_pheno`
   - Validation : Barre d'espace

---

## Phase 8 : Fin Expérience

- **Affichage** : `end` ("Merci beaucoup pour votre participation !")
- **Durée** : `DURATION_END` = **3 secondes**
- **Action** : Fin de la tâche

---

## Récapitulatif des Timings

| Paramètre | Durée | Usage |
|-----------|-------|-------|
| `FIXATION_BEFORE_BLOCK` | 7 s | Croix avant chaque bloc PPS/Vigilance/RT |
| `DURATION_END_BLOCK` | 1 s | Affichage "Fin du bloc X/Y" |
| `DURATION_AFTER_BLOCK` | 2 s | Message inter-bloc |
| `DURATION_FEEDBACK` | 1.5 s | Affichage feedback fraises |
| `DURATION_RESTING_STATE` | 120 s | Croix repos (2 min) |
| `DURATION_RESTING_STATE_MSG` | 3 s | Message avant resting state |
| `DURATION_TASK_START_MSG` | 2 s | "La tâche va commencer" |
| `DURATION_MEDITATION_1` | 60 s | Méditation phase 1 |
| `DURATION_MEDITATION_2` | 1 s | Méditation phase 2 + croix |
| `DURATION_VIGILANCE_1` | 1 s | Instruction vigilance |
| `DURATION_END` | 3 s | Message de fin |

---

## Résumé : Flux Global

```
STARTUP
├─ Langue (F/E)
├─ Participant ID
├─ Groupe (E/C)
└─ Condition (M/V)

FAMILIARISATION
├─ Audio (4 × Near→Far→Near→Far + Y/N repeat)
└─ Tactile (1 × Vibration + Y/N repeat)

INTRO TÂCHE

BOUCLE CONDITIONS (2 itérations)
│
├─ Condition 1 (M ou V)
│  ├─ Consigne
│  ├─ Resting State (3s msg + 120s croix + 2s amorce)
│  ├─ Bloc 1
│  │  ├─ [Méditation/Vigilance intro]
│  │  ├─ 7s croix
│  │  ├─ Stimuli PPS [+ Fruits si V]
│  │  ├─ 1s "Fin bloc 1/2"
│  │  ├─ iPad phéno
│  │  └─ 2s message inter-bloc
│  ├─ Bloc 2
│  │  ├─ [Méditation/Vigilance intro]
│  │  ├─ 7s croix
│  │  ├─ Stimuli PPS [+ Fruits si V]
│  │  ├─ 1s "Fin bloc 2/2"
│  │  ├─ iPad phéno
│  │  └─ [Si Vigilance : question fraises + feedback]
│  │
│  └─ Pause Condition 1
│
├─ Condition 2 (M ou V, généralement l'opposée de Condition 1)
│  ├─ [Même structure que Condition 1]
│  └─ Pause Condition 2
│
RT BLOCK
├─ Intro RT
├─ 2s amorce + 7s croix
├─ Bloc 1 RT
│  ├─ Stimuli RT (mesure RT)
│  ├─ 1s "Fin bloc 1/2"
│  ├─ iPad phéno
│  └─ 2s message inter-bloc
├─ Bloc 2 RT
│  ├─ Stimuli RT (mesure RT)
│  ├─ 1s "Fin bloc 2/2"
│  └─ iPad phéno
│
FIN
└─ 3s "Merci !"
```

---

## Notes Importantes

1. **Pas de hint** pour : `group_heading`, `condition_heading`, `famil_repeat_question`, `famil_repeat_question` (tactile)
2. **Validation barre d'espace** : toutes les étapes affichant `intro_hint`, `famil_sound_hint`, `famil_tactile_hint`, `consigne_hint`, `pause_hint`, sauf input numérique
3. **Triggers LSL** : envoyés lors de chaque stimulation PPS (audio proche/lointain, tactile)
4. **RT mesure** : chronométré à partir du trigger LSL jusqu'à l'appui barre d'espace
5. **Condition initiale** : stockée à l'étape 1.4 et utilisée pour l'ordre des deux conditions (première condition = celle choisie, deuxième = l'opposée)
6. **iPad phéno** : questionnaire externe, pas géré par pps-task.py (instructeur donne iPad, participant répond, revient appuyer barre d'espace)
