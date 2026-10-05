import os
import csv
import random
from datetime import datetime
import wave
import numpy as np
import serial
import sys
from pylsl import StreamInfo, StreamOutlet, local_clock
from psychopy import prefs

# ============================================================
# MACHINE-SPECIFIC SETTINGS
try:
    from config_local import AUDIO_DEVICE_NAME, STUDY_ROOT
except ImportError:
    raise RuntimeError(
        "Missing config_local.py. Copy config_local.example.py to "
        "config_local.py and fill in AUDIO_DEVICE_NAME and STUDY_ROOT "
        "for this machine."
    )

# ============================================================
# PSYCHOPY AUDIO BACKEND
# sounddevice must be FIRST in the list to avoid ptb trying first and failing
prefs.hardware["audioLib"] = ["sounddevice", "pyo", "pygame"]
prefs.hardware["audioDevice"] = [AUDIO_DEVICE_NAME]

from psychopy import core, visual, sound, event
from psychopy.hardware import keyboard

# ============================================================
# GLOBAL FLAGS
LSL_AVAILABLE = True
SERIAL_AVAILABLE = True
ARDUINO_ENABLED = True

# GENERAL PATHS
# Behavioral logs go to STUDY_ROOT/sub-<pp_id>/ses-<ses_id>/beh/ (see beh_dir()),
# alongside the matching EEG recording written by LabRecorder.
AUDIO_DIR = "audio"
NOISE_CACHE_DIR = "audio_cache"  # generated white-noise wav files (not tracked in git)

# ============================================================
# ARDUINO VIBRATOR SETTINGS
ARDUINO_PORT = "COM5"
ARDUINO_BAUDRATE = 115200
TTL_BYTE = 1
DURATION_TACTILE = 100  # ms - sent to Arduino.
INTENSITY = 300

# ============================================================
# EXPERIMENT DESIGN
NUM_BLOCKS_PPS = 6
TRIALS_PER_CONDITION_PER_BLOCK = 11
PPS_CONDITIONS = ["T", "AN", "AF", "ANT", "AFT"]

# ============================================================
# TIMING PARAMETERS (all in seconds unless otherwise noted)
# Audio stimulus
DURATION_AUDIO = 0.1
ISI_VALUES_PPS = [2.5, 2.6, 2.7, 2.8, 2.9, 3.0]

# Block timing and fixation
FIXATION_BEFORE_BLOCK = 7.0
DURATION_END_BLOCK = 2.5
DURATION_AFTER_BLOCK = 3.0  # inter-block message (after_block_rt), auto-timed

# Resting state and meditation
DURATION_BASELINE_STATE = 2.0  # 7 minutes initial baseline at start of experiment
DURATION_INDUCTION_MEDITATION = 2.0  # 7 minutes fixation cross for M condition
DURATION_INDUCTION_VIGILANCE = 2.0  # 7 minutes fixation cross for V condition
DURATION_END = 3.0            # final "thank you" screen, auto-timed

# ============================================================
# PHENOMENOLOGY SCALE PARAMETERS
# --- For questions AFTER baseline/induction (vertical style) ---
PHENO_V_FONT_OPTION = 36
PHENO_V_FONT_LABEL = 32
PHENO_V_FONT_TIME_HALF = 44
PHENO_V_SCALE_X = -520
PHENO_V_SCALE_LABEL_OFFSET_X = 70
PHENO_V_SCALE_LABEL_WRAP = 1300
PHENO_V_SCALE_SPACING = 50
PHENO_V_SCALE_MID_Y = -50  # vertical center that the option list is built around, regardless of its length
PHENO_V_BOX_W = 70
PHENO_V_BOX_H = 60
PHENO_V_BOX_LINE_WIDTH = 2

# --- For questions AFTER PPS blocks (pheno_bloc style) ---
# Bloc-specific layout differences (reuses V constants where identical)
PHENO_BLOC_FONT_QUESTION = 48
PHENO_BLOC_FONT_TIME_HALF = 44
PHENO_BLOC_POS_Y_QUESTION = 300
PHENO_BLOC_POS_Y_TIME_HALF = 180
PHENO_BLOC_V_SCALE_CENTER_Y = -80  # vertical center that the option list is built around, regardless of its length
PHENO_BLOC_H_SCALE_Y = 0
PHENO_BLOC_H_SCALE_SPACING = 70
PHENO_BLOC_H_SCALE_START_X = -385
PHENO_BLOC_H_SCALE_LABEL_OFFSET_Y = 70

# ============================================================
# DISPLAY PARAMETERS
TEXT_HEIGHT = 56
TEXT_WRAP = 1400

# ============================================================
# AUDIO PARAMETERS
SAMPLE_RATE = 44100
TARGET_RMS = 0.08

# ============================================================
# TRIGGER CODES FOR LSL
TRIGGER_CODES = {
    # Stimuli (3 types only - onset only, no offset)
    "AN": 1,           # Audio Near (PPS blocks only)
    "AF": 2,           # Audio Far (PPS blocks only)
    "T": 3,            # Tactile

    # Baseline (7 min initial)
    "BASELINE_START": 20,
    "BASELINE_END": 21,

    # Induction periods (7 min)
    "INDUCTION_M_START": 30,
    "INDUCTION_M_END": 31,
    "INDUCTION_V_START": 32,
    "INDUCTION_V_END": 33,
    "GONG": 34,            # Gong sound (meditation start/end cues, block-end cues)

    # Consignes (all instructions)
    "CONSIGNE_START": 40,
    "CONSIGNE_END": 41,

    # Blocks - condition-specific so the EEG marker stream itself identifies
    # M vs V (and their order), since both conditions run in the same
    # continuous recording.
    "BLOCK_M_START": 50,
    "BLOCK_M_END": 51,
    "CONDITION_M_START": 52,
    "CONDITION_M_END": 53,
    "CONDITION_V_START": 54,
    "CONDITION_V_END": 55,
    "BLOCK_V_START": 56,
    "BLOCK_V_END": 57,

    # RT block
    "RT_BLOCK_START": 60,
    "RT_BLOCK_END": 61,
    "RT_TRAINING_END": 62,     # End of RT training, real RT trials about to start

    # Spacebar responses
    "SPACEBAR_M": 72,      # Spacebar press in Meditation condition (mind recognition loss)
    "SPACEBAR_V": 70,      # Spacebar press in Vigilance condition
    "SPACEBAR_RT": 71,     # Spacebar press in RT block

    # Phenomenology
    "PHENO_RESPONSE": 80,
    "PHENO_BLOCK_START": 81,   # Start of a full phenomenology question battery
    "PHENO_BLOCK_END": 82,     # End of a full phenomenology question battery

    # Session start/end
    "EXP_START": 10,
    "EXP_END": 99,
}

