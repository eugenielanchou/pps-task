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
ARDUINO_ENABLED = False

# GENERAL PATHS
DATA_DIR = "data"
AUDIO_DIR = "audio"

# ============================================================
# ARDUINO VIBRATOR SETTINGS
ARDUINO_PORT = "COM5"
ARDUINO_BAUDRATE = 115200
TTL_BYTE = 1
DURATION_TACTILE = 50  # ms - sent to Arduino, firmware clamps any value below 50ms
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
DURATION_FRUIT = 1
ISI_VALUES_FRUIT = [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

# Block timing and fixation
FIXATION_BEFORE_BLOCK = 7.0
DURATION_END_BLOCK = 1.0
DURATION_AFTER_BLOCK = 3.0  # inter-block message (after_block_M/V/rt), auto-timed
DURATION_FEEDBACK = 3.0
FEEDBACK_GOOD_MAX_ERROR = 3.0

# Resting state and meditation
DURATION_RESTING_STATE_MSG = 6.0  # intro message before the fixation cross, auto-timed (V condition only)
DURATION_MEDITATION = 4.0  # METTRE 480!! 8 minutes fixation cross for M condition
DURATION_BASELINE = 1.0  # (METTRE 120) 2 minutes fixation cross for V condition
DURATION_TASK_START_MSG = 3.0
DURATION_VIGILANCE_1 = 3.0    # short instruction shown at the start of EACH V block
DURATION_END = 3.0            # final "thank you" screen, auto-timed

# ============================================================
# DISPLAY PARAMETERS
TEXT_HEIGHT = 56
TEXT_WRAP = 1400

# --- Phenomenology layout constants ---
FONT_QUESTION = 56
FONT_TIME_HALF = 44
FONT_INSTRUCTION = 54
FONT_OPTION = 44
FONT_LABEL = 40
FONT_HINT = 36
FONT_X_NOTE = 28

POS_Y_QUESTION = 300
POS_Y_TIME_HALF = 180
POS_Y_HINT = -340

V_SCALE_X = -520
V_SCALE_LABEL_OFFSET_X = 720
V_SCALE_LABEL_WRAP = 1300
V_SCALE_SPACING = 68
V_SCALE_TOP_FIXED_Y = 90
V_SCALE_CENTER_Y = -80

H_SCALE_Y = 0
H_SCALE_SPACING = 85
H_SCALE_START_X = -550
H_SCALE_LABEL_OFFSET_Y = 70

BOX_W = 90
BOX_H = 80
BOX_LINE_WIDTH = 2

COLOR_DEFAULT = "white"
COLOR_SELECTED = "yellow"

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
    "EXP_END": 96,  # whole-session end marker (fired on normal completion via safe_quit-style abort path, or use CONDITION_END for per-condition end)
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

    "CONDITION_START": 141,
    "CONDITION_END": 142,

    "MEDITATION_1_START": 143,
    "MEDITATION_1_END": 144,
    "MEDITATION_2_START": 145,
    "MEDITATION_2_END": 146,
    "VIGILANCE_1_START": 147,
    "VIGILANCE_1_END": 148,
    "AFTER_BLOCK_START": 149,
    "AFTER_BLOCK_END": 150,
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
        "condition_heading": "La condition :",
        "rt_timing_heading": "Le RT :",

        # ===== FAMILIARIZATION =====
        "intro_hint": "Cliquer sur la barre d'espace.",
        "famil_intro": "Au cours de cette expérience, vous entendrez des sons provenant de deux enceintes et ressentirez une légère vibration au niveau du torse.\n\nNous allons d'abord vous familiariser avec ces différentes sensations.",
        "famil_near": "Vous allez maintenant entendre le son \nPROCHE.",
        "famil_far": "Vous allez maintenant entendre le son \nLOINTAIN.",
        "famil_sound_hint": "Appuyez sur la barre d'espace pour l'écouter.",
        "famil_tactile": "Vous allez maintenant ressentir la vibration.",
        "famil_tactile_hint": "Appuyez sur la barre d'espace pour la ressentir.",
        "famil_repeat_question": "Souhaitez-vous recommencer ?",

        # ===== TASK DESCRIPTIONS =====
        "task_intro_start": "L'expérience se déroulera en trois parties, séparées par de courtes pauses.\n\nLes sons et la vibration seront les mêmes dans chaque partie. Seul l'état dans lequel vous devrez être changera.\n\nAprès chaque bloc, vous répondrez à des questions sur votre expérience.\n",
       
        "consigne_E_M": "Dans cette partie, nous vous invitons à méditer sur la Nature de l'Esprit pendant que vous allez entendre des sons et sentir la vibration.\n\nVous n'aurez rien d'autre à faire que de continuer à méditer sur la Nature de l'Esprit.",
        "consigne_E_V": "Dans cette partie, essayez, de ne PAS chercher à reconnaître la Nature de l'Esprit.\n\nPortez simplement votre attention sur la croix de fixation à l'écran. La croix changera de couleur progressivement. Comptez mentalement le nombre de fois où elle est MAGENTA.",
        "consigne_C_M": "Dans cette partie, vous allez écouter un audio pendant 8min qui vous guidera vers un état de calme. Laissez-vous guider par les instructions.",
        "consigne_C_V": "Dans cette partie, portez simplement votre attention sur la croix de fixation à l'écran. La croix changera de couleur progressivement.\n\nComptez mentalement le nombre de fois où elle est MAGENTA.",
        "rt_block_intro": "Dans cette partie, appuyez aussi rapidement que possible sur la barre d'espace dès que vous ressentez la VIBRATION.\n\nFixer la croix, ne pas fermer les yeux.",

        "consigne_hint": "Lorsque vous êtes prêt, appuyez sur la barre d'espace pour commencer.",
        
        # ===== MEDITATION =====#
        "meditation_prepare": "Un gong va sonner, vous allez avoir une période de préparation : installez-vous, videz votre esprit.\n\nPuis un second gong indiquera l'arrivée des sons et de la vibration. Restez en méditation.\n\nGardez les yeux ouverts en fixant la croix blanche sur l'écran.",
        "meditation_prepare_control": "Une fois l'audio terminé, vous allez entendre les sons et ressentir la vibration. Vous n'avez rien à faire, juste essayez de conserver le même état de calme que pendant l'audio.\n\nGarder les yeux ouverts et fixer la croix.",
        "meditation_prepare_hint": "Cliquez sur la barre d'espace quand vous êtes prêt.",
        "meditation_start_stimuli": "Les sons et la vibration vont maintenant arriver. Restez dans l'état de méditation.", 

        # ===== RESTING STATE (once per condition) =====
        "resting_state_heading": "Nous allons commencer par une période de repos de 2 minutes.\n\nVeuillez simplement fixer la croix qui apparaîtra à l'écran. \n\nEssayer, si possible, de ne pas bouger.",

        # ===== PER-BLOCK PROMPTS (Vigilance) =====
        "vigilance_1": "Fixez la croix. La croix changera de couleur. Comptez le nombre de fois où elle est magenta.",

        # ===== COLOR QUESTION & FEEDBACK =====
        "question_fraise": "Combien de fois la croix était-elle magenta ?",
        "feedback_template": "Vous avez répondu : {ans}\nNombre réel de fois magenta : {real}\n\nÉcart : {err}",
        "feedback_well_done": "Bravo, continuez comme ça !",
        "feedback_good": "Presque !",
        "feedback_try_harder": "Soyez plus attentif !",

        # ===== BREAKS & TRANSITIONS (within a condition, per block) =====
        "end_block": "Fin du bloc {}/{}.",
        "ipad_pheno": "Veuillez prendre l'iPad et répondre à la question dessus.\n\nUne fois terminé, appuyez sur la barre d'espace.",
        "after_block_M": "Prenez quelques instants pour vous replacer dans l'état méditatif.\n\nL'expérience reprendra bientôt.",
        "after_block_V": "La même tâche va reprendre.\n\nInstallez-vous confortablement et portez votre attention sur l'écran.",

        # ===== BETWEEN CONDITIONS / BEFORE RT =====
        "pause_condition_1": "Fin de la première partie.\n\nPrenez quelques minutes. Vous pouvez bouger et demander de l'eau à l'expérimentateur si besoin.",
        "pause_entre_condition_1_hint": "Appuyez sur la barre d'espace quand vous êtes prêt à commencer la partie suivante.",
        "pause_condition_2": "Fin de la deuxième partie.\n\nPrenez quelques minutes. Vous pouvez bouger et demander de l'eau à l'expérimentateur si besoin.",
        "pause_entre_condition_2_hint": "Appuyez sur la barre d'espace quand vous êtes prêt à commencer la dernière partie.",

        # ===== REACTION TIME BLOCK =====
        "rt_between_blocks": "Fin du bloc {}/{}.",
        "rt_block_end": "Fin du bloc {}/{}.",
        "after_block_rt": "La même tâche va reprendre.\n\nCliquer aussi rapidement que possible sur la barre d'espace quand vous sentez la VIBRATION.",
        "rt_training_intro": "Commençons par un court entraînement.",
        "rt_training_hint": "Cliquer sur la barre d'espace pour commencer.",
        "rt_feedback_good": "Bon !",
        "rt_feedback_wrong_click": "Ne pas cliquer !",
        "rt_feedback_click": "Cliquer !",
        "rt_training_end": "Fin de l'entraînement.",
        "rt_end_hint": "Cliquer sur la barre d'espace pour démarrer la tâche.",

        # ===== END =====
        "end": "Merci beaucoup pour votre participation !",
    },

    "en": {
        # ===== STARTUP & INFO COLLECTION =====
        "lang_select": "Pour avoir les consignes en français, appuyez sur : F\n\nTo have the instructions in English, press: E",
        "participant_heading": "Participant number:",
        "participant_hint": "Type the ID, then press the space bar.",
        "group_heading": "Group:",
        "condition_heading": "Condition:",
        "rt_timing_heading": "RT :",

        # ===== FAMILIARIZATION =====
        "intro_hint": "Press the space bar.",
        "famil_intro": "During this experiment, you will hear sounds coming from two speakers and feel a slight vibration on your chest.\n\nWe will first familiarize you with these different sensations.",
        "famil_near": "You will now hear the NEAR sound.",
        "famil_far": "You will now hear the FAR sound.",
        "famil_sound_hint": "Press the space bar to listen.",
        "famil_tactile": "You will now feel the vibration.",
        "famil_tactile_hint": "Press the space bar to feel it.",
        "famil_repeat_question": "Would you like to do it again?",

        # ===== TASK DESCRIPTIONS =====
        "task_intro_start": "The experiment will unfold in three parts, separated by short breaks.\n\nThe sounds and vibration will be the same in each part. Only the state you must be in will change.\n\nAfter each block, you will answer questions about your experience.",


        # ===== CONDITION-SPECIFIC INSTRUCTIONS =====
        "meditation_prepare": "A gong will sound, and you will have a preparation period: settle into the meditative state and clear your mind.\n\nThen a second gong will signal the arrival of sounds and vibration. Remain in meditation from beginning to end.",
        "meditation_prepare_control": "Once the audio ends, you will hear sounds and feel vibration. You have nothing to do—just try to maintain the same calm state you had during the audio.\n\nKeep your eyes open and fixed on the cross.",
        "meditation_prepare_hint": "Press the space bar when you are ready.",
        "meditation_start_stimuli": "Sounds and vibration will now arrive. Remain in the meditative state.",
        "consigne_E_M": "In this part, we invite you to meditate on the Nature of Mind while sounds and vibration arrive.\n\nYour only task is to continue meditating on the Nature of Mind.\n\nKeep your eyes open and fixed on the white cross on the screen.",
        "consigne_E_V": "In this part, try, if possible, NOT to seek out the Nature of Mind.\n\nTo help with this, simply focus your attention on the fixation cross on the screen. The cross will change color progressively. Mentally count the number of times the cross is MAGENTA.",
        "consigne_C_M": "In this part, you will listen to an 8-minute audio recording that will guide you towards a state of calm. Let yourself be guided by the instructions.",
        "consigne_C_V": "In this part, simply focus your attention on the fixation cross on the screen. The cross will change color progressively.\n\nMentally count the number of times the cross is MAGENTA.",
        "consigne_hint": "When you are ready, press the space bar to begin.",


        # ===== RESTING STATE (once per condition) =====
        "resting_state_heading": "We will start with a 2-minute resting period.\n\nPlease simply fixate on the cross that will appear on the screen. Try, if possible, not to move.",

        # ===== PER-BLOCK PROMPTS (Vigilance) =====
        "vigilance_1": "Fixate on the cross. The cross will change color. Count how many times it is magenta.",

        # ===== COLOR QUESTION & FEEDBACK =====
        "question_fraise": "How many times was the cross magenta?",
        "feedback_template": "Your answer: {ans}\nActual number of times magenta: {real}\n\nDifference: {err}",
        "feedback_well_done": "Great job, keep it up!",
        "feedback_good": "Almost!",
        "feedback_try_harder": "Be more attentive!",

        # ===== BREAKS & TRANSITIONS (within a condition, per block) =====
        "end_block": "End of block {}/{}.",
        "ipad_pheno": "Please take the iPad and answer the question.\n\nThen, press the space bar.",
        "after_block_M": "Take a moment to settle back into the meditative state.\n\nThe experiment will resume shortly.",
        "after_block_V": "The same task will resume.\n\nGet comfortable and focus your attention on the screen.",

        # ===== BETWEEN CONDITIONS / BEFORE RT =====
        "pause_condition_1": "End of the first part.\n\nTake a few minutes. You can move around and ask the experimenter for water if needed.",
        "pause_entre_condition_1_hint": "Press the space bar when you are ready to begin the next part.",
        "pause_condition_2": "End of the second part.\n\nTake a few minutes. You can move around and ask the experimenter for water if needed.",
        "pause_entre_condition_2_hint": "Press the space bar when you are ready to begin the last part.",

        # ===== REACTION TIME BLOCK =====
        "rt_block_intro": "Press the space bar as quickly as possible as soon as you feel the vibration.\n\nKeep your eyes on the cross, do not close your eyes.",
        "rt_between_blocks": "End of block {}/{}.",
        "rt_block_end": "End of block {}/{}.",
        "after_block_rt": "The same task will resume.\n\nPress the space bar when you feel the vibration.",
        "rt_training_intro": "Let's start with a short training.",
        "rt_training_hint": "Press the space bar to begin.",
        "rt_feedback_good": "Good!",
        "rt_feedback_wrong_click": "Don't click!",
        "rt_feedback_click": "Click!",
        "rt_training_end": "End of training.",
        "rt_end_hint": "Press the space bar to start the task.",

        # ===== END =====
        "end": "Thank you very much for your participation!",
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
    "group", "participant_num", "datetime", "condition_task",
    "block", "trial_index", "condition_trial",
    "isi_sec", "stim_onset_clock", "stim_offset_clock", "trigger_code", "trigger_code_offset",
    "lsl_sent", "ttl_sent", "lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time",
]

