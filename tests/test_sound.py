# uv pip install numpy sounddevice psychopy psychopy-sounddevice
import os
import numpy as np
from psychopy import prefs
from config_local import AUDIO_DEVICE_NAME

prefs.hardware["audioLib"] = ["sounddevice"]
prefs.hardware["audioDevice"] = [AUDIO_DEVICE_NAME]

from psychopy import core, visual, sound
from psychopy.hardware import keyboard
import wave

# ============================================================
# AUDIO PARAMETERS
SAMPLE_RATE = 44100
DURATION_AUDIO = 0.1
TARGET_RMS = 0.08
AUDIO_DIR = "audio_cache"

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

def make_audio_files():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    noise_right_path = os.path.join(AUDIO_DIR, "noise_right.wav")
    noise_left_path = os.path.join(AUDIO_DIR, "noise_left.wav")
    write_wav_file(noise_right_path, generate_white_noise_array(pan="right"))
    write_wav_file(noise_left_path, generate_white_noise_array(pan="left"))
    return noise_right_path, noise_left_path

NOISE_RIGHT_PATH, NOISE_LEFT_PATH = make_audio_files()
NOISE_RIGHT = sound.Sound(NOISE_RIGHT_PATH)
NOISE_LEFT = sound.Sound(NOISE_LEFT_PATH)

# ============================================================
# WINDOW AND INPUT
win = visual.Window(fullscr=True, color="black", units="pix")
kb = keyboard.Keyboard()

# ============================================================
# UTILITIES
def clear_keyboard():
    kb.clearEvents()

def get_keys(key_list=None):
    return kb.getKeys(keyList=key_list)

def draw_text(text, height=32, wrap=900, pos=(0, 0)):
    stim = visual.TextStim(win, text=text, color="white", height=height, wrapWidth=wrap, pos=pos)
    stim.draw()

def stop_all_sounds():
    for s in [NOISE_RIGHT, NOISE_LEFT]:
        try:
            s.stop()
        except Exception:
            pass

def safe_quit():
    try:
        stop_all_sounds()
    except Exception:
        pass
    try:
        win.close()
    except Exception:
        pass
    core.quit()

# ============================================================
# MAIN LOOP
clear_keyboard()
while True:
    draw_text("F = Son FAR (loin)\n\nN = Son NEAR (proche)\n\nESC = Quitter", height=40, pos=(0, 0))
    win.flip()
    core.wait(0.01)

    keys = get_keys(["f", "n", "escape"])

    for k in keys:
        if k.name == "escape":
            safe_quit()
        elif k.name == "f":
            stop_all_sounds()
            NOISE_LEFT.stop()
            NOISE_LEFT.play()
            core.wait(DURATION_AUDIO + 0.2)
            NOISE_LEFT.stop()
        elif k.name == "n":
            stop_all_sounds()
            NOISE_RIGHT.stop()
            NOISE_RIGHT.play()
            core.wait(DURATION_AUDIO + 0.2)
            NOISE_RIGHT.stop()
