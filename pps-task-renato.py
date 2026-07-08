from psychopy import prefs
import os
import csv
import random
from datetime import datetime
import wave
import numpy as np
import serial
from pylsl import StreamInfo, StreamOutlet, local_clock
import sys 
from config_local import AUDIO_DEVICE_NAME, MMBT_PORT

# ============================================================
# PSYCHOPY AUDIO BACKEND
prefs.hardware["audioLib"] = ["sounddevice"]
prefs.hardware["audioDevice"] = [AUDIO_DEVICE_NAME]

from psychopy import core, visual, sound
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
# EXPERIMENT DESIGN
# PPS conditions:
# T   = tactile only
# AN  = auditory near only
# AF  = auditory far only
# ANT = audio + tactile near
# AFT = audio + tactile far
# P3A = oddball tone
NUM_BLOCKS_PPS = 6
TRIALS_PER_CONDITION_PER_BLOCK = 11
PPS_CONDITIONS = ["T", "AN", "AF", "ANT", "AFT"]
EXTRA_CONDITION = "P3A"

# ============================================================
# TIMING PARAMETERS
DURATION_AUDIO = 0.100
DURATION_TACTILE = 0.005
ISI_VALUES_PPS = [2.5, 2.6, 2.7, 2.8, 2.9, 3.0]

DURATION_FRUIT = 3.5
ISI_FRUIT = 0.3

DURATION_END_BLOCK = 1.0
DURATION_AFTER_BREAK = 30.0
DURATION_FEEDBACK = 2.0
DURATION_BASELINE = 5.0
DURATION_BASELINE_BLOCK = 3.0

# ============================================================
# DISPLAY PARAMETERS
TEXT_HEIGHT = 20
TEXT_WRAP = 900

# ============================================================
# AUDIO PARAMETERS
SAMPLE_RATE = 44100
P3A_FREQ = 1000
TARGET_RMS = 0.08

# ============================================================
# ARDUINO TTL SETTINGS
ARDUINO_PORT = "COM5"   # change this
ARDUINO_BAUDRATE = 115200
ARDUINO_PULSE_WIDTH = 0.005
TTL_BYTE = 1
DURATION_MILLISECONDS = 200
INTENSITY = 150

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
}

