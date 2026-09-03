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
    from config_local import AUDIO_DEVICE_NAME
except ImportError:
    raise RuntimeError(
        "Missing config_local.py. Copy config_local.example.py to "
        "config_local.py and fill in AUDIO_DEVICE_NAME for this machine."
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
DATA_DIR = "data"
AUDIO_DIR = "audio_cache"

# ============================================================
# ARDUINO VIBRATOR SETTINGS
ARDUINO_PORT = "COM5"
ARDUINO_BAUDRATE = 115200
TTL_BYTE = 1
DURATION_TACTILE = 5  # ms - sent to Arduino
INTENSITY = 150

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

# Vigilance task (strawberry counting)
DURATION_FRUIT = 1.5
ISI_VALUES_FRUIT = [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

# Block timing and fixation
FIXATION_BEFORE_FIRST_BLOCK = 30.0
FIXATION_BEFORE_LATER_BLOCK = 10.0
DURATION_END_BLOCK = 1.0
DURATION_AFTER_BREAK = 30.0
DURATION_FEEDBACK = 3.0

# Resting state and meditation
DURATION_RESTING_STATE = 50.0
DURATION_TASK_START_MSG = 3.0
DURATION_MEDITATION = 60.0  # 60 seconds for testing; set to 480 for 8 minutes in production

# RT block baseline
DURATION_BASELINE_BEFORE_RT = 30

# ============================================================
# DISPLAY PARAMETERS
TEXT_HEIGHT = 56
TEXT_WRAP = 1400

# ============================================================
# AUDIO PARAMETERS
SAMPLE_RATE = 44100
P3A_FREQ = 1000
TARGET_RMS = 0.08

# ============================================================
# TRIGGER CODES FOR LSL
TRIGGER_CODES = {
    "T": 1,
    "AN": 2,
    "AF": 3,
    "ANT": 4,
    "AFT": 5,
    "T_OFF": 11,
    "AN_OFF": 12,
    "AF_OFF": 13,
    "ANT_OFF": 14,
    "AFT_OFF": 15,
    "BLOCK_START": 99,
    "BLOCK_END": 98,
    "EXP_START": 97,
    "EXP_END": 96,
    "BASELINE_START": 95,
    "BASELINE_END": 94,
    "RESTING_STATE_START": 93,
    "RESTING_STATE_END": 92,

    # Instruction screens
    "LANG_SELECT_START": 100,
    "PARTICIPANT_ID_START": 104,
    "CONDITION_SELECT_START": 106,
    "RESTING_STATE_INSTR_START": 108,
    "RESTING_STATE_INSTR_END": 109,
    "TASK_START_MSG_START": 110,
    "TASK_START_MSG_END": 111,
    "CONSIGNE_M_START": 112,
    "CONSIGNE_M_END": 113,
    "CONSIGNE_V_START": 114,
    "CONSIGNE_V_END": 115,
    "BLOCK_BREAK_START": 116,
    "BLOCK_BREAK_END": 117,
    "IPAD_PHENO_START": 118,
    "IPAD_PHENO_END": 119,
    "AFTER_BREAK_START": 120,
    "AFTER_BREAK_END": 121,
    "FEEDBACK_START": 122,
    "FEEDBACK_END": 123,
    "TRANSITION_START": 124,
    "TRANSITION_END": 125,
    "END_SCREEN_START": 126,
    "END_SCREEN_END": 127,
    "STRAWBERRY_QUESTION_START": 128,
    "STRAWBERRY_QUESTION_END": 129,
    "STRAWBERRY_DISPLAY": 130,
    "OTHER_FRUIT_DISPLAY": 134,
    "RT_BLOCK_START": 131,
    "RT_BLOCK_END": 132,
    "RT_RESPONSE": 133,
    "MEDITATION_CLICK": 140,
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
        "group_heading": "Le groupe :",
        "group_hint": "Appuyez sur E ou C, puis sur la barre d'espace.",
        "condition_heading": "La condition :",
        "condition_hint": "Appuyez sur M ou V, puis sur la barre d'espace.",
        "rt_block_position_heading": "Bloc avec RT :",
        "rt_block_position_hint": "Appuyez sur B (before) ou A (after), puis sur la barre d'espace.",

        # ===== CALIBRATION & FAMILIARIZATION =====
        "calibration_intro": "Pendant cette expérience, vous allez entendre des sons provenant des deux haut-parleurs situés devant vous. et vous allez ressentir une légère vibration au niveau du torse.\n\nNous allons  vous familiariser avec la distance des deux sons et la vibration.",
        "calibration_instruction": "Calibration :\n\n\nLe son va être présenté plusieurs fois.\n\nVous devrez indiquer si vous avez entendu un son ou non.",
        "calibration_instruction_hint": "Appuyez sur la barre d'espace quand vous êtes prêt.",
        "calibration_trial": "Avez-vous entendu un son ?",
        "calibration_yes": "OUI",
        "calibration_no": "NON",
        "calibration_summary": "Calibration terminée.\n\nMerci !",

        "famil_intro": "En plus d'entendre des sons, vous allez également ressentir une légère vibration au niveau du torse.\n\n\nNous allons vous familiariser avec la distance des deux sons et la vibration.",
        "famil_intro_hint": "Appuyez sur la barre d'espace pour essayer.",
        "famil_near_sound": "Vous allez entendre le son PROCHE.",
        "famil_near_sound_hint": "Appuyez sur la barre d'espace pour l'écouter.",
        "famil_far_sound": "Vous allez entendre le son LOIN.",
        "famil_far_sound_hint": "Appuyez sur la barre d'espace pour l'écouter.",
        "famil_tactile": "Vous allez sentir la vibration tactile.",
        "famil_tactile_hint": "An nppuyez sur la barre d'espace pour le sentir.",
        "famil_repeat_question": "Voulez-vous écouter à nouveau la différence ?",
        "famil_repeat_question_tactile": "Voulez-vous réessayer ?",
        "famil_repeat_yes_no": "Oui ou Non : appuyez sur O ou N, puis barre d'espace.",

        "consigne_stimuli": "Durant l'expérience ce sont exactement ces sons et cette vibration que vous allez percevoir.",
        "consigne_stimuli_hint": "Appuyez sur la barre espace pour commencer.",

        # ===== TASK DESCRIPTIONS (for dynamic task order) =====
        "task_intro_start": "Pendant cette expérience, vous allez entendre ces exacts mêmes sons et cette vibration.\n\nVous allez avoir trois différentes tâches :",
        "task_rt_desc": "Vous devrez réagir aussi rapidement que possible en appuyant sur la barre d'espace dès que vous ressentez la vibration.",
        "task_m_desc": "Vous devrez entrer dans un état de méditation et fixer la croix à l'écran.",
        "task_v_desc": "Vous devrez compter mentalement le nombre de fraises qui défilent à l'écran.",

        # ===== TASK 1 INTRO (first task in experiment) =====
        "task_1_rt_first": "Tâche 1 : Vous allez devoir réagir aussi rapidement que possible en appuyant sur la barre d'espace dès que vous ressentez la vibration.\n\nVous allez avoir un court entraînement.",
        "task_1_v_first": "Tâche 1 : Vous devrez compter mentalement le nombre de fraises qui défilent à l'écran.\n\nVous allez avoir un court entraînement.",
        "task_1_hint": "Appuyez sur la barre d'espace pour continuer.",

        # ===== RESTING STATE INTRO (different for RT/V vs M) =====
        "resting_state_intro_before_task": "Avant de commencer, vous allez d'abord avoir une croix de fixation devant vous pendant 2 minutes.\n\nPuis la tâche commencera.\n\nVous êtes prêt ?",
        "resting_state_intro_before_m": "Avant de commencer, vous allez d'abord avoir une croix de fixation devant vous pendant 2 minutes.\n\nVous allez simplement fixer la croix.",
        "meditation_intro_before_task": "Ensuite, vous allez avoir un moment pour entrer dans votre état de méditation.\n\nPuis, les stimulations des sons et la vibration commenceront.",

        # ===== REACTION TIME BLOCK =====
        "rt_block_intro_first": "Nous allons commencer par le premier bloc d'exercice (Bloc 1/2) : dès que vous sentez la vibration, appuyez sur la barre d'espace AUSSI RAPIDEMENT que possible.\n\n",
        "rt_block_intro_end": "Nous allons maintenant faire le second bloc d'exercice (Bloc 2/2) : vous allez entendre les mêmes sons et sentir la même vibration.\n\nMais, cette fois, vous devez appuyer sur la barre d'espace AUSSI RAPIDEMENT que possible quand vous ressentez la vibration.",
        "rt_block_intro_hint": "Appuyez sur la barre d'espace pour commencer l'entraînement.",
        "rt_practice_heading": "Phase d'entraînement",
        "rt_practice_done": "Bien! Vous avez maintenant une idée de ce qui va se passer.",
        "rt_practice_repeat_question": "Refaire l'entraînement ?",
        "rt_ready": "Le bloc va bientôt commencer.",
        "rt_block_end": "Merci pour ce bloc d'exercice.",
        "rt_block_end_first": "Nous allons maintenant continuer avec la tâche principale.\n\nPour la suite de l'expérience, vous n'aurez pas besoin d'utiliser la souris, vous allez seulement devoir entendre les sons et ressentir la vibration, sans rien faire.",
        "rt_block_end_first_hint": "Appuyez sur la barre d'espace quand vous avez compris.",

        # ===== CONDITION-SPECIFIC INSTRUCTIONS =====
        "task_will_start": "La tâche va commencer maintenant.",
        "consigne_M_E_first": "L'expérience va se dérouler en deux parties :\n\n Durant cette première partie, vous allez devoir entrer dans un état de méditation non-duelle. \n\nNous allons vous laisser 8 minutes pour cela, maintenant.\nInstallez vous",
        "consigne_V_E_first": "L'expérience va se dérouler en deux parties : \n\n Durant cette première partie, vous ne devez PAS entrer dans un état de méditation (si possible).\n\nPour vous aider, nous vous proposons une petite mission : des fruits vont défiler à l'écran, veuillez compter (mentalement) le nombre de FRAISES qui apparaissent.",
        "consigne_M_E_after": "Nous entrons maintenant dans la seconde phase de l'expérience. \n\nVous allez devoir, cette fois, entrer dans un état de méditation non-duelle. \n\nNous allons vous laisser 8 minutes pour cela, maintenant.\nInstallez vous",
        "consigne_V_E_after": "Nous entrons maintenant dans la seconde phase de l'expérience. \n\nElle sera identique, mais cette fois vous ne devez PAS entrer dans un état de méditation.\n\nPour vous aider, nous vous proposons une petite mission : des fruits vont défiler à l'écran, veuillez compter mentalement le nombre de FRAISES qui apparaissent.",
        "consigne_M_C_first": "L'expérience va se dérouler en deux parties : durant cette première partie, vous allez écouter un audio qui va vous guider progressivement, étape par étape vers un état de méditation, calme. \n\nLaissez-vous porter par les instructions, sans chercher à faire quoi que ce soit de particulier en dehors de ce qu'elles vous demandent.",
        "consigne_V_C_first": "L'expérience va se dérouler en deux parties : durant cette première partie, on va vous demander de vous concentrer sur l'écran. Pour vous aider, nous vous proposons une petite mission : des fruits vont défiler à l'écran, veuillez compter mentalement le nombre de FRAISES qui apparaissent.",
        "consigne_M_C_after": "Nous entrons maintenant dans la seconde phase de l'expérience. Vous allez, cette fois, écouter un audio qui va vous guider progressivement, étape par étape. Laissez-vous porter par les instructions, sans chercher à faire quoi que ce soit de particulier en dehors de ce qu'elles vous demandent.",
        "consigne_V_C_after": "Nous entrons maintenant dans la seconde phase de l'expérience. Elle sera identique, mais cette fois on va vous demander de rester simplement concentré sur l'écran.\n\nPour vous aider, nous vous proposons une petite mission : des fruits vont défiler à l'écran, veuillez compter mentalement le nombre de FRAISES qui apparaissent.",
        "consigne_hint": "Quand vous êtes prêt, appuyez sur la barre d'espace pour commencer.",

        # ===== PRACTICE PHASES =====
        "vigilance_practice_heading": "Phase d'entraînement",
        "vigilance_practice_intro": "Vous allez faire une courte phase d'entraînement.\n\nVous entendrez les sons et ressentirez les vibrations, tandis que les fruits défileront à l'écran.\n\nCompter le nombre de FRAISES.",
        "vigilance_practice_hint": "Appuyez sur la barre d'espace pour commencer.",
        "vigilance_practice_done": "Bien! Vous avez maintenant une idée de ce qui va se passer.\n\nLe même protocole sera répété sur plusieurs blocs.",
        "vigilance_practice_repeat_question": "Voulez-vous refaire l'entraînement ?",
        "yes_no_hint": "Oui ou Non : appuyez sur O ou N, puis barre d'espace.",
        "meditation_practice_done_hint": "Appuyez sur la barre d'espace pour continuer.",

        "meditation_label": "Méditation",
        "meditation_practice_heading": "Phase d'entraînement",
        "meditation_practice_intro": "Vous allez faire une courte phase d'entraînement.\n\nVous entendrez les sons et ressentirez les vibrations, tandis que vous devez fixer la croix à l'écran et rester en état de méditation.",
        "meditation_practice_hint": "Appuyez sur la barre d'espace pour commencer.",
        "meditation_practice_done": "Bien! Vous avez maintenant une idée de ce qui va se passer.\n\nLe même protocole sera répété sur plusieurs blocs.\nTentez de maintenir votre état de méditation tout au long.",
        "meditation_practice_repeat_question": "Voulez-vous refaire l'entraînement ?",

        # ===== RESTING STATE & TRIALS =====
        "resting_state_heading": "Nous commençons juste par une période de repos de 2 minutes : Veuillez simplement fixer la croix qui va apparaître à l'écran, sans bouger. \n\n\La tâche commencera directement après.",
        "resting_state_hint": "Quand vous êtes prêt, appuyez sur la barre d'espace pour commencer l'expérience.",

        # ===== TRIALS =====
        "question": "Combien de fraises avez-vous vues ?",
        "question_hint": "Appuyez sur la barre d'espace pour valider.",
        "feedback_template": "Vous avez répondu : {ans}\nNombre réel de fraises : {real}\n\nÉcart : {err}",
        "feedback_well_done": "Bravo, continuez comme ça !",
        "feedback_try_harder": "Soyez plus attentif !",

        # ===== BREAKS & TRANSITIONS =====
        "break": "Fin du bloc {}/{}",
        "ipad_pheno": "Veuillez prendre l'iPad et répondre à la question dessus.\n\nUne fois terminé, appuyez sur la barre d'espace.",
        "after_break_M": "Prenez quelques secondes pour vous remettre dans l'état de méditation.\n\nL'expérience reprendra bientôt.",
        "after_break_V": "La même tâche va de nouveau vous être présentée.\n\nInstallez-vous, l'expérience reprendra bientôt.",
        "transition": "Fin de la condition {}.\n\nLa condition {} va maintenant commencer.\n\nAppuyez sur la barre d'espace quand vous êtes prêt.",
        "condition_pause": "Prenez quelques minutes.\n\nVous pouvez bouger et demander de l'eau à l'expérimentateur si besoin.",
        "condition_pause_hint": "Appuyez sur la barre d'espace quand vous êtes prêt.",

        # ===== END =====
        "end": "Merci pour votre participation !",
    },
    "en": {
        # ===== STARTUP & INFO COLLECTION =====
        "lang_select": "Pour avoir les consignes en français, appuyez sur : F\n\nTo have the instructions in English, press: E",
        "participant_heading": "Participant number:",
        "participant_hint": "Type the number or code, then press the space bar to continue.",
        "group_heading": "Group:",
        "group_hint": "Press E or C, then press the space bar to continue.",
        "condition_heading": "Condition:",
        "condition_hint": "Press M or V, then press the space bar to continue.",
        "rt_block_position_heading": "Reaction time block:",
        "rt_block_position_hint": "Press B (before) or A (after), then press the space bar to continue.",

        # ===== CALIBRATION & FAMILIARIZATION =====
        "calibration_intro": "During this experiment, you will hear sounds from the two loudspeakers in front of you. and you will feel a slight vibration on your chest.\n\nWe will familiarize you with the distance of the two sounds and the vibration.",
        "calibration_instruction": "Calibration:\n\n\nThe sound will be presented several times.\n\nYou will need to indicate whether you heard a sound or not.",
        "calibration_instruction_hint": "Press the space bar when you are ready.",
        "calibration_trial": "Did you hear a sound?",
        "calibration_yes": "YES",
        "calibration_no": "NO",
        "calibration_summary": "Calibration complete.\n\nThank you!",

        "famil_intro": "In addition to hearing sounds, you will also feel a slight vibration on your chest.\n\n\nWe will familiarize you with these sensations.",
        "famil_intro_hint": "Press the space bar to try.",
        "famil_near_sound": "You will hear the NEAR sound.",
        "famil_near_sound_hint": "Press the space bar to listen.",
        "famil_far_sound": "You will hear the FAR sound.",
        "famil_far_sound_hint": "Press the space bar to listen.",
        "famil_tactile": "You will feel the tactile vibration.",
        "famil_tactile_hint": "Press the space bar to feel it.",
        "famil_repeat_question": "Would you like to hear the difference again?",
        "famil_repeat_question_tactile": "Would you like to try again?",
        "famil_repeat_yes_no": "Yes or No: press Y or N, then space bar.",

        "consigne_stimuli": "During the experiment, you will perceive exactly these sounds and this vibration.\n\nYou will only be asked to perceive them, without doing anything else.\n\nOnly your mental state will change: meditation or not.",
        "consigne_stimuli_hint": "If you understood, press the space bar.",

        # ===== TASK DESCRIPTIONS (for dynamic task order) =====
        "task_intro_start": "During this experiment, you will hear these exact same sounds and this vibration.\n\nYou will have three different tasks:",
        "task_rt_desc": "You must react as quickly as possible by pressing the space bar as soon as you feel the vibration.",
        "task_m_desc": "You must enter a meditative state and fix your eyes on the cross on the screen.",
        "task_v_desc": "You must mentally count the number of strawberries that appear on the screen.",

        # ===== TASK 1 INTRO (first task in experiment) =====
        "task_1_rt_first": "Task 1: You must react as quickly as possible by pressing the space bar as soon as you feel the vibration.\n\nYou will have a short training.",
        "task_1_v_first": "Task 1: You must mentally count the number of strawberries that appear on the screen.\n\nYou will have a short training.",
        "task_1_hint": "Press the space bar to continue.",

        # ===== RESTING STATE INTRO (different for RT/V vs M) =====
        "resting_state_intro_before_task": "Before you begin, you will first see a fixation cross on the screen for 2 minutes.\n\nThen the task will begin.\n\nAre you ready?",
        "resting_state_intro_before_m": "Before you begin, you will first see a fixation cross on the screen for 2 minutes.\n\nYou will simply fix your eyes on the cross.",
        "meditation_intro_before_task": "Then, you will have a moment to enter your meditative state.\n\nAfter that, the sounds and vibration will begin.",

        # ===== CONDITION-SPECIFIC INSTRUCTIONS =====
        "task_will_start": "The task will now begin.",
        "consigne_M_E_first": "The experiment will unfold in two parts:\n\nDuring this first part, you will need to enter a non-dual meditative state.\n\nWe will give you several minutes to do this.",
        "consigne_V_E_first": "The experiment will unfold in two parts:\n\nDuring this first part, you must NOT enter a meditative state, if possible.\n\nTo help you, we propose a small task: fruits will appear on the screen. Please count mentally the number of STRAWBERRIES that appear.",
        "consigne_M_E_after": "We are now entering the second phase of the experiment.\n\nYou will need, this time, to enter a non-dual meditative state.\n\nWe will give you several minutes to do this.",
        "consigne_V_E_after": "We are now entering the second phase of the experiment.\n\nIt will be identical, but this time you must NOT enter a meditative state.\n\nTo help you, we propose a small task: fruits will appear on the screen. Please count mentally the number of STRAWBERRIES that appear.",
        "consigne_M_C_first": "The experiment will unfold in two parts: during this first part, you will listen to an audio that will guide you progressively, step by step towards a calm meditative state.\n\nLet yourself be guided by the instructions, without trying to do anything special beyond what they ask you to do.",
        "consigne_V_C_first": "The experiment will unfold in two parts: during this first part, we will ask you to focus on the screen. To help you, we propose a small task: fruits will appear on the screen. Please count mentally the number of STRAWBERRIES that appear.",
        "consigne_M_C_after": "We are now entering the second phase of the experiment. You will, this time, listen to an audio that will guide you progressively, step by step. Let yourself be guided by the instructions, without trying to do anything special beyond what they ask you to do.",
        "consigne_V_C_after": "We are now entering the second phase of the experiment. It will be identical, but this time we will ask you to simply stay focused on the screen.\n\nTo help you, we propose a small task: fruits will appear on the screen. Please count mentally the number of STRAWBERRIES that appear.",
        "consigne_hint": "When you are ready, press the space bar to begin.",

        # ===== REACTION TIME BLOCK =====
        "rt_block_intro_first": "We will start with the first training block (Block 1/2): as soon as you feel the vibration, press the space bar AS QUICKLY AS POSSIBLE.\n\n",
        "rt_block_intro_end": "We will now do the second training block (Block 2/2): you will hear the same sounds and feel the same vibration.\n\nBut this time, you must press the space bar AS QUICKLY AS POSSIBLE when you feel the vibration.",
        "rt_block_intro_hint": "Press the space bar to begin the training.",
        "rt_practice_heading": "Training phase",
        "rt_practice_hint": "Press the space bar to begin.",
        "rt_practice_done": "Good! You now have an idea of what will happen.",
        "rt_practice_repeat_question": "Would you like to redo the training?",
        "rt_ready": "The block will begin soon.",
        "rt_block_end": "Thank you for this training block.",
        "rt_block_end_first": "We will now move to the main task.\n\nFor the rest of the experiment, you will not need to use the mouse. You will only need to hear the sounds and feel the vibration, without doing anything else.",
        "rt_block_end_first_hint": "Press the space bar when you understand.",

        # ===== PRACTICE PHASES =====
        "vigilance_practice_heading": "Training phase",
        "vigilance_practice_intro": "You will now do a short training phase.\n\nYou will hear the sounds and feel the vibrations, while fruits appear on the screen.\n\nCount the number of STRAWBERRIES.",
        "vigilance_practice_hint": "Press the space bar to begin.",
        "meditation_label": "Meditation",
        "meditation_practice_heading": "Training phase",
        "meditation_practice_intro": "You will now do a short training phase.\n\nYou will hear the sounds and feel the vibrations, while you must focus on the cross on the screen and remain in a meditative state.",
        "meditation_practice_hint": "Press the space bar to begin.",
        "meditation_practice_done": "Good! You now have an idea of what will happen.\n\nThe same protocol will be repeated over several blocks.\nTry to maintain your meditative state throughout.\n\n\nWe will now start with a resting period for 2 minutes.\nPlease simply focus on the cross that will appear on the screen, without moving.",
        "meditation_practice_repeat_question": "Would you like to redo the training?",
        "vigilance_practice_done": "Good! You now have an idea of what will happen.\n\nThe same protocol will be repeated over several blocks.\n\n\nWe will now start with a resting period for 2 minutes, then the task will begin.\nPlease simply focus on the cross that will appear on the screen, without moving.",
        "vigilance_practice_repeat_question": "Would you like to redo the training?",
        "yes_no_hint": "Yes or No: press Y or N, then space bar.",

        # ===== RESTING STATE & TRIALS =====
        "resting_state_heading": "We will first record a resting-state period for 2 minutes.\n\nPlease simply fixate on the cross that will appear on the screen, without moving.",
        "resting_state_hint": "When you are ready, press the space bar to begin.",
        "question": "How many strawberries did you see?",
        "question_hint": "Press the space bar to validate.",
        "feedback_template": "Your answer: {ans}\nReal number of strawberries: {real}\n\nDifference: {err}",
        "feedback_well_done": "Great job, keep it up!",
        "feedback_try_harder": "Be more attentive!",

        # ===== BREAKS & TRANSITIONS =====
        "break": "End of block {}/{}",
        "ipad_pheno": "Please take the iPad and answer the question.\n\nThen, press the space bar.",
        "after_break_M": "Take a few seconds to return to a meditative state.\n\nThe experiment will resume soon.",
        "after_break_V": "The same task will be presented again.\n\nPlease get settled; the experiment will resume soon.",
        "transition": "End of the {} condition.\n\nThe {} condition will now begin.\n\nPress the space bar when you are ready.",
        "condition_pause": "Take a few minutes.\n\nYou can move around and ask the experimenter for water if needed.",
        "condition_pause_hint": "Press the space bar when you are ready.",

        # ===== END =====
        "end": "Thank you for your participation!",
    }
}

# ============================================================
# CSV HEADERS
BLOCK_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition_task", "block",
    "response_strawberries", "real_strawberries", "error", "total_fruits",
    "trial_sequence", "n_T", "n_AN", "n_AF", "n_ANT", "n_AFT",
    "block_duration_sec",
]