# ============================================================
# INSTRUCTION TEXTS
# Organized in order of appearance in the experiment
TEXTS = {
    "fr": {
        # ===== STARTUP & INFO COLLECTION =====
        "lang_select": "Pour avoir les consignes en français, appuyez sur : F\n\nTo have the instructions in English, press: E",
        "participant_heading": "Le numéro du participant :",
        "participant_hint": "Tapez l'identifiant, puis appuyez sur la barre d'espace.",
        "session_heading": "Le numéro de session :",
        "session_hint": "Appuyez sur la barre d'espace.",
        "condition_heading": "La condition :",
        "rt_timing_heading": "Le RT :",
        "familiarization_heading": "La familiarisation :",
        "baseline_heading": "Le baseline :",

        # ===== FAMILIARIZATION =====
        "intro_hint": "Cliquer sur la barre d'espace.",
        "famil_intro": "Au cours de cette expérience, vous entendrez des sons provenant de deux enceintes et ressentirez une légère vibration au niveau du torse.\n\nNous allons d'abord vous familiariser avec ces différentes sensations.",
        "famil_near": "Pour entendre le son PROCHE, cliquer sur la barre d'espace.",
        "famil_far": "Pour entendre le son LOIN, cliquer sur la barre d'espace.",
        "famil_tactile": "Vous allez maintenant ressentir la vibration.",
        "famil_repeat_question": "Souhaitez-vous recommencer ?",
    
       # ===== TASK DESCRIPTIONS =====
        "task_intro_start": "L'expérience se déroulera en trois parties, séparées par de courtes pauses.\n\nLes sons et la vibration seront les mêmes dans chaque partie. Seul l'état dans lequel vous devrez être changera.\n\nVous serez invité à répondre à des questions sur l'écran entre chaque phase.\n",
       
        # ===== MEDITATION =====#
        "meditation_prepare": "Nous allons maintenant commencer une pratique de méditation sur la nature de l'esprit. Poser votre regard sur la croix qui apparaîtra à l'écran et gardez les yeux ouverts.\n\nVous disposerez de 7 minutes pour cette pratique. Un gong marquera le début et la fin de cette période.",
        "meditation_reconnection": "Reprenez votre pratique de la nature de l'esprit. Maintenez cette pratique pendant que les sons et les vibrations se produisent.\n\nSi vous reconnaissez la nature de l'esprit, appuyez une fois sur la barre d'espace lorsque cette reconnaissance prend fin, puis poursuivez votre pratique.\n\nSix courts blocs seront séparés par des questions affichées à l'écran.",
        "meditation_hint": "Cliquez sur la barre d'espace quand vous êtes prêt.",

        # ===== VIGILANCE =====
        "vigilance_prepare": "Nous allons maintenant commencer une tâche de concentration. Fixez votre regard sur la croix qui va apparaître au centre de l'écran, en excluant activement les distractions (pensées, émotions, etc.). Restez vigilant, moment après moment.\n\nVous disposerez d'abord de 7 minutes pour pratiquer cet état de concentration seul(e). Vous répondrez ensuite à un court questionnaire, puis vous continuerez à maintenir cet état de concentration pendant la suite de l'expérience.",
        "vigilance_reconnection": "Prenez un moment pour retourner au même état de concentration et de vigilance. Continuez à concentrer votre attention exclusivement sur les sons provenant des haut-parleurs, en gardant votre regard sur la croix.\n\nDe plus, appuyez sur la barre d'espace chaque fois que vous entendez deux sons lointains d'affilée.\n\nLa tâche consistera en six courts blocs, avec des questions affichées à l'écran entre les blocs.",
        "vigilance_hint": "Cliquez sur la barre d'espace quand vous êtes prêt.",

        # ===== BASELINE =====
        "baseline_induction_instruction": "D'abord, veuillez rester assis et regarder la croix qui apparaîtra au centre de l'écran.\nIl s'agit d'un état non méditatif. Il est normal de vous laisser absorber et de vous perdre dans vos pensées et vos émotions. \nLaissez votre esprit vagabonder pendant 7 minutes.",

        # ===== PHENOMENOLOGY QUESTIONS =====
        "pheno_questions_intro_induction": "Veuillez répondre aux questions suivantes à l'aide des flèches du clavier.\n\nNous vous invitons à vous remémorer la tâche précédente en deux moments successifs : son début et sa fin. Répondez séparément à chaque question pour chacun de ces deux moments.",
        "pheno_questions_intro_bloc": "Veuillez répondre aux questions suivantes à l'aide des flèches du clavier.\n\nNous vous invitons à vous remémorer le bloc précédent en deux moments successifs : son début et sa fin. Répondez séparément à chaque question pour chacun de ces deux moments.",
        "pheno_time_half_first": "Début",
        "pheno_time_half_second": "Fin",

        # Induction phenomenology questions (11 questions)
        "pheno_induction_q1": "Avez-vous suivi la consigne avec succès ?",
        "pheno_induction_q1_labels": ["Je ne me souviens pas", "En moyenne, sans succès", "", "", "", "", "En moyenne, assez réussi", "", "", "", "", "En moyenne, très réussi"],
        "pheno_induction_q2": "Avez-vous ressenti de l'effort pendant la session ?",
        "pheno_induction_q2_labels": ["Je ne me souviens pas", "Très laborieux, c'était du travail", "", "", "", "", "", "", "", "", "", "Complètement sans effort; la session semblait spontanée"],
        "pheno_induction_q3": "Quel était votre niveau d'énergie ou d'activation pendant la session ?",
        "pheno_induction_q3_labels": ["Je ne me souviens pas", "Très peu d'énergie (au bord de l'endormissement, ou réellement endormi)", "", "", "", "", "Niveau moyen d'énergie ou d'activation", "", "", "", "", "Beaucoup d'énergie ou d'activation (l'énergie qu'on ressent après une tasse de café fort)"],
        "pheno_induction_q4": "Dans quelle mesure étiez-vous conscient(e) des processus de l'esprit ?",
        "pheno_induction_q4_labels": ["Je ne me souviens pas", "Jamais (0%)", "", "", "", "", "Parfois (50%)", "", "", "", "", "Toujours (100%)"],
        "pheno_induction_q5": "Votre champ de conscience était-il ouvert, étendu, spacieux ? Ou plutôt focalisé et étroit ?",
        "pheno_induction_q5_labels": ["Je ne me souviens pas", "Généralement très ouvert, étendu, spacieux", "", "", "", "", "Plutôt ouvert, étendu, spacieux", "", "", "", "", "Généralement étroit"],
        "pheno_induction_q6": "À quel point les pensées vous semblaient-elles réelles par rapport à des pensées ? (ex : la pensée d'une pomme peut sembler être une vraie pomme, ou simplement une pensée)",
        "pheno_induction_q6_labels": ["Je ne me souviens pas", "Surtout apparaissant comme des pensées", "", "", "", "", "Parfois réelles, parfois comme des pensées", "", "", "", "", "Surtout apparaissant comme réelles"],
        "pheno_induction_q7": "À quelle fréquence aviez-vous des pensées sans rapport avec votre méditation (discours intérieur, imagerie mentale, souvenirs) ?",
        "pheno_induction_q7_labels": ["Je ne me souviens pas", "Jamais (0%)", "", "", "", "", "Modérément (50%)", "", "", "", "", "Tout le temps (100%)"],
        "pheno_induction_q8": "Durant la session, votre pratique était-elle stable ou distrait ?",
        "pheno_induction_q8_labels": ["Je ne me souviens pas", "Instable, toujours distrait", "", "", "", "", "Généralement stable, parfois distrait", "", "", "", "", "L'état était complètement stable, aucune distraction (ou capture de l'attention)"],
        "pheno_induction_q9": "Avez-vous expérimenté des moments que vous décririez comme reconnaître la Nature de l'Esprit ?",
        "pheno_induction_q9_labels": ["Je ne me souviens pas assez pour répondre", "Non, je n'ai pas reconnu la Nature de l'Esprit", "Oui, une fois", "Quelques fois", "Plusieurs fois", "La plupart du temps"],
        "pheno_induction_q10": "Êtes-vous confiant dans votre réponse ?",
        "pheno_induction_q10_labels": ["Je ne me souviens pas assez pour répondre", "Pas confiant", "Un peu confiant", "Confiant"],
        "pheno_induction_q11": "Comment avez-vous principalement expérimenté le temps ?",
        "pheno_induction_q11_labels": ["Je ne me souviens pas", "L'expérience semblait au-delà du temps", "J'étais dans le moment présent", "J'étais perdu dans le futur ou le passé"],

        # Bloc phenomenology questions (8 questions)
        "pheno_bloc_q1": "Dans ce bloc, et selon votre propre compréhension, avez-vous suivi la consigne avec succès ?",
        "pheno_bloc_q1_labels": ["Je ne me souviens pas", "sans succès", "", "", "", "", "", "", "", "", "", "très réussi"],
        "pheno_bloc_q2": "Avez-vous expérimenté des moments que vous décririez comme reconnaître la nature de l'esprit ?",
        "pheno_bloc_q2_labels": ["Je ne me souviens pas", "non", "oui, une fois", "quelques fois", "plusieurs fois", "la plupart du temps"],
        "pheno_bloc_q3": "Êtes-vous confiant dans votre réponse ?",
        "pheno_bloc_q3_labels": ["Je ne me souviens pas", "pas confiant", "un peu confiant", "confiant"],
        "pheno_bloc_q4": "Y avait-il une différence entre les sons proches et les sons lointains ?",
        "pheno_bloc_q4_labels": ["Non", "Oui"],
        "pheno_bloc_q5": "À quel point avez-vous ressenti une limite entre vous et les sons ?",
        "pheno_bloc_q5_labels": ["Aucune limite", "Une distance entre le sujet percevant et le son perçu", "Une séparation entre un sujet et des sons extérieurs"],
        "pheno_bloc_q6": "Y avait-il un centre de conscience ?",
        "pheno_bloc_q6_labels": ["Aucun centre", "Un sujet observant des phénomènes mentaux (sons et vibration)", "Un sentiment d'être un agent percevant les stimulations extérieures (sons et vibration)"],
        "pheno_bloc_q7": "À quel point avez-vous expérimenté les sons comme étant dans l'esprit ou comme venant de l'extérieur ?",
        "pheno_bloc_q7_labels": ["Je ne me souviens pas", "Les sons semblaient survenir dans mon esprit", "Les sons semblaient survenir en dehors de mon esprit", "Les sons semblaient survenir à la fois dans et en dehors de mon esprit"],
        "pheno_bloc_q8": "À quel point les expériences auditives impliquaient-elles une séparation entre le son entendu et un observateur ?",
        "pheno_bloc_q8_labels": ["Je ne me souviens pas", "Il n'y avait pas de sensation d'un son entendu par un observateur séparé du son", "Il semblait y avoir un observateur séparé du son, mais sans forte sensation de séparation", "Il y avait une claire sensation que les sons étaient entendus par un observateur séparé des sons"],

        # ===== BREAKS & TRANSITIONS (within a condition, per block) =====
        "end_block": "Fin du bloc {}/{}.",
        "after_pheno_bloc_M": "Reprenez votre pratique de la nature de l'esprit pendant que les sons et les vibrations se produisent, en gardant votre regard sur la croix.\n\nAppuyez une fois sur la barre d'espace dès qu'un moment de reconnaissance de la nature de l'esprit se termine.",
        "after_pheno_bloc_V": "Retournez à un état de concentration et de vigilance, en concentrant votre attention sur les sons. Gardez votre regard sur la croix.\n\nAppuyez sur la barre d'espace chaque fois que vous entendez deux sons lointains d'affilée.",

        # ===== BETWEEN CONDITIONS / BEFORE RT =====
        "pause_condition_1": "Fin de la première partie.\n\nPrenez quelques minutes pour vous détendre. Appelez l'expérimentateur avant de continuer.",
        "pause_entre_condition_1_hint": "Appelez l'expérimentateur.",
        "pause_condition_2": "Fin de la deuxième partie.\n\nPrenez quelques minutes pour vous détendre. Appelez l'expérimentateur avant de continuer.",
        "pause_entre_condition_2_hint": "Appelez l'expérimentateur.",

        # ===== REACTION TIME BLOCK =====
        "rt_block_intro": "Appuyez sur la barre d'espace dès que vous sentez la vibration, aussi rapidement que possible.",
        "rt_between_blocks": "Fin du bloc {}/{}.",
        "rt_block_end": "Fin du bloc {}/{}.",
        "after_block_rt": "La même tâche va reprendre.\n\nCliquer aussi rapidement que possible sur la barre d'espace quand vous sentez la VIBRATION.",
        "rt_training_intro": "Commençons par un court entraînement.",
        "rt_training_end_msg": "Fin de l'entraînement. La tâche va maintenant commencer.",
        "rt_feedback_good": "Bon !",
        "rt_feedback_click": "Cliquer !",

        # ===== END =====
        "end": "Merci beaucoup pour votre participation !",
    },

    "en": {
        # ===== STARTUP & INFO COLLECTION =====
        "lang_select": "Pour avoir les consignes en français, appuyez sur : F\n\nTo have the instructions in English, press: E",
        "participant_heading": "Participant number:",
        "participant_hint": "Type the ID, then press the space bar.",
        "session_heading": "Session number:",
        "session_hint": "Type the number, then press the space bar.",
        "condition_heading": "Condition:",
        "rt_timing_heading": "RT :",
        "familiarization_heading": "Familiarization:",
        "baseline_heading": "Baseline:",

        # ===== FAMILIARIZATION =====
        "intro_hint": "Press the space bar to continue.",
        "famil_intro": "During this experiment, you will hear sounds coming from two speakers and feel a slight vibration on your chest.\n\nWe will first familiarize you with these different sensations.",
        "famil_near": "To hear the NEAR sound, press the space bar.",
        "famil_far": "To hear the FAR sound, press the space bar.",
        "famil_tactile": "You will now feel the vibration.",
        "famil_repeat_question": "Would you like to do it again?",

        # ===== TASK DESCRIPTIONS =====
        "task_intro_start": "The experiment will unfold in three parts, separated by short breaks.\n\nThe sounds and vibration will be the same in each part. Only the state you must be in will change.\n\nYou will be asked to answer questions on the screen between each phase.",
        
        
        # ===== BASELINE =====
        "baseline_induction_instruction": "First, please sit still and gaze at the cross that will appear at the center of the screen. \nThis is a non-meditative state. It is okay to become absorbed in and lost in your thoughts and emotions. \n\nAllow your mind to wander for 7 minutes.",


        # ===== MEDITATION =====
        "meditation_prepare": "We will now begin a meditation practice on the Nature of Mind. Keep your eyes open and rest your gaze gently on the cross on the screen.\n\nYou will first have 7 minutes to practice on your own. A gong will mark the beginning and end of this period. \n\nYou will then complete a questionnaire and continue to sustain this state during the next part of the experiment.",
        "meditation_hint": "Press the space bar when you are ready.",
        "meditation_reconnection": "Resume your Nature of Mind practice. Maintain this practice while the sounds and vibrations occur.\n\nIf you recognise the Nature of Mind, press the space bar once when this recognition ends, then continue your practice.\n\n6 short blocks will be separated by on-screen questions.",

        # ===== VIGILANCE =====
        "vigilance_prepare": "We will now begin a concentration task. Please keep your gaze steadily focused on the cross that will appear at the center of the screen. Let the cross remain the main object of your attention, while setting aside any distractions (thoughts, emotions).\n\n" "You will first have 7 minutes to practice maintaining your focus on the cross. You will then complete a questionnaire before continuing to sustain this focused state during the next part of the experiment.",
        "vigilance_hint": "Press the space bar when you are ready.",
        "vigilance_reconnection": "Return to a concentrated state. Focus your attention on the sounds coming from the speakers, press the space bar whenever you hear two distant sounds in a row. \n\nThe task will consist of 6 short blocks, with questions displayed on the screen between blocks.",

        # ===== PHENOMENOLOGY QUESTIONS =====
        "pheno_questions_intro_induction": "Please answer the following questions using the arrow keys.\n\nWe invite you to recall the previous task in two successive moments: its beginning and its end. Answer each question separately for each of these two moments.",
        "pheno_questions_intro_bloc": "Please answer the following questions using the arrow keys.\n\nWe invite you to recall the previous block in two successive moments: its beginning and its end. Answer each question separately for each of these two moments.",
        "pheno_time_half_first": "Beginning",
        "pheno_time_half_second": "End",

        # Induction phenomenology questions (11 questions)
        "pheno_induction_q1": "How successfully did you follow the instruction?",
        "pheno_induction_q1_labels": ["I do not recall anything about this", "On average, unsuccessfully", "", "", "", "", "On average, somewhat successfully", "", "", "", "", "On average, very successfully"],
        "pheno_induction_q2": "How much effort did you feel during the session?",
        "pheno_induction_q2_labels": ["I do not recall anything about this", "Very effortful, was hard work", "", "", "", "", "", "", "", "", "", "Utterly effortless; felt the session was spontaneous"],
        "pheno_induction_q3": "What was your level of energy or arousal during the session?",
        "pheno_induction_q3_labels": ["I do not recall anything about this", "Very low energy (on the verge of falling asleep, or actually asleep)", "", "", "", "", "Average level of energy or arousal", "", "", "", "", "Very high energy or arousal (the high energy that comes from a strong cup of tea)"],
        "pheno_induction_q4": "How much were you aware of the processes of the mind?",
        "pheno_induction_q4_labels": ["I do not recall anything about this", "Never (0%)", "", "", "", "", "Sometimes (50%)", "", "", "", "", "Always (100%)"],
        "pheno_induction_q5": "Was your field of awareness open, extended, or spacious? Or rather focused and narrow?",
        "pheno_induction_q5_labels": ["I do not recall anything about this", "Usually extremely open, extended, spacious", "", "", "", "", "Somewhat open, extended, spacious", "", "", "", "", "Usually narrow"],
        "pheno_induction_q6": "To what degree did thoughts appear to be real as opposed to appearing just as thoughts? (ex: the thought of an apple can appear to be a real apple, or simply like a thought)",
        "pheno_induction_q6_labels": ["I do not recall anything about this", "Mostly appearing just as thoughts", "", "", "", "", "Sometimes real, sometimes just as thoughts", "", "", "", "", "Mostly appearing to be real"],
        "pheno_induction_q7": "How frequently did you have thoughts unrelated to your meditation (inner speech, mental imagery, memories)?",
        "pheno_induction_q7_labels": ["I do not recall anything about this", "Never (0%)", "", "", "", "", "Moderately (50%)", "", "", "", "", "All the time (100%)"],
        "pheno_induction_q8": "During the session, how stable or distracted was your practice?",
        "pheno_induction_q8_labels": ["I do not recall anything about this", "Unstable, always distracted", "", "", "", "", "Mostly stable, sometimes distracted", "", "", "", "", "The state was completely stable, no distraction (or attention capture)"],
        "pheno_induction_q9": "According to your own understanding, did you experience any moments during the session that you would describe as recognizing the Nature of Mind?",
        "pheno_induction_q9_labels": ["I do not recall enough to answer this question.", "No, I did not recognize the Nature of Mind", "Yes, once", "A few times", "Many times", "Most of the time"],
        "pheno_induction_q10": "How confident are you about your rating?",
        "pheno_induction_q10_labels": ["I do not recall enough to answer this question.", "Not confident", "A little confident", "Confident"],
        "pheno_induction_q11": "How was time most frequently experienced?",
        "pheno_induction_q11_labels": ["I do not recall anything about this", "Experience seemed beyond time", "I was in the present moment", "I was lost in the future or the past"],

        # Bloc phenomenology questions (8 questions)
        "pheno_bloc_q1": "In this block, and based on your own personal best, how successfully did you follow the instruction?",
        "pheno_bloc_q1_labels": ["I do not recall", "unsuccessful", "", "", "", "", "", "", "", "", "", "very successful"],
        "pheno_bloc_q2": "Did you experience any moments you would describe as recognizing the nature of mind?",
        "pheno_bloc_q2_labels": ["I do not recall", "no", "yes, once", "a few times", "many times", "most of the time"],
        "pheno_bloc_q3": "How confident are you about your rating?",
        "pheno_bloc_q3_labels": ["I do not recall", "not confident", "a little confident", "confident"],
        "pheno_bloc_q4": "Was there a difference between near sounds and distant sounds?",
        "pheno_bloc_q4_labels": ["No", "Yes"],
        "pheno_bloc_q5": "To what extent did you experience a boundary between you and the sounds?",
        "pheno_bloc_q5_labels": ["No boundary", "A distance between the perceiving subject and the perceived sound", "A separation between a subject and exterior sounds"],
        "pheno_bloc_q6": "Was there a center of consciousness?",
        "pheno_bloc_q6_labels": ["No center", "A subject observing mental phenomena (sounds and vibration)", "A sense of being an agent perceiving exterior stimulations (sounds and vibration)"],
        "pheno_bloc_q7": "To what extent did you experience sounds as occurring within the mind, or as feeling like they were outside it?",
        "pheno_bloc_q7_labels": ["I do not recall anything like this", "The sounds seemed to occur within my mind", "The sounds seemed to occur outside of my mind", "The sounds seemed to occur both within my mind and outside of it"],
        "pheno_bloc_q8": "To what extent did experiences of sounds involve a separation between the sound being heard and an observer (a 'hearer'), as opposed to no separation?",
        "pheno_bloc_q8_labels": ["I do not recall anything about this", "There was no sense of a sound being heard by an observer who was separate from the sound", "There seemed to be an observer separate from the sound, but without a strong sense of separation", "There was a clear sense that the sounds were being heard by an observer who was separate from the sounds"],

        "after_pheno_bloc_M": "Resume your Nature of Mind practice while the sounds and vibrations occur, keeping your gaze on the cross.\n\nPress the space bar once as soon as a moment of recognizing the Nature of Mind ends.",
        "after_pheno_bloc_V": "Return to a concentrated and vigilant state, focusing your attention on the sounds. Keep your gaze on the cross.\n\nPress the space bar whenever you hear two distant sounds in a row.",

        # ===== BREAKS & TRANSITIONS (within a condition, per block) =====
        "end_block": "End of block {}/{}.",

        # ===== BETWEEN CONDITIONS / BEFORE RT =====
        "pause_condition_1": "End of the part.\n\nTake a few minutes to relax. Call the experimenter before continuing.",
        "pause_entre_condition_1_hint": "Call the experimenter.",
        "pause_condition_2": "End of the part.\n\nTake a few minutes to relax. Call the experimenter before continuing.",
        "pause_entre_condition_2_hint": "Call the experimenter.",

        # ===== REACTION TIME BLOCK =====
        "rt_block_intro": "In that part, Press the space bar as soon as you feel the vibration, as quickly as possible.",
        "rt_between_blocks": "End of block {}/{}.",
        "rt_block_end": "End of block {}/{}.",
        "after_block_rt": "The same task will resume.\n\nPress the space bar as quickly as possible when you feel the vibration.",
        "rt_training_intro": "Let's start with a short training.",
        "rt_training_end_msg": "End of training. The task will now begin.",
        "rt_feedback_good": "Good!",
        "rt_feedback_click": "Click!",

        # ===== END =====
        "end": "Thank you very much for your participation!",
    }
}

