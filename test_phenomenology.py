"""
Standalone test for phenomenology questions.
Run this to quickly test and iterate on the questions.
"""

from psychopy import prefs

prefs.hardware["audioLib"] = ["sounddevice", "pyo", "pygame"]

from psychopy import core, visual
from psychopy.hardware import keyboard

# ============================================================
# LAYOUT CONSTANTS (single source of truth for sizing/spacing)
# ============================================================

# --- Font sizes ---
FONT_QUESTION = 56
FONT_TIME_HALF = 44
FONT_INSTRUCTION = 54
FONT_OPTION = 44
FONT_LABEL = 40
FONT_HINT = 36
FONT_X_NOTE = 28

TEXT_WRAP = 1400

# --- Fixed vertical anchors (same for every question type) ---
POS_Y_QUESTION = 300
POS_Y_TIME_HALF = 180   # more breathing room under the question
POS_Y_HINT = -340        # hint pushed further down

# --- Vertical scale layout ---
V_SCALE_X = -520               # numbers pinned near the left edge
V_SCALE_LABEL_OFFSET_X = 720   # label starts just to the right of the number
V_SCALE_LABEL_WRAP = 1300      # narrower wrap so long labels don't run off-screen
V_SCALE_SPACING = 68           # spacing between options/labels
V_SCALE_TOP_FIXED_Y = 90       # more breathing room under the T1/T2 indicator (NOM Q2)
V_SCALE_CENTER_Y = -80  # vertical center for scale options (pushed lower)

# --- Horizontal scale layout (success rating) ---
H_SCALE_Y = 0
H_SCALE_SPACING = 85
H_SCALE_START_X = -550
H_SCALE_LABEL_OFFSET_Y = 70

# --- Selection box ---
BOX_W = 90
BOX_H = 80
BOX_LINE_WIDTH = 2

# --- Colors ---
COLOR_DEFAULT = "white"
COLOR_SELECTED = "yellow"

# ============================================================
# SETUP
# ============================================================
win = visual.Window(fullscr=True, color="black", units="pix", screen=1)
kb = keyboard.Keyboard()


# ============================================================
# LOW-LEVEL HELPERS
# ============================================================
def clear_keyboard():
    kb.clearEvents()


def get_keys(key_list=None, wait_release=False):
    return kb.getKeys(keyList=key_list, waitRelease=wait_release)


def check_escape():
    keys = get_keys(["escape"])
    if any(k.name == "escape" for k in keys):
        win.close()
        core.quit()


def draw_text(text, height=FONT_QUESTION, wrap=TEXT_WRAP, pos=(0, 0),
              italic=False, color=COLOR_DEFAULT, align_text="center", bold=False):
    stim = visual.TextStim(win, text=text, color=color, height=height, wrapWidth=wrap,
                            pos=pos, italic=italic, bold=bold, alignText=align_text)
    stim.draw()
    return stim


def draw_hint(text, pos=(0, POS_Y_HINT)):
    draw_text(text, height=FONT_HINT, wrap=TEXT_WRAP, pos=pos, italic=True)


def draw_question_block(question_text, time_half=None, time_half_y=None):
    """Draw the question and, if provided, the T1/T2 indicator - always at the same anchors."""
    if time_half_y is None:
        time_half_y = POS_Y_TIME_HALF
    draw_text(question_text, height=FONT_QUESTION, wrap=TEXT_WRAP, pos=(0, POS_Y_QUESTION))
    if time_half:
        label = "T1 (first half of the block)" if time_half == "T1" else "T2 (second half of the block)"
        draw_text(f"Respond for {label}", height=FONT_TIME_HALF, wrap=TEXT_WRAP,
                   pos=(0, time_half_y), color=COLOR_SELECTED, bold=True)


def draw_selection_box(pos):
    rect = visual.Rect(win, width=BOX_W, height=BOX_H, pos=pos,
                        fillColor=None, lineColor=COLOR_SELECTED, lineWidth=BOX_LINE_WIDTH)
    rect.draw()


