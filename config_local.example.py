# Machine-specific settings for pps-task.py.
#
# Copy this file to "config_local.py" (same folder) and fill in the values
# for the computer you are running the task on. "config_local.py" is
# git-ignored on purpose: each machine (your laptop, the lab PC...) can have
# its own audio device name and COM port without touching the shared code.

# Exact name of the sound output device to use for PsychoPy/sounddevice.
# On Windows: Settings > System > Sound > Output, or run this in a Python
# console to list all available device names:
#   import sounddevice; print(sounddevice.query_devices())
AUDIO_DEVICE_NAME = "sortie_pps (Realtek(R) Audio)"

# COM port of the MMBT-S / Digitimer tactile stimulator.
# On Windows: Device Manager > Ports (COM & LPT).
MMBT_PORT = "COM3"
