# uv pip install numpy sounddevice psychopy psychopy-sounddevice pylsl pyserial
import os
import csv
import random
from datetime import datetime
import wave
import numpy as np
import serial
from pylsl import StreamInfo, StreamOutlet, local_clock
from psychopy import prefs

# ============================================================
# MACHINE-SPECIFIC SETTINGS
# Audio device name and COM port differ from one computer to another.
# See config_local.example.py for setup instructions.
try:
    from config_local import AUDIO_DEVICE_NAME, MMBT_PORT
except ImportError:
    raise RuntimeError(
        "Missing config_local.py. Copy config_local.example.py to "
        "config_local.py and fill in AUDIO_DEVICE_NAME / MMBT_PORT for this machine."
    )

# ============================================================
# PSYCHOPY AUDIO BACKEND
prefs.hardware["audioLib"] = ["sounddevice"]
prefs.hardware["audioDevice"] = [AUDIO_DEVICE_NAME]

from psychopy import core, visual, sound, event
from psychopy.hardware import keyboard

# ============================================================
# GLOBAL FLAGS
LSL_AVAILABLE = True
SERIAL_AVAILABLE = True
MMBT_ENABLED = True

# GENERAL PATHS
DATA_DIR = "data"
AUDIO_DIR = "audio_cache"

# ============================================================
# EXPERIMENT DESIGN
# PPS conditions:
# T   = tactile only
# AN  = auditory near only
# AF  = auditory far only
# ANT = audio + tactile near
# AFT = audio + tactile far
# P3A = oddball tone
#
# SPEAKER SETUP (must match the audio panning below to get a real near/far effect):
#   "near" (AN / ANT) is played on the RIGHT audio channel -> place the RIGHT speaker IN FRONT OF / close to the participant.
#   "far"  (AF / AFT) is played on the LEFT audio channel  -> place the LEFT speaker BEHIND / far from the participant.
NUM_BLOCKS_PPS = 6
TRIALS_PER_CONDITION_PER_BLOCK = 11
PPS_CONDITIONS = ["T", "AN", "AF", "ANT", "AFT"]
EXTRA_CONDITION = "P3A"

# ============================================================
# TIMING PARAMETERS
DURATION_AUDIO = 0.100
ISI_VALUES_PPS = [2.5, 2.6, 2.7, 2.8, 2.9, 3.0]

DURATION_FRUIT = 2.0
ISI_FRUIT = 0.2

DURATION_END_BLOCK = 1.0
DURATION_AFTER_BREAK = 30.0
DURATION_FEEDBACK = 4.0
DURATION_BASELINE = 5.0
DURATION_BASELINE_BLOCK = 3.0
DURATION_RESTING_STATE = 1
DURATION_TASK_START_MSG = 3.0
DURATION_MEDITATION_PREP = 8  # 8 seconds for testing (set to 480 for 8 minutes in production)

# ============================================================
# DISPLAY PARAMETERS
TEXT_HEIGHT = 32
TEXT_WRAP = 900

# ============================================================
# AUDIO PARAMETERS
SAMPLE_RATE = 44100
P3A_FREQ = 1000
TARGET_RMS = 0.08

# ============================================================
# MMBT-S / DIGITIMER SETTINGS
# MMBT_PORT comes from config_local.py (see MACHINE-SPECIFIC SETTINGS above).
MMBT_BAUDRATE = 9600
MMBT_PULSE_WIDTH = 0.005
DIGITIMER_TTL_CODE = 128 
MMBT_MODE = "pulse"   # "pulse" or "simple"