TRIAL_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition_task",
    "block", "trial_index", "condition_trial",
    "audio_side", "audio_present", "tactile_present",
    "isi_sec", "stim_onset_clock", "stim_offset_clock", "trigger_code", "trigger_code_offset",
    "lsl_sent", "ttl_sent", "lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time", "meditation_click_count", "meditation_click_times",
]

RT_TRIAL_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition_task",
    "trial_index", "condition_trial",
    "audio_side", "audio_present", "tactile_present",
    "isi_sec", "stim_onset_clock", "stim_offset_clock", "trigger_code", "trigger_code_offset",
    "lsl_sent", "ttl_sent", "lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time", "reaction_time_sec", "response_absolute_clock", "response_lsl_time",
]

# ============================================================
# GLOBAL STATE VARIABLES
marker_outlet = None
arduino = None
block_log_rows = []
trial_log_rows = []
rt_log_rows = []
block_log_path = None
trial_log_path = None
rt_log_path = None
language = ""
group = ""  # "E" (expert meditator) or "C" (control)
condition_task = ""  # "M" = meditation, "V" = vigilance
rt_block_position = ""  # "A" (after) or "B" (before)
pp_id = ""
session_dt = ""
vigilance_task = None

# ============================================================
# BASIC UTILITIES
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def timestamp_for_filename():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def ensure_audio_dir():
    os.makedirs(AUDIO_DIR, exist_ok=True)

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
        sys.exit(1)

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
        code = TRIGGER_CODES.get(code_key, 0)
    else:
        code = int(code_key)

    if code == 0:
        print(f"WARNING: Unknown trigger key '{code_key}', code set to 0")    

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