# ============================================================
# CSV HEADERS
BLOCK_FIELDNAMES = [
    "group", "participant_num", "session", "language", "datetime", "rt_timing",
    "condition_task", "block",
    "faf_total_targets", "faf_hits", "faf_misses", "faf_false_positives",
    "faf_detection_rate", "faf_mean_rt_sec",
    "trial_sequence", "n_T", "n_AN", "n_AF", "n_ANT", "n_AFT",
    "block_duration_sec",
]

TRIAL_FIELDNAMES = [
    "group", "participant_num", "session", "datetime", "rt_timing", "condition_task",
    "block", "trial_index", "condition_trial",
    "isi_sec", "stim_onset_clock", "stim_offset_clock",
    "audio_trigger_code", "tactile_trigger_code",
    "lsl_sent", "ttl_sent", "lsl_time", "tactile_lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time", "meditation_spacebar_min_in_block",
    "faf_is_target", "faf_response_time_sec",
]

RT_TRIAL_FIELDNAMES = [
    "group", "participant_num", "session", "datetime", "rt_timing", "condition_task",
    "block", "trial_index", "condition_trial",
    "isi_sec", "stim_onset_clock", "stim_offset_clock",
    "audio_trigger_code", "tactile_trigger_code",
    "lsl_sent", "ttl_sent", "lsl_time", "tactile_lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time", "response_type",
    "reaction_time_sec", "response_absolute_clock", "response_lsl_time",
]

PHENO_FIELDNAMES = [
    "group", "participant_num", "session", "datetime", "rt_timing", "block_id",
    "time_half", "question_num", "question_text", "response",
]

# ============================================================
# GLOBAL STATE VARIABLES
marker_outlet = None
arduino = None
block_log_rows = []
trial_log_rows = []
rt_log_rows = []
pheno_log_rows = []
block_log_path = None
trial_log_path = None
rt_log_path = None
pheno_log_path = None
language = ""
group = ""  # "E" (expert meditator) or "C" (control)
condition_task = ""  # "M" = meditation, "V" = vigilance
pp_id = ""
session_dt = ""
faf_task = None
rt_timing = ""  # "before" or "after" - when RT block runs relative to M/V conditions
block_start_time = 0  # clock.getTime() when the current PPS block begins (reset at each BLOCK_START)

# ============================================================
# BASIC UTILITIES
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def timestamp_for_filename():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def beh_dir(pp_id, ses_id):
    """BIDS behavioral folder for this participant/session, alongside the
    EEG recordings: STUDY_ROOT/sub-<pp_id>/ses-<ses_id>/beh/"""
    path = os.path.join(STUDY_ROOT, f"sub-{pp_id}", f"ses-{ses_id}", "beh")
    os.makedirs(path, exist_ok=True)
    return path

def update_participants_tsv(pp_id, group, cond_1, cond_2, rt_timing):
    """Add this participant to STUDY_ROOT/participants.tsv (one row per
    participant, BIDS convention) if not already listed - including the
    condition order actually drawn, so the randomization stays traceable
    without having to reopen the task logs. No-op on repeat runs for the
    same participant."""
    subject_id = f"sub-{pp_id}"
    path = os.path.join(STUDY_ROOT, "participants.tsv")
    os.makedirs(STUDY_ROOT, exist_ok=True)

    existing_ids = set()
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                existing_ids.add(row.get("participant_id", ""))

    if subject_id in existing_ids:
        return

    is_new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        if is_new_file:
            writer.writerow(
                ["participant_id", "group", "cond_1", "cond_2", "rt_timing"]
            )
        writer.writerow([subject_id, group, cond_1, cond_2, rt_timing])

def ensure_noise_cache_dir():
    os.makedirs(NOISE_CACHE_DIR, exist_ok=True)

# ============================================================
# LSL SETUP
# one marker outlet with integer markers.
# nominal_srate = 0 means event-based irregular timing.
def setup_lsl():
    global marker_outlet

    if not LSL_AVAILABLE:
        return

    try:
        info = StreamInfo(
            name="PPS_Markers",
            type="Markers",
            channel_count=1,
            nominal_srate=0,
            channel_format="int32",
            source_id="pps_psychopy_001"
        )

        chns = info.desc().append_child("channels")
        ch = chns.append_child("channel")
        ch.append_child_value("label", "Markers")
        ch.append_child_value("type", "Markers")

        marker_outlet = StreamOutlet(info)
        print("LSL marker outlet created: PPS_Markers")
        core.wait(1.0)

    except Exception as e:
        print(f"WARNING: Could not create LSL marker outlet: {e}")
        marker_outlet = None

# ============================================================
# Arduino setup
def setup_arduino():
    global arduino
    if not ARDUINO_ENABLED or not SERIAL_AVAILABLE:
        print("Arduino vibrator disabled.")
        return

    try:
        arduino = serial.Serial(
            port=ARDUINO_PORT,
            baudrate=ARDUINO_BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.01,
            write_timeout=0.01,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        try:
            arduino.setDTR(True)
        except Exception:
            pass
        core.wait(0.2)
        arduino.write(bytes([0]))
        arduino.flush()
        core.wait(0.05)
        print(f"Arduino connected on {ARDUINO_PORT} ({ARDUINO_BAUDRATE} baud)")
    except Exception as e:
        print(f"WARNING: Could not open Arduino on {ARDUINO_PORT}: {e}")
        arduino = None
        core.quit()

def send_arduino_ttl():
    ttl_on_time = None
    ttl_off_time = None
    if arduino is not None:
        try:
            ttl_on_time = core.getTime()
            arduino.write(f"{DURATION_TACTILE},{INTENSITY}\n".encode("utf-8"))
            arduino.flush()
            ttl_off_time = core.getTime()
        except Exception as e:
            print(f"WARNING: failed to send Arduino TTL: {e}")
    return ttl_on_time, ttl_off_time

def send_lsl_marker(code):
    global marker_outlet
 
    lsl_time = None
    if marker_outlet is not None:
        try:
            lsl_time = local_clock()
            marker_outlet.push_sample([int(code)], lsl_time)
        except Exception as e:
            print(f"WARNING: failed to send LSL marker {code}: {e}")
    return lsl_time

def send_event(code_key, send_lsl=True, send_ttl=False, ttl_code=TTL_BYTE):

    global marker_outlet

    if isinstance(code_key, str):
        if code_key not in TRIGGER_CODES:
            # Hard fail rather than silently sending a 0 marker: a typo'd
            # trigger key during a real session would otherwise go
            # unnoticed on the console and only surface during analysis.
            raise KeyError(f"Unknown trigger key '{code_key}' - check TRIGGER_CODES / spelling.")
        code = TRIGGER_CODES[code_key]
    else:
        code = int(code_key)

    local_time = core.getTime()
    lsl_time = None
    ttl_on_time = None
    ttl_off_time = None

    if send_lsl:
        lsl_time = send_lsl_marker(code)
        print(f"sending trigger '{code_key}' = {code} : ")

    if send_ttl:
        ttl_on_time, ttl_off_time = send_arduino_ttl()

    return {
        "event_code": code,
        "local_time": local_time,
        "lsl_time": lsl_time,
        "ttl_on_time": ttl_on_time,
        "ttl_off_time": ttl_off_time,
        "ttl_sent": int(send_ttl and arduino is not None),
        "lsl_sent": int(send_lsl and marker_outlet is not None),
    }

# ============================================================
# AUDIO GENERATION
# Audio files are generated on the fly and then loaded by PsychoPy.
# White noise is panned left/right depending on the condition.
def normalize_rms(x, target_rms=TARGET_RMS):
    rms = np.sqrt(np.mean(x ** 2))
    if rms == 0:
        return x
    return (x / rms) * target_rms

def apply_ramp(arr, ramp_ms=5, sr=SAMPLE_RATE):
    ramp_n = int(sr * ramp_ms / 1000)
    ramp_up = np.linspace(0, 1, ramp_n, dtype=np.float32)
    ramp_down = np.linspace(1, 0, ramp_n, dtype=np.float32)
    arr = arr.copy()
    arr[:ramp_n] *= ramp_up[:, None]
    arr[-ramp_n:] *= ramp_down[:, None]
    return arr

def float_to_int16(stereo_arr):
    stereo_arr = np.clip(stereo_arr, -1.0, 1.0)
    return (stereo_arr * 32767).astype(np.int16)

def write_wav_file(path, stereo_arr, sample_rate=SAMPLE_RATE):
    pcm = float_to_int16(stereo_arr)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

def generate_white_noise_array(duration=DURATION_AUDIO, pan="both", target_rms=TARGET_RMS):
    n_samples = int(SAMPLE_RATE * duration)
    noise_arr = np.random.randn(n_samples).astype(np.float32)
    noise_arr = normalize_rms(noise_arr, target_rms=target_rms).astype(np.float32)

    if pan == "right":
        stereo = np.column_stack([np.zeros(n_samples, dtype=np.float32), noise_arr])
    elif pan == "left":
        stereo = np.column_stack([noise_arr, np.zeros(n_samples, dtype=np.float32)])
    else:
        stereo = np.column_stack([noise_arr, noise_arr])

    return apply_ramp(stereo)

def make_audio_files():
    ensure_noise_cache_dir()

    noise_right_path = os.path.join(NOISE_CACHE_DIR, "noise_right.wav")
    noise_left_path = os.path.join(NOISE_CACHE_DIR, "noise_left.wav")

    write_wav_file(noise_right_path, generate_white_noise_array(pan="right"))
    write_wav_file(noise_left_path, generate_white_noise_array(pan="left"))

    return noise_right_path, noise_left_path

NOISE_RIGHT_PATH, NOISE_LEFT_PATH = make_audio_files()
NOISE_RIGHT = sound.Sound(NOISE_RIGHT_PATH)
NOISE_LEFT = sound.Sound(NOISE_LEFT_PATH)
GONG = sound.Sound(os.path.join(AUDIO_DIR, "tibetan-bowl.wav"))

def play_sound_obj(sound_obj):
    # Stop first to avoid overlap from previous trial
    sound_obj.stop()
    sound_obj.play()
def stop_all_sounds():
    for s in [NOISE_RIGHT, NOISE_LEFT]:
        try:
            s.stop()
        except Exception:
            pass

# ============================================================
# WINDOW AND INPUT
win = visual.Window(fullscr=True, color="black", units="pix", screen=1)
win.winHandle.activate()  # force OS keyboard focus onto the PsychoPy window -
# without this, the terminal/IDE that launched the script can keep focus,
# so the very first key-driven screen (language selection) silently
# receives no keypresses at all.
kb = keyboard.Keyboard()
mouse = event.Mouse(win=win, visible=False)

# ============================================================
# INITIALIZATION of LSL and Arduino
# Done before any screen is shown, so every instruction/consigne the
# participant sees (including language/group/condition selection) can be
# marked in the EEG/ECG signal.
setup_lsl()
setup_arduino()
send_event("EXP_START", send_lsl=True, send_ttl=False)

fixation_h = visual.Line(win, start=(-50, 0), end=(50, 0), lineWidth=8, lineColor="white")
fixation_v = visual.Line(win, start=(0, -50), end=(0, 50), lineWidth=8, lineColor="white")

def clear_keyboard():
    kb.clearEvents()

def get_keys(key_list=None, wait_release=False):
    return kb.getKeys(keyList=key_list, waitRelease=wait_release)

def draw_fixation_only():
    fixation_h.draw()
    fixation_v.draw()

def draw_text(text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 0), italic=False, color="white", align_text="center", bold=False):
    # Left-aligned text should also anchor from its left edge, otherwise PsychoPy
    # still centers the text block on `pos` and it can overlap whatever sits to its left.
    anchor_horiz = "left" if align_text == "left" else "center"
    stim = visual.TextStim(win, text=text, color=color, height=height, wrapWidth=wrap, pos=pos, italic=italic,
                            alignText=align_text, anchorHoriz=anchor_horiz, bold=bold)
    stim.draw()
    return stim