# ============================================================
# INSTRUCTION TEXTS
TEXTS = {
    "fr": {
        "group": "Groupe : \n\nAppuyez sur E ou C, puis sur la barre d'espace.",
        "participant": "Le numéro du participant :\nAppuyez sur la barre d'espace.",
        "condition": "La condition : \n\nAppuyez sur M ou V, puis sur la barre d'espace",
        "consigne_M": "Vous allez d'abord entendre des audios de méditation.\nVeuillez rester dans cet état tout au long de la séquence.\n\nPendant ce temps, vous entendrez des sons provenant des deux haut-parleurs situés devant vous\net percevrez une légère stimulation au niveau de votre torse.\n\nMerci de rester aussi immobile que possible, en fixant la croix.\n\nQuand vous êtes prêt(e), appuyez sur la barre d'espace pour commencer.",
        "consigne_V": "Vous allez voir des fruits défiler.\nVeuillez compter le nombre de FRAISES.\n\nEn même temps, vous allez entendre des sons depuis les deux haut-parleurs devant vous\net percevoir une petite stimulation au niveau de votre torse.\n\nRestez aussi immobile que possible.\n\nQuand vous êtes prêt(e), appuyez sur la barre d'espace pour commencer.",
        "break": "Fin du bloc {}/{}",
        "question": "Combien de fraises avez-vous vues ?\n\nAppuyez sur la barre d'espace pour valider.",
        "feedback_template": "Vous avez répondu : {ans}\nNombre réel de fraises : {real}\n\nÉcart : {err}",
        "ipad_pheno": "Veuillez prendre l'iPad et répondre à la question dessus.\n\nUne fois terminé, appuyez sur la barre d'espace.",
        "after_break_M": "Prenez quelques secondes pour vous remettre dans l'état de méditation.\n\nL'expérience reprendra bientôt.",
        "after_break_V": "La même tâche va de nouveau vous être présentée.\n\nInstallez-vous, l'expérience reprendra bientôt.",
        "end": "Merci pour votre participation !",
        "lang_select": "Pour avoir les consignes en français, appuyez sur : F\n\nTo have the instructions in English, press: E",
        "transition": "Fin de la condition {}.\n\nLa condition {} va maintenant commencer.\n\nAppuyez sur la barre d'espace quand vous êtes prêt(e).",
    },
    "en": {
        "group": "Group: \n\nPress E or C, then press the space bar.",
        "participant": "Participant number:\nPress the space bar.",
        "condition": "Condition: \n\nPress M or V, then press the space bar.",
        "consigne_M": "You will first hear meditation audio recordings.\nPlease remain in this state throughout the sequence.\n\nDuring this time, you will hear sounds coming from the two loudspeakers in front of you\nand feel a brief stimulation on your chest.\n\nPlease remain as still as possible while fixating the cross.\n\nWhen you are ready, press the space bar to begin.",
        "consigne_V": "You will see fruits appearing on the screen.\nPlease count the number of STRAWBERRIES.\n\nAt the same time, you will hear sounds coming from the two loudspeakers in front of you\nand feel a brief stimulation on your chest.\n\nPlease remain as still as possible.\n\nWhen you are ready, press the space bar to begin.",
        "break": "End of block {}/{}",
        "question": "How many strawberries did you see?\n\nPress the space bar to validate.",
        "feedback_template": "Your answer: {ans}\nReal number of strawberries: {real}\n\nDifference: {err}",
        "ipad_pheno": "Please take the iPad and answer the question.\n\nThen, press the space bar.",
        "after_break_M": "Take a few seconds to return to a meditative state.\n\nThe experiment will resume soon.",
        "after_break_V": "The same task will be presented again.\n\nPlease get settled; the experiment will resume soon.",
        "end": "Thank you for your participation!",
        "lang_select": "Pour avoir les consignes en français, appuyez sur : F\n\nTo have the instructions in English, press: E",
        "transition": "End of the {} condition.\n\nThe {} condition will now begin.\n\nPress the space bar when you are ready.",
    }
}

# ============================================================
# CSV HEADERS
BLOCK_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition", "block",
    "response_strawberries", "real_strawberries", "error", "total_fruits",
    "trial_sequence", "n_T", "n_AN", "n_AF", "n_ANT", "n_AFT", "n_P3A",
    "block_duration_sec",
]

TRIAL_FIELDNAMES = [
    "group", "participant_num", "language", "datetime", "condition",
    "block", "trial_index", "trial_condition",
    "audio_side", "audio_present", "tactile_present",
    "isi_sec", "stim_onset_clock", "trigger_code",
    "lsl_sent", "ttl_sent", "lsl_time", "ttl_on_time", "ttl_off_time",
    "audio_play_call_time",
]

# ============================================================
# GLOBAL STATE VARIABLES
marker_outlet = None
arduino = None
block_log_rows = []
trial_log_rows = []
block_log_path = None
trial_log_path = None
language = ""
group = ""
condition = ""
pp_id = ""
session_dt = ""

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
def setup_lsl():
    global marker_outlet
    if not LSL_AVAILABLE:
        return

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

# ============================================================
# Arduino setup 
def setup_arduino():
    global arduino
    if not ARDUINO_ENABLED or not SERIAL_AVAILABLE:
        print("Arduino TTL disabled.")
    
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
            arduino.write(f"{DURATION_MILLISECONDS},{INTENSITY}\n".encode("utf-8"))
            arduino.flush()
            ttl_off_time = core.getTime()

        except Exception as e:
            print(f"WARNING: failed to send Arduino TTL: {e}")
    return ttl_on_time, ttl_off_time

def send_lsl_marker(code):
    lsl_time = None
    if marker_outlet is not None:
        try:
            lsl_time = local_clock()
            marker_outlet.push_sample([int(code)], lsl_time)
        except Exception as e:
            print(f"WARNING: failed to send LSL marker {code}: {e}")
    return lsl_time

def send_event(code_key, send_lsl=True, send_ttl=False, ttl_code=TTL_BYTE):
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
    write_wav_file(noise_right_path, generate_white_noise_array(pan="right"))
    write_wav_file(noise_left_path, generate_white_noise_array(pan="left"))
    write_wav_file(tone_p3a_path, generate_tone_array())
    return noise_right_path, noise_left_path, tone_p3a_path