def generate_tone_array(freq=P3A_FREQ, duration=DURATION_AUDIO, target_rms=TARGET_RMS):
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False).astype(np.float32)
    tone_arr = np.sin(2 * np.pi * freq * t).astype(np.float32)
    tone_arr = normalize_rms(tone_arr, target_rms=target_rms).astype(np.float32)
    stereo = np.column_stack([tone_arr, tone_arr])
    return apply_ramp(stereo)

def make_audio_files():
    ensure_audio_dir()

    noise_right_path = os.path.join(AUDIO_DIR, "noise_right.wav")
    noise_left_path = os.path.join(AUDIO_DIR, "noise_left.wav")
    calibration_path = os.path.join(AUDIO_DIR, "calibration_noise.wav")

    write_wav_file(noise_right_path, generate_white_noise_array(pan="right"))
    write_wav_file(noise_left_path, generate_white_noise_array(pan="left"))
    write_wav_file(calibration_path, generate_white_noise_array(duration=5.0, pan="both"))

    return noise_right_path, noise_left_path, calibration_path

NOISE_RIGHT_PATH, NOISE_LEFT_PATH, CALIBRATION_NOISE_PATH = make_audio_files()
NOISE_RIGHT = sound.Sound(NOISE_RIGHT_PATH)
NOISE_LEFT = sound.Sound(NOISE_LEFT_PATH)
CALIBRATION_NOISE = sound.Sound(CALIBRATION_NOISE_PATH)

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
kb = keyboard.Keyboard()
mouse = event.Mouse(win=win, visible=False)