def draw_hint(text, pos=(0, -350)):
    draw_text(text, height=48, wrap=TEXT_WRAP, pos=pos, italic=True)

# ============================================================
# CSV SAVING
def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def make_block_log_filename(pp_id, ses_id, group):
    return os.path.join(
        beh_dir(pp_id, ses_id),
        f"sub-{pp_id}_ses-{ses_id}_group-{group}_{timestamp_for_filename()}_blocks.csv"
    )

def make_trial_log_filename(pp_id, ses_id, group):
    return os.path.join(
        beh_dir(pp_id, ses_id),
        f"sub-{pp_id}_ses-{ses_id}_group-{group}_{timestamp_for_filename()}_trials.csv"
    )

def make_rt_log_filename(pp_id, ses_id, group):
    return os.path.join(
        beh_dir(pp_id, ses_id),
        f"sub-{pp_id}_ses-{ses_id}_group-{group}_rt_{timestamp_for_filename()}_trials.csv"
    )

def make_pheno_log_filename(pp_id, ses_id, group):
    return os.path.join(
        beh_dir(pp_id, ses_id),
        f"sub-{pp_id}_ses-{ses_id}_group-{group}_{timestamp_for_filename()}_pheno.csv"
    )

def save_logs_now():
    try:
        if block_log_path and block_log_rows:
            write_csv(block_log_path, block_log_rows, BLOCK_FIELDNAMES)
            print("Saved blocks:", block_log_path)
    except Exception as e:
        print("Could not save block log:", e)

    try:
        if trial_log_path and trial_log_rows:
            write_csv(trial_log_path, trial_log_rows, TRIAL_FIELDNAMES)
            print("Saved trials:", trial_log_path)
    except Exception as e:
        print("Could not save trial log:", e)

    try:
        if rt_log_path and rt_log_rows:
            write_csv(rt_log_path, rt_log_rows, RT_TRIAL_FIELDNAMES)
            print("Saved RT trials:", rt_log_path)
    except Exception as e:
        print("Could not save RT trial log:", e)

    try:
        if pheno_log_path and pheno_log_rows:
            write_csv(pheno_log_path, pheno_log_rows, PHENO_FIELDNAMES)
            print("Saved phenomenology responses:", pheno_log_path)
    except Exception as e:
        print("Could not save pheno log:", e)

def save_phenomenology_responses(block_id, responses_dict, question_list, response_keys=None):
    global pheno_log_rows
    if response_keys is None:
        response_keys = [f"q{i}" for i in range(1, len(question_list) + 1)]

    for time_half, responses in responses_dict.items():
        for idx, (question_text, response_key) in enumerate(zip(question_list, response_keys), 1):
            if response_key in responses:
                response = responses[response_key]
                row = {
                    "group": group,
                    "participant_num": pp_id,
                    "session": ses_id,
                    "datetime": now_str(),
                    "rt_timing": rt_timing,
                    "block_id": block_id,
                    "time_half": time_half,
                    "question_num": idx,
                    "question_text": question_text,
                    "response": response,
                }
                pheno_log_rows.append(row)

# ============================================================
# SAFE EXIT
def safe_quit():
    try:
        if arduino is not None:
            arduino.close()
    except Exception as e:
        print(f"Error while closing Arduino: {e}")

    try:
        stop_all_sounds()
    except Exception as e:
        print(f"Error while stopping sounds: {e}")

    try:
        send_event("EXP_END", send_lsl=True, send_ttl=False)
    except Exception as e:
        print(f"Error while sending EXP_END: {e}")

    try:
        save_logs_now()
    except Exception as e:
        print(f"Error while saving logs: {e}")

    try:
        win.close()
    except Exception as e:
        print(f"Error while closing PsychoPy window: {e}")

    core.quit()

def check_escape():
    keys = get_keys(["escape"])
    if any(k.name == "escape" for k in keys):
        safe_quit()

# ============================================================
# SCREEN HELPERS
def show_text_space(text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, start_key=None, end_key=None):
    clear_keyboard()
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)
    while True:
        check_escape()
        draw_text(text, height=height, wrap=wrap)
        win.flip()
        keys = get_keys(["space", "escape"])
        if any(k.name == "escape" for k in keys):
            safe_quit()
        if any(k.name == "space" for k in keys):
            break
    if end_key:
        send_event(end_key, send_lsl=True, send_ttl=False)

def show_instruction_space(heading, hint, height=TEXT_HEIGHT, wrap=TEXT_WRAP, start_key=None, end_key=None):
    # Same idea as the group/condition screens: the heading stays prominent,
    # the "press space to continue" hint is small and italic at the bottom.
    clear_keyboard()
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)
    while True:
        check_escape()
        draw_text(heading, height=height, wrap=wrap, pos=(0, 80))
        draw_hint(hint)
        win.flip()
        keys = get_keys(["space", "escape"])
        if any(k.name == "escape" for k in keys):
            safe_quit()
        if any(k.name == "space" for k in keys):
            break
    if end_key:
        send_event(end_key, send_lsl=True, send_ttl=False)

def show_text_timed(text, seconds, height=TEXT_HEIGHT, wrap=TEXT_WRAP, start_key=None, end_key=None):
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)
    t_end = core.getTime() + seconds
    while core.getTime() < t_end:
        check_escape()
        draw_text(text, height=height, wrap=wrap)
        win.flip()
    if end_key:
        send_event(end_key, send_lsl=True, send_ttl=False)

def show_baseline(seconds, send_markers=False, start_key=None, end_key=None):
    if send_markers:
        send_event(start_key, send_lsl=True, send_ttl=False)

    t_end = core.getTime() + seconds
    while core.getTime() < t_end:
        check_escape()
        draw_fixation_only()
        win.flip()

    if send_markers:
        send_event(end_key, send_lsl=True, send_ttl=False)

def show_baseline_state():
    """Initial baseline at the start of the experiment (7 minutes).
    Shown once, before any conditions start."""
    show_baseline(
        DURATION_BASELINE_STATE,
        send_markers=True,
        start_key="BASELINE_START",
        end_key="BASELINE_END",
    )

def show_end_of_block_screen(block_idx):
    txt = TEXTS[language]["end_block"].format(block_idx + 1, NUM_BLOCKS_PPS)
    show_text_timed(txt, seconds=DURATION_END_BLOCK, height=56, wrap=TEXT_WRAP,
                     start_key="CONSIGNE_START", end_key="CONSIGNE_END")

# ============================================================
# PHENOMENOLOGY QUESTIONS AFTER INDUCTION (vertical style)
def draw_selection_box_pheno(pos):
    rect = visual.Rect(win, width=PHENO_V_BOX_W, height=PHENO_V_BOX_H, pos=pos,
                        fillColor=None, lineColor="yellow", lineWidth=PHENO_V_BOX_LINE_WIDTH)
    rect.draw()

def draw_question_block_pheno(question_text, time_half=None):
    draw_text(question_text, height=52, wrap=TEXT_WRAP, pos=(0, 420), color="white")
    if time_half:
        label_key = "pheno_time_half_first" if time_half == "T1" else "pheno_time_half_second"
        label = TEXTS[language][label_key]
        draw_text(label, height=PHENO_V_FONT_TIME_HALF, wrap=TEXT_WRAP,
                   pos=(0, 300), color="yellow", bold=True)

def ask_scale_vertical_pheno(question_text, scale_options, scale_labels, start_idx=1, time_half=None):
    clear_keyboard()
    selected_idx = start_idx
    start_y = PHENO_V_SCALE_MID_Y + (len(scale_options) - 1) * PHENO_V_SCALE_SPACING / 2

    while True:
        check_escape()
        draw_question_block_pheno(question_text, time_half=time_half)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            y_pos = start_y - idx * PHENO_V_SCALE_SPACING
            color = "yellow" if idx == selected_idx else "white"

            if idx == selected_idx:
                draw_selection_box_pheno((PHENO_V_SCALE_X, y_pos))

            draw_text(option, height=PHENO_V_FONT_OPTION, pos=(PHENO_V_SCALE_X, y_pos), color=color)
            if label:
                draw_text(label.capitalize(), height=PHENO_V_FONT_LABEL, wrap=PHENO_V_SCALE_LABEL_WRAP,
                           pos=(PHENO_V_SCALE_X + PHENO_V_SCALE_LABEL_OFFSET_X, y_pos),
                           color=color, align_text="left")

        win.flip()

        for k in get_keys(["up", "down", "space", "escape"]):
            if k.name == "escape":
                safe_quit()
            elif k.name == "up" and selected_idx > 0:
                selected_idx -= 1
            elif k.name == "down" and selected_idx < len(scale_options) - 1:
                selected_idx += 1
            elif k.name == "space":
                send_event("PHENO_RESPONSE", send_lsl=True, send_ttl=False)
                return scale_options[selected_idx]