# ============================================================
# TRIGGER CODES FOR LSL
TRIGGER_CODES = {
    "T": 1,
    "AN": 2,
    "AF": 3,
    "ANT": 4,
    "AFT": 5,
    "P3A": 6,
    "T_OFF": 11,
    "AN_OFF": 12,
    "AF_OFF": 13,
    "ANT_OFF": 14,
    "AFT_OFF": 15,
    "P3A_OFF": 16,
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

        # ===== CALIBRATION & FAMILIARIZATION =====
        "calibration_intro": "Pendant cette expérience, vous allez entendre des sons provenant des deux haut-parleurs situés devant vous.\n\n\nNous allons commencer par une phase de calibration auditive.",
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
        "famil_tactile_hint": "Appuyez sur la barre d'espace pour le sentir.",
        "famil_repeat_question": "Voulez-vous écouter à nouveau la différence ?",
        "famil_repeat_question_tactile": "Voulez-vous réessayer ?",
        "famil_repeat_yes_no": "Oui ou Non : appuyez sur O ou N, puis barre d'espace.",

        "consigne_stimuli": "Durant l'expérience ce sont exactement ces sons et cette vibration que vous allez percevoir. \n\nOn vous demandera uniquement de les percevoir, sans rien faire d'autre. Seul votre état mental devra changer : méditation ou non.",
        "consigne_stimuli_hint": "Appuyez sur la barre espace pour commencer.",

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
        "vigilance_practice_done_hint": "Appuyez sur la barre d'espace pour continuer.",
        "meditation_practice_done_hint": "Appuyez sur la barre d'espace pour continuer.",

        "meditation_label": "Méditation",
        "meditation_practice_heading": "Phase d'entraînement",
        "meditation_practice_intro": "Vous allez faire une courte phase d'entraînement.\n\nVous entendrez les sons et ressentirez les vibrations, tandis que vous devez fixer la croix à l'écran et rester en état de méditation.",
        "meditation_practice_hint": "Appuyez sur la barre d'espace pour commencer.",
        "meditation_practice_done": "Bien! Vous avez maintenant une idée de ce qui va se passer.\n\nLe même protocole sera répété sur plusieurs blocs.\nTentez de maintenir votre état de méditation tout au long.",

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

        # ===== CALIBRATION & FAMILIARIZATION =====
        "calibration_intro": "During this experiment, you will hear sounds from the two loudspeakers in front of you.\n\nWe will start with an auditory calibration phase.",
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

        # ===== PRACTICE PHASES =====
        "vigilance_practice_heading": "Training phase",
        "vigilance_practice_intro": "You will now do a short training phase.\n\nYou will hear the sounds and feel the vibrations, while fruits appear on the screen.\n\nCount the number of STRAWBERRIES.",
        "vigilance_practice_hint": "Press the space bar to begin.",
        "meditation_label": "Meditation",
        "meditation_practice_heading": "Training phase",
        "meditation_practice_intro": "You will now do a short training phase.\n\nYou will hear the sounds and feel the vibrations, while you must focus on the cross on the screen and remain in a meditative state.",
        "meditation_practice_hint": "Press the space bar to begin.",
        "meditation_practice_done": "Good! You now have an idea of what will happen.\n\nThe same protocol will be repeated over several blocks.\nTry to maintain your meditative state throughout.\n\n\nWe will now start with a resting period for 2 minutes.\nPlease simply focus on the cross that will appear on the screen, without moving.",
        "meditation_practice_done_hint": "Press the space bar to continue.",
        "vigilance_practice_done": "Good! You now have an idea of what will happen.\n\nThe same protocol will be repeated over several blocks.\n\n\nWe will now start with a resting period for 2 minutes, then the task will begin.\nPlease simply focus on the cross that will appear on the screen, without moving.",
        "vigilance_practice_done_hint": "Press the space bar to continue.",

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

        # ===== END =====
        "end": "Thank you for your participation!",
    }
}

# ============================================================
# CSV HEADERS
BLOCK_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition_task", "block",
    "response_strawberries", "real_strawberries", "error", "total_fruits",
    "trial_sequence", "n_T", "n_AN", "n_AF", "n_ANT", "n_AFT", "n_P3A",
    "block_duration_sec",
]

TRIAL_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition_task",
    "block", "trial_index", "condition_trial",
    "audio_side", "audio_present", "tactile_present",
    "isi_sec", "stim_onset_clock", "trigger_code",
    "lsl_sent", "ttl_sent", "lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time",
]