RT_TRIAL_FIELDNAMES = [
    "group", "participant_num", "datetime", "condition_task",
    "block", "trial_index", "condition_trial",
    "isi_sec", "stim_onset_clock", "stim_offset_clock", "trigger_code", "trigger_code_offset",
    "lsl_sent", "ttl_sent", "lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time", "response_type",
    "reaction_time_sec", "response_absolute_clock", "response_lsl_time",
]

PHENO_FIELDNAMES = [
    "participant_num", "group", "datetime", "condition_task", "block", "time_half",
    "success_rating", "nom_recognition", "nom_confidence",
    "near_far_difference", "boundary_experience", "center_of_consciousness",
    "sounds_location", "sound_observer_separation",
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
vigilance_task = None
rt_timing = ""  # "before" or "after" - when RT block runs relative to M/V conditions
in_rt_block = False  # track if currently running RT block

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

    write_wav_file(noise_right_path, generate_white_noise_array(pan="right"))
    write_wav_file(noise_left_path, generate_white_noise_array(pan="left"))

    return noise_right_path, noise_left_path

NOISE_RIGHT_PATH, NOISE_LEFT_PATH = make_audio_files()
NOISE_RIGHT = sound.Sound(NOISE_RIGHT_PATH)
NOISE_LEFT = sound.Sound(NOISE_LEFT_PATH)
GONG = sound.Sound(os.path.join(AUDIO_DIR, "tibetan-bowl.wav"))
MEDITATION_AUDIO = sound.Sound(os.path.join(AUDIO_DIR, "conscience-ouverte.wav"))
MEDITATION_AUDIO.volume = 1

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

fixation_h = visual.Line(win, start=(-50, 0), end=(50, 0), lineWidth=8, lineColor="white")
fixation_v = visual.Line(win, start=(0, -50), end=(0, 50), lineWidth=8, lineColor="white")

def clear_keyboard():
    kb.clearEvents()

def get_keys(key_list=None, wait_release=False):
    return kb.getKeys(keyList=key_list, waitRelease=wait_release)

def draw_fixation_only():
    fixation_h.draw()
    fixation_v.draw()

def draw_text(text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 0), italic=False, color="white"):
    stim = visual.TextStim(win, text=text, color=color, height=height, wrapWidth=wrap, pos=pos, italic=italic)
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