NOISE_RIGHT_PATH, NOISE_LEFT_PATH, TONE_P3A_PATH = make_audio_files()
NOISE_RIGHT = sound.Sound(NOISE_RIGHT_PATH)
NOISE_LEFT = sound.Sound(NOISE_LEFT_PATH)
TONE_P3A = sound.Sound(TONE_P3A_PATH)

def play_sound_obj(sound_obj):
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

fixation_h = visual.Line(win, start=(-15, 0), end=(15, 0), lineWidth=3, lineColor="white")
fixation_v = visual.Line(win, start=(0, -15), end=(0, 15), lineWidth=3, lineColor="white")

def clear_keyboard():
    kb.clearEvents()

def get_keys(key_list=None, wait_release=False):
    return kb.getKeys(keyList=key_list, waitRelease=wait_release)

def draw_fixation_only():
    fixation_h.draw()
    fixation_v.draw()

def draw_text(text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 0)):
    stim = visual.TextStim(win, text=text, color="white", height=height, wrapWidth=wrap, pos=pos)
    stim.draw()
    return stim

# ============================================================
# CSV SAVING
def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def make_block_log_filename(pp_id, group, condition):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_cond-{condition}_{timestamp_for_filename()}_blocks.csv"
    )

def make_trial_log_filename(pp_id, group, condition):
    ensure_data_dir()
    return os.path.join(
        DATA_DIR,
        f"sub-{pp_id}_group-{group}_cond-{condition}_{timestamp_for_filename()}_trials.csv"
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
def show_text_space(text, height=TEXT_HEIGHT, wrap=TEXT_WRAP):
    clear_keyboard()
    while True:
        check_escape()
        draw_text(text, height=height, wrap=wrap)
        win.flip()
        keys = get_keys(["space", "escape"])
        if any(k.name == "escape" for k in keys):
            safe_quit()
        if any(k.name == "space" for k in keys):
            break

def show_text_timed(text, seconds, height=TEXT_HEIGHT, wrap=TEXT_WRAP):
    t_end = core.getTime() + seconds
    while core.getTime() < t_end:
        check_escape()
        draw_text(text, height=height, wrap=wrap)
        win.flip()

def show_baseline(seconds, send_markers=False):
    if send_markers:
        send_event("BASELINE_START", send_lsl=True, send_ttl=False)
    t_end = core.getTime() + seconds
    while core.getTime() < t_end:
        check_escape()
        draw_fixation_only()
        win.flip()
    if send_markers:
        send_event("BASELINE_END", send_lsl=True, send_ttl=False)

def show_end_of_block_screen(block_idx):
    txt = TEXTS[language]["break"].format(block_idx + 1, NUM_BLOCKS_PPS)
    show_text_timed(txt, seconds=DURATION_END_BLOCK, height=28, wrap=TEXT_WRAP)

def show_feedback(ans, real, err):
    fb_txt = TEXTS[language]["feedback_template"].format(ans=ans, real=real, err=err)
    show_text_timed(fb_txt, seconds=DURATION_FEEDBACK, height=22, wrap=TEXT_WRAP)

def show_ipad_pheno():
    show_text_space(TEXTS[language]["ipad_pheno"], height=TEXT_HEIGHT, wrap=TEXT_WRAP)

def show_after_break():
    key_name = "after_break_V" if condition == "V" else "after_break_M"
    show_text_timed(TEXTS[language][key_name], seconds=DURATION_AFTER_BREAK, height=TEXT_HEIGHT, wrap=TEXT_WRAP)

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

def collect_numeric_input(prompt_text, max_digits=2):
    typed = ""
    clear_keyboard()
    while True:
        check_escape()
        display_text = typed if typed else "_"
        draw_text(prompt_text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 40))
        draw_text(display_text, height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, -20))
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
                return typed
            elif name == "backspace":
                typed = typed[:-1]
            elif name.isdigit() and len(typed) < max_digits:
                typed += name
            elif name.startswith("num_") and len(typed) < max_digits:
                typed += name[-1]