def ask_phenomenology_questions_after_induction():
    send_event("PHENO_BLOCK_START", send_lsl=True, send_ttl=False)

    time_moments = ["T1", "T2"]
    responses = {}

    question_texts = [
        TEXTS[language]["pheno_induction_q1"],
        TEXTS[language]["pheno_induction_q2"],
        TEXTS[language]["pheno_induction_q3"],
        TEXTS[language]["pheno_induction_q4"],
        TEXTS[language]["pheno_induction_q5"],
        TEXTS[language]["pheno_induction_q6"],
        TEXTS[language]["pheno_induction_q7"],
        TEXTS[language]["pheno_induction_q8"],
        TEXTS[language]["pheno_induction_q9"],
        TEXTS[language]["pheno_induction_q10"],
        TEXTS[language]["pheno_induction_q11"],
    ]

    q1_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q1_labels = TEXTS[language]["pheno_induction_q1_labels"]

    q2_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q2_labels = TEXTS[language]["pheno_induction_q2_labels"]

    q3_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q3_labels = TEXTS[language]["pheno_induction_q3_labels"]

    q4_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q4_labels = TEXTS[language]["pheno_induction_q4_labels"]

    q5_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q5_labels = TEXTS[language]["pheno_induction_q5_labels"]

    q6_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q6_labels = TEXTS[language]["pheno_induction_q6_labels"]

    q7_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q7_labels = TEXTS[language]["pheno_induction_q7_labels"]

    q8_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q8_labels = TEXTS[language]["pheno_induction_q8_labels"]

    q9_options = ["X", "0", "1", "2", "3", "4"]
    q9_labels = TEXTS[language]["pheno_induction_q9_labels"]

    q10_options = ["X", "1", "2", "3"]
    q10_labels = TEXTS[language]["pheno_induction_q10_labels"]

    q11_options = ["X", "1", "2", "3"]
    q11_labels = TEXTS[language]["pheno_induction_q11_labels"]

    for moment in time_moments:
        responses[moment] = {}

    for moment in time_moments:
        responses[moment]["q1"] = ask_scale_vertical_pheno(question_texts[0], q1_options, q1_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q2"] = ask_scale_vertical_pheno(question_texts[1], q2_options, q2_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q3"] = ask_scale_vertical_pheno(question_texts[2], q3_options, q3_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q4"] = ask_scale_vertical_pheno(question_texts[3], q4_options, q4_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q5"] = ask_scale_vertical_pheno(question_texts[4], q5_options, q5_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q6"] = ask_scale_vertical_pheno(question_texts[5], q6_options, q6_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q7"] = ask_scale_vertical_pheno(question_texts[6], q7_options, q7_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q8"] = ask_scale_vertical_pheno(question_texts[7], q8_options, q8_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q9"] = ask_scale_vertical_pheno(question_texts[8], q9_options, q9_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q10"] = ""
        if responses[moment]["q9"] not in ["0", "X"]:
            responses[moment]["q10"] = ask_scale_vertical_pheno(question_texts[9], q10_options, q10_labels, 1, time_half=moment)

    for moment in time_moments:
        responses[moment]["q11"] = ask_scale_vertical_pheno(question_texts[10], q11_options, q11_labels, 1, time_half=moment)

    send_event("PHENO_BLOCK_END", send_lsl=True, send_ttl=False)
    return responses, question_texts

# ============================================================
# PHENOMENOLOGY QUESTIONS AFTER PPS BLOCKS (pheno_bloc style)
def draw_selection_box_bloc(pos):
    rect = visual.Rect(win, width=PHENO_V_BOX_W, height=PHENO_V_BOX_H, pos=pos,
                        fillColor=None, lineColor="yellow", lineWidth=PHENO_V_BOX_LINE_WIDTH)
    rect.draw()

def draw_question_block_bloc(question_text, time_half=None):
    draw_text(question_text, height=PHENO_BLOC_FONT_QUESTION, wrap=TEXT_WRAP, pos=(0, PHENO_BLOC_POS_Y_QUESTION))
    if time_half:
        label_key = "pheno_time_half_first" if time_half == "T1" else "pheno_time_half_second"
        label = TEXTS[language][label_key]
        draw_text(label, height=PHENO_BLOC_FONT_TIME_HALF, wrap=TEXT_WRAP,
                   pos=(0, PHENO_BLOC_POS_Y_TIME_HALF), color="yellow", bold=True)

def ask_scale_vertical_bloc(question_text, scale_options, scale_labels, start_idx=1, time_half=None, spacing=None, time_half_y=None):
    if spacing is None:
        spacing = PHENO_V_SCALE_SPACING

    clear_keyboard()
    selected_idx = start_idx
    start_y = PHENO_BLOC_V_SCALE_CENTER_Y + (len(scale_options) - 1) * spacing / 2

    while True:
        check_escape()
        draw_question_block_bloc(question_text, time_half=time_half)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            y_pos = start_y - idx * spacing
            color = "yellow" if idx == selected_idx else "white"

            if idx == selected_idx:
                draw_selection_box_bloc((PHENO_V_SCALE_X, y_pos))

            draw_text(option, height=PHENO_V_FONT_OPTION, pos=(PHENO_V_SCALE_X, y_pos), color=color)
            if label:
                draw_text(label.capitalize(), height=PHENO_V_FONT_LABEL, wrap=PHENO_V_SCALE_LABEL_WRAP,
                           pos=(PHENO_V_SCALE_X + PHENO_V_SCALE_LABEL_OFFSET_X, y_pos),
                           color=color, align_text="left")

        win.flip()

        for k in get_keys(["up", "down", "space", "escape"]):
            if k.name == "escape":
                safe_quit()
            elif k.name == "up" and selected_idx > 0:
                selected_idx -= 1
            elif k.name == "down" and selected_idx < len(scale_options) - 1:
                selected_idx += 1
            elif k.name == "space":
                send_event("PHENO_RESPONSE", send_lsl=True, send_ttl=False)
                return scale_options[selected_idx]

def ask_success_rating_bloc(question_text, time_half=None):
    clear_keyboard()
    scale_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    scale_labels = TEXTS[language]["pheno_bloc_q1_labels"]
    selected_idx = 1

    while True:
        check_escape()
        draw_question_block_bloc(question_text, time_half=time_half)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            x_pos = PHENO_BLOC_H_SCALE_START_X + idx * PHENO_BLOC_H_SCALE_SPACING
            color = "yellow" if idx == selected_idx else "white"

            if idx == selected_idx:
                draw_selection_box_bloc((x_pos, PHENO_BLOC_H_SCALE_Y))

            draw_text(option, height=PHENO_V_FONT_OPTION, pos=(x_pos, PHENO_BLOC_H_SCALE_Y), color=color)
            if label and option == "X":
                draw_text(label, height=28, pos=(x_pos, PHENO_BLOC_H_SCALE_Y + PHENO_BLOC_H_SCALE_LABEL_OFFSET_Y), color=color)
            elif label:
                draw_text(label, height=28, pos=(x_pos, PHENO_BLOC_H_SCALE_Y - PHENO_BLOC_H_SCALE_LABEL_OFFSET_Y), color=color)

        win.flip()

        for k in get_keys(["left", "right", "space", "escape"]):
            if k.name == "escape":
                safe_quit()
            elif k.name == "left" and selected_idx > 0:
                selected_idx -= 1
            elif k.name == "right" and selected_idx < len(scale_options) - 1:
                selected_idx += 1
            elif k.name == "space":
                send_event("PHENO_RESPONSE", send_lsl=True, send_ttl=False)
                return scale_options[selected_idx]

def ask_phenomenology_questions_after_block(block_idx):
    send_event("PHENO_BLOCK_START", send_lsl=True, send_ttl=False)

    responses = {"T1": {}, "T2": {}}

    q1_txt = TEXTS[language]["pheno_bloc_q1"]
    responses["T1"]["success_rating"] = ask_success_rating_bloc(q1_txt, "T1")
    responses["T2"]["success_rating"] = ask_success_rating_bloc(q1_txt, "T2")

    q2_txt = TEXTS[language]["pheno_bloc_q2"]
    q2_options = ["X", "0", "1", "2", "3", "4"]
    q2_labels = TEXTS[language]["pheno_bloc_q2_labels"]

    q3_txt = TEXTS[language]["pheno_bloc_q3"]
    q3_options = ["X", "1", "2", "3"]
    q3_labels = TEXTS[language]["pheno_bloc_q3_labels"]

    responses["T1"]["nom_recognition"] = ask_scale_vertical_bloc(q2_txt, q2_options, q2_labels, 1, time_half="T1")
    responses["T1"]["nom_confidence"] = ""
    if responses["T1"]["nom_recognition"] not in ["0", "X"]:
        responses["T1"]["nom_confidence"] = ask_scale_vertical_bloc(
            q3_txt, q3_options, q3_labels, 1, time_half="T1")

    responses["T2"]["nom_recognition"] = ask_scale_vertical_bloc(q2_txt, q2_options, q2_labels, 1, time_half="T2")
    responses["T2"]["nom_confidence"] = ""
    if responses["T2"]["nom_recognition"] not in ["0", "X"]:
        responses["T2"]["nom_confidence"] = ask_scale_vertical_bloc(
            q3_txt, q3_options, q3_labels, 1, time_half="T2")

    q4_txt = TEXTS[language]["pheno_bloc_q4"]
    q4_options = ["0", "1"]
    q4_labels = TEXTS[language]["pheno_bloc_q4_labels"]
    responses["T1"]["near_far_difference"] = ask_scale_vertical_bloc(q4_txt, q4_options, q4_labels, 0, time_half="T1")
    responses["T2"]["near_far_difference"] = ask_scale_vertical_bloc(q4_txt, q4_options, q4_labels, 0, time_half="T2")

    q5_txt = TEXTS[language]["pheno_bloc_q5"]
    q5_options = ["0", "1", "2"]
    q5_labels = TEXTS[language]["pheno_bloc_q5_labels"]
    responses["T1"]["boundary_experience"] = ask_scale_vertical_bloc(q5_txt, q5_options, q5_labels, 0, time_half="T1")
    responses["T2"]["boundary_experience"] = ask_scale_vertical_bloc(q5_txt, q5_options, q5_labels, 0, time_half="T2")

    q6_txt = TEXTS[language]["pheno_bloc_q6"]
    q6_options = ["0", "1", "2"]
    q6_labels = TEXTS[language]["pheno_bloc_q6_labels"]
    responses["T1"]["center_of_consciousness"] = ask_scale_vertical_bloc(q6_txt, q6_options, q6_labels, 0, time_half="T1", spacing=90)
    responses["T2"]["center_of_consciousness"] = ask_scale_vertical_bloc(q6_txt, q6_options, q6_labels, 0, time_half="T2", spacing=90)

    q7_txt = TEXTS[language]["pheno_bloc_q7"]
    q7_options = ["X", "1", "2", "3"]
    q7_labels = TEXTS[language]["pheno_bloc_q7_labels"]
    responses["T1"]["sounds_location"] = ask_scale_vertical_bloc(q7_txt, q7_options, q7_labels, 1, time_half="T1")
    responses["T2"]["sounds_location"] = ask_scale_vertical_bloc(q7_txt, q7_options, q7_labels, 1, time_half="T2")

    q8_txt = TEXTS[language]["pheno_bloc_q8"]
    q8_options = ["X", "1", "2", "3"]
    q8_labels = TEXTS[language]["pheno_bloc_q8_labels"]
    responses["T1"]["sound_observer_separation"] = ask_scale_vertical_bloc(q8_txt, q8_options, q8_labels, 1, time_half="T1", spacing=100)
    responses["T2"]["sound_observer_separation"] = ask_scale_vertical_bloc(q8_txt, q8_options, q8_labels, 1, time_half="T2", spacing=100)

    question_texts = [q1_txt, q2_txt, q3_txt, q4_txt, q5_txt, q6_txt, q7_txt, q8_txt]
    send_event("PHENO_BLOCK_END", send_lsl=True, send_ttl=False)
    return responses, question_texts

def ask_yes_no_question(question_key="famil_repeat_question"):
    # No hint shown for these questions (per spec).
    clear_keyboard()
    while True:
        check_escape()
        draw_text(TEXTS[language][question_key], height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 60))
        win.flip()

        valid_keys = ["o", "n"] if language == "fr" else ["y", "n"]
        keys = get_keys(valid_keys + ["escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name in valid_keys:
                return k.name.lower() == ("o" if language == "fr" else "y")

def show_stimulus_familiarization():
    send_event("CONSIGNE_START", send_lsl=True, send_ttl=False)

    show_instruction_space(
        TEXTS[language]["famil_intro"],
        TEXTS[language]["intro_hint"],
    )

    # Audio: 4 presentations in a row (near, far, near, far), then a
    # single repeat question. Restarts the full 4-presentation sequence
    # if the answer is yes.
    while True:
        for _ in range(2):
            show_instruction_space(
                TEXTS[language]["famil_near"],
                "",
            )
            play_sound_obj(NOISE_RIGHT)
            core.wait(DURATION_AUDIO + 0.2)
            stop_all_sounds()

            show_instruction_space(
                TEXTS[language]["famil_far"],
                "",
            )
            play_sound_obj(NOISE_LEFT)
            core.wait(DURATION_AUDIO + 0.2)
            stop_all_sounds()

        if not ask_yes_no_question("famil_repeat_question"):
            break

    # Tactile: single vibration, then the SAME repeat question key as audio.
    while True:
        show_instruction_space(
            TEXTS[language]["famil_tactile"],
            "",
        )
        send_arduino_ttl()
        core.wait(0.5)

        if not ask_yes_no_question("famil_repeat_question"):
            break

    send_event("CONSIGNE_END", send_lsl=True, send_ttl=False)

# ============================================================
# INPUT HELPERS
def collect_single_choice(valid_keys):
    clear_keyboard()
    while True:
        check_escape()
        keys = get_keys(valid_keys + ["escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            if k.name in valid_keys:
                return k.name

def select_single_key(heading, hint=None, valid_keys=None, start_key=None, end_key=None):
    # The experimenter presses one of the valid keys directly - that key
    # press itself confirms and advances immediately, no space bar needed.
    clear_keyboard()
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)

    while True:
        check_escape()
        draw_text(heading, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 120))
        if hint:
            draw_hint(hint)
        win.flip()

        keys = get_keys(valid_keys + ["escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name in valid_keys:
                chosen = k.name.upper()
                if end_key:
                    send_event(end_key, send_lsl=True, send_ttl=False)
                return chosen

LETTER_KEYS = list("abcdefghijklmnopqrstuvwxyz")

def collect_text_input(heading, hint, max_chars=10, start_key=None, end_key=None):
    # Accepts digits and letters (e.g. participant IDs like "12" or "P03").
    typed = ""
    clear_keyboard()
    digit_keys = [str(i) for i in range(10)] + [f"num_{i}" for i in range(10)]
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)

    while True:
        check_escape()
        display_text = typed if typed else "_"
        draw_text(heading, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 120))
        draw_text(display_text, height=48, wrap=TEXT_WRAP, pos=(0, 0))
        draw_hint(hint)
        win.flip()

        keys = get_keys(["space", "backspace", "escape"] + LETTER_KEYS + digit_keys)

        for k in keys:
            name = k.name
            if name == "escape":
                safe_quit()
            elif name == "space" and typed != "":
                if end_key:
                    send_event(end_key, send_lsl=True, send_ttl=False)
                return typed
            elif name == "backspace":
                typed = typed[:-1]
            elif name.startswith("num_") and len(typed) < max_chars:
                typed += name[-1]
            elif (name.isdigit() or name in LETTER_KEYS) and len(typed) < max_chars:
                typed += name.upper()

# ============================================================
# BLOCK RANDOMIZATION
def build_block():
    # Build one block with balanced conditions
    trials = []
    for cond in PPS_CONDITIONS:
        trials.extend([cond] * TRIALS_PER_CONDITION_PER_BLOCK)

    best_trials = None
    min_consecutive = 999

    # Try multiple shuffles and keep the best one
    for _ in range(500):
        random.shuffle(trials)
        consecutive_count = sum(
            1 for i in range(1, len(trials)) if trials[i] == trials[i - 1]
        )
        if consecutive_count < min_consecutive:
            min_consecutive = consecutive_count
            best_trials = trials.copy()
        if consecutive_count == 0:
            break

    if min_consecutive > 0:
        print(f"Block has {min_consecutive} consecutive pair(s).")

    return best_trials

def build_experiment():
    return [build_block() for _ in range(NUM_BLOCKS_PPS)]

# ============================================================
# VIGILANCE TASK - FAF DETECTION
class FAFDetectionTask:
    """Tracks consecutive FAF (two far sounds) detection task for V condition."""
    def __init__(self):
        self.running = False
        self.stimulus_history = []
        self.responses = []
        self.target_indices = []

    def start(self):
        self.running = True
        self.stimulus_history = []
        self.responses = []
        self.target_indices = []

    def stop(self):
        self.running = False

    def add_stimulus(self, condition_trial, trial_idx, stim_onset_time):
        """Called when a stimulus is presented. Checks if two AF are consecutive."""
        if not self.running:
            return

        self.stimulus_history.append({
            "condition": condition_trial,
            "trial_idx": trial_idx,
            "stim_time": stim_onset_time
        })

        # Check if we have two consecutive AF
        if len(self.stimulus_history) >= 2:
            prev_stimulus = self.stimulus_history[-2]["condition"]
            curr_stimulus = self.stimulus_history[-1]["condition"]

            if prev_stimulus == "AF" and curr_stimulus == "AF":
                self.target_indices.append(trial_idx)

    def log_response(self, trial_idx, response_time=None):
        """Log a participant's response (spacebar click)."""
        if not self.running:
            return

        self.responses.append({
            "trial_idx": trial_idx,
            "response_time": response_time
        })

    def get_stats(self):
        """Calculate detection statistics."""
        target_set = set(self.target_indices)
        response_set = {r["trial_idx"] for r in self.responses}

        hits = len(target_set & response_set)
        misses = len(target_set - response_set)
        false_positives = len(response_set - target_set)

        reaction_times = [r["response_time"] for r in self.responses if r["response_time"] is not None]
        mean_rt = (sum(reaction_times) / len(reaction_times)) if reaction_times else 0

        total_targets = len(target_set)
        detection_rate = (hits / total_targets * 100) if total_targets > 0 else 0

        return {
            "total_targets": total_targets,
            "hits": hits,
            "misses": misses,
            "false_positives": false_positives,
            "detection_rate": detection_rate,
            "mean_rt": mean_rt,
        }

# ============================================================
# MASTER CLOCK
clock = core.Clock()
clock.reset()

def frame_loop_until(t_end, vigilance_task=None, faf_task=None, trial_idx=None, stim_onset=0, meditation_spacebar_times=None, faf_response_times=None):
    while True:
        check_escape()
        now = clock.getTime()

        if now >= t_end:
            break

        draw_fixation_only()

        # Detect spacebar presses for meditation condition (mind recognition loss tracking).
        # Recorded as minutes elapsed since the start of the CURRENT block (not the
        # condition, and not the trial's stimulus) - the clock resets at each of the
        # 6 PPS blocks, so it reflects when within that block the loss of recognition
        # happened.
        if meditation_spacebar_times is not None and condition_task == "M":
            keys = get_keys(["space"])
            if any(k.name == "space" for k in keys):
                elapsed_min = (now - block_start_time) / 60.0
                meditation_spacebar_times.append(elapsed_min)
                send_event("SPACEBAR_M", send_lsl=True, send_ttl=False)

        # Detect spacebar presses for FAF detection (only during vigilance condition).
        # Checked against faf_task.responses (not a local flag) because this function
        # is called twice per trial - once for the stimulus window, once for the ISI -
        # and a flag reset on each call would have let a second click on the same
        # trial be logged twice.
        if faf_task is not None and condition_task == "V":
            already_responded = any(r["trial_idx"] == trial_idx for r in faf_task.responses)
            if not already_responded:
                keys = get_keys(["space"])
                if any(k.name == "space" for k in keys):
                    response_time = now - stim_onset
                    faf_task.log_response(trial_idx, response_time)
                    if faf_response_times is not None:
                        faf_response_times.append(response_time)
                    send_event("SPACEBAR_V", send_lsl=True, send_ttl=False)

        win.flip()

# ============================================================
# TRIAL LOGIC
def describe_trial(condition_trial):
    if condition_trial == "T":
        return False, True, ""
    if condition_trial == "AN":
        return True, False, "near"
    if condition_trial == "AF":
        return True, False, "far"
    if condition_trial == "ANT":
        return True, True, "near"
    if condition_trial == "AFT":
        return True, True, "far"
    raise ValueError(f"Unknown condition_trial: {condition_trial}")

def get_trigger_codes(condition_trial):
    """Return (audio_trigger_code, tactile_trigger_code): the code(s) of the
    LSL marker(s) actually sent for this trial. ANT/AFT send two separate
    markers (AN or AF, then T) rather than one blended code - see run_trial
    for the full rationale - so both are reported here."""
    audio_code = ""
    tactile_code = ""
    if condition_trial in ("AN", "AF"):
        audio_code = TRIGGER_CODES[condition_trial]
    elif condition_trial == "T":
        tactile_code = TRIGGER_CODES["T"]
    elif condition_trial in ("ANT", "AFT"):
        audio_code = TRIGGER_CODES["AN"] if condition_trial == "ANT" else TRIGGER_CODES["AF"]
        tactile_code = TRIGGER_CODES["T"]
    return audio_code, tactile_code

def build_rt_block():
    # Build one RT block (55 trials, biased toward audio+tactile).
    # Called NUM_RT_BLOCKS times (see run_rt_block_task) - 3 x 55 = 165 total.
    trials = []
    trials.extend(["T"] * 5)
    trials.extend(["AN"] * 5)
    trials.extend(["AF"] * 5)
    trials.extend(["ANT"] * 20)
    trials.extend(["AFT"] * 20)

    best_trials = None
    min_consecutive = 999

    for _ in range(500):
        random.shuffle(trials)
        consecutive_count = sum(
            1 for i in range(1, len(trials)) if trials[i] == trials[i - 1]
        )
        if consecutive_count < min_consecutive:
            min_consecutive = consecutive_count
            best_trials = trials.copy()
        if consecutive_count == 0:
            break

    if min_consecutive > 0:
        print(f"RT Block has {min_consecutive} consecutive pair(s).")

    return best_trials

def run_rt_trial(condition_trial, trial_idx, block_idx=0):
    """Run one RT trial with keyboard response detection for tactile stimuli."""
    global rt_log_rows, marker_outlet

    audio_present, tactile_present, _ = describe_trial(condition_trial)
    stim_onset = clock.getTime()

    event_info = {
        "event_code": TRIGGER_CODES.get(condition_trial, 0),
        "local_time": None,
        "lsl_time": None,
        "ttl_on_time": None,
        "ttl_off_time": None,
        "ttl_sent": 0,
        "lsl_sent": 0,
    }

    audio_play_call_time = None
    response_time = None
    response_lsl_time = None

    # Tactile only
    if condition_trial == "T":
        event_info = send_event(
            condition_trial,
            send_lsl=True,
            send_ttl=True,
            ttl_code=TTL_BYTE
        )

    # Audio only
    elif condition_trial in ["AN", "AF"]:
        event_info = send_event(condition_trial, send_lsl=True, send_ttl=False)
        audio_play_call_time = core.getTime()

        if condition_trial == "AN":
            play_sound_obj(NOISE_RIGHT)
        elif condition_trial == "AF":
            play_sound_obj(NOISE_LEFT)

    # Audio + tactile - synchronized.
    # Sent as TWO separate component markers (AN/AF for the audio onset,
    # T for the tactile onset) fired at their own true dispatch time,
    # rather than one blended "ANT"/"AFT" marker. This lets each modality's
    # onset be latency-corrected independently once measured on the
    # oscilloscope (audio ~instant, tactile lagged by the vibration
    # motor's mechanical rise time). The tactile command still goes out
    # first in code order, since it is the one with the longer physical
    # latency to compensate for - once you know the measured lag, insert
    # an explicit core.wait() here between the two calls to align the two
    # PHYSICAL onsets rather than the two software calls.
    elif condition_trial in ["ANT", "AFT"]:
        audio_code = "AN" if condition_trial == "ANT" else "AF"
        sound_to_play = NOISE_RIGHT if condition_trial == "ANT" else NOISE_LEFT

        sound_to_play.stop()

        # Tactile component first (compensates mechanical lag once calibrated)
        ttl_on_time, ttl_off_time = send_arduino_ttl()
        tactile_lsl_time = send_lsl_marker(TRIGGER_CODES["T"])

        # Audio component
        audio_play_call_time = core.getTime()
        audio_lsl_time = send_lsl_marker(TRIGGER_CODES[audio_code])
        sound_to_play.play()

        event_info = {
            "event_code": TRIGGER_CODES.get(condition_trial, 0),  # kept in the trial log only, not sent as its own EEG marker
            "local_time": core.getTime(),
            "lsl_time": audio_lsl_time,
            "tactile_lsl_time": tactile_lsl_time,
            "ttl_on_time": ttl_on_time,
            "ttl_off_time": ttl_off_time,
            "ttl_sent": 1 if arduino is not None else 0,
            "lsl_sent": 1 if marker_outlet is not None else 0,
        }

    # Stimulus presentation window - let sound play
    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset)
    stop_all_sounds()

    # Response detection window. Keys are now ALWAYS checked (not gated
    # behind tactile_present) so that spurious responses on AN/AF-only
    # trials (false alarms) are captured rather than silently dropped.
    clear_keyboard()
    response_detected = False
    response_window_end = stim_offset + 1.5

    while clock.getTime() < response_window_end:
        check_escape()
        draw_fixation_only()
        win.flip()

        if not response_detected:
            keys = get_keys(["space"])
            if any(k.name == "space" for k in keys):
                response_time = clock.getTime() - stim_onset
                response_lsl_time = send_lsl_marker(TRIGGER_CODES["SPACEBAR_RT"])
                response_detected = True

    response_type = "response" if response_detected else "no_response"

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = response_window_end + isi
    frame_loop_until(trial_end)

    stim_offset_clock = stim_onset + DURATION_AUDIO
    audio_trigger_code, tactile_trigger_code = get_trigger_codes(condition_trial)

    rt_log_rows.append({
        "participant_num": pp_id,
        "group": group,
        "session": ses_id,
        "datetime": session_dt,
        "rt_timing": rt_timing,
        "condition_task": condition_task,
        "block": block_idx + 1,
        "trial_index": trial_idx + 1,
        "condition_trial": condition_trial,
        "isi_sec": isi,
        "stim_onset_clock": round(stim_onset, 6),
        "stim_offset_clock": round(stim_offset_clock, 6),
        "audio_trigger_code": audio_trigger_code,
        "tactile_trigger_code": tactile_trigger_code,
        "lsl_sent": event_info["lsl_sent"],
        "ttl_sent": event_info["ttl_sent"],
        "lsl_time": event_info["lsl_time"],
        "tactile_lsl_time": event_info.get("tactile_lsl_time", ""),
        "ttl_on_time": event_info["ttl_on_time"],
        "ttl_off_time": event_info["ttl_off_time"],
        "audio_play_call_time": audio_play_call_time,
        "response_type": response_type,
        "reaction_time_sec": round(response_time, 6) if response_time is not None else "",
        "response_absolute_clock": round(stim_onset + response_time, 6) if response_time is not None else "",
        "response_lsl_time": response_lsl_time,
    })

def run_trial(condition_trial, block_idx, trial_idx, faf_task=None):
    audio_present, tactile_present, _ = describe_trial(condition_trial)
    stim_onset = clock.getTime()

    meditation_spacebar_times = []
    faf_response_times = []
    faf_is_target = ""
    if faf_task is not None:
        faf_task.add_stimulus(condition_trial, trial_idx, stim_onset)
        faf_is_target = 1 if trial_idx in faf_task.target_indices else 0

    event_info = {
        "event_code": TRIGGER_CODES.get(condition_trial, 0),
        "local_time": None,
        "lsl_time": None,
        "ttl_on_time": None,
        "ttl_off_time": None,
        "ttl_sent": 0,
        "lsl_sent": 0,
    }

    audio_play_call_time = None

    # Tactile only
    if condition_trial == "T":
        event_info = send_event(
            condition_trial,
            send_lsl=True,
            send_ttl=True,
            ttl_code=TTL_BYTE
        )

    # Audio only
    elif condition_trial in ["AN", "AF"]:
        event_info = send_event(condition_trial, send_lsl=True, send_ttl=False)
        audio_play_call_time = core.getTime()

        if condition_trial == "AN":
            play_sound_obj(NOISE_RIGHT)
        elif condition_trial == "AF":
            play_sound_obj(NOISE_LEFT)

    # Audio + tactile - synchronized.
    # Sent as TWO separate component markers (AN/AF for the audio onset, T
    # for the tactile onset) at their own true dispatch time, rather than
    # one blended "ANT"/"AFT" marker - see run_rt_trial for the full
    # rationale. The condition label ("ANT"/"AFT") is still recorded in
    # the trial CSV log for bookkeeping; in the EEG marker stream these
    # trials are identifiable as an AN/AF marker immediately followed by a
    # T marker (well within the >2s ITI, so unambiguous vs. two separate
    # unisensory trials).
    elif condition_trial in ["ANT", "AFT"]:
        audio_code = "AN" if condition_trial == "ANT" else "AF"
        sound_to_play = NOISE_RIGHT if condition_trial == "ANT" else NOISE_LEFT

        sound_to_play.stop()

        # Tactile component first (compensates mechanical lag once calibrated
        # via oscilloscope - insert an explicit core.wait() here once you
        # know the measured lag, to align the two PHYSICAL onsets)
        ttl_on_time, ttl_off_time = send_arduino_ttl()
        tactile_lsl_time = send_lsl_marker(TRIGGER_CODES["T"])

        # Audio component
        audio_play_call_time = core.getTime()
        audio_lsl_time = send_lsl_marker(TRIGGER_CODES[audio_code])
        sound_to_play.play()

        event_info = {
            "event_code": TRIGGER_CODES.get(condition_trial, 0),  # kept in the trial log only, not sent as its own EEG marker
            "local_time": core.getTime(),
            "lsl_time": audio_lsl_time,
            "tactile_lsl_time": tactile_lsl_time,
            "ttl_on_time": ttl_on_time,
            "ttl_off_time": ttl_off_time,
            "ttl_sent": 1 if arduino is not None else 0,
            "lsl_sent": 1 if marker_outlet is not None else 0,
        }

    # Stimulus presentation window
    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset, faf_task=faf_task, trial_idx=trial_idx, stim_onset=stim_onset, meditation_spacebar_times=meditation_spacebar_times, faf_response_times=faf_response_times)
    stop_all_sounds()

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = stim_offset + isi
    frame_loop_until(trial_end, faf_task=faf_task, trial_idx=trial_idx, stim_onset=stim_onset, meditation_spacebar_times=meditation_spacebar_times, faf_response_times=faf_response_times)

    stim_offset_clock = stim_onset + DURATION_AUDIO
    audio_trigger_code, tactile_trigger_code = get_trigger_codes(condition_trial)

    meditation_spacebar_str = "|".join(f"{round(t, 3)}" for t in meditation_spacebar_times) if meditation_spacebar_times else ""
    faf_response_str = "|".join(f"{round(t, 3)}" for t in faf_response_times) if faf_response_times else ""

    trial_log_rows.append({
        "participant_num": pp_id,
        "group": group,
        "session": ses_id,
        "datetime": session_dt,
        "rt_timing": rt_timing,
        "condition_task": condition_task,
        "block": block_idx + 1,
        "trial_index": trial_idx + 1,
        "condition_trial": condition_trial,
        "isi_sec": isi,
        "stim_onset_clock": round(stim_onset, 6),
        "stim_offset_clock": round(stim_offset_clock, 6),
        "audio_trigger_code": audio_trigger_code,
        "tactile_trigger_code": tactile_trigger_code,
        "lsl_sent": event_info["lsl_sent"],
        "ttl_sent": event_info["ttl_sent"],
        "lsl_time": event_info["lsl_time"],
        "tactile_lsl_time": event_info.get("tactile_lsl_time", ""),
        "ttl_on_time": event_info["ttl_on_time"],
        "ttl_off_time": event_info["ttl_off_time"],
        "audio_play_call_time": audio_play_call_time,
        "meditation_spacebar_min_in_block": meditation_spacebar_str,
        "faf_is_target": faf_is_target,
        "faf_response_time_sec": faf_response_str,
    })