# ============================================================
# INITIALIZATION of LSL and Arduino
# Done before any screen is shown, so every instruction/consigne the
# participant sees (including language/group/condition selection) can be
# marked in the EEG/ECG signal.
setup_lsl()
setup_arduino()

fixation_h = visual.Line(win, start=(-50, 0), end=(50, 0), lineWidth=8, lineColor="white")
fixation_v = visual.Line(win, start=(0, -50), end=(0, 50), lineWidth=8, lineColor="white")

def clear_keyboard():
    kb.clearEvents()

def get_keys(key_list=None, wait_release=False):
    return kb.getKeys(keyList=key_list, waitRelease=wait_release)

def draw_fixation_only():
    fixation_h.draw()
    fixation_v.draw()

def draw_text(text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 0), italic=False):
    stim = visual.TextStim(win, text=text, color="white", height=height, wrapWidth=wrap, pos=pos, italic=italic)
    stim.draw()
    return stim

def draw_hint(text, pos=(0, -300)):
    draw_text(text, height=48, wrap=TEXT_WRAP, pos=pos, italic=True)

# ============================================================
# CSV SAVING
def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def make_block_log_filename(pp_id, group, condition_task):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_cond-{condition_task}_{timestamp_for_filename()}_blocks.csv"
    )

def make_trial_log_filename(pp_id, group, condition_task):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_cond-{condition_task}_{timestamp_for_filename()}_trials.csv"
    )

def make_rt_log_filename(pp_id, group):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_rt_{timestamp_for_filename()}_trials.csv"
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

def show_baseline(seconds, send_markers=False, start_key="BASELINE_START", end_key="BASELINE_END"):
    if send_markers:
        send_event(start_key, send_lsl=True, send_ttl=False)

    t_end = core.getTime() + seconds
    while core.getTime() < t_end:
        check_escape()
        draw_fixation_only()
        win.flip()

    if send_markers:
        send_event(end_key, send_lsl=True, send_ttl=False)

def show_resting_state():
    show_instruction_space(
        TEXTS[language]["resting_state_heading"],
        TEXTS[language]["resting_state_hint"],
        start_key="RESTING_STATE_INSTR_START",
        end_key="RESTING_STATE_INSTR_END",
    )
    show_baseline(
        DURATION_RESTING_STATE,
        send_markers=True,
        start_key="RESTING_STATE_START",
        end_key="RESTING_STATE_END",
    )
    show_text_timed(
        TEXTS[language]["task_will_start"], seconds=DURATION_TASK_START_MSG, height=TEXT_HEIGHT, wrap=TEXT_WRAP,
        start_key="TASK_START_MSG_START", end_key="TASK_START_MSG_END",
    )

def show_end_of_block_screen(block_idx):
    txt = TEXTS[language]["break"].format(block_idx + 1, NUM_BLOCKS_PPS)
    show_text_timed(txt, seconds=DURATION_END_BLOCK, height=56, wrap=TEXT_WRAP,
                     start_key="BLOCK_BREAK_START", end_key="BLOCK_BREAK_END")

def show_feedback(ans, real, err):
    fb_txt = TEXTS[language]["feedback_template"].format(ans=ans, real=real, err=err)
    if err == 0:
        fb_txt += "\n\n" + TEXTS[language]["feedback_well_done"]
    elif err != 0:
        fb_txt += "\n\n" + TEXTS[language]["feedback_try_harder"]
    show_text_timed(fb_txt, seconds=DURATION_FEEDBACK, height=56, wrap=TEXT_WRAP,
                     start_key="FEEDBACK_START", end_key="FEEDBACK_END")

def show_ipad_pheno():
    show_text_space(TEXTS[language]["ipad_pheno"], height=TEXT_HEIGHT, wrap=TEXT_WRAP,
                     start_key="IPAD_PHENO_START", end_key="IPAD_PHENO_END")

def show_after_break():
    key_name = "after_break_V" if condition_task == "V" else "after_break_M"
    show_text_timed(TEXTS[language][key_name], seconds=DURATION_AFTER_BREAK, height=TEXT_HEIGHT, wrap=TEXT_WRAP,
                     start_key="AFTER_BREAK_START", end_key="AFTER_BREAK_END")