# ============================================================
# GLOBAL STATE VARIABLES
marker_outlet = None
mmbt = None
block_log_rows = []
trial_log_rows = []
block_log_path = None
trial_log_path = None
language = ""
group = ""  # "E" (expert meditator) or "C" (control) 
condition_task = ""  # "M" = meditation, "V" = vigilance
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
# MMBT-S SERIAL SETUP
# TTL values are sent as raw bytes with ser.write(bytes([code])).
def setup_mmbt():
    global mmbt

    if not MMBT_ENABLED or not SERIAL_AVAILABLE:
        return

    try:
        mmbt = serial.Serial(
            port=MMBT_PORT,
            baudrate=MMBT_BAUDRATE,
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
            mmbt.setDTR(True)
        except Exception:
            pass

        core.wait(0.2)

        # Reset output state at startup
        mmbt.write(bytes([0]))
        mmbt.flush()
        core.wait(0.05)

        print(f"MMBT-S connected on {MMBT_PORT} ({MMBT_BAUDRATE} baud)")
        print(f"Digitimer TTL code = {DIGITIMER_TTL_CODE}")

    except Exception as e:
        print(f"WARNING: Could not open MMBT-S on {MMBT_PORT}: {e}")
        mmbt = None

# ============================================================
def send_lsl_marker(code):
    lsl_time = None
    if marker_outlet is not None:
        try:
            lsl_time = local_clock()
            marker_outlet.push_sample([int(code)], lsl_time)
        except Exception as e:
            print(f"WARNING: failed to send LSL marker {code}: {e}")
    return lsl_time

def send_mmbt_ttl(code=DIGITIMER_TTL_CODE, pulse_width=MMBT_PULSE_WIDTH):
    ttl_on_time = None
    ttl_off_time = None

    if mmbt is not None:
        try:
            ttl_on_time = core.getTime()
            mmbt.write(bytes([int(code)]))
            mmbt.flush()

            if MMBT_MODE.lower() == "simple":
                core.wait(pulse_width)
                ttl_off_time = core.getTime()
                mmbt.write(bytes([0]))
                mmbt.flush()
            else:
                # In pulse mode, the hardware resets automatically.
                ttl_off_time = ttl_on_time + 0.008

        except Exception as e:
            print(f"WARNING: failed to send TTL pulse {code}: {e}")

    return ttl_on_time, ttl_off_time

def send_event(code_key, send_lsl=True, send_ttl=False, ttl_code=DIGITIMER_TTL_CODE):
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

    if send_ttl:
        ttl_on_time, ttl_off_time = send_mmbt_ttl(ttl_code)

    return {
        "event_code": code,
        "local_time": local_time,
        "lsl_time": lsl_time,
        "ttl_on_time": ttl_on_time,
        "ttl_off_time": ttl_off_time,
        "ttl_sent": int(send_ttl and mmbt is not None),
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
    tone_p3a_path = os.path.join(AUDIO_DIR, "tone_p3a.wav")
    calibration_path = os.path.join(AUDIO_DIR, "calibration_noise.wav")

    write_wav_file(noise_right_path, generate_white_noise_array(pan="right"))
    write_wav_file(noise_left_path, generate_white_noise_array(pan="left"))
    write_wav_file(tone_p3a_path, generate_tone_array())
    write_wav_file(calibration_path, generate_white_noise_array(duration=5.0, pan="both"))

    return noise_right_path, noise_left_path, tone_p3a_path, calibration_path

NOISE_RIGHT_PATH, NOISE_LEFT_PATH, TONE_P3A_PATH, CALIBRATION_NOISE_PATH = make_audio_files()
NOISE_RIGHT = sound.Sound(NOISE_RIGHT_PATH)
NOISE_LEFT = sound.Sound(NOISE_LEFT_PATH)
TONE_P3A = sound.Sound(TONE_P3A_PATH)
CALIBRATION_NOISE = sound.Sound(CALIBRATION_NOISE_PATH)

def play_sound_obj(sound_obj):
    # Stop first to avoid overlap from previous trial
    sound_obj.stop()
    sound_obj.play()

def stop_all_sounds():
    for s in [NOISE_RIGHT, NOISE_LEFT, TONE_P3A]:
        try:
            s.stop()
        except Exception:
            pass

# ============================================================
# WINDOW AND INPUT
win = visual.Window(fullscr=True, color="black", units="pix")
kb = keyboard.Keyboard()

# ============================================================
# INITIALIZATION of LSL + MMBT
# Done before any screen is shown, so every instruction/consigne the
# participant sees (including language/group/condition selection) can be
# marked in the EEG/ECG signal.
setup_lsl()
setup_mmbt()

fixation_h = visual.Line(win, start=(-15, 0), end=(15, 0), lineWidth=3, lineColor="white")
fixation_v = visual.Line(win, start=(0, -15), end=(0, 15), lineWidth=3, lineColor="white")

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
    draw_text(text, height=22, wrap=TEXT_WRAP, pos=pos, italic=True)

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

# ============================================================
# SAFE EXIT
def safe_quit():
    try:
        if mmbt is not None:
            mmbt.close()
    except Exception as e:
        print(f"Error while closing MMBT-S: {e}")

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
    show_text_timed(txt, seconds=DURATION_END_BLOCK, height=28, wrap=TEXT_WRAP,
                     start_key="BLOCK_BREAK_START", end_key="BLOCK_BREAK_END")

def show_feedback(ans, real, err):
    fb_txt = TEXTS[language]["feedback_template"].format(ans=ans, real=real, err=err)
    if err == 0:
        fb_txt += "\n\n" + TEXTS[language]["feedback_well_done"]
    elif err != 0:
        fb_txt += "\n\n" + TEXTS[language]["feedback_try_harder"]
    show_text_timed(fb_txt, seconds=DURATION_FEEDBACK, height=28, wrap=TEXT_WRAP,
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
        draw_text(chosen if chosen else "_", height=48, wrap=TEXT_WRAP, pos=(0, -40))
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
        show_instruction_space(
            TEXTS[language]["famil_tactile"],
            TEXTS[language]["famil_tactile_hint"],
        )
        send_mmbt_ttl()
        core.wait(0.5)

        if not ask_yes_no_question(question_key="famil_repeat_question_tactile"):
            break

def show_calibration_psychophysical():
    NUM_TRIALS = 20
    CATCH_TRIAL_PROB = 0.25

    show_instruction_space(
        TEXTS[language]["calibration_instruction"],
        TEXTS[language]["calibration_instruction_hint"],
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

    mouse_obj = event.Mouse(win=win, visible=True)

    yes_button = visual.Rect(win, width=150, height=80, pos=(-150, -150), fillColor="gray", opacity=0.7)
    no_button = visual.Rect(win, width=150, height=80, pos=(150, -150), fillColor="gray", opacity=0.7)
    yes_text = visual.TextStim(win, text=TEXTS[language]["calibration_yes"], pos=(-150, -150), height=28, color="white", bold=True)
    no_text = visual.TextStim(win, text=TEXTS[language]["calibration_no"], pos=(150, -150), height=28, color="white", bold=True)
    sound_indicator = visual.TextStim(win, text="Son", pos=(0, 100), height=40, color="yellow", bold=True)
    question = visual.TextStim(win, text=TEXTS[language]["calibration_trial"], pos=(0, 0), height=32, color="white")

    calibration_done = False
    trial_idx = 0

    while not calibration_done:
        is_catch_trial = random.random() < CATCH_TRIAL_PROB

        sound_indicator.draw()
        win.flip()
        core.wait(0.5)

        if not is_catch_trial:
            play_sound_obj(NOISE_RIGHT)
            core.wait(DURATION_AUDIO + 0.1)
            stop_all_sounds()
        else:
            core.wait(DURATION_AUDIO + 0.1)

        core.wait(0.5)

        answered = False
        while not answered:
            check_escape()
            question.draw()
            yes_button.draw()
            no_button.draw()
            yes_text.draw()
            no_text.draw()
            win.flip()

            if yes_button.contains(mouse_obj):
                if mouse_obj.getPressed()[0]:
                    answered = True
                    core.wait(0.3)
            elif no_button.contains(mouse_obj):
                if mouse_obj.getPressed()[0]:
                    answered = True
                    core.wait(0.3)

        t_end = core.getTime() + 4.0
        while core.getTime() < t_end:
            check_escape()
            draw_fixation_only()
            win.flip()

            keys = get_keys(["space", "escape"])
            if any(k.name == "escape" for k in keys):
                safe_quit()
            if any(k.name == "space" for k in keys):
                calibration_done = True
                break

    mouse_obj.setVisible(False)

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
    # Build one block with balanced conditions + one P3A trial
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

    p3a_pos = random.randint(14, len(best_trials))
    best_trials.insert(p3a_pos, EXTRA_CONDITION)
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
            p: visual.ImageStim(self.win, image=p, size=(200, 200))
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
                self.t_next = now + ISI_FRUIT
            else:
                self.current_path = random.choice(self.stimuli)
                self.total_fruit_count += 1
                if "fraise" in os.path.basename(self.current_path).lower():
                    self.strawberry_count += 1
                    send_event("STRAWBERRY_DISPLAY", send_lsl=True, send_ttl=False)
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

def frame_loop_until(t_end, vigilance_task=None):
    while True:
        check_escape()
        now = clock.getTime()

        if now >= t_end:
            break

        if vigilance_task is not None and vigilance_task.running:
            vigilance_task.update_and_draw(now)
        else:
            draw_fixation_only()

        win.flip()

# ============================================================
# TRIAL LOGIC
def describe_trial(condition_trial):
    if condition_trial == "T":
        return False, True, ""
    if condition_trial == "AN":
        return True, False, "right"
    if condition_trial == "AF":
        return True, False, "left"
    if condition_trial == "ANT":
        return True, True, "right"
    if condition_trial == "AFT":
        return True, True, "left"
    if condition_trial == "P3A":
        return True, False, "both"
    raise ValueError(f"Unknown condition_trial: {condition_trial}")

def run_trial(condition_trial, block_idx, trial_idx, vigilance_task=None):
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

    # Tactile only
    if condition_trial == "T":
        event_info = send_event(
            condition_trial,
            send_lsl=True,
            send_ttl=True,
            ttl_code=DIGITIMER_TTL_CODE
        )

    # Audio only
    elif condition_trial in ["AN", "AF", "P3A"]:
        event_info = send_event(condition_trial, send_lsl=True, send_ttl=False)
        audio_play_call_time = core.getTime()

        if condition_trial == "AN":
            play_sound_obj(NOISE_RIGHT)
        elif condition_trial == "AF":
            play_sound_obj(NOISE_LEFT)
        elif condition_trial == "P3A":
            play_sound_obj(TONE_P3A)

    # Audio + tactile
    elif condition_trial in ["ANT", "AFT"]:
        event_info = send_event(
            condition_trial,
            send_lsl=True,
            send_ttl=True,
            ttl_code=DIGITIMER_TTL_CODE
        )
        audio_play_call_time = core.getTime()

        if condition_trial == "ANT":
            play_sound_obj(NOISE_RIGHT)
        elif condition_trial == "AFT":
            play_sound_obj(NOISE_LEFT)

    # Stimulus presentation window
    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset, vigilance_task=vigilance_task)
    stop_all_sounds()

    # Offset marker
    send_event(condition_trial + "_OFF", send_lsl=True, send_ttl=False)

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = stim_offset + isi
    frame_loop_until(trial_end, vigilance_task=vigilance_task)

    # Save trial row
    trial_log_rows.append({
        "participant_num": pp_id,
        "language": language,
        "group":group,
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
        "trigger_code": event_info["event_code"],
        "lsl_sent": event_info["lsl_sent"],
        "ttl_sent": event_info["ttl_sent"],
        "lsl_time": event_info["lsl_time"],
        "ttl_on_time": event_info["ttl_on_time"],
        "ttl_off_time": event_info["ttl_off_time"],
        "audio_play_call_time": audio_play_call_time,
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
# AUDIO CALIBRATION INTRO
show_instruction_space(
    TEXTS[language]["calibration_intro"],
    TEXTS[language]["consigne_stimuli_hint"],
)

# ============================================================
# AUDIO CALIBRATION
show_calibration_psychophysical()

# ============================================================
# STIMULUS FAMILIARIZATION
show_stimulus_familiarization()

# ============================================================
# GENERAL INSTRUCTION ABOUT STIMULI (same for all conditions)
show_instruction_space(
    TEXTS[language]["consigne_stimuli"],
    TEXTS[language]["consigne_stimuli_hint"],
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
            p: visual.ImageStim(self.win, image=p, size=(200, 200))
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
        t_end = core.getTime() + (self.total_fruit_count * (DURATION_FRUIT + ISI_FRUIT))

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
            core.wait(DURATION_FRUIT + ISI_FRUIT)

def run_vigilance_practice():
    # Introduction to practice phase
    show_instruction_space(
        TEXTS[language]["vigilance_practice_intro"],
        TEXTS[language]["vigilance_practice_hint"],
    )

    # Setup practice vigilance task
    practice_vigilance = VigilanceTaskContinuous(win)
    practice_vigilance.start(clock.getTime())

    # Mini block with ~3 practice trials (mix of conditions)
    practice_trials = ["AN", "T", "AF"]
    t_end = clock.getTime() + 20.0  # 20 seconds of practice
    trial_idx = 0

    while clock.getTime() < t_end and trial_idx < len(practice_trials):
        check_escape()
        cond_trial = practice_trials[trial_idx]

        # Run trial with PPS stimulation + vigilance task
        run_trial(cond_trial, block_idx=0, trial_idx=trial_idx, vigilance_task=practice_vigilance)
        trial_idx += 1

    practice_vigilance.stop()

    # Ask strawberry count
    real = practice_vigilance.strawberry_count
    ans, err = ask_strawberry_question(real)
    show_feedback(ans, real, err)

    # Brief confirmation (4 seconds)
    show_text_timed(
        TEXTS[language]["vigilance_practice_done"],
        seconds=8.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

def run_meditation_preparation():
    # Meditation preparation period - just display "Méditation" / "Meditation"
    clear_keyboard()
    t_end = core.getTime() + DURATION_MEDITATION_PREP

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

    # Mini meditation task with ~3 PPS trials
    practice_trials = ["AN", "T", "AF"]
    t_end = clock.getTime() + 20.0  # 20 seconds of practice
    trial_idx = 0

    while clock.getTime() < t_end and trial_idx < len(practice_trials):
        check_escape()
        cond_trial = practice_trials[trial_idx]

        # Run trial with PPS stimulation only (no vigilance task)
        run_trial(cond_trial, block_idx=0, trial_idx=trial_idx, vigilance_task=None)
        trial_idx += 1

    # Brief confirmation (4 seconds)
    show_text_timed(
        TEXTS[language]["meditation_practice_done"],
        seconds=8.0,
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

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
        # Meditation preparation period (only for experts)
        if group == "E":
            run_meditation_preparation()
        run_meditation_practice()

    if is_first:
        show_resting_state()

    send_event("EXP_START", send_lsl=True, send_ttl=False)
    show_baseline(DURATION_BASELINE, send_markers=True)

    for block_idx, block in enumerate(all_blocks):
        print(f"\nStart block {block_idx + 1}/{NUM_BLOCKS_PPS}")

        show_baseline(DURATION_BASELINE_BLOCK, send_markers=True)
        send_event("BLOCK_START", send_lsl=True, send_ttl=False)
        block_t0 = clock.getTime()

        counts = {k: 0 for k in PPS_CONDITIONS + [EXTRA_CONDITION]}

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
            "n_P3A": counts["P3A"],
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


try:
    # Condition 1 : chosen by experimenter
    cond_1 = condition_task
    cond_2 = "V" if cond_1 == "M" else "M"

    run_condition_task(cond_1, is_first=True)

    run_condition_task(cond_2, is_first=False)

finally:
    save_logs_now()

# ============================================================
# END SCREEN
send_event("END_SCREEN_START", send_lsl=True, send_ttl=False)
draw_text(TEXTS[language]["end"], height=24, wrap=TEXT_WRAP)
win.flip()
core.wait(3)
send_event("END_SCREEN_END", send_lsl=True, send_ttl=False)

print("\nExperiment finished.")
win.close()
core.quit()