# ============================================================
# LANGUAGE SELECTION
while True:
    check_escape()
    draw_text(TEXTS["fr"]["lang_select"], height=TEXT_HEIGHT, wrap=TEXT_WRAP)
    win.flip()

    key_name = collect_single_choice(["f", "e"])
    if key_name == "f":
        language = "fr"
        break
    elif key_name == "e":
        language = "en"
        break

# ============================================================
# PARTICIPANT INFO
pp_id = collect_text_input(
    TEXTS[language]["participant_heading"],
    TEXTS[language]["participant_hint"],
    max_chars=10,
)
print(f"Participant ID: {pp_id}")

# ============================================================
# SESSION INFO
# Must match the "Session" field typed into LabRecorder so the behavioral
# logs (beh_dir) and the .xdf recordings end up under the same sub-/ses-.
ses_id = collect_text_input(
    TEXTS[language]["session_heading"],
    TEXTS[language]["session_hint"],
    max_chars=4,
)
print(f"Session: {ses_id}")

# ============================================================
# GROUP SELECTION
group = "E"
print(f"Group: {group}")

# ============================================================
# CONDITION SELECTION (M = meditation, V = vigilance)
# No hint shown (per spec).
condition_task = select_single_key(
    TEXTS[language]["condition_heading"],
    valid_keys=["m", "v"],
)
print(f"Condition: {condition_task}")