# ============================================================
# QUESTION FUNCTIONS
# ============================================================
def ask_ordinal_question(question_text, min_val, max_val, allow_x=False):
    """Collect ordinal response (e.g., 0-4 or 1-3). If allow_x=True, participant can press 'X'."""
    clear_keyboard()
    valid_keys = [str(i) for i in range(min_val, max_val + 1)]
    if allow_x:
        valid_keys.append("x")

    while True:
        check_escape()
        draw_question_block(question_text)
        hint_txt = f"Press {min_val}-{max_val}" + (" or X" if allow_x else "")
        draw_hint(hint_txt)
        win.flip()

        for k in get_keys(valid_keys + ["escape"]):
            if k.name == "escape":
                win.close()
                core.quit()
            elif k.name in valid_keys:
                return k.name.upper()


def ask_yes_no_simple(question_text):
    """Collect yes/no response (Y/N)."""
    clear_keyboard()
    valid_keys = ["y", "n"]

    while True:
        check_escape()
        draw_question_block(question_text)
        draw_hint("Press Y or N")
        win.flip()

        for k in get_keys(valid_keys + ["escape"]):
            if k.name == "escape":
                win.close()
                core.quit()
            elif k.name in valid_keys:
                return k.name.upper()


def ask_scale_vertical(question_text, scale_options, scale_labels, start_idx=1,
                        time_half=None, fixed_top_y=None, spacing=None, time_half_y=None):
    """
    Display a vertical scale with options and labels.
    User navigates with UP/DOWN arrows and confirms with SPACE.

    fixed_top_y: if given, the scale starts at that fixed Y (used when a time_half
    indicator is shown above it, e.g. NOM recognition). Otherwise the scale is
    centered on V_SCALE_CENTER_Y, the midpoint between the question and the hint,
    so numbers and labels sit evenly spaced between the two.

    spacing: vertical spacing between options. Defaults to V_SCALE_SPACING.
    """
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
        draw_question_block(question_text, time_half=time_half, time_half_y=time_half_y)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            y_pos = start_y - idx * spacing
            color = COLOR_SELECTED if idx == selected_idx else COLOR_DEFAULT

            if idx == selected_idx:
                draw_selection_box((V_SCALE_X, y_pos))

            draw_text(option, height=FONT_OPTION, pos=(V_SCALE_X, y_pos), color=color)
            if label:
                draw_text(label, height=FONT_LABEL, wrap=V_SCALE_LABEL_WRAP,
                           pos=(V_SCALE_X + V_SCALE_LABEL_OFFSET_X, y_pos),
                           color=color, align_text="left")

        win.flip()

        for k in get_keys(["up", "down", "space", "escape"]):
            if k.name == "escape":
                win.close()
                core.quit()
            elif k.name == "up" and selected_idx > 0:
                selected_idx -= 1
            elif k.name == "down" and selected_idx < len(scale_options) - 1:
                selected_idx += 1
            elif k.name == "space":
                return scale_options[selected_idx]


def ask_nom_recognition_vertical(question_text, time_half=None):
    """NOM recognition scale (X, 0-4), vertical layout. Thin wrapper around ask_scale_vertical
    with a fixed top anchor, since this question is always shown together with a time_half label."""
    scale_options = ["X", "0", "1", "2", "3", "4"]
    scale_labels = [
        "I do not recall",
        "no",
        "yes, once",
        "a few times",
        "many times",
        "most of the time",
    ]
    return ask_scale_vertical(question_text, scale_options, scale_labels, start_idx=1,
                               time_half=time_half, fixed_top_y=V_SCALE_TOP_FIXED_Y)


