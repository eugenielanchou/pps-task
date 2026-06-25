"""
Real-time EEG electrode impedance visualization.
Connects to gNEEDaccess and displays impedances as a topographic map.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import Normalize, LinearSegmentedColormap
from pathlib import Path
import time

# Try to import pygds (gNEEDaccess Python API)
try:
    sys.path.insert(0, str(Path.home() / "Documents" / "gtec" / "gNEEDaccessClientAPI" / "Python"))
    import pygds
    HAS_PYGDS = True
except ImportError:
    HAS_PYGDS = False
    print("Warning: pygds not available. Using demo mode with dummy impedances.")


# Standard 10-20 system electrode positions (normalized to -1 to 1 range)
ELECTRODE_POSITIONS_10_20 = {
    # Frontal (Fp, F)
    'Fp1': (-0.5, 0.95), 'Fp2': (0.5, 0.95),
    'F7': (-0.95, 0.65), 'F3': (-0.6, 0.8), 'Fz': (0.0, 0.85), 'F4': (0.6, 0.8), 'F8': (0.95, 0.65),

    # Central (C)
    'T3': (-1.0, 0.3), 'C3': (-0.8, 0.5), 'Cz': (0.0, 0.55), 'C4': (0.8, 0.5), 'T4': (1.0, 0.3),

    # Parietal (P)
    'T5': (-1.0, -0.3), 'P3': (-0.8, -0.5), 'Pz': (0.0, -0.55), 'P4': (0.8, -0.5), 'T6': (1.0, -0.3),

    # Occipital (O)
    'O1': (-0.5, -0.95), 'O2': (0.5, -0.95),

    # Extended 10-20 (intermediate)
    'AF7': (-0.7, 0.85), 'AF3': (-0.35, 0.88), 'AFz': (0.0, 0.9), 'AF4': (0.35, 0.88), 'AF8': (0.7, 0.85),
    'F5': (-0.77, 0.72), 'F1': (-0.3, 0.83), 'F2': (0.3, 0.83), 'F6': (0.77, 0.72),
    'FC5': (-0.9, 0.58), 'FC1': (-0.4, 0.68), 'FC2': (0.4, 0.68), 'FC6': (0.9, 0.58),
    'C5': (-0.92, 0.4), 'C1': (-0.4, 0.55), 'C2': (0.4, 0.55), 'C6': (0.92, 0.4),
    'CP5': (-0.9, 0.22), 'CP1': (-0.4, 0.38), 'CP2': (0.4, 0.38), 'CP6': (0.9, 0.22),
    'P5': (-0.77, -0.28), 'P1': (-0.3, -0.5), 'P2': (0.3, -0.5), 'P6': (0.77, -0.28),
    'PO7': (-0.6, -0.75), 'PO3': (-0.35, -0.82), 'POz': (0.0, -0.85), 'PO4': (0.35, -0.82), 'PO8': (0.6, -0.75),
    'TP7': (-0.95, 0.0), 'TP8': (0.95, 0.0),
    'FT7': (-0.97, 0.48), 'FT8': (0.97, 0.48),
    'T7': (-1.0, 0.15), 'T8': (1.0, 0.15),
    'P7': (-0.95, -0.45), 'P8': (0.95, -0.45),
    'Oz': (0.0, -1.0),

    # Reference/ground (typically not displayed, but included for completeness)
    'Ref': (0.0, -1.2), 'Gnd': (0.0, -1.3),
}

# Map typical channel names to 10-20 positions
CHANNEL_TO_ELECTRODE = {
    'AF7': 'AF7', 'AF3': 'AF3', 'AFz': 'AFz', 'AF4': 'AF4', 'AF8': 'AF8',
    'F7': 'F7', 'F5': 'F5', 'F3': 'F3', 'F1': 'F1', 'Fz': 'Fz', 'F2': 'F2', 'F4': 'F4', 'F6': 'F6', 'F8': 'F8',
    'FT7': 'FT7', 'FC5': 'FC5', 'FC1': 'FC1', 'FC2': 'FC2', 'FC6': 'FC6', 'FT8': 'FT8',
    'T7': 'T7', 'C5': 'C5', 'C3': 'C3', 'C1': 'C1', 'Cz': 'Cz', 'C2': 'C2', 'C4': 'C4', 'C6': 'C6', 'T8': 'T8',
    'TP7': 'TP7', 'CP5': 'CP5', 'CP1': 'CP1', 'CP2': 'CP2', 'CP6': 'CP6', 'TP8': 'TP8',
    'P7': 'P7', 'P5': 'P5', 'P3': 'P3', 'P1': 'P1', 'Pz': 'Pz', 'P2': 'P2', 'P4': 'P4', 'P6': 'P6', 'P8': 'P8',
    'PO7': 'PO7', 'PO3': 'PO3', 'POz': 'POz', 'PO4': 'PO4', 'PO8': 'PO8',
    'O1': 'O1', 'Oz': 'Oz', 'O2': 'O2',
}


def impedance_to_color(impedance, threshold_good=50000, threshold_bad=100000):
    """
    Convert impedance value (in ohms) to a color.
    Green (< 50k ohms) -> Yellow -> Red (> 100k ohms)
    """
    if impedance < threshold_good:
        return np.array([0, 1, 0])  # Green
    elif impedance < threshold_bad:
        ratio = (impedance - threshold_good) / (threshold_bad - threshold_good)
        return np.array([ratio, 1 - ratio * 0.5, 0])  # Green to yellow to orange
    else:
        return np.array([1, 0, 0])  # Red


def draw_head(ax):
    """Draw head outline for EEG topography."""
    # Head circle
    head = patches.Circle((0, 0), 1.0, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(head)

    # Nose
    nose_x = [0, -0.1, 0.1, 0]
    nose_y = [1.05, 0.95, 0.95, 1.05]
    ax.plot(nose_x, nose_y, 'k-', linewidth=2)

    # Ears
    left_ear = patches.Wedge((-1.1, 0), 0.15, 45, 315, fill=False, edgecolor='black', linewidth=1.5)
    right_ear = patches.Wedge((1.1, 0), 0.15, 225, 135, fill=False, edgecolor='black', linewidth=1.5)
    ax.add_patch(left_ear)
    ax.add_patch(right_ear)


def plot_impedances(impedance_dict, title="EEG Electrode Impedances", figsize=(12, 10)):
    """
    Plot impedances as a topographic map.

    Args:
        impedance_dict: Dictionary {channel_name: impedance_value_in_ohms}
        title: Plot title
        figsize: Figure size
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Draw head
    draw_head(ax)

    # Plot electrodes
    for channel, impedance in impedance_dict.items():
        electrode = CHANNEL_TO_ELECTRODE.get(channel, channel)

        if electrode in ELECTRODE_POSITIONS_10_20:
            x, y = ELECTRODE_POSITIONS_10_20[electrode]
            color = impedance_to_color(impedance)

            # Draw electrode circle
            circle = patches.Circle((x, y), 0.08, color=color, ec='black', linewidth=1.5, zorder=10)
            ax.add_patch(circle)

            # Add label
            ax.text(x, y, channel, ha='center', va='center', fontsize=7, weight='bold', zorder=11)

    # Set axis properties
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)

    # Add legend
    legend_elements = [
        patches.Patch(facecolor='green', edgecolor='black', label='< 50 kΩ (Good)'),
        patches.Patch(facecolor='yellow', edgecolor='black', label='50-100 kΩ (Fair)'),
        patches.Patch(facecolor='red', edgecolor='black', label='> 100 kΩ (Poor)'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

    return fig, ax


def get_impedances_from_gneedaccess():
    """
    Try to connect to gNEEDaccess and retrieve impedances.
    Returns dict {channel: impedance_in_ohms}.
    """
    if not HAS_PYGDS:
        return None

    try:
        # Initialize client
        client = pygds.GDSClient()

        # Connect to gNEEDaccess server (default localhost)
        if not client.connect("127.0.0.1", 50223, 50224):
            print("Could not connect to gNEEDaccess server.")
            return None

        # Get device list
        devices = client.get_device_list()
        if not devices:
            print("No devices found in gNEEDaccess.")
            return None

        device = devices[0]  # Use first device

        # Get impedances
        impedances = {}
        for i, channel_info in enumerate(device.channels):
            channel_name = channel_info.label
            impedance = channel_info.impedance  # Should be in ohms
            impedances[channel_name] = impedance

        client.disconnect()
        return impedances

    except Exception as e:
        print(f"Error connecting to gNEEDaccess: {e}")
        return None


def get_dummy_impedances():
    """Generate dummy impedances for testing."""
    dummy_data = {}
    for channel in CHANNEL_TO_ELECTRODE.keys():
        # Random impedances: mostly good (green), some fair (yellow), few bad (red)
        rand = np.random.random()
        if rand < 0.7:
            impedance = np.random.uniform(10000, 40000)
        elif rand < 0.9:
            impedance = np.random.uniform(60000, 90000)
        else:
            impedance = np.random.uniform(110000, 200000)
        dummy_data[channel] = impedance
    return dummy_data


def main():
    """Main loop: update impedances and refresh plot."""
    print("Starting EEG Electrode Impedance Viewer...")
    print("Attempting to connect to gNEEDaccess...")

    fig = None

    while True:
        # Try to get real impedances first
        impedances = get_impedances_from_gneedaccess()

        # Fall back to dummy data if not available
        if impedances is None:
            print("Using demo mode (random impedances)...")
            impedances = get_dummy_impedances()

        # Clear previous figure
        if fig is not None:
            plt.close(fig)

        # Plot
        fig, ax = plot_impedances(impedances,
                                  title="EEG Electrode Impedances (Real-time)")
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(0.1)

        # Print summary
        good = sum(1 for z in impedances.values() if z < 50000)
        fair = sum(1 for z in impedances.values() if 50000 <= z < 100000)
        poor = sum(1 for z in impedances.values() if z >= 100000)
        print(f"Status: {good} Good | {fair} Fair | {poor} Poor")

        # Wait before refreshing (5 seconds)
        time.sleep(5)


if __name__ == "__main__":
    main()