# ============================================================
# BLOCK RANDOMIZATION
def build_block():
    trials = []
    for cond in PPS_CONDITIONS:
        trials.extend([cond] * TRIALS_PER_CONDITION_PER_BLOCK)

    best_trials = None
    min_consecutive = 999
    for _ in range(500):
        random.shuffle(trials)
        consecutive_count = sum(1 for i in range(1, len(trials)) if trials[i] == trials[i - 1])
        if consecutive_count < min_consecutive:
            min_consecutive = consecutive_count
            best_trials = trials.copy()
        if consecutive_count == 0:
            break

    if min_consecutive > 0:
        print(f"Block has {min_consecutive} consecutive pair(s).")

    p3a_pos = random.randint(20, len(best_trials))
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
        self.image_stims = {p: visual.ImageStim(self.win, image=p, size=(200, 200)) for p in self.stimuli}
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
def describe_trial(condition):
    if condition == "T":
        return False, True, ""
    if condition == "AN":
        return True, False, "right"
    if condition == "AF":
        return True, False, "left"
    if condition == "ANT":
        return True, True, "right"
    if condition == "AFT":
        return True, True, "left"
    if condition == "P3A":
        return True, False, "both"
    raise ValueError(f"Unknown condition: {condition}")

def run_trial(condition, block_idx, trial_idx, vigilance_task=None):
    audio_present, tactile_present, audio_side = describe_trial(condition)
    stim_onset = clock.getTime()

    event_info = {
        "event_code": TRIGGER_CODES.get(condition, 0),
        "local_time": None,
        "lsl_time": None,
        "ttl_on_time": None,
        "ttl_off_time": None,
        "ttl_sent": 0,
        "lsl_sent": 0,
    }

    audio_play_call_time = None

    if condition == "T":
        event_info = send_event(condition, send_lsl=True, send_ttl=True, ttl_code=TTL_BYTE)

    elif condition in ["AN", "AF", "P3A"]:
        event_info = send_event(condition, send_lsl=True, send_ttl=False)
        audio_play_call_time = core.getTime()
        if condition == "AN":
            play_sound_obj(NOISE_RIGHT)
        elif condition == "AF":
            play_sound_obj(NOISE_LEFT)
        elif condition == "P3A":
            play_sound_obj(TONE_P3A)

    elif condition in ["ANT", "AFT"]:
        event_info = send_event(condition, send_lsl=True, send_ttl=True, ttl_code=TTL_BYTE)
        audio_play_call_time = core.getTime()
        if condition == "ANT":
            play_sound_obj(NOISE_RIGHT)
        elif condition == "AFT":
            play_sound_obj(NOISE_LEFT)

    stim_offset = stim_onset + DURATION_AUDIO
    frame_loop_until(stim_offset, vigilance_task=vigilance_task)
    stop_all_sounds()

    send_event(condition + "_OFF", send_lsl=True, send_ttl=False)

    isi = random.choice(ISI_VALUES_PPS)
    trial_end = stim_offset + isi
    frame_loop_until(trial_end, vigilance_task=vigilance_task)

    trial_log_rows.append({
        "participant_num": pp_id,
        "language": language,
        "group": group,
        "datetime": session_dt,
        "condition": condition,
        "block": block_idx + 1,
        "trial_index": trial_idx + 1,
        "trial_condition": condition,
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
    while True:
        check_escape()
        draw_text(TEXTS[language]["question"], height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 40))
        draw_text(typed if typed else "_", height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, -20))
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
                return ans_n, err
            elif name == "backspace":
                typed = typed[:-1]
            elif name.isdigit() and len(typed) < 2:
                typed += name
            elif name.startswith("num_") and len(typed) < 2:
                typed += name[-1]

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
# GROUP SELECTION
draw_text(TEXTS[language]["group"], height=TEXT_HEIGHT, wrap=TEXT_WRAP)
win.flip()
group = collect_single_choice(["e", "c"]).upper()
print(f"Group: {group}")

# ============================================================
# PARTICIPANT INFO
pp_id = collect_numeric_input(TEXTS[language]["participant"], max_digits=2)
print(f"Participant ID: {pp_id}")

