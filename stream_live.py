import sys
from pylsl import resolve_stream, StreamInlet
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import threading

# Configuration
WINDOW_DURATION = 5  # seconds
MAX_BUFFER_SIZE = 5000
UPDATE_INTERVAL = 100  # milliseconds

# Data buffers
eeg_buffer = deque(maxlen=MAX_BUFFER_SIZE)
eeg_times = deque(maxlen=MAX_BUFFER_SIZE)
marker_times = []
marker_values = []
marker_lock = threading.Lock()

eeg_inlet = None
marker_inlet = None
eeg_sfreq = 512

def find_streams():
    global eeg_inlet, marker_inlet, eeg_sfreq

    print("Searching for LSL streams...")
    streams = resolve_stream()

    if len(streams) == 0:
        print("ERROR: No LSL streams found. Start gNEEDaccess and pps-task.py first.")
        return False

    for stream in streams:
        name = stream.name()
        print(f"Found stream: {name}")

        if "HA-2012" in name or "gHIamp" in name or "EEG" in name:
            eeg_inlet = StreamInlet(stream)
            info = eeg_inlet.info()
            eeg_sfreq = int(float(info.nominal_srate()))
            print(f"  -> Using as EEG (sampling rate: {eeg_sfreq} Hz)")

        elif "Markers" in name or "PPS_Markers" in name:
            marker_inlet = StreamInlet(stream)
            print(f"  -> Using as Markers")

    if eeg_inlet is None:
        print("ERROR: EEG stream not found")
        return False

    return True

def read_eeg_stream():
    while True:
        if eeg_inlet is None:
            break

        sample, timestamp = eeg_inlet.pull_sample(timeout=0.0)
        if sample:
            eeg_buffer.append(sample)
            eeg_times.append(timestamp)

def read_marker_stream():
    while True:
        if marker_inlet is None:
            break

        sample, timestamp = marker_inlet.pull_sample(timeout=0.0)
        if sample:
            marker_value = int(sample[0])
            with marker_lock:
                marker_times.append(timestamp)
                marker_values.append(marker_value)

def plot_live():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                     gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle('LSL Live EEG Stream', fontsize=14, fontweight='bold')

    lines = [ax1.plot([], [], lw=0.5, alpha=0.7)[0] for _ in range(4)]
    ax1.set_ylim(-200, 200)
    ax1.set_ylabel('Amplitude (uV)')
    ax1.grid(True, alpha=0.3)
    ax1.set_title('EEG Signal (first 4 channels)')

    marker_text = ax2.text(0.05, 0.5, 'Waiting for markers...',
                           fontsize=12, family='monospace')
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    def update(frame):
        if len(eeg_buffer) < 100:
            return lines + [marker_text]

        buffer_array = np.array(list(eeg_buffer))

        for i in range(min(4, buffer_array.shape[1])):
            lines[i].set_data(range(len(buffer_array)), buffer_array[:, i] * 1e6)

        ax1.set_xlim(max(0, len(eeg_buffer) - WINDOW_DURATION * eeg_sfreq),
                     len(eeg_buffer))

        with marker_lock:
            if marker_values:
                marker_info = "Recent markers:\n"
                for i in range(max(0, len(marker_values) - 10), len(marker_values)):
                    marker_info += f"  Code {marker_values[i]} at t={marker_times[i]:.2f}s\n"
                marker_text.set_text(marker_info)

        return lines + [marker_text]

    ani = FuncAnimation(fig, update, interval=UPDATE_INTERVAL, blit=True, cache_frame_data=False)
    plt.show()

if __name__ == "__main__":
    if not find_streams():
        sys.exit(1)

    print("\nStarting EEG stream threads...")
    eeg_thread = threading.Thread(target=read_eeg_stream, daemon=True)
    marker_thread = threading.Thread(target=read_marker_stream, daemon=True)

    eeg_thread.start()
    marker_thread.start()

    print("EEG stream listening active. Plotting in 2 seconds...\n")
    import time
    time.sleep(2)

    plot_live()