def ask_yes_no_question(question_key="famil_repeat_question"):
    chosen = ""
    clear_keyboard()
    while True:
        check_escape()
        draw_text(TEXTS[language][question_key], height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 60))
        draw_text(chosen if chosen else "_", height=80, wrap=TEXT_WRAP, pos=(0, -40))
        draw_hint(TEXTS[language]["famil_repeat_yes_no"])
        win.flip()

        valid_keys = ["o", "n"] if language == "fr" else ["y", "n"]
        keys = get_keys(valid_keys + ["space", "escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name in valid_keys and chosen == "":
                chosen = k.name.upper()
            elif k.name == "space" and chosen != "":
                return chosen.lower() == ("o" if language == "fr" else "y")

def show_stimulus_familiarization():
    show_instruction_space(
        TEXTS[language]["famil_intro"],
        TEXTS[language]["famil_intro_hint"],
    )

    while True:
        for _ in range(3):
            show_instruction_space(
                TEXTS[language]["famil_near_sound"],
                TEXTS[language]["famil_near_sound_hint"],
            )
            play_sound_obj(NOISE_RIGHT)
            core.wait(DURATION_AUDIO + 0.2)
            stop_all_sounds()

            show_instruction_space(
                TEXTS[language]["famil_far_sound"],
                TEXTS[language]["famil_far_sound_hint"],
            )
            play_sound_obj(NOISE_LEFT)
            core.wait(DURATION_AUDIO + 0.2)
            stop_all_sounds()

        if not ask_yes_no_question():
            break

    while True:
        for _ in range(3):
            show_instruction_space(
                TEXTS[language]["famil_tactile"],
                TEXTS[language]["famil_tactile_hint"],
            )
            send_arduino_ttl()
            core.wait(0.5)

        if not ask_yes_no_question(question_key="famil_repeat_question_tactile"):
            break

def show_calibration_psychophysical():
    CATCH_TRIAL_PROB = 0.25

    show_instruction_space(
        TEXTS[language]["calibration_instruction"],
        TEXTS[language]["calibration_instruction_hint"],
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

    print("\n=== Auditory Calibration Start ===")
    print("Press ENTER when calibration is complete.")
    calibration_done = False
    trial_idx = 0

    while not calibration_done:
        trial_idx += 1
        is_catch_trial = random.random() < CATCH_TRIAL_PROB

        # Show sound indicator
        sound_indicator = visual.TextStim(win, text="Son", pos=(0, 100), height=72, color="yellow", bold=True)
        sound_indicator.draw()
        win.flip()
        core.wait(0.5)

        if not is_catch_trial:
            play_sound_obj(NOISE_RIGHT)

        core.wait(DURATION_AUDIO)
        stop_all_sounds()

        # Wait for response (space = heard, or timeout)
        response_timeout = core.getTime() + 2.0
        clear_keyboard()

        response_detected = False
        while core.getTime() < response_timeout:
            check_escape()
            draw_fixation_only()
            win.flip()

            keys = get_keys(["space", "escape", "return"])
            if any(k.name == "escape" for k in keys):
                safe_quit()
            if any(k.name == "return" for k in keys):
                print("=== Auditory Calibration End ===\n")
                calibration_done = True
                break
            if any(k.name == "space" for k in keys):
                response_yes = TEXTS[language]["calibration_yes"]
                catch_info = " (CATCH)" if is_catch_trial else ""
                print(f"Trial {trial_idx}: {response_yes}{catch_info}")
                response_detected = True
                break

        if calibration_done:
            break

        if not response_detected:
            response_no = TEXTS[language]["calibration_no"]
            catch_info = " (CATCH)" if is_catch_trial else ""
            print(f"Trial {trial_idx}: {response_no} - timeout{catch_info}")

        # Inter-trial interval
        t_end = core.getTime() + 1.0
        while core.getTime() < t_end:
            check_escape()
            draw_fixation_only()
            win.flip()

            keys = get_keys(["return", "escape"])
            if any(k.name == "escape" for k in keys):
                safe_quit()
            if any(k.name == "return" for k in keys):
                print("=== Auditory Calibration End ===\n")
                calibration_done = True
                break

    show_text_timed(
        TEXTS[language]["calibration_summary"],
        seconds=2.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

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

def select_single_key(heading, hint, valid_keys, start_key=None, end_key=None):
    # Show the picked key on screen and wait for space bar to confirm
    # (backspace clears the current choice so it can be re-picked).
    chosen = ""
    clear_keyboard()
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)

    while True:
        check_escape()
        draw_text(heading, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 120))
        draw_text(chosen if chosen else "_", height=48, wrap=TEXT_WRAP, pos=(0, 0))
        draw_hint(hint)
        win.flip()

        keys = get_keys(valid_keys + ["space", "backspace", "escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name == "backspace":
                chosen = ""
            elif k.name in valid_keys and chosen == "":
                chosen = k.name.upper()
            elif k.name == "space" and chosen != "":
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
# VIGILANCE TASK
class VigilanceTaskContinuous:
    def __init__(self, win_):
        self.win = win_
        self.running = False
        self.strawberry_count = 0
        self.total_fruit_count = 0

        self.stimuli = [
            "stimuli/banane.png",
            "stimuli/citron.png",
            "stimuli/fraise.png",
            "stimuli/goyave.png",
            "stimuli/kiwi.png",
            "stimuli/myrtilles.png",
            "stimuli/passion.png",
            "stimuli/raisin.png",
        ]

        missing = [p for p in self.stimuli if not os.path.exists(p)]
        if missing:
            print("\nMissing stimulus files:")
            for p in missing:
                print(" -", p)
            safe_quit()

        self.image_stims = {
            p: visual.ImageStim(self.win, image=p, size=(350, 350))
            for p in self.stimuli
        }

        self.phase = "fruit"
        self.t_next = 0.0
        self.current_path = None

    def start(self, now):
        self.running = True
        self.strawberry_count = 0
        self.total_fruit_count = 0

        self.current_path = random.choice(self.stimuli)
        self.total_fruit_count = 1

        if "fraise" in os.path.basename(self.current_path).lower():
            self.strawberry_count += 1
            send_event("STRAWBERRY_DISPLAY", send_lsl=True, send_ttl=False)
        else:
            send_event("OTHER_FRUIT_DISPLAY", send_lsl=True, send_ttl=False)

        self.phase = "fruit"
        self.t_next = now + DURATION_FRUIT

    def stop(self):
        self.running = False

    def update_and_draw(self, now):
        if not self.running:
            draw_fixation_only()
            return

        if now >= self.t_next:
            if self.phase == "fruit":
                self.phase = "isi"
                self.t_next = now + random.choice(ISI_VALUES_FRUIT)
            else:
                self.current_path = random.choice(self.stimuli)
                self.total_fruit_count += 1
                if "fraise" in os.path.basename(self.current_path).lower():
                    self.strawberry_count += 1
                    send_event("STRAWBERRY_DISPLAY", send_lsl=True, send_ttl=False)
                else:
                    send_event("OTHER_FRUIT_DISPLAY", send_lsl=True, send_ttl=False)
                self.phase = "fruit"
                self.t_next = now + DURATION_FRUIT

        if self.phase == "isi":
            draw_fixation_only()
        else:
            self.image_stims[self.current_path].draw()

# ============================================================
# MASTER CLOCK
clock = core.Clock()
clock.reset()

def frame_loop_until(t_end, vigilance_task=None, track_meditation_clicks=None, stim_onset=0):
    button_was_down = False

    while True:
        check_escape()
        now = clock.getTime()

        if now >= t_end:
            break

        if vigilance_task is not None and vigilance_task.running:
            vigilance_task.update_and_draw(now)
        else:
            draw_fixation_only()

        # Detect meditation clicks (only during meditation condition)
        if track_meditation_clicks is not None and condition_task == "M":
            buttons = mouse.getPressed()
            button_is_down = buttons[0]  # Left mouse button

            # Detect rising edge (click begins)
            if button_is_down and not button_was_down:
                click_time = now - stim_onset
                track_meditation_clicks.append(click_time)
                send_event("MEDITATION_CLICK", send_lsl=True, send_ttl=False)

            button_was_down = button_is_down

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

def build_rt_block():
    # Build one RT block (55 trials, biased toward audio+tactile)
    # Two blocks: before (55) + after (55) = 110 total
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

def run_rt_trial(condition_trial, trial_idx):
    """Run one RT trial with mouse response detection for tactile stimuli."""
    global rt_log_rows, marker_outlet

    audio_present, tactile_present, audio_side = describe_trial(condition_trial)
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

    # Audio + tactile - synchronized
    elif condition_trial in ["ANT", "AFT"]:
        if condition_trial == "ANT":
            sound_to_play = NOISE_RIGHT
        elif condition_trial == "AFT":
            sound_to_play = NOISE_LEFT

        sound_to_play.stop()

        lsl_time = send_lsl_marker(TRIGGER_CODES.get(condition_trial, 0))
        ttl_on_time, ttl_off_time = send_arduino_ttl()

        audio_play_call_time = core.getTime()
        sound_to_play.play()

        event_info = {
            "event_code": TRIGGER_CODES.get(condition_trial, 0),
            "local_time": core.getTime(),
            "lsl_time": lsl_time,
            "ttl_on_time": ttl_on_time,
            "ttl_off_time": ttl_off_time,
            "ttl_sent": 1 if arduino is not None else 0,
            "lsl_sent": 1 if marker_outlet is not None else 0,
        }

    # Stimulus presentation window - let sound play
    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset)
    stop_all_sounds()

    # Offset marker
    send_event(condition_trial + "_OFF", send_lsl=True, send_ttl=False)

    # Response detection window (1.5 sec after stimulus)
    clear_keyboard()
    response_detected = False
    response_window_end = stim_offset + 1.5

    while clock.getTime() < response_window_end:
        check_escape()
        draw_fixation_only()
        win.flip()

        if not response_detected and tactile_present:
            keys = get_keys(["space"])
            if any(k.name == "space" for k in keys):
                response_time = clock.getTime() - stim_onset
                response_lsl_time = send_lsl_marker(TRIGGER_CODES["RT_RESPONSE"])
                response_detected = True

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = response_window_end + isi
    frame_loop_until(trial_end)

    stim_offset_clock = stim_onset + DURATION_AUDIO
    trigger_code_offset = TRIGGER_CODES.get(condition_trial + "_OFF", 0)

    rt_log_rows.append({
        "participant_num": pp_id,
        "language": language,
        "group": group,
        "datetime": session_dt,
        "condition_task": condition_task,
        "trial_index": trial_idx + 1,
        "condition_trial": condition_trial,
        "audio_side": audio_side,
        "audio_present": int(audio_present),
        "tactile_present": int(tactile_present),
        "isi_sec": isi,
        "stim_onset_clock": round(stim_onset, 6),
        "stim_offset_clock": round(stim_offset_clock, 6),
        "trigger_code": event_info["event_code"],
        "trigger_code_offset": trigger_code_offset,
        "lsl_sent": event_info["lsl_sent"],
        "ttl_sent": event_info["ttl_sent"],
        "lsl_time": event_info["lsl_time"],
        "ttl_on_time": event_info["ttl_on_time"],
        "ttl_off_time": event_info["ttl_off_time"],
        "audio_play_call_time": audio_play_call_time,
        "reaction_time_sec": round(response_time, 6) if response_time is not None else "",
        "response_absolute_clock": round(stim_onset + response_time, 6) if response_time is not None else "",
        "response_lsl_time": response_lsl_time,
    })

def run_trial(condition_trial, block_idx, trial_idx, vigilance_task=None):
    audio_present, tactile_present, audio_side = describe_trial(condition_trial)
    stim_onset = clock.getTime()
    meditation_clicks = []

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

    # Audio + tactile - synchronized
    elif condition_trial in ["ANT", "AFT"]:
        if condition_trial == "ANT":
            sound_to_play = NOISE_RIGHT
        elif condition_trial == "AFT":
            sound_to_play = NOISE_LEFT

        sound_to_play.stop()

        lsl_time = send_lsl_marker(TRIGGER_CODES.get(condition_trial, 0))
        ttl_on_time, ttl_off_time = send_arduino_ttl()

        audio_play_call_time = core.getTime()
        sound_to_play.play()

        event_info = {
            "event_code": TRIGGER_CODES.get(condition_trial, 0),
            "local_time": core.getTime(),
            "lsl_time": lsl_time,
            "ttl_on_time": ttl_on_time,
            "ttl_off_time": ttl_off_time,
            "ttl_sent": 1 if arduino is not None else 0,
            "lsl_sent": 1 if marker_outlet is not None else 0,
        }

    # Stimulus presentation window
    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset, vigilance_task=vigilance_task, track_meditation_clicks=meditation_clicks, stim_onset=stim_onset)
    stop_all_sounds()

    # Offset marker
    send_event(condition_trial + "_OFF", send_lsl=True, send_ttl=False)

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = stim_offset + isi
    frame_loop_until(trial_end, vigilance_task=vigilance_task, track_meditation_clicks=meditation_clicks, stim_onset=stim_onset)

    stim_offset_clock = stim_onset + DURATION_AUDIO
    trigger_code_offset = TRIGGER_CODES.get(condition_trial + "_OFF", 0)

    meditation_click_times_str = ",".join(f"{t:.3f}" for t in meditation_clicks) if meditation_clicks else ""

    trial_log_rows.append({
        "participant_num": pp_id,
        "language": language,
        "group": group,
        "datetime": session_dt,
        "condition_task": condition_task,
        "block": block_idx + 1,
        "trial_index": trial_idx + 1,
        "condition_trial": condition_trial,
        "audio_side": audio_side,
        "audio_present": int(audio_present),
        "tactile_present": int(tactile_present),
        "isi_sec": isi,
        "stim_onset_clock": round(stim_onset, 6),
        "stim_offset_clock": round(stim_offset_clock, 6),
        "trigger_code": event_info["event_code"],
        "trigger_code_offset": trigger_code_offset,
        "lsl_sent": event_info["lsl_sent"],
        "ttl_sent": event_info["ttl_sent"],
        "lsl_time": event_info["lsl_time"],
        "ttl_on_time": event_info["ttl_on_time"],
        "ttl_off_time": event_info["ttl_off_time"],
        "audio_play_call_time": audio_play_call_time,
        "meditation_click_count": len(meditation_clicks),
        "meditation_click_times": meditation_click_times_str,
    })

# ============================================================
# BLOCK QUESTION
def ask_strawberry_question(real_count):
    typed = ""
    clear_keyboard()
    send_event("STRAWBERRY_QUESTION_START", send_lsl=True, send_ttl=False)

    while True:
        check_escape()
        draw_text(TEXTS[language]["question"], height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 80))
        draw_text(typed, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 0))
        draw_hint(TEXTS[language]["question_hint"], pos=(0, -200))
        win.flip()

        keys = get_keys(
            ["space", "backspace"] +
            [str(i) for i in range(10)] +
            [f"num_{i}" for i in range(10)] +
            ["escape"]
        )

        for k in keys:
            name = k.name
            if name == "escape":
                safe_quit()
            elif name == "space" and typed != "":
                ans_n = int(typed)
                err = ans_n - real_count
                send_event("STRAWBERRY_QUESTION_END", send_lsl=True, send_ttl=False)
                return ans_n, err
            elif name == "backspace":
                typed = typed[:-1]
            elif name.isdigit() and len(typed) < 2:
                typed += name
            elif name.startswith("num_") and len(typed) < 2:
                typed += name[-1]