def ask_success_rating_with_slider(question_text, time_half=None):
    """
    Visual scale for success rating (X, 0-10), horizontal layout.
    User navigates with LEFT/RIGHT arrows and confirms with SPACE.
    """
    clear_keyboard()

    scale_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    scale_labels = ["I do not recall", "unsuccessful", "", "", "", "", "", "", "", "", "", "very successful"]
    selected_idx = 1  # Start at 0 (unsuccessful)

    while True:
        check_escape()
        draw_question_block(question_text, time_half=time_half)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            x_pos = H_SCALE_START_X + idx * H_SCALE_SPACING
            color = COLOR_SELECTED if idx == selected_idx else COLOR_DEFAULT

            if idx == selected_idx:
                draw_selection_box((x_pos, H_SCALE_Y))

            draw_text(option, height=FONT_OPTION, pos=(x_pos, H_SCALE_Y), color=color)

            if label and option == "X":
                draw_text(label, height=FONT_X_NOTE, pos=(x_pos, H_SCALE_Y + H_SCALE_LABEL_OFFSET_Y), color=color)
            elif label:
                draw_text(label, height=FONT_X_NOTE, pos=(x_pos, H_SCALE_Y - H_SCALE_LABEL_OFFSET_Y), color=color)

        draw_hint("Use arrows to navigate, SPACE to confirm")
        win.flip()

        for k in get_keys(["left", "right", "space", "escape"]):
            if k.name == "escape":
                win.close()
                core.quit()
            elif k.name == "left" and selected_idx > 0:
                selected_idx -= 1
            elif k.name == "right" and selected_idx < len(scale_options) - 1:
                selected_idx += 1
            elif k.name == "space":
                return scale_options[selected_idx]


def show_general_instruction():
    """Show general instruction at the beginning."""
    general_txt = "Please answer the following questions using the arrow keys."
    clear_keyboard()
    while True:
        check_escape()
        draw_text(general_txt, height=FONT_INSTRUCTION, wrap=TEXT_WRAP, pos=(0, 50))
        draw_hint("Press SPACE to continue")
        win.flip()
        for k in get_keys(["space", "escape"]):
            if k.name == "escape":
                win.close()
                core.quit()
            elif k.name == "space":
                return


def show_time_half_explanation():
    """Explain T1 and T2."""
    explanation_txt = "We will distinguish two moments:\n\nT1 = first half of the block\nT2 = second half of the block"
    clear_keyboard()
    while True:
        check_escape()
        draw_text(explanation_txt, height=FONT_INSTRUCTION, wrap=TEXT_WRAP, pos=(0, 0))
        draw_hint("Press SPACE to continue")
        win.flip()
        for k in get_keys(["space", "escape"]):
            if k.name == "escape":
                win.close()
                core.quit()
            elif k.name == "space":
                return


def ask_question_for_time_half(question_text, time_half, ask_func, *args, **kwargs):
    """Ask question with time half indicator in bold yellow."""
    kwargs['time_half'] = time_half
    return ask_func(question_text, *args, **kwargs)