def make_block_log_filename(pp_id, group):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_{timestamp_for_filename()}_blocks.csv"
    )

def make_trial_log_filename(pp_id, group):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_{timestamp_for_filename()}_trials.csv"
    )

def make_rt_log_filename(pp_id, group):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_rt_{timestamp_for_filename()}_trials.csv"
    )

def make_pheno_log_filename(pp_id, group):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_{timestamp_for_filename()}_phenomenology.csv"
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
            print("Saved phenomenology:", pheno_log_path)
    except Exception as e:
        print("Could not save phenomenology log:", e)

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

def show_instruction_space_with_image(heading, hint, image_path, height=TEXT_HEIGHT, wrap=TEXT_WRAP, image_size=(300, 300), start_key=None, end_key=None):
    clear_keyboard()
    if start_key:
        send_event(start_key, send_lsl=True, send_ttl=False)

    image_stim = visual.ImageStim(win, image=image_path, size=image_size)

    while True:
        check_escape()
        draw_text(heading, height=height, wrap=wrap, pos=(0, 100))
        image_stim.pos = (0, -80)
        image_stim.draw()
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

def show_baseline_with_audio(audio_obj, seconds, send_markers=False, start_key="BASELINE_START", end_key="BASELINE_END"):
    if send_markers:
        send_event(start_key, send_lsl=True, send_ttl=False)

    audio_obj.play()
    t_end = core.getTime() + seconds
    while core.getTime() < t_end:
        check_escape()
        draw_fixation_only()
        win.flip()
    audio_obj.stop()

    if send_markers:
        send_event(end_key, send_lsl=True, send_ttl=False)

def show_resting_state():
    """Called once per V condition: intro message (auto-timed) -> 2-minute
    fixation cross -> "task will start" message (auto-timed)."""
    show_text_timed(
        TEXTS[language]["resting_state_heading"], seconds=DURATION_RESTING_STATE_MSG,
        height=TEXT_HEIGHT, wrap=TEXT_WRAP,
        start_key="RESTING_STATE_INSTR_START", end_key="RESTING_STATE_INSTR_END",
    )
    show_baseline(
        DURATION_BASELINE,
        send_markers=True,
        start_key="RESTING_STATE_START",
        end_key="RESTING_STATE_END",
    )

def show_end_of_block_screen(block_idx):
    txt = TEXTS[language]["end_block"].format(block_idx + 1, NUM_BLOCKS_PPS)
    show_text_timed(txt, seconds=DURATION_END_BLOCK, height=56, wrap=TEXT_WRAP,
                     start_key="BLOCK_BREAK_START", end_key="BLOCK_BREAK_END")

def show_after_block(cond):
    key_name = "after_block_V" if cond == "V" else "after_block_M"
    show_text_timed(TEXTS[language][key_name], seconds=DURATION_AFTER_BLOCK, height=TEXT_HEIGHT, wrap=TEXT_WRAP,
                     start_key="AFTER_BLOCK_START", end_key="AFTER_BLOCK_END")

def show_vigilance_prompt():
    show_text_timed(TEXTS[language]["vigilance_1"], seconds=DURATION_VIGILANCE_1, height=TEXT_HEIGHT, wrap=TEXT_WRAP,
                     start_key="VIGILANCE_1_START", end_key="VIGILANCE_1_END")

def show_feedback(ans, real, err):
    # err is already |ans - real| (see ask_strawberry_question).
    # Tiers per spec: 0 -> well_done, 1-2 -> good, >2 -> try_harder.
    fb_txt = TEXTS[language]["feedback_template"].format(ans=ans, real=real, err=err)
    if err == 0:
        fb_txt += "\n\n" + TEXTS[language]["feedback_well_done"]
    elif err <= FEEDBACK_GOOD_MAX_ERROR:
        fb_txt += "\n\n" + TEXTS[language]["feedback_good"]
    else:
        fb_txt += "\n\n" + TEXTS[language]["feedback_try_harder"]
    show_text_timed(fb_txt, seconds=DURATION_FEEDBACK, height=56, wrap=TEXT_WRAP,
                     start_key="FEEDBACK_START", end_key="FEEDBACK_END")

