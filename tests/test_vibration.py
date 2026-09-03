# uv pip install pyserial psychopy
import serial
from psychopy import core, visual
from psychopy.hardware import keyboard

# ============================================================
# ARDUINO VIBRATOR SETTINGS
ARDUINO_PORT = "COM5"
ARDUINO_BAUDRATE = 115200
DURATION_MILLISECONDS = 100
INTENSITY = 150

# ============================================================
# GLOBAL STATE
arduino = None

# ============================================================
# ARDUINO SETUP
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
        except Exception:
            pass
        core.wait(0.5)
        print(f"Arduino connected on {ARDUINO_PORT} ({ARDUINO_BAUDRATE} baud)")
        return True
    except Exception as e:
        print(f"ERROR: Could not open Arduino on {ARDUINO_PORT}: {e}")
        return False

def send_arduino_ttl():
    if arduino is not None:
        try:
            arduino.write(f"{DURATION_MILLISECONDS},{INTENSITY}\n".encode("utf-8"))
            arduino.flush()
        except Exception as e:
            print(f"ERROR: failed to send Arduino TTL: {e}")

# ============================================================
# WINDOW AND INPUT
win = visual.Window(fullscr=True, color="black", units="pix")
kb = keyboard.Keyboard()

# ============================================================
# UTILITIES
def get_keys(key_list=None):
    return kb.getKeys(keyList=key_list)

def draw_text(text, height=32, wrap=900, pos=(0, 0)):
    stim = visual.TextStim(win, text=text, color="white", height=height, wrapWidth=wrap, pos=pos)
    stim.draw()

def safe_quit():
    try:
        if arduino is not None:
            arduino.close()
    except Exception as e:
        print(f"Error while closing Arduino: {e}")

    try:
        win.close()
    except Exception:
        pass
    core.quit()

# ============================================================
# MAIN LOOP
if not setup_arduino():
    safe_quit()

kb.clearEvents()
while True:
    draw_text("Appuyez sur V pour recevoir la vibration\n\nESC = Quitter", height=40, pos=(0, 0))
    win.flip()
    core.wait(0.01)

    keys = get_keys(["v", "escape"])

    for k in keys:
        if k.name == "escape":
            safe_quit()
        elif k.name == "v":
            send_arduino_ttl()
            core.wait(0.5)