# ============================================================
# LANGUAGE SELECTION
send_event("LANG_SELECT_START", send_lsl=True, send_ttl=False)
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
    start_key="PARTICIPANT_ID_START",
)
print(f"Participant ID: {pp_id}")

# ============================================================
# GROUP SELECTION
# "E" = expert meditator, "C" = control (never meditated). Typed by the experimenter, not shown to the participant.
group = select_single_key(
    TEXTS[language]["group_heading"],
    TEXTS[language]["group_hint"],
    ["e", "c"],
)
print(f"Group: {group}")

# ============================================================
# CONDITION SELECTION (M = meditation, V = vigilance)
condition_task = select_single_key(
    TEXTS[language]["condition_heading"],
    TEXTS[language]["condition_hint"],
    ["m", "v"],
    start_key="CONDITION_SELECT_START",
)
print(f"Condition: {condition_task}")

# ============================================================
# RT BLOCK POSITION SELECTION (B = before, A = after)
rt_block_position = select_single_key(
    TEXTS[language]["rt_block_position_heading"],
    TEXTS[language]["rt_block_position_hint"],
    ["b", "a"],
)
print(f"RT block position: {rt_block_position}")

# ============================================================
# STIMULUS FAMILIARIZATION
show_stimulus_familiarization()

# ============================================================
# BUILD DYNAMIC TASK ORDER TEXT
cond_1 = condition_task
cond_2 = "V" if cond_1 == "M" else "M"

task_order = []
if rt_block_position == "B":
    task_order = ["RT", cond_1, cond_2]
