import random
from psychopy import visual, core, event
import numpy as np

# Setup window
win = visual.Window(
    size=(1200, 800),
    units='pix',
    color=[-1, -1, -1],  # black background
    fullscr=False
)

# Fixation cross
fixation = visual.TextStim(
    win,
    text='+',
    font='Arial',
    height=80,
    color=[1, 1, 1],  # start white
    bold=True
)

# Color sequence (RGB, PsychoPy scale: -1 to 1)
colors_sequence = [
    [1, 1, 1],        # white
    [0.5, 0.5, 0.5],  # gray
    [-1, -1, 1],      # blue
    [-1, 1, -1],      # green
    [1, -1, -1],      # red
]

# Randomize order
random.shuffle(colors_sequence)
print(f"Color sequence: {colors_sequence}")

# Parameters
transition_duration = 2.0  # seconds per color transition
frame_rate = 60
transition_frames = int(transition_duration * frame_rate)
total_cycles = 3  # how many times to cycle through all colors

clock = core.Clock()
frame_count = 0
max_frames = len(colors_sequence) * transition_frames * total_cycles

print(f"Running for {max_frames} frames (~{max_frames/frame_rate:.1f} seconds)")
print("Press ESC to exit early")

# Main loop
while frame_count < max_frames:
    # Check for exit
    keys = event.getKeys(keyList=['escape'])
    if keys:
        break

    # Calculate which color we're transitioning to
    color_index = (frame_count // transition_frames) % len(colors_sequence)
    progress = (frame_count % transition_frames) / transition_frames

    # Get current and next colors
    current_color = colors_sequence[color_index]
    next_color = colors_sequence[(color_index + 1) % len(colors_sequence)]

    # Interpolate between colors
    interpolated_color = [
        current_color[i] + (next_color[i] - current_color[i]) * progress
        for i in range(3)
    ]

    # Clamp to valid range
    interpolated_color = [np.clip(c, -1, 1) for c in interpolated_color]

    # Update and draw
    fixation.color = interpolated_color
    fixation.draw()

    # Display info
    info_text = visual.TextStim(
        win,
        text=f"Frame: {frame_count} | Color: {color_index} | Progress: {progress:.2f}",
        font='Arial',
        height=20,
        color=[0.5, 0.5, 0.5],
        pos=(0, -350)
    )
    info_text.draw()

    win.flip()
    frame_count += 1

print(f"Finished after {frame_count} frames")
win.close()
core.quit()