def ask_phenomenology_both_halves(block_idx):
    """Ask phenomenology questions for both T1 and T2.
    Each question is asked twice (once for T1, once for T2) before moving to the next question."""

    # Show general instruction only on first block
    if block_idx == 0:
        show_general_instruction()
        show_time_half_explanation()

    responses = {"T1": {}, "T2": {}}

    # Q1: Success rating (X, 0-10)
    q1_txt = "In this block, and based on your own personal best, how successfully did you follow the instruction?"
    responses["T1"]["success_rating"] = ask_question_for_time_half(q1_txt, "T1", ask_success_rating_with_slider)
    responses["T2"]["success_rating"] = ask_question_for_time_half(q1_txt, "T2", ask_success_rating_with_slider)

    # Q2: Nature of Mind recognition (X, 0-4)
    q2_txt = "Did you experience any moments you would describe as recognizing the nature of mind?"
    responses["T1"]["nom_recognition"] = ask_question_for_time_half(q2_txt, "T1", ask_nom_recognition_vertical)
    responses["T2"]["nom_recognition"] = ask_question_for_time_half(q2_txt, "T2", ask_nom_recognition_vertical)

    # Q3: Confidence in NOM rating (only if NOM = 1, 2, 3, or 4)
    q3_txt = "How confident are you about your rating?"
    q3_options = ["X", "1", "2", "3"]
    q3_labels = ["I do not recall", "not confident", "a little confident", "confident"]

    responses["T1"]["nom_confidence"] = ""
    responses["T2"]["nom_confidence"] = ""
    for time_half in ("T1", "T2"):
        if responses[time_half]["nom_recognition"] not in ["0", "X"]:
            responses[time_half]["nom_confidence"] = ask_question_for_time_half(
                q3_txt, time_half, ask_scale_vertical, q3_options, q3_labels, 1
            )

    # Q4: Near vs. far difference (Y/N)
    q4_txt = "Was there a difference between near sounds and distant sounds?"
    q4_options = ["0", "1"]
    q4_labels = ["No", "Yes"]
    responses["T1"]["near_far_difference"] = ask_question_for_time_half(
        q4_txt, "T1", ask_scale_vertical, q4_options, q4_labels, 0)
    responses["T2"]["near_far_difference"] = ask_question_for_time_half(
        q4_txt, "T2", ask_scale_vertical, q4_options, q4_labels, 0)

    # Q5: Boundary experience (0-2)
    q5_txt = "To what extent did you experience a boundary between you and the sounds?"
    q5_options = ["0", "1", "2"]
    q5_labels = ["no boundary", "a distance between the perceiving subject and the perceived sound", "a separation between a subject and exterior sounds"]
    responses["T1"]["boundary_experience"] = ask_question_for_time_half(
        q5_txt, "T1", ask_scale_vertical, q5_options, q5_labels, 0)
    responses["T2"]["boundary_experience"] = ask_question_for_time_half(
        q5_txt, "T2", ask_scale_vertical, q5_options, q5_labels, 0)

    # Q6: Center of consciousness (0-2)
    q6_txt = "Was there a center of consciousness?"
    q6_options = ["0", "1", "2"]
    q6_labels = ["no center", "a subject observing mental phenomena (sounds and vibration)", "a sense of being an agent perceiving exterior stimulations (sounds and vibration)"]
    responses["T1"]["center_of_consciousness"] = ask_question_for_time_half(
        q6_txt, "T1", ask_scale_vertical, q6_options, q6_labels, spacing=90)
    responses["T2"]["center_of_consciousness"] = ask_question_for_time_half(
        q6_txt, "T2", ask_scale_vertical, q6_options, q6_labels, spacing=90)

    # Q7: Sounds location (X, 1-3)
    q7_txt = "To what extent did you experience sounds as occurring within the mind, or as feeling like they were outside it?"
    q7_options = ["X", "1", "2", "3"]
    q7_labels = [
        "I do not recall anything like this",
        "The sounds seemed to occur within my mind",
        "The sounds seemed to occur outside of my mind",
        "The sounds seemed to occur both within my mind and outside of it",
    ]
    responses["T1"]["sounds_location"] = ask_question_for_time_half(
        q7_txt, "T1", ask_scale_vertical, q7_options, q7_labels, 1)
    responses["T2"]["sounds_location"] = ask_question_for_time_half(
        q7_txt, "T2", ask_scale_vertical, q7_options, q7_labels, 1)

    # Q8: Sound-observer separation (X, 1-3)
    q8_txt = "To what extent did experiences of sounds involve a separation between the sound being heard and an observer (a 'hearer'), as opposed to no separation?"
    q8_options = ["X", "1", "2", "3"]
    q8_labels = ['I do not recall anything about this',
        'There was no sense of a sound being heard by an observer who was separate from the sound',
        'There seemed to be an observer separate from the sound, but without a strong sense of separation',
        'There was a clear sense that the sounds were being heard by an observer who was separate from the sounds',
    ]
    responses['T1']['sound_observer_separation'] = ask_question_for_time_half(
        q8_txt, 'T1', ask_scale_vertical, q8_options, q8_labels, 1, spacing=100, time_half_y=160)
    responses['T2']['sound_observer_separation'] = ask_question_for_time_half(
        q8_txt, 'T2', ask_scale_vertical, q8_options, q8_labels, 1, spacing=100, time_half_y=160)

    return responses


# ============================================================
# MAIN TEST LOOP
# ============================================================
if __name__ == "__main__":
    print("\n=== Phenomenology Test (15 blocks) ===")
    print("Press ESC in the window to quit at any time.\n")

    all_responses = []
    for block_idx in range(15):
        print(f"\n--- Block {block_idx + 1}/15 ---")
        responses = ask_phenomenology_both_halves(block_idx)
        all_responses.append(responses)

    print("\n\n=== RESULTS ===")
    for block_idx, responses in enumerate(all_responses):
        print(f"\n=== Block {block_idx + 1} ===")
        for time_half in ["T1", "T2"]:
            print(f"\n{time_half}:")
            for key, val in responses[time_half].items():
                print(f"  {key}: {val}")

    print("\nTest complete. Closing window...")
    win.close()
    core.quit()