while True:
    clear_keyboard()
    draw_text(TEXTS[language]["condition"], height=TEXT_HEIGHT, wrap=TEXT_WRAP, pos=(0, 30))
    draw_text(condition if condition else "_", height=24, wrap=TEXT_WRAP, pos=(0, -120))
    win.flip()
    keys = get_keys(["m", "v", "space", "backspace", "escape"])
    for k in keys:
        if k.name == "escape":
            safe_quit()
        elif k.name == "backspace":
            condition = ""
        elif k.name in ["m", "v"] and condition == "":
            condition = k.name.upper()
        elif k.name == "space" and condition in ["M", "V"]:
            break
    if any(k.name == "space" for k in keys) and condition in ["M", "V"]:
        break

print(f"Condition: {condition}")

# ============================================================
# INITIALIZATION of LOG + LSL + ARDUINO
session_dt = now_str()
block_log_path = make_block_log_filename(pp_id, group, condition)
trial_log_path = make_trial_log_filename(pp_id, group, condition)

print("Block log:", block_log_path)
print("Trial log:", trial_log_path)

setup_lsl()
setup_arduino()

# ============================================================
# BUILD EXPERIMENT
all_blocks = build_experiment()
vigilance_task = VigilanceTaskContinuous(win) if condition == "V" else None

instruction_key = "consigne_V" if condition == "V" else "consigne_M"
show_text_space(TEXTS[language][instruction_key])

send_event("EXP_START", send_lsl=True, send_ttl=False)
show_baseline(DURATION_BASELINE, send_markers=True)

# ============================================================
# MAIN LOOP
condition_labels = {
    "M": {"fr": "méditation", "en": "meditation"},
    "V": {"fr": "vigilance", "en": "vigilance"},
}

def run_condition(cond):
    global block_log_rows, trial_log_rows, block_log_path, trial_log_path
    global condition, vigilance_task

    condition = cond

    block_log_rows = []
    trial_log_rows = []
    block_log_path = make_block_log_filename(pp_id, language, condition)
    trial_log_path = make_trial_log_filename(pp_id, language, condition)
    print(f"\n=== Starting condition {condition} ===")
    print("Block log:", block_log_path)
    print("Trial log:", trial_log_path)

    vigilance_task = VigilanceTaskContinuous(win) if condition == "V" else None
    all_blocks = build_experiment()

    instruction_key = "consigne_V" if condition == "V" else "consigne_M"
    show_text_space(TEXTS[language][instruction_key])

    send_event("EXP_START", send_lsl=True, send_ttl=False)
    show_baseline(DURATION_BASELINE, send_markers=True)

    for block_idx, block in enumerate(all_blocks):
        print(f"\nStart block {block_idx + 1}/{NUM_BLOCKS_PPS}")
        show_baseline(DURATION_BASELINE_BLOCK, send_markers=True)
        send_event("BLOCK_START", send_lsl=True, send_ttl=False)
        block_t0 = clock.getTime()
        counts = {k: 0 for k in PPS_CONDITIONS + [EXTRA_CONDITION]}

        if condition == "V":
            vigilance_task.start(clock.getTime())

        for trial_idx, cond_trial in enumerate(block):
            counts[cond_trial] += 1
            run_trial(
                condition=cond_trial,
                block_idx=block_idx,
                trial_idx=trial_idx,
                vigilance_task=vigilance_task if condition == "V" else None
            )

        if condition == "V":
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
            "condition": condition,
            "block": block_idx + 1,
            "response_strawberries": "",
            "real_strawberries": "",
            "error": "",
            "total_fruits": vigilance_task.total_fruit_count if condition == "V" else "",
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

        if condition == "V":
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
    cond_1 = condition
    cond_2 = "V" if cond_1 == "M" else "M"

    run_condition(cond_1)

    label_1 = condition_labels[cond_1][language]
    label_2 = condition_labels[cond_2][language]
    show_text_space(TEXTS[language]["transition"].format(label_1, label_2))

    run_condition(cond_2)

finally:
    save_logs_now()

# ============================================================
# END SCREEN
draw_text(TEXTS[language]["end"], height=24, wrap=TEXT_WRAP)
win.flip()
core.wait(3)

print("\nExperiment finished.")
win.close()
core.quit()