else:
    task_order = [cond_1, cond_2, "RT"]

task_descriptions = {
    "RT": TEXTS[language]["task_rt_desc"],
    "M": TEXTS[language]["task_m_desc"],
    "V": TEXTS[language]["task_v_desc"],
}

task_order_text = TEXTS[language]["task_intro_start"]
for i, task in enumerate(task_order, 1):
    task_order_text += f"\n\n{i}. {task_descriptions[task]}"

show_instruction_space(
    task_order_text,
    TEXTS[language]["consigne_stimuli_hint"],
)

# ============================================================
# TASK 1 SPECIFIC INSTRUCTIONS
first_task = task_order[0]

if first_task == "RT":
    show_instruction_space(
        TEXTS[language]["task_1_rt_first"],
        TEXTS[language]["task_1_hint"],
    )
    show_instruction_space(
        TEXTS[language]["resting_state_intro_before_task"],
        TEXTS[language]["task_1_hint"],
    )
elif first_task == "V":
    show_instruction_space(
        TEXTS[language]["task_1_v_first"],
        TEXTS[language]["task_1_hint"],
    )
    show_instruction_space(
        TEXTS[language]["resting_state_intro_before_task"],
        TEXTS[language]["task_1_hint"],
    )
else:  # first_task == "M"
    show_instruction_space(
        TEXTS[language]["consigne_M_E_first"] if group == "E" else TEXTS[language]["consigne_M_C_first"],
        TEXTS[language]["consigne_hint"],
    )
    show_instruction_space(
        TEXTS[language]["resting_state_intro_before_m"],
        TEXTS[language]["task_1_hint"],
    )
    show_instruction_space(
        TEXTS[language]["meditation_intro_before_task"],
        TEXTS[language]["task_1_hint"],
    )

# ============================================================
# SESSION TIMESTAMP (for log filenames)
session_dt = now_str()

# ============================================================
# VIGILANCE PRACTICE TASK (short trial before main blocks)
class VigilanceTaskPractice:
    def __init__(self, win_, num_fruits=12, num_strawberries=2):
        self.win = win_
        self.num_fruits_target = num_fruits
        self.strawberry_count = 0
        self.total_fruit_count = 0
        self.fruits_displayed = []

        self.stimuli = [
            "stimuli/banane.png",
            "stimuli/citron.png",
            "stimuli/fraise.png",
            "stimuli/goyave.png",
            "stimuli/kiwi.png",
            "stimuli/myrtilles.png",
            "stimuli/passion.png",
            "stimuli/raisin.png",
        ]

        self.image_stims = {
            p: visual.ImageStim(self.win, image=p, size=(350, 350))
            for p in self.stimuli
        }

        # Generate random sequence with a fixed number of strawberries
        non_strawberry_stimuli = [s for s in self.stimuli if "fraise" not in s.lower()]
        strawberry_stimuli = [s for s in self.stimuli if "fraise" in s.lower()]

        self.fruits_displayed = random.sample(non_strawberry_stimuli, min(num_fruits - num_strawberries, len(non_strawberry_stimuli)))
        self.fruits_displayed.extend(random.choices(strawberry_stimuli, k=num_strawberries))
        random.shuffle(self.fruits_displayed)
        self.strawberry_count = num_strawberries
        self.total_fruit_count = len(self.fruits_displayed)

    def show(self):
        clear_keyboard()
        fruit_idx = 0
        avg_isi = np.mean(ISI_VALUES_FRUIT)
        t_end = core.getTime() + (self.total_fruit_count * (DURATION_FRUIT + avg_isi))

        while core.getTime() < t_end and fruit_idx < len(self.fruits_displayed):
            check_escape()

            # Show current fruit or fixation
            if (fruit_idx % 2) == 0:
                fruit_path = self.fruits_displayed[fruit_idx]
                self.image_stims[fruit_path].draw()
                fruit_idx += 1
            else:
                draw_fixation_only()
                fruit_idx += 1

            win.flip()
            core.wait(DURATION_FRUIT + random.choice(ISI_VALUES_FRUIT))

def run_vigilance_practice():
    # Introduction to practice phase
    show_instruction_space(
        TEXTS[language]["vigilance_practice_intro"],
        TEXTS[language]["vigilance_practice_hint"],
    )

    repeat_training = True
    while repeat_training:
        # Setup practice vigilance task
        practice_vigilance = VigilanceTaskContinuous(win)
        practice_vigilance.start(clock.getTime())

        # Practice trials: 3 of each stimulus (15 trials total)
        practice_block = ["T", "AN", "AF", "ANT", "AFT"] * 3
        random.shuffle(practice_block)
        trial_idx = 0

        for cond_trial in practice_block:
            check_escape()
            # Run trial with PPS stimulation + vigilance task
            run_trial(cond_trial, block_idx=0, trial_idx=trial_idx, vigilance_task=practice_vigilance)
            trial_idx += 1

        practice_vigilance.stop()

        # Ask strawberry count
        real = practice_vigilance.strawberry_count
        ans, err = ask_strawberry_question(real)
        show_feedback(ans, real, err)

        # Show practice done confirmation
        show_text_timed(
            TEXTS[language]["vigilance_practice_done"],
            seconds=4.0,
            height=TEXT_HEIGHT,
            wrap=TEXT_WRAP,
        )

        # Ask if participant wants to redo training
        repeat_training = ask_yes_no_question(question_key="vigilance_practice_repeat_question")

def run_meditation_preparation():
    # Meditation preparation period - just display "Méditation" / "Meditation"
    clear_keyboard()
    t_end = core.getTime() + DURATION_MEDITATION

    while core.getTime() < t_end:
        check_escape()
        draw_text(TEXTS[language]["meditation_label"], height=48, wrap=TEXT_WRAP)
        win.flip()
        core.wait(0.05)

def run_meditation_practice():
    # Introduction to meditation practice phase
    show_instruction_space(
        TEXTS[language]["meditation_practice_intro"],
        TEXTS[language]["meditation_practice_hint"],
    )

    repeat_training = True
    while repeat_training:
        # Practice trials: 3 of each stimulus (15 trials total)
        practice_block = ["T", "AN", "AF", "ANT", "AFT"] * 3
        random.shuffle(practice_block)
        trial_idx = 0

        for cond_trial in practice_block:
            check_escape()
            # Run trial with PPS stimulation only (no vigilance task)
            run_trial(cond_trial, block_idx=0, trial_idx=trial_idx, vigilance_task=None)
            trial_idx += 1

        # Show practice done confirmation
        show_text_timed(
            TEXTS[language]["meditation_practice_done"],
            seconds=4.0,
            height=TEXT_HEIGHT,
            wrap=TEXT_WRAP,
        )

        # Ask if participant wants to redo training
        repeat_training = ask_yes_no_question(question_key="meditation_practice_repeat_question")

# ============================================================
# MAIN LOOP
condition_task_labels = {
    "M": {"fr": "méditation", "en": "meditation"},
    "V": {"fr": "vigilance",  "en": "vigilance"},
}