# ============================================================
# RT TIMING SELECTION (before or after M/V conditions)
rt_timing_choice = select_single_key(
    TEXTS[language]["rt_timing_heading"],
    valid_keys=["1", "2"],
)
rt_timing = "before" if rt_timing_choice == "1" else "after"
print(f"RT Timing: {rt_timing}")

# ============================================================
# FAMILIARIZATION TOGGLE
# Lets the experimenter skip the stimulus familiarization (e.g. already
# done earlier the same day).
familiarization_choice = select_single_key(
    TEXTS[language]["familiarization_heading"],
    valid_keys=["o", "n"] if language == "fr" else ["y", "n"],
)
do_familiarization = familiarization_choice == ("O" if language == "fr" else "Y")
print(f"Familiarization: {do_familiarization}")

# ============================================================
# STIMULUS FAMILIARIZATION
if do_familiarization:
    show_stimulus_familiarization()

# ============================================================
# BASELINE TOGGLE
# Lets the experimenter skip the initial baseline (with its phenomenology
# questions, which are part of the same block and are not asked separately).
baseline_choice = select_single_key(
    TEXTS[language]["baseline_heading"],
    valid_keys=["o", "n"] if language == "fr" else ["y", "n"],
)
do_baseline = baseline_choice == ("O" if language == "fr" else "Y")
print(f"Baseline: {do_baseline}")

# ============================================================
# CONDITION ORDER
cond_1 = condition_task
cond_2 = "V" if cond_1 == "M" else "M"
update_participants_tsv(pp_id, group, cond_1, cond_2, rt_timing)

show_instruction_space(
    TEXTS[language]["task_intro_start"],
    TEXTS[language]["intro_hint"],
    start_key="CONSIGNE_START", end_key="CONSIGNE_END",
)

# ============================================================
# SESSION TIMESTAMP (for log filenames)
session_dt = now_str()

# ============================================================
# BASELINE INDUCTION INSTRUCTION + INITIAL BASELINE STATE + PHENOMENOLOGY
if do_baseline:
    show_instruction_space(
        TEXTS[language]["baseline_induction_instruction"].format(duration="7 minutes"),
        TEXTS[language]["intro_hint"],
        start_key="CONSIGNE_START", end_key="CONSIGNE_END",
    )

    # INITIAL BASELINE STATE (7 minutes at the very start)
    show_baseline_state()

    show_instruction_space(
        TEXTS[language]["pheno_questions_intro_induction"],
        TEXTS[language]["intro_hint"],
        start_key="CONSIGNE_START", end_key="CONSIGNE_END",
    )

    responses, question_texts = ask_phenomenology_questions_after_induction()
    save_phenomenology_responses("phenobaseline", responses, question_texts)

# ============================================================
# MAIN LOOP

def show_transition_pause(part_number):
    """Pause screen shown between the 3 parts of the session (RT / M / V,
    in whichever order was chosen). part_number is the part that JUST
    ENDED (1 or 2) - this picks "fin de la premiere/deuxieme partie" so
    the text always matches where we actually are, regardless of which
    part (RT, M or V) that happens to be."""
    key = "pause_condition_1" if part_number == 1 else "pause_condition_2"
    hint_key = ("pause_entre_condition_1_hint" if part_number == 1
                else "pause_entre_condition_2_hint")
    show_instruction_space(
        TEXTS[language][key],
        TEXTS[language][hint_key],
        start_key="CONSIGNE_START", end_key="CONSIGNE_END",
    )


