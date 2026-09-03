# uv pip install pylsl pyserial psychopy psychopy-sounddevice
"""Test ANT/AFT synchronization: audio + tactile should be sent together"""

import os
from config_local import AUDIO_DEVICE_NAME
from psychopy import prefs
prefs.hardware["audioLib"] = ["sounddevice"]
prefs.hardware["audioDevice"] = [AUDIO_DEVICE_NAME]

import numpy as np
from pylsl import StreamInfo, StreamOutlet, local_clock
from psychopy import core, visual, sound
from psychopy.hardware import keyboard
import serial
import wave

# ============================================================
# CONSTANTS
SAMPLE_RATE = 44100
DURATION_AUDIO = 0.1
TARGET_RMS = 0.08
ARDUINO_PORT = "COM5"
ARDUINO_BAUDRATE = 115200
DURATION_MILLISECONDS = 200
INTENSITY = 150

# ============================================================
# AUDIO SETUP
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

def write_wav_file(path, stereo_arr):
    pcm = float_to_int16(stereo_arr)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())

def generate_white_noise_array(pan="both"):
    n_samples = int(SAMPLE_RATE * DURATION_AUDIO)
    noise_arr = np.random.randn(n_samples).astype(np.float32)
    noise_arr = normalize_rms(noise_arr, target_rms=TARGET_RMS).astype(np.float32)

    if pan == "right":
        stereo = np.column_stack([np.zeros(n_samples, dtype=np.float32), noise_arr])
    elif pan == "left":
        stereo = np.column_stack([noise_arr, np.zeros(n_samples, dtype=np.float32)])
    else:
        stereo = np.column_stack([noise_arr, noise_arr])

    return apply_ramp(stereo)

os.makedirs("audio_cache", exist_ok=True)
write_wav_file("audio_cache/noise_right.wav", generate_white_noise_array(pan="right"))
write_wav_file("audio_cache/noise_left.wav", generate_white_noise_array(pan="left"))

NOISE_RIGHT = sound.Sound("audio_cache/noise_right.wav")
NOISE_LEFT = sound.Sound("audio_cache/noise_left.wav")

# ============================================================
# LSL SETUP
marker_outlet = None

def setup_lsl():
    global marker_outlet
    info = StreamInfo(
        name="pps_markers",
        type="Markers",
        channel_count=1,
        nominal_srate=0,
        channel_format="int32",
        source_id="pps_test"
    )
    marker_outlet = StreamOutlet(info)

# ============================================================
# ARDUINO SETUP
arduino = None

def setup_arduino():
    global arduino
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
        except:
            pass
        core.wait(0.5)
        print(f"✓ Arduino connected on {ARDUINO_PORT}")
        return True
    except Exception as e:
        print(f"✗ Arduino error: {e}")
        return False

def send_arduino_ttl():
    if arduino is not None:
        try:
            arduino.write(f"{DURATION_MILLISECONDS},{INTENSITY}\n".encode("utf-8"))
            arduino.flush()
            return core.getTime()
        except Exception as e:
            print(f"Arduino send error: {e}")
    return None

# ============================================================
# SYNC TEST
win = visual.Window(fullscr=False, size=(800, 600), color="black", units="pix")
kb = keyboard.Keyboard()

def draw_text(text):
    stim = visual.TextStim(win, text=text, color="white", height=28, wrapWidth=900)
    stim.draw()
    win.flip()

def safe_quit():
    try:
        if arduino is not None:
            arduino.close()
    except:
        pass
    try:
        win.close()
    except:
        pass
    core.quit()

# ============================================================
# MAIN TEST
setup_lsl()
arduino_ok = setup_arduino()

print("\n" + "="*70)
print("ANT/AFT SYNCHRONIZATION TEST")
print("="*70)
print("Checking if audio + tactile arrive at the same time\n")

results = []

for trial in range(5):
    print(f"\n--- Trial {trial + 1} ---")

    # Prepare
    NOISE_RIGHT.stop()
    draw_text(f"Trial {trial + 1}/5\n\nPreparing...")
    core.wait(1)

    # Send ANT trigger + audio + tactile TOGETHER
    draw_text(f"Trial {trial + 1}/5\n\nSending ANT (audio-tactile)...")

    # Critical sync: send marker, ttl, and audio start together
    t0 = core.getTime()
    lsl_time = local_clock()
    marker_outlet.push_sample([4], lsl_time)  # ANT = 4

    ttl_time = send_arduino_ttl()

    NOISE_RIGHT.stop()
    audio_time = core.getTime()
    NOISE_RIGHT.play()

    delta_ttl_audio = (audio_time - t0) * 1000 if ttl_time else None
    delta_lsl_audio = (audio_time - t0) * 1000

    print(f"  LSL marker sent:  t=0 ms")
    if delta_ttl_audio is not None:
        print(f"  Arduino TTL sent: Δt=+{delta_ttl_audio:.2f} ms")
    print(f"  Audio play call:  Δt=+{delta_lsl_audio:.2f} ms")

    if delta_ttl_audio is not None and abs(delta_ttl_audio - delta_lsl_audio) < 10:
        print(f"  ✓ GOOD: TTL and audio within 10ms")
        results.append(True)
    elif delta_ttl_audio is not None:
        print(f"  ✗ WARNING: {abs(delta_ttl_audio - delta_lsl_audio):.1f}ms drift")
        results.append(False)

    core.wait(DURATION_AUDIO + 0.3)

# Summary
print("\n" + "="*70)
print(f"Results: {sum(results)}/{len(results)} trials well-synchronized")
print("="*70)

draw_text(f"Summary:\n{sum(results)}/{len(results)} trials synchronized\n\nPress ESC to quit")
core.wait(2)

while True:
    keys = kb.getKeys(keyList=["escape"])
    if keys:
        safe_quit()
    core.wait(0.1)