def run_condition_task(cond, is_first=False):
    global block_log_rows, trial_log_rows, block_log_path, trial_log_path
    global condition_task, vigilance_task

    condition_task = cond

    # Reset logs for this condition
    block_log_rows = []
    trial_log_rows = []
    block_log_path = make_block_log_filename(pp_id, group, condition_task)
    trial_log_path = make_trial_log_filename(pp_id, group, condition_task)
    print(f"\n=== Starting condition {condition_task} ===")
    print("Block log:", block_log_path)
    print("Trial log:", trial_log_path)

    vigilance_task = VigilanceTaskContinuous(win) if condition_task == "V" else None
    all_blocks = build_experiment()

    # Determine the correct instruction key based on group, condition, and order
    order_suffix = "first" if is_first else "after"
    instruction_key = f"consigne_{condition_task}_{group}_{order_suffix}"

    consigne_start_key = "CONSIGNE_V_START" if condition_task == "V" else "CONSIGNE_M_START"
    consigne_end_key = "CONSIGNE_V_END" if condition_task == "V" else "CONSIGNE_M_END"
    show_instruction_space(
        TEXTS[language][instruction_key], TEXTS[language]["consigne_hint"],
        start_key=consigne_start_key, end_key=consigne_end_key,
    )

    # Practice phase for vigilance or meditation condition
    if condition_task == "V":
        run_vigilance_practice()
    elif condition_task == "M":
        run_meditation_practice()

    send_event("EXP_START", send_lsl=True, send_ttl=False)

    for block_idx, block in enumerate(all_blocks):
        print(f"\nStart block {block_idx + 1}/{NUM_BLOCKS_PPS}")

        fixation_duration = FIXATION_BEFORE_FIRST_BLOCK if block_idx == 0 else FIXATION_BEFORE_LATER_BLOCK
        show_baseline(fixation_duration, send_markers=True)
        send_event("BLOCK_START", send_lsl=True, send_ttl=False)
        block_t0 = clock.getTime()

        counts = {k: 0 for k in PPS_CONDITIONS}

        if condition_task == "V":
            vigilance_task.start(clock.getTime())

        for trial_idx, cond_trial in enumerate(block):
            counts[cond_trial] += 1
            run_trial(
                condition_trial=cond_trial,
                block_idx=block_idx,
                trial_idx=trial_idx,
                vigilance_task=vigilance_task if condition_task == "V" else None
            )

        if condition_task == "V":
            vigilance_task.stop()

        block_t1 = clock.getTime()
        block_duration = block_t1 - block_t0
        trial_sequence_str = ",".join(block)

        send_event("BLOCK_END", send_lsl=True, send_ttl=False)

        row = {
            "participant_num": pp_id,
            "language": language,
            "group": group,
            "datetime": session_dt,
            "condition_task": condition_task,
            "block": block_idx + 1,
            "response_strawberries": "",
            "real_strawberries": "",
            "error": "",
            "total_fruits": vigilance_task.total_fruit_count if condition_task == "V" else "",
            "trial_sequence": trial_sequence_str,
            "n_T": counts["T"],
            "n_AN": counts["AN"],
            "n_AF": counts["AF"],
            "n_ANT": counts["ANT"],
            "n_AFT": counts["AFT"],
            "block_duration_sec": round(block_duration, 3),
        }

        show_end_of_block_screen(block_idx)

        if condition_task == "V":
            real = vigilance_task.strawberry_count
            ans, err = ask_strawberry_question(real)
            show_feedback(ans, real, err)
            row["response_strawberries"] = ans
            row["real_strawberries"] = real
            row["error"] = err

        block_log_rows.append(row)
        save_logs_now()

        if block_idx < NUM_BLOCKS_PPS - 1:
            show_ipad_pheno()
            show_after_break()

    send_event("EXP_END", send_lsl=True, send_ttl=False)
    save_logs_now()


def run_rt_practice():
    # Run 15 practice trials: 3 of each stimulus type
    practice_trials = ["T", "AN", "AF", "ANT", "AFT"] * 3

    for trial_idx, cond_trial in enumerate(practice_trials):
        check_escape()

        audio_present, tactile_present, audio_side = describe_trial(cond_trial)
        stim_onset = clock.getTime()

        # Send event and play sounds (same as run_trial)
        if cond_trial == "T":
            print("T:", end=" ")
            send_event(cond_trial, send_lsl=True, send_ttl=True, ttl_code=TTL_BYTE)
        elif cond_trial == "AN":
            print("AN:", end=" ")
            send_event(cond_trial, send_lsl=True, send_ttl=False)
            play_sound_obj(NOISE_RIGHT)
        elif cond_trial == "AF":
            print("AF:", end=" ")
            send_event(cond_trial, send_lsl=True, send_ttl=False)
            play_sound_obj(NOISE_LEFT)
        elif cond_trial == "ANT":
            print("ANT:", end=" ")
            send_event(cond_trial, send_lsl=True, send_ttl=True, ttl_code=TTL_BYTE)
            play_sound_obj(NOISE_RIGHT)
        elif cond_trial == "AFT":
            print("AFT:", end=" ")
            send_event(cond_trial, send_lsl=True, send_ttl=True, ttl_code=TTL_BYTE)
            play_sound_obj(NOISE_LEFT)

        # Stimulus presentation window
        stim_offset = stim_onset + DURATION_AUDIO
        frame_loop_until(stim_offset)
        stop_all_sounds()

        # Offset marker
        send_event(cond_trial + "_OFF", send_lsl=True, send_ttl=False)

        # Response detection window (1.5 sec after stimulus)
        clear_keyboard()
        response_detected = False
        response_time = None
        response_window_end = stim_offset + 1.5

        while clock.getTime() < response_window_end:
            check_escape()
            draw_fixation_only()
            win.flip()

            if not response_detected:
                keys = get_keys(["space"])
                if any(k.name == "space" for k in keys):
                    response_time = clock.getTime() - stim_onset
                    response_detected = True
                    if tactile_present:
                        print(f"→ Response: {response_time:.3f}s ✓")
                    else:
                        print(f"→ Response: {response_time:.3f}s ✗")

        if not response_detected:
            if tactile_present:
                print("→ No response ✗")
            else:
                print("→ No response ✓")

        # ISI
        isi = random.choice(ISI_VALUES_PPS)
        trial_end = stim_offset + 1.5 + isi
        frame_loop_until(trial_end)

def run_rt_block_task(is_first=True):
    global rt_log_rows, rt_log_path

    # Reset logs for RT
    rt_log_rows = []
    rt_log_path = make_rt_log_filename(pp_id, group)
    print("\n=== Starting RT block ===")
    print("RT log:", rt_log_path)

    # Choose appropriate intro text based on position
    intro_key = "rt_block_intro_first" if is_first else "rt_block_intro_end"

    # 1. Show intro with hint about training
    show_instruction_space(
        TEXTS[language][intro_key],
        TEXTS[language]["rt_block_intro_hint"],
    )

    # 2-5. Training loop
    repeat_training = True
    while repeat_training:
        # 2. Display "Training phase" heading for 4 seconds
        show_text_timed(
            TEXTS[language]["rt_practice_heading"],
            seconds=4.0,
            height=TEXT_HEIGHT,
            wrap=TEXT_WRAP,
        )

        # 3. Run practice trials (no output shown during this)
        run_rt_practice()

        # 4. Show practice done confirmation
        show_text_timed(
            TEXTS[language]["rt_practice_done"],
            seconds=4.0,
            height=TEXT_HEIGHT,
            wrap=TEXT_WRAP,
        )

        # Ask if participant wants to redo training
        repeat_training = ask_yes_no_question(question_key="rt_practice_repeat_question")

    # 5. Display "Task will begin soon" for 4 seconds
    show_text_timed(
        TEXTS[language]["rt_ready"],
        seconds=4.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

    # 6. Start main RT block
    send_event("RT_BLOCK_START", send_lsl=True, send_ttl=False)
    show_baseline(DURATION_BASELINE_BEFORE_RT, send_markers=True)

    rt_block = build_rt_block()

    print(f"Running {len(rt_block)} RT trials")
    for trial_idx, cond_trial in enumerate(rt_block):
        run_rt_trial(condition_trial=cond_trial, trial_idx=trial_idx)

    send_event("RT_BLOCK_END", send_lsl=True, send_ttl=False)

    # 7. Display common end message for 4 seconds
    show_text_timed(
        TEXTS[language]["rt_block_end"],
        seconds=4.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

    # 8. If RT block is at the beginning, show the message about no mouse for the rest
    if is_first:
        show_instruction_space(
            TEXTS[language]["rt_block_end_first"],
            TEXTS[language]["rt_block_end_first_hint"],
        )

    save_logs_now()

try:
    # Condition 1 : chosen by experimenter
    cond_1 = condition_task
    cond_2 = "V" if cond_1 == "M" else "M"

    if rt_block_position == "B":
        run_rt_block_task(is_first=True)

    # Meditation preparation (one-time only, before any PPS task block)
    if group == "E":
        run_meditation_preparation()

    # Resting state (one-time only, before any PPS task block)
    show_resting_state()

    run_condition_task(cond_1, is_first=True)
    run_condition_task(cond_2, is_first=False)

    if rt_block_position == "A":
        run_rt_block_task(is_first=False)

finally:
    save_logs_now()

# ============================================================
# END SCREEN
send_event("END_SCREEN_START", send_lsl=True, send_ttl=False)
draw_text(TEXTS[language]["end"], height=52, wrap=TEXT_WRAP)
win.flip()
core.wait(3)
send_event("END_SCREEN_END", send_lsl=True, send_ttl=False)

print("\nExperiment finished.")
win.close()
core.quit()