def run_condition_task(cond):
    global condition_task, faf_task, block_start_time

    condition_task = cond
    print(f"\n=== Starting condition {condition_task} ===")

    faf_task = FAFDetectionTask() if condition_task == "V" else None
    all_blocks = build_experiment()

    # Condition-specific preparation
    if condition_task == "M":
        # M condition: prepare meditation → long fixation (7 min) → ready to start
        show_instruction_space(
            TEXTS[language]["meditation_prepare"],
            TEXTS[language]["meditation_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        # Gong sounds at the start of fixation
        send_event("GONG", send_lsl=True, send_ttl=False)
        GONG.play()

        # Meditation preparation period (7 min): silent fixation, no audio
        show_baseline(DURATION_INDUCTION_MEDITATION, send_markers=True,
                       start_key="INDUCTION_M_START", end_key="INDUCTION_M_END")

        # Gong sounds at the end of fixation (before stimuli begin)
        send_event("GONG", send_lsl=True, send_ttl=False)
        GONG.play()

        show_instruction_space(
            TEXTS[language]["pheno_questions_intro_induction"],
            TEXTS[language]["intro_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        responses, question_texts = ask_phenomenology_questions_after_induction()
        save_phenomenology_responses("phenoM", responses, question_texts)

        show_instruction_space(
            TEXTS[language]["meditation_reconnection"],
            TEXTS[language]["meditation_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

    else:  # V condition
        # V condition: prepare vigilance → long fixation (7 min) → ready to start
        show_instruction_space(
            TEXTS[language]["vigilance_prepare"],
            TEXTS[language]["vigilance_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        # Vigilance preparation period (7 min): fixation cross only, no sounds
        show_baseline(DURATION_INDUCTION_VIGILANCE, send_markers=True,
                     start_key="INDUCTION_V_START", end_key="INDUCTION_V_END")

        show_instruction_space(
            TEXTS[language]["pheno_questions_intro_induction"],
            TEXTS[language]["intro_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        responses, question_texts = ask_phenomenology_questions_after_induction()
        save_phenomenology_responses("phenoV", responses, question_texts)

        show_instruction_space(
            TEXTS[language]["vigilance_reconnection"],
            TEXTS[language]["vigilance_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

    send_event(f"CONDITION_{condition_task}_START", send_lsl=True, send_ttl=False)

    for block_idx, block in enumerate(all_blocks):
        print(f"\nStart block {block_idx + 1}/{NUM_BLOCKS_PPS}")

        show_baseline(FIXATION_BEFORE_BLOCK)

        send_event(f"BLOCK_{condition_task}_START", send_lsl=True, send_ttl=False)
        block_t0 = clock.getTime()
        block_start_time = block_t0

        counts = {k: 0 for k in PPS_CONDITIONS}

        if condition_task == "V":
            faf_task.start()

        for trial_idx, cond_trial in enumerate(block):
            counts[cond_trial] += 1
            run_trial(
                condition_trial=cond_trial,
                block_idx=block_idx,
                trial_idx=trial_idx,
                faf_task=faf_task if condition_task == "V" else None
            )

        faf_stats = None
        if condition_task == "V":
            faf_task.stop()
            faf_stats = faf_task.get_stats()

        # Gong at block end (M condition)
        if condition_task == "M":
            send_event("GONG", send_lsl=True, send_ttl=False)
            GONG.play()

        block_t1 = clock.getTime()
        block_duration = block_t1 - block_t0
        trial_sequence_str = ",".join(block)

        send_event(f"BLOCK_{condition_task}_END", send_lsl=True, send_ttl=False)

        row = {
            "participant_num": pp_id,
            "session": ses_id,
            "language": language,
            "group": group,
            "datetime": session_dt,
            "rt_timing": rt_timing,
            "condition_task": condition_task,
            "block": block_idx + 1,
            "faf_total_targets": faf_stats["total_targets"] if faf_stats else "",
            "faf_hits": faf_stats["hits"] if faf_stats else "",
            "faf_misses": faf_stats["misses"] if faf_stats else "",
            "faf_false_positives": faf_stats["false_positives"] if faf_stats else "",
            "faf_detection_rate": round(faf_stats["detection_rate"], 2) if faf_stats else "",
            "faf_mean_rt_sec": round(faf_stats["mean_rt"], 6) if faf_stats else "",
            "trial_sequence": trial_sequence_str,
            "n_T": counts["T"],
            "n_AN": counts["AN"],
            "n_AF": counts["AF"],
            "n_ANT": counts["ANT"],
            "n_AFT": counts["AFT"],
            "block_duration_sec": round(block_duration, 3),
        }

        # Sequence after each block's trials:
        # end-of-block screen -> phenomenology question -> after every
        # block, including the last. The after_block message + closing
        # fixation, however, ONLY run between blocks (not after the last
        # block of the condition - the condition ends there and
        # transitions straight to the pause_condition_1/2 screen instead).
        # FAF detection stats (V condition) are still computed and logged
        # to CSV below, just not shown on screen (raw numbers confused
        # participants).
        show_end_of_block_screen(block_idx)

        show_instruction_space(
            TEXTS[language]["pheno_questions_intro_bloc"],
            TEXTS[language]["intro_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        responses, question_texts = ask_phenomenology_questions_after_block(block_idx)
        block_id = f"phenoblocpps{condition_task}{block_idx + 1}"
        response_keys = ["success_rating", "nom_recognition", "nom_confidence", "near_far_difference",
                        "boundary_experience", "center_of_consciousness", "sounds_location", "sound_observer_separation"]
        save_phenomenology_responses(block_id, responses, question_texts, response_keys)

        # Display reconnection message after phenomenology questions
        pheno_bloc_key = "after_pheno_bloc_M" if condition_task == "M" else "after_pheno_bloc_V"
        show_instruction_space(TEXTS[language][pheno_bloc_key], TEXTS[language]["intro_hint"],
                                start_key="CONSIGNE_START", end_key="CONSIGNE_END")

        block_log_rows.append(row)
        save_logs_now()

        if block_idx < NUM_BLOCKS_PPS - 1:
            if condition_task == "M":
                core.wait(2.0)
                send_event("GONG", send_lsl=True, send_ttl=False)
                GONG.play()
            show_baseline(FIXATION_BEFORE_BLOCK)

    send_event(f"CONDITION_{condition_task}_END", send_lsl=True, send_ttl=False)
    save_logs_now()


NUM_RT_BLOCKS = 3  # 3 blocks x 55 trials = 165 total, 60 ANT + 60 AFT

def build_rt_training_block():
    """Build RT training block: 3T + 3AFT + 3ANT + 2AN + 1AF = 12 trials."""
    trials = []
    trials.extend(["T"] * 3)
    trials.extend(["AFT"] * 3)
    trials.extend(["ANT"] * 3)
    trials.extend(["AN"] * 2)
    trials.extend(["AF"] * 1)
    random.shuffle(trials)
    return trials

def run_rt_training_trial(condition_trial, trial_idx):
    """Run one RT training trial with tactile feedback."""
    audio_present, tactile_present, audio_side = describe_trial(condition_trial)
    stim_onset = clock.getTime()

    response_detected = False

    if condition_trial == "T":
        send_event(
            condition_trial,
            send_lsl=True,
            send_ttl=True,
            ttl_code=TTL_BYTE
        )

    elif condition_trial in ["AN", "AF"]:
        send_event(condition_trial, send_lsl=True, send_ttl=False)
        if condition_trial == "AN":
            play_sound_obj(NOISE_RIGHT)
        elif condition_trial == "AF":
            play_sound_obj(NOISE_LEFT)

    elif condition_trial in ["ANT", "AFT"]:
        audio_code = "AN" if condition_trial == "ANT" else "AF"
        sound_to_play = NOISE_RIGHT if condition_trial == "ANT" else NOISE_LEFT
        sound_to_play.stop()

        send_arduino_ttl()
        send_lsl_marker(TRIGGER_CODES["T"])

        send_lsl_marker(TRIGGER_CODES[audio_code])
        sound_to_play.play()

    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset)
    stop_all_sounds()

    clear_keyboard()
    response_window_end = stim_offset + 1.5

    while clock.getTime() < response_window_end:
        check_escape()
        draw_fixation_only()
        win.flip()

        if not response_detected:
            keys = get_keys(["space"])
            if any(k.name == "space" for k in keys):
                response_time = clock.getTime() - stim_onset
                send_lsl_marker(TRIGGER_CODES["SPACEBAR_RT"])
                response_detected = True

    if tactile_present:
        if response_detected:
            feedback_txt = TEXTS[language]["rt_feedback_good"]
            feedback_color = "green"
        else:
            feedback_txt = TEXTS[language]["rt_feedback_click"]
            feedback_color = "red"

        clear_keyboard()
        t_end = core.getTime() + 1.0
        while core.getTime() < t_end:
            check_escape()
            draw_text(feedback_txt, height=TEXT_HEIGHT, wrap=TEXT_WRAP, color=feedback_color)
            win.flip()

    isi = random.choice(ISI_VALUES_PPS)
    trial_end = response_window_end + isi
    frame_loop_until(trial_end)

def run_rt_training_block():
    """Run RT training block with 18 trials and tactile feedback."""
    show_text_timed(
        TEXTS[language]["rt_training_intro"],
        seconds=2.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
        start_key="CONSIGNE_START", end_key="CONSIGNE_END",
    )

    show_baseline(FIXATION_BEFORE_BLOCK)

    training_block = build_rt_training_block()
    print(f"RT training block: running {len(training_block)} trials")

    for trial_idx, cond_trial in enumerate(training_block):
        run_rt_training_trial(condition_trial=cond_trial, trial_idx=trial_idx)

def run_rt_block_task():
    """RT block: always runs last, after both M and V condition blocks and
    the pre-RT pause. Runs RT training block first, then NUM_RT_BLOCKS
    sub-blocks of build_rt_block() trials each."""
    global rt_log_rows, rt_log_path

    # Reset logs for RT
    rt_log_rows = []
    rt_log_path = make_rt_log_filename(pp_id, ses_id, group)
    print("\n=== Starting RT block ===")
    print("RT log:", rt_log_path)

    show_instruction_space(
        TEXTS[language]["rt_block_intro"],
        "",
        start_key="CONSIGNE_START", end_key="CONSIGNE_END",
    )

    run_rt_training_block()

    show_text_timed(
        TEXTS[language]["rt_training_end_msg"],
        seconds=5.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
        start_key="RT_TRAINING_END",
    )

    send_event("RT_BLOCK_START", send_lsl=True, send_ttl=False)
    show_baseline(FIXATION_BEFORE_BLOCK)

    for rt_block_idx in range(NUM_RT_BLOCKS):
        rt_block = build_rt_block()
        print(f"RT sub-block {rt_block_idx + 1}/{NUM_RT_BLOCKS}: running {len(rt_block)} trials")

        for trial_idx, cond_trial in enumerate(rt_block):
            run_rt_trial(condition_trial=cond_trial, trial_idx=trial_idx, block_idx=rt_block_idx)

        show_instruction_space(
            TEXTS[language]["pheno_questions_intro_bloc"],
            TEXTS[language]["intro_hint"],
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        responses, question_texts = ask_phenomenology_questions_after_block(rt_block_idx)
        block_id = f"phenoblocppsRT{rt_block_idx + 1}"
        response_keys = ["success_rating", "nom_recognition", "nom_confidence", "near_far_difference",
                        "boundary_experience", "center_of_consciousness", "sounds_location", "sound_observer_separation"]
        save_phenomenology_responses(block_id, responses, question_texts, response_keys)

        is_last = rt_block_idx == NUM_RT_BLOCKS - 1
        block_num = rt_block_idx + 1
        if is_last:
            msg = TEXTS[language]["rt_block_end"].format(block_num, NUM_RT_BLOCKS)
        else:
            msg = TEXTS[language]["rt_between_blocks"].format(block_num, NUM_RT_BLOCKS)

        show_text_timed(
            msg,
            seconds=DURATION_END_BLOCK,
            height=TEXT_HEIGHT,
            wrap=TEXT_WRAP,
            start_key="CONSIGNE_START", end_key="CONSIGNE_END",
        )

        if not is_last:
            show_text_timed(
                TEXTS[language]["after_block_rt"],
                seconds=DURATION_AFTER_BLOCK,
                height=TEXT_HEIGHT,
                wrap=TEXT_WRAP,
                start_key="CONSIGNE_START", end_key="CONSIGNE_END",
            )
            show_baseline(FIXATION_BEFORE_BLOCK)

        save_logs_now()

    send_event("RT_BLOCK_END", send_lsl=True, send_ttl=False)
    save_logs_now()

try:
    # Initialize session logs (used for both M and V conditions)
    # pheno_log_rows is NOT reset here: it already holds the baseline
    # phenomenology responses collected before this block (see
    # save_phenomenology_responses("phenobaseline", ...) above).
    block_log_rows = []
    trial_log_rows = []
    block_log_path = make_block_log_filename(pp_id, ses_id, group)
    trial_log_path = make_trial_log_filename(pp_id, ses_id, group)
    pheno_log_path = make_pheno_log_filename(pp_id, ses_id, group)
    print("\n=== Session logs ===")
    print("Block log:", block_log_path)
    print("Trial log:", trial_log_path)
    print("Pheno log:", pheno_log_path)

    # Condition 1 : chosen by experimenter
    cond_1 = condition_task
    cond_2 = "V" if cond_1 == "M" else "M"

    if rt_timing == "before":
        run_rt_block_task()
        show_transition_pause(1)
        run_condition_task(cond_1)
        show_transition_pause(2)
        run_condition_task(cond_2)

    else:
        run_condition_task(cond_1)
        show_transition_pause(1)
        run_condition_task(cond_2)
        show_transition_pause(2)
        run_rt_block_task()

finally:
    save_logs_now()

# ============================================================
# END SCREEN
draw_text(TEXTS[language]["end"], height=52, wrap=TEXT_WRAP)
win.flip()
core.wait(DURATION_END)

send_event("EXP_END", send_lsl=True, send_ttl=False)
save_logs_now()

print("\nExperiment finished.")
win.close()
core.quit()