def ask_ordinal_question(question_text, min_val, max_val, allow_x=False):
    """Collect ordinal response (e.g., 0-4 or 1-3). If allow_x=True, participant can press 'X'."""
    clear_keyboard()
    valid_keys = [str(i) for i in range(min_val, max_val + 1)]
    if allow_x:
        valid_keys.append("x")

    while True:
        check_escape()
        draw_text(question_text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 80))

        if allow_x:
            hint_txt = f"Press {min_val}-{max_val} or X"
        else:
            hint_txt = f"Press {min_val}-{max_val}"
        draw_hint(hint_txt)
        win.flip()

        keys = get_keys(valid_keys + ["escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name in valid_keys:
                return k.name.upper()

def ask_yes_no_simple(question_text):
    """Collect yes/no response (Y/N)."""
    clear_keyboard()
    valid_keys = ["y", "n"]

    while True:
        check_escape()
        draw_text(question_text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 80))
        draw_hint("Press Y or N")
        win.flip()

        keys = get_keys(valid_keys + ["escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name in valid_keys:
                return k.name.upper()

def ask_forced_choice_3(question_text, allow_x=False):
    """Collect forced choice response (1-3, optionally with X)."""
    clear_keyboard()
    valid_keys = ["1", "2", "3"]
    if allow_x:
        valid_keys.append("x")

    while True:
        check_escape()
        draw_text(question_text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 80))

        if allow_x:
            hint_txt = "Press 1, 2, 3 or X"
        else:
            hint_txt = "Press 1, 2 or 3"
        draw_hint(hint_txt)
        win.flip()

        keys = get_keys(valid_keys + ["escape"])
        for k in keys:
            if k.name == "escape":
                safe_quit()
            elif k.name in valid_keys:
                return k.name.upper()

def run_phenomenology_questionnaire(block_idx, time_half):
    """
    Run complete phenomenology questionnaire for one time half (T1 or T2).
    time_half: "T1" or "T2"
    Returns dict with all answers.
    """
    global pheno_log_rows

    send_event("IPAD_PHENO_START", send_lsl=True, send_ttl=False)

    q_prefix = f"Block {block_idx + 1}, {time_half}:\n\n"

    # Q1: Success rating (0-10 + X)
    q1_txt = q_prefix + "In this block, and based on your own personal best, how successfully did you follow the instruction?\n\n0 = unsuccessful | 5 = somewhat | 10 = very successful | X = I do not recall"
    success_rating = ask_ordinal_question(q1_txt, 0, 10, allow_x=True)

    # Q2: Nature of Mind recognition (0-4 + X)
    q2_txt = q_prefix + "Did you experience any moments you would describe as recognizing the nature of mind?\n\n0 = no | 1 = once | 2 = a few times | 3 = many times | 4 = most of the time | X = I do not recall"
    nom_recognition = ask_ordinal_question(q2_txt, 0, 4, allow_x=True)

    # Q3: Confidence in NOM rating (only if NOM = 1, 2, 3, or 4)
    nom_confidence = ""
    if nom_recognition not in ["0", "X"]:
        q3_txt = q_prefix + "How confident are you about your rating?\n\n1 = not confident | 2 = a little confident | 3 = confident | X = I do not recall"
        nom_confidence = ask_ordinal_question(q3_txt, 1, 3, allow_x=True)

    # Q4: Near vs. far difference (Y/N)
    q4_txt = q_prefix + "Was there a difference between near sounds and distant sounds?"
    near_far_difference = ask_yes_no_simple(q4_txt)

    # Q5: Boundary experience (0-2)
    q5_txt = q_prefix + "To what extent did you experience a boundary between you and the sounds?\n\n0 = no boundary | 1 = a distance | 2 = a separation"
    boundary_experience = ask_ordinal_question(q5_txt, 0, 2)

    # Q6: Center of consciousness (0-2)
    q6_txt = q_prefix + "Was there a center of consciousness?\n\n0 = no center | 1 = a subject observing mental phenomena | 2 = a sense of being an agent"
    center_of_consciousness = ask_ordinal_question(q6_txt, 0, 2)

    # Q7: Sounds location (1-3 + X)
    q7_txt = q_prefix + "To what extent did you experience sounds as occurring within the mind, or as feeling outside?\n\n1 = within the mind | 2 = outside | 3 = as much within as outside | X = I do not recall"
    sounds_location = ask_forced_choice_3(q7_txt, allow_x=True)

    # Q8: Sound-observer separation (1-3 + X)
    q8_txt = q_prefix + "To what extent did experiences involve a separation between the sound and an observer/hearer?\n\n1 = no sense of separation | 2 = observer separate but weak separation | 3 = clear sense of separation | X = I do not recall"
    sound_observer_separation = ask_forced_choice_3(q8_txt, allow_x=True)

    send_event("IPAD_PHENO_END", send_lsl=True, send_ttl=False)

    return {
        "success_rating": success_rating,
        "nom_recognition": nom_recognition,
        "nom_confidence": nom_confidence,
        "near_far_difference": near_far_difference,
        "boundary_experience": boundary_experience,
        "center_of_consciousness": center_of_consciousness,
        "sounds_location": sounds_location,
        "sound_observer_separation": sound_observer_separation,
    }

# ============================================================
# PHENOMENOLOGY QUESTIONNAIRE FUNCTIONS
# ============================================================
def draw_text_pheno(text, height=FONT_QUESTION, wrap=TEXT_WRAP, pos=(0, 0),
                    italic=False, color=COLOR_DEFAULT, align_text="center", bold=False):
    """Draw text with support for bold."""
    stim = visual.TextStim(win, text=text, color=color, height=height, wrapWidth=wrap,
                            pos=pos, italic=italic, bold=bold, alignText=align_text)
    stim.draw()
    return stim

def draw_hint_pheno(text, pos=(0, POS_Y_HINT)):
    draw_text_pheno(text, height=FONT_HINT, wrap=TEXT_WRAP, pos=pos, italic=True)

def draw_question_block_pheno(question_text, time_half=None, time_half_y=None):
    """Draw the question and, if provided, the T1/T2 indicator."""
    if time_half_y is None:
        time_half_y = POS_Y_TIME_HALF
    draw_text_pheno(question_text, height=FONT_QUESTION, wrap=TEXT_WRAP, pos=(0, POS_Y_QUESTION))
    if time_half:
        label = "T1 (first half of the block)" if time_half == "T1" else "T2 (second half of the block)"
        draw_text_pheno(f"Respond for {label}", height=FONT_TIME_HALF, wrap=TEXT_WRAP,
                   pos=(0, time_half_y), color=COLOR_SELECTED, bold=True)

def draw_selection_box_pheno(pos):
    rect = visual.Rect(win, width=BOX_W, height=BOX_H, pos=pos,
                        fillColor=None, lineColor=COLOR_SELECTED, lineWidth=BOX_LINE_WIDTH)
    rect.draw()

def ask_scale_vertical_pheno(question_text, scale_options, scale_labels, start_idx=1,
                        time_half=None, fixed_top_y=None, spacing=None, time_half_y=None):
    """Display a vertical scale with options and labels."""
    if spacing is None:
        spacing = V_SCALE_SPACING

    clear_keyboard()
    selected_idx = start_idx

    if fixed_top_y is not None:
        start_y = fixed_top_y
    else:
        num_options = len(scale_options)
        start_y = V_SCALE_CENTER_Y + ((num_options - 1) * spacing) / 2

    while True:
        check_escape()
        draw_question_block_pheno(question_text, time_half=time_half, time_half_y=time_half_y)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            y_pos = start_y - idx * spacing
            color = COLOR_SELECTED if idx == selected_idx else COLOR_DEFAULT

            if idx == selected_idx:
                draw_selection_box_pheno((V_SCALE_X, y_pos))

            draw_text_pheno(option, height=FONT_OPTION, pos=(V_SCALE_X, y_pos), color=color)
            if label:
                draw_text_pheno(label, height=FONT_LABEL, wrap=V_SCALE_LABEL_WRAP,
                           pos=(V_SCALE_X + V_SCALE_LABEL_OFFSET_X, y_pos),
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
                return scale_options[selected_idx]

def ask_nom_recognition_vertical_pheno(question_text, time_half=None):
    """NOM recognition scale (X, 0-4), vertical layout."""
    scale_options = ["X", "0", "1", "2", "3", "4"]
    scale_labels = [
        "I do not recall",
        "no",
        "yes, once",
        "a few times",
        "many times",
        "most of the time",
    ]
    return ask_scale_vertical_pheno(question_text, scale_options, scale_labels, start_idx=1,
                               time_half=time_half, fixed_top_y=V_SCALE_TOP_FIXED_Y)

def ask_success_rating_with_slider_pheno(question_text, time_half=None):
    """Visual scale for success rating (X, 0-10), horizontal layout."""
    clear_keyboard()

    scale_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    scale_labels = ["I do not recall", "unsuccessful", "", "", "", "", "", "", "", "", "", "very successful"]
    selected_idx = 1

    while True:
        check_escape()
        draw_question_block_pheno(question_text, time_half=time_half)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            x_pos = H_SCALE_START_X + idx * H_SCALE_SPACING
            color = COLOR_SELECTED if idx == selected_idx else COLOR_DEFAULT

            if idx == selected_idx:
                draw_selection_box_pheno((x_pos, H_SCALE_Y))

            draw_text_pheno(option, height=FONT_OPTION, pos=(x_pos, H_SCALE_Y), color=color)

            if label and option == "X":
                draw_text_pheno(label, height=FONT_X_NOTE, pos=(x_pos, H_SCALE_Y + H_SCALE_LABEL_OFFSET_Y), color=color)
            elif label:
                draw_text_pheno(label, height=FONT_X_NOTE, pos=(x_pos, H_SCALE_Y - H_SCALE_LABEL_OFFSET_Y), color=color)

        draw_hint_pheno("Use arrows to navigate, SPACE to confirm")
        win.flip()

        for k in get_keys(["left", "right", "space", "escape"]):
            if k.name == "escape":
                safe_quit()
            elif k.name == "left" and selected_idx > 0:
                selected_idx -= 1
            elif k.name == "right" and selected_idx < len(scale_options) - 1:
                selected_idx += 1
            elif k.name == "space":
                return scale_options[selected_idx]

def ask_question_for_time_half_pheno(question_text, time_half, ask_func, *args, **kwargs):
    """Ask question with time half indicator."""
    kwargs['time_half'] = time_half
    return ask_func(question_text, *args, **kwargs)

def ask_phenomenology_both_halves(block_idx):
    """Ask phenomenology questions for both T1 and T2."""
    recorded_condition = "RT" if in_rt_block else condition_task

    # Show general instruction
    general_txt = "Please answer the following questions using the arrow keys."
    clear_keyboard()
    while True:
        check_escape()
        draw_text_pheno(general_txt, height=FONT_INSTRUCTION, wrap=TEXT_WRAP, pos=(0, 50))
        draw_hint_pheno("Press SPACE to continue")
        win.flip()
        for k in get_keys(["space", "escape"]):
            if k.name == "escape":
                safe_quit()
            elif k.name == "space":
                break
        break

    # Show T1/T2 explanation
    explanation_txt = "We will distinguish two moments:\n\nT1 = first half of the block\nT2 = second half of the block"
    clear_keyboard()
    while True:
        check_escape()
        draw_text_pheno(explanation_txt, height=FONT_INSTRUCTION, wrap=TEXT_WRAP, pos=(0, 0))
        draw_hint_pheno("Press SPACE to continue")
        win.flip()
        for k in get_keys(["space", "escape"]):
            if k.name == "escape":
                safe_quit()
            elif k.name == "space":
                break
        break

    responses = {"T1": {}, "T2": {}}

    # Q1: Success rating (X, 0-10)
    q1_txt = "In this block, and based on your own personal best, how successfully did you follow the instruction?"
    responses["T1"]["success_rating"] = ask_question_for_time_half_pheno(q1_txt, "T1", ask_success_rating_with_slider_pheno)
    responses["T2"]["success_rating"] = ask_question_for_time_half_pheno(q1_txt, "T2", ask_success_rating_with_slider_pheno)

    # Q2: Nature of Mind recognition (X, 0-4)
    q2_txt = "Did you experience any moments you would describe as recognizing the nature of mind?"
    responses["T1"]["nom_recognition"] = ask_question_for_time_half_pheno(q2_txt, "T1", ask_nom_recognition_vertical_pheno)
    responses["T2"]["nom_recognition"] = ask_question_for_time_half_pheno(q2_txt, "T2", ask_nom_recognition_vertical_pheno)

    # Q3: Confidence in NOM rating (only if NOM = 1, 2, 3, or 4)
    q3_txt = "How confident are you about your rating?"
    q3_options = ["X", "1", "2", "3"]
    q3_labels = ["I do not recall", "not confident", "a little confident", "confident"]
    responses["T1"]["nom_confidence"] = ""
    responses["T2"]["nom_confidence"] = ""
    for time_half in ("T1", "T2"):
        if responses[time_half]["nom_recognition"] not in ["0", "X"]:
            responses[time_half]["nom_confidence"] = ask_question_for_time_half_pheno(
                q3_txt, time_half, ask_scale_vertical_pheno, q3_options, q3_labels, 1)

    # Q4: Near vs. far difference
    q4_txt = "Was there a difference between near sounds and distant sounds?"
    q4_options = ["0", "1"]
    q4_labels = ["No", "Yes"]
    responses["T1"]["near_far_difference"] = ask_question_for_time_half_pheno(
        q4_txt, "T1", ask_scale_vertical_pheno, q4_options, q4_labels, 0)
    responses["T2"]["near_far_difference"] = ask_question_for_time_half_pheno(
        q4_txt, "T2", ask_scale_vertical_pheno, q4_options, q4_labels, 0)

    # Q5: Boundary experience (0-2)
    q5_txt = "To what extent did you experience a boundary between you and the sounds?"
    q5_options = ["0", "1", "2"]
    q5_labels = ["no boundary", "a distance between the perceiving subject and the perceived sound", "a separation between a subject and exterior sounds"]
    responses["T1"]["boundary_experience"] = ask_question_for_time_half_pheno(
        q5_txt, "T1", ask_scale_vertical_pheno, q5_options, q5_labels, 0)
    responses["T2"]["boundary_experience"] = ask_question_for_time_half_pheno(
        q5_txt, "T2", ask_scale_vertical_pheno, q5_options, q5_labels, 0)

    # Q6: Center of consciousness (0-2)
    q6_txt = "Was there a center of consciousness?"
    q6_options = ["0", "1", "2"]
    q6_labels = ["no center", "a subject observing mental phenomena (sounds and vibration)", "a sense of being an agent perceiving exterior stimulations (sounds and vibration)"]
    responses["T1"]["center_of_consciousness"] = ask_question_for_time_half_pheno(
        q6_txt, "T1", ask_scale_vertical_pheno, q6_options, q6_labels, 0, spacing=90)
    responses["T2"]["center_of_consciousness"] = ask_question_for_time_half_pheno(
        q6_txt, "T2", ask_scale_vertical_pheno, q6_options, q6_labels, 0, spacing=90)

    # Q7: Sounds location (X, 1-3)
    q7_txt = "To what extent did you experience sounds as occurring within the mind, or as feeling like they were outside it?"
    q7_options = ["X", "1", "2", "3"]
    q7_labels = [
        "I do not recall anything like this",
        "The sounds seemed to occur within my mind",
        "The sounds seemed to occur outside of my mind",
        "The sounds seemed to occur both within my mind and outside of it",
    ]
    responses["T1"]["sounds_location"] = ask_question_for_time_half_pheno(
        q7_txt, "T1", ask_scale_vertical_pheno, q7_options, q7_labels, 1)
    responses["T2"]["sounds_location"] = ask_question_for_time_half_pheno(
        q7_txt, "T2", ask_scale_vertical_pheno, q7_options, q7_labels, 1)

    # Q8: Sound-observer separation (X, 1-3)
    q8_txt = "To what extent did experiences of sounds involve a separation between the sound being heard and an observer (a 'hearer'), as opposed to no separation?"
    q8_options = ["X", "1", "2", "3"]
    q8_labels = [
        'I do not recall anything about this',
        'There was no sense of a sound being heard by an observer who was separate from the sound',
        'There seemed to be an observer separate from the sound, but without a strong sense of separation',
        'There was a clear sense that the sounds were being heard by an observer who was separate from the sounds',
    ]
    responses["T1"]["sound_observer_separation"] = ask_question_for_time_half_pheno(
        q8_txt, "T1", ask_scale_vertical_pheno, q8_options, q8_labels, 1, spacing=100, time_half_y=160)
    responses["T2"]["sound_observer_separation"] = ask_question_for_time_half_pheno(
        q8_txt, "T2", ask_scale_vertical_pheno, q8_options, q8_labels, 1, spacing=100, time_half_y=160)

    # Record in pheno_log_rows
    for time_half in ["T1", "T2"]:
        row = {
            "participant_num": pp_id,
            "group": group,
            "datetime": session_dt,
            "condition_task": recorded_condition,
            "block": block_idx + 1,
            "time_half": time_half,
            "success_rating": responses[time_half]["success_rating"],
            "nom_recognition": responses[time_half]["nom_recognition"],
            "nom_confidence": responses[time_half]["nom_confidence"],
            "near_far_difference": responses[time_half]["near_far_difference"],
            "boundary_experience": responses[time_half]["boundary_experience"],
            "center_of_consciousness": responses[time_half]["center_of_consciousness"],
            "sounds_location": responses[time_half]["sounds_location"],
            "sound_observer_separation": responses[time_half]["sound_observer_separation"],
        }
        pheno_log_rows.append(row)

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
                TEXTS[language]["famil_sound_hint"],
            )
            play_sound_obj(NOISE_RIGHT)
            core.wait(DURATION_AUDIO + 0.2)
            stop_all_sounds()

            show_instruction_space(
                TEXTS[language]["famil_far"],
                TEXTS[language]["famil_sound_hint"],
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
            TEXTS[language]["famil_tactile_hint"],
        )
        send_arduino_ttl()
        core.wait(0.5)

        if not ask_yes_no_question("famil_repeat_question"):
            break

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
# VIGILANCE TASK - COLOR CHANGING CROSS
class VigilanceTaskColorCross:
    def __init__(self, win_):
        self.win = win_
        self.running = False
        self.magenta_count = 0
        self.color_change_count = 0

        self.colors = ["blue", "red", "#FFFF00", "green", "magenta", "cyan","white"]
        self.stable_duration = 6.0
        self.transition_duration = 2.5

        self.phase = "stable"
        self.t_phase_start = 0.0
        self.current_color_idx = random.randint(0, len(self.colors) - 1)
        self.current_color = self.colors[self.current_color_idx]
        self.target_color = self.colors[self.current_color_idx]

        self.fixation_h = visual.Line(win_, start=(-50, 0), end=(50, 0), lineWidth=8, lineColor=self.current_color)
        self.fixation_v = visual.Line(win_, start=(0, -50), end=(0, 50), lineWidth=8, lineColor=self.current_color)

    def hex_to_rgb_normalized(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0 * 2 - 1
        g = int(hex_color[2:4], 16) / 255.0 * 2 - 1
        b = int(hex_color[4:6], 16) / 255.0 * 2 - 1
        return [r, g, b]

    def get_color_rgb(self, color):
        color_map = {
            "blue": [-1, -1, 1],
            "red": [1, -1, -1],
            "green": [-1, 1, -1],
            "yellow": [1, 1, -1],
            "magenta": [1, -1, 1],
            "cyan": [-1, 1, 1],
            "white": [1, 1, 1],
        }
        if color.startswith('#'):
            return self.hex_to_rgb_normalized(color)
        else:
            return color_map[color]

    def interpolate_color(self, color1, color2, t):
        c1 = np.array(self.get_color_rgb(color1), dtype=np.float32)
        c2 = np.array(self.get_color_rgb(color2), dtype=np.float32)
        interpolated = c1 + (c2 - c1) * t
        return tuple(interpolated.tolist())

    def start(self, now):
        self.running = True
        self.magenta_count = 0
        self.color_change_count = 0
        self.phase = "stable"
        self.t_phase_start = now
        self.current_color_idx = 0
        self.current_color = self.colors[0]
        self.target_color = self.colors[0]
        self.color_change_count = 1
        if self.current_color == "magenta":
            self.magenta_count += 1
            send_event("STRAWBERRY_DISPLAY", send_lsl=True, send_ttl=False)

    def stop(self):
        self.running = False

    def update_and_draw(self, now):
        if not self.running:
            draw_fixation_only()
            return

        elapsed = now - self.t_phase_start

        if self.phase == "stable":
            self.current_color = self.colors[self.current_color_idx]
            if elapsed >= self.stable_duration:
                self.phase = "transition"
                self.t_phase_start = now
                self.current_color_idx = (self.current_color_idx + 1) % len(self.colors)
                self.target_color = self.colors[self.current_color_idx]

        elif self.phase == "transition":
            if elapsed >= self.transition_duration:
                self.phase = "stable"
                self.t_phase_start = now
                self.current_color = self.target_color
                self.color_change_count += 1
                if self.target_color == "magenta":
                    self.magenta_count += 1
                    send_event("STRAWBERRY_DISPLAY", send_lsl=True, send_ttl=False)
            else:
                progress = elapsed / self.transition_duration
                prev_color = self.colors[(self.current_color_idx - 1) % len(self.colors)]
                self.current_color = self.interpolate_color(prev_color, self.target_color, progress)

        self.fixation_h.lineColor = self.current_color
        self.fixation_v.lineColor = self.current_color
        self.fixation_h.draw()
        self.fixation_v.draw()

# ============================================================
# MASTER CLOCK
clock = core.Clock()
clock.reset()

def frame_loop_until(t_end, vigilance_task=None, stim_onset=0):
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

def run_rt_trial(condition_trial, trial_idx, block_idx=0):
    """Run one RT trial with keyboard response detection for tactile stimuli."""
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

    # Offset marker
    send_event(condition_trial + "_OFF", send_lsl=True, send_ttl=False)

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
                response_lsl_time = send_lsl_marker(TRIGGER_CODES["RT_RESPONSE"])
                response_detected = True

    response_type = "response" if response_detected else "no_response"

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = response_window_end + isi
    frame_loop_until(trial_end)

    stim_offset_clock = stim_onset + DURATION_AUDIO
    trigger_code_offset = TRIGGER_CODES.get(condition_trial + "_OFF", 0)

    rt_log_rows.append({
        "participant_num": pp_id,
        "group": group,
        "datetime": session_dt,
        "condition_task": condition_task,
        "block": block_idx + 1,
        "trial_index": trial_idx + 1,
        "condition_trial": condition_trial,
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
        "response_type": response_type,
        "reaction_time_sec": round(response_time, 6) if response_time is not None else "",
        "response_absolute_clock": round(stim_onset + response_time, 6) if response_time is not None else "",
        "response_lsl_time": response_lsl_time,
    })

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
    frame_loop_until(stim_offset, vigilance_task=vigilance_task, stim_onset=stim_onset)
    stop_all_sounds()

    # Offset marker
    send_event(condition_trial + "_OFF", send_lsl=True, send_ttl=False)

    # Inter-stimulus interval
    isi = random.choice(ISI_VALUES_PPS)
    trial_end = stim_offset + isi
    frame_loop_until(trial_end, vigilance_task=vigilance_task, stim_onset=stim_onset)

    stim_offset_clock = stim_onset + DURATION_AUDIO
    trigger_code_offset = TRIGGER_CODES.get(condition_trial + "_OFF", 0)

    trial_log_rows.append({
        "participant_num": pp_id,
        "group": group,
        "datetime": session_dt,
        "condition_task": condition_task,
        "block": block_idx + 1,
        "trial_index": trial_idx + 1,
        "condition_trial": condition_trial,
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
    })

# ============================================================
# BLOCK QUESTION
def ask_strawberry_question(real_count):
    # Multi-digit input (0-999), press Enter to confirm, Backspace to delete.
    clear_keyboard()
    send_event("STRAWBERRY_QUESTION_START", send_lsl=True, send_ttl=False)

    digit_keys = [str(i) for i in range(10)] + [f"num_{i}" for i in range(10)]
    user_input = ""

    while True:
        check_escape()
        draw_text(TEXTS[language]["question_fraise"], height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 80))
        draw_text(user_input if user_input else "0", height=TEXT_HEIGHT * 0.7, pos=(0, -80))
        win.flip()

        keys = get_keys(digit_keys + ["escape", "return", "backspace"])
        for k in keys:
            name = k.name
            if name == "escape":
                safe_quit()
            elif name == "return":
                if user_input:
                    ans_n = int(user_input)
                    err = abs(ans_n - real_count)
                    send_event("STRAWBERRY_QUESTION_END", send_lsl=True, send_ttl=False)
                    return ans_n, err
            elif name == "backspace":
                user_input = user_input[:-1]
            elif name.isdigit() or name.startswith("num_"):
                digit = name[-1]
                if len(user_input) < 3:
                    user_input += digit

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
# No hint shown (per spec).
group = select_single_key(
    TEXTS[language]["group_heading"],
    valid_keys=["e", "c"],
)
print(f"Group: {group}")

# ============================================================
# CONDITION SELECTION (M = meditation, V = vigilance)
# No hint shown (per spec).
condition_task = select_single_key(
    TEXTS[language]["condition_heading"],
    valid_keys=["m", "v"],
    start_key="CONDITION_SELECT_START",
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
# STIMULUS FAMILIARIZATION
show_stimulus_familiarization()

# ============================================================
# CONDITION ORDER
cond_1 = condition_task
cond_2 = "V" if cond_1 == "M" else "M"

show_instruction_space(
    TEXTS[language]["task_intro_start"],
    TEXTS[language]["intro_hint"],
)

# ============================================================
# SESSION TIMESTAMP (for log filenames)
session_dt = now_str()

# ============================================================
# MAIN LOOP

def show_condition_transition_pause():
    """Shown once, right after Condition 1 ends, transitioning into
    Condition 2."""
    show_instruction_space(
        TEXTS[language]["pause_condition_1"],
        TEXTS[language]["pause_entre_condition_1_hint"],
        start_key="TRANSITION_START", end_key="TRANSITION_END",
    )

def show_pre_rt_pause():
    """Shown once, right after Condition 2 ends, transitioning into the
    RT block."""
    show_instruction_space(
        TEXTS[language]["pause_condition_2"],
        TEXTS[language]["pause_entre_condition_2_hint"],
        start_key="TRANSITION_START", end_key="TRANSITION_END",
    )


def run_condition_task(cond):
    global condition_task, vigilance_task

    condition_task = cond
    print(f"\n=== Starting condition {condition_task} ===")

    vigilance_task = VigilanceTaskColorCross(win) if condition_task == "V" else None
    all_blocks = build_experiment()

    # All conditions start with resting state intro
    show_text_timed(
        TEXTS[language]["resting_state_heading"], seconds=DURATION_RESTING_STATE_MSG,
        height=TEXT_HEIGHT, wrap=TEXT_WRAP,
        start_key="RESTING_STATE_INSTR_START", end_key="RESTING_STATE_INSTR_END",
    )

    # Resting state fixation baseline (2 minutes for all conditions)
    show_baseline(
        DURATION_BASELINE,
        send_markers=True,
        start_key="RESTING_STATE_START",
        end_key="RESTING_STATE_END",
    )

    # Determine the correct instruction key based on group and condition.
    instruction_key = f"consigne_{group}_{condition_task}"

    consigne_start_key = "CONSIGNE_V_START" if condition_task == "V" else "CONSIGNE_M_START"
    consigne_end_key = "CONSIGNE_V_END" if condition_task == "V" else "CONSIGNE_M_END"

    show_instruction_space(
        TEXTS[language][instruction_key], TEXTS[language]["consigne_hint"],
        start_key=consigne_start_key, end_key=consigne_end_key,
    )

    # Condition-specific preparation
    if condition_task == "M":
        # M condition: prepare meditation → long fixation (8 min) → ready to start
        msg_key = "meditation_prepare" if group == "E" else "meditation_prepare_control"
        show_instruction_space(
            TEXTS[language][msg_key],
            TEXTS[language]["meditation_prepare_hint"],
            start_key="MEDITATION_1_START", end_key="MEDITATION_1_END",
        )

        # Gong sounds at the start of fixation (experts only)
        if group == "E":
            GONG.play()

        # Meditation preparation period (8 min): audio guidance for controls, silent fixation for experts
        if group == "C":
            show_baseline_with_audio(MEDITATION_AUDIO, DURATION_MEDITATION, send_markers=True,
                                     start_key="RESTING_STATE_START", end_key="RESTING_STATE_END")
        else:
            show_baseline(DURATION_MEDITATION, send_markers=True,
                         start_key="RESTING_STATE_START", end_key="RESTING_STATE_END")

        # Gong sounds at the end of fixation (before stimuli begin, experts only)
        if group == "E":
            GONG.play()

        show_text_timed(TEXTS[language]["meditation_start_stimuli"], seconds=5.0, height=TEXT_HEIGHT, wrap=TEXT_WRAP,
                         start_key="MEDITATION_2_START", end_key="MEDITATION_2_END")

    send_event("CONDITION_START", send_lsl=True, send_ttl=False)

    for block_idx, block in enumerate(all_blocks):
        print(f"\nStart block {block_idx + 1}/{NUM_BLOCKS_PPS}")

        # For V condition only: vigilance prompt before each block
        if condition_task == "V":
            show_vigilance_prompt()

        show_baseline(FIXATION_BEFORE_BLOCK, send_markers=True)

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

        # Gong at block end (M condition, experts only)
        if condition_task == "M" and group == "E":
            GONG.play()

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
            "total_fruits": vigilance_task.color_change_count if condition_task == "V" else "",
            "trial_sequence": trial_sequence_str,
            "n_T": counts["T"],
            "n_AN": counts["AN"],
            "n_AF": counts["AF"],
            "n_ANT": counts["ANT"],
            "n_AFT": counts["AFT"],
            "block_duration_sec": round(block_duration, 3),
        }

        # Sequence after each block's trials:
        # end-of-block screen -> (if V) strawberry question + feedback ->
        # iPad phenomenology question -> after every block, including the
        # last. The after_block message + closing fixation, however, ONLY
        # run between blocks (not after the last block of the condition -
        # the condition ends there and transitions straight to the
        # pause_condition_1/2 screen instead).
        show_end_of_block_screen(block_idx)

        if condition_task == "V":
            real = vigilance_task.magenta_count
            ans, err = ask_strawberry_question(real)
            show_feedback(ans, real, err)
            row["response_strawberries"] = ans
            row["real_strawberries"] = real
            row["error"] = err

        block_log_rows.append(row)
        save_logs_now()

        ask_phenomenology_both_halves(block_idx)

        if block_idx < NUM_BLOCKS_PPS - 1:
            show_after_block(condition_task)
            if condition_task == "M" and group == "E":
                core.wait(2.0)
                GONG.play()
            show_baseline(FIXATION_BEFORE_BLOCK, send_markers=True)

    send_event("CONDITION_END", send_lsl=True, send_ttl=False)
    save_logs_now()


NUM_RT_BLOCKS = 3  # 3 blocks x 55 trials = 165 total, 60 ANT + 60 AFT

def build_rt_training_block():
    """Build RT training block: 4T + 4AFT + 4ANT + 2AN + 2AF = 18 trials."""
    trials = []
    trials.extend(["T"] * 4)
    trials.extend(["AFT"] * 4)
    trials.extend(["ANT"] * 4)
    trials.extend(["AN"] * 2)
    trials.extend(["AF"] * 2)
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

    send_event(condition_trial + "_OFF", send_lsl=True, send_ttl=False)

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
                send_lsl_marker(TRIGGER_CODES["RT_RESPONSE"])
                response_detected = True

    if tactile_present:
        if response_detected:
            feedback_txt = TEXTS[language]["rt_feedback_good"]
            feedback_color = "green"
        else:
            feedback_txt = TEXTS[language]["rt_feedback_click"]
            feedback_color = "red"

        clear_keyboard()
        t_end = core.getTime() + 0.4
        while core.getTime() < t_end:
            check_escape()
            draw_text(feedback_txt, height=TEXT_HEIGHT, wrap=TEXT_WRAP, color=feedback_color)
            win.flip()
    elif response_detected:
        feedback_txt = TEXTS[language]["rt_feedback_wrong_click"]
        feedback_color = "red"

        clear_keyboard()
        t_end = core.getTime() + 0.4
        while core.getTime() < t_end:
            check_escape()
            draw_text(feedback_txt, height=TEXT_HEIGHT, wrap=TEXT_WRAP, color=feedback_color)
            win.flip()

    isi = random.choice(ISI_VALUES_PPS)
    trial_end = response_window_end + isi
    frame_loop_until(trial_end)

def run_rt_training_block():
    """Run RT training block with 18 trials and tactile feedback."""
    show_instruction_space(
        TEXTS[language]["rt_training_intro"],
        TEXTS[language]["rt_training_hint"],
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

    show_baseline(FIXATION_BEFORE_BLOCK, send_markers=True)

    training_block = build_rt_training_block()
    print(f"RT training block: running {len(training_block)} trials")

    for trial_idx, cond_trial in enumerate(training_block):
        run_rt_training_trial(condition_trial=cond_trial, trial_idx=trial_idx)

    show_instruction_space(
        TEXTS[language]["rt_training_end"],
        TEXTS[language]["rt_end_hint"],
        height=TEXT_HEIGHT,
        wrap=TEXT_WRAP,
    )

def run_rt_block_task():
    """RT block: always runs last, after both M and V condition blocks and
    the pre-RT pause. Runs RT training block first, then NUM_RT_BLOCKS
    sub-blocks of build_rt_block() trials each."""
    global rt_log_rows, rt_log_path, in_rt_block

    in_rt_block = True

    # Reset logs for RT
    rt_log_rows = []
    rt_log_path = make_rt_log_filename(pp_id, group)
    print("\n=== Starting RT block ===")
    print("RT log:", rt_log_path)

    show_instruction_space(
        TEXTS[language]["rt_block_intro"],
        TEXTS[language]["consigne_hint"],
    )

    run_rt_training_block()

    send_event("RT_BLOCK_START", send_lsl=True, send_ttl=False)
    show_baseline(FIXATION_BEFORE_BLOCK, send_markers=True)

    for rt_block_idx in range(NUM_RT_BLOCKS):
        rt_block = build_rt_block()
        print(f"RT sub-block {rt_block_idx + 1}/{NUM_RT_BLOCKS}: running {len(rt_block)} trials")

        for trial_idx, cond_trial in enumerate(rt_block):
            run_rt_trial(condition_trial=cond_trial, trial_idx=trial_idx, block_idx=rt_block_idx)

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
        )

        ask_phenomenology_both_halves(rt_block_idx)

        if not is_last:
            show_text_timed(
                TEXTS[language]["after_block_rt"],
                seconds=DURATION_AFTER_BLOCK,
                height=TEXT_HEIGHT,
                wrap=TEXT_WRAP,
            )
            show_baseline(FIXATION_BEFORE_BLOCK, send_markers=True)

        save_logs_now()

    in_rt_block = False
    send_event("RT_BLOCK_END", send_lsl=True, send_ttl=False)
    save_logs_now()

try:
    # Initialize session logs (used for both M and V conditions)
    block_log_rows = []
    trial_log_rows = []
    pheno_log_rows = []
    block_log_path = make_block_log_filename(pp_id, group)
    trial_log_path = make_trial_log_filename(pp_id, group)
    pheno_log_path = make_pheno_log_filename(pp_id, group)
    print("\n=== Session logs ===")
    print("Block log:", block_log_path)
    print("Trial log:", trial_log_path)
    print("Phenomenology log:", pheno_log_path)

    # Condition 1 : chosen by experimenter
    cond_1 = condition_task
    cond_2 = "V" if cond_1 == "M" else "M"

    # Resting state is now shown once per condition, inside run_condition_task
    # (see show_resting_state), not once globally here.

    if rt_timing == "before":
        # RT block runs FIRST, before M and V conditions
        run_rt_block_task()

        # Short break before the first M/V condition
        show_condition_transition_pause()

        run_condition_task(cond_1)

        # Short break between the two M/V condition blocks
        show_condition_transition_pause()

        run_condition_task(cond_2)

    else:
        # RT block runs LAST, after both M and V conditions (default)
        run_condition_task(cond_1)

        # Short break between the two M/V condition blocks
        show_condition_transition_pause()

        run_condition_task(cond_2)

        # Short break before the final RT block
        show_pre_rt_pause()

        # RT block runs last: participants are already familiar with
        # the stimuli (familiarization + both M/V blocks), so no separate
        # practice/training phase is needed here.
        run_rt_block_task()

finally:
    save_logs_now()

# ============================================================
# END SCREEN
send_event("END_SCREEN_START", send_lsl=True, send_ttl=False)
draw_text(TEXTS[language]["end"], height=52, wrap=TEXT_WRAP)
win.flip()
core.wait(DURATION_END)
send_event("END_SCREEN_END", send_lsl=True, send_ttl=False)

print("\nExperiment finished.")
win.close()
core.quit()
