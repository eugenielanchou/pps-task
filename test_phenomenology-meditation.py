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
POS_Y_QUESTION = 420
POS_Y_TIME_ABOVE_RESPONSES = 220  # just above the scale options
POS_Y_HINT = -340        # hint pushed further down

# --- Vertical scale layout ---
V_SCALE_X = -520               # numbers pinned near the left edge
V_SCALE_LABEL_OFFSET_X = 720   # label starts just to the right of the number
V_SCALE_LABEL_WRAP = 1300      # narrower wrap so long labels don't run off-screen
V_SCALE_SPACING = 68           # spacing between options/labels
V_SCALE_FIRST_OPTION_Y = 140   # fixed position for first option on all questions (consistent spacing from time indicator)

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


def draw_question_block(question_text, time_half=None):
    draw_text(question_text, height=FONT_QUESTION, wrap=TEXT_WRAP, pos=(0, POS_Y_QUESTION))
    if time_half:
        time_labels = {"T1": "(beginning of the period)", "T2": "(middle of the period)", "T3": "(end of the period)"}
        label = time_labels.get(time_half, time_half)
        draw_text(f"{time_half} {label}", height=FONT_TIME_HALF, wrap=TEXT_WRAP,
                   pos=(0, POS_Y_TIME_ABOVE_RESPONSES), color=COLOR_SELECTED, bold=True)


def draw_selection_box(pos):
    rect = visual.Rect(win, width=BOX_W, height=BOX_H, pos=pos,
                        fillColor=None, lineColor=COLOR_SELECTED, lineWidth=BOX_LINE_WIDTH)
    rect.draw()


# ============================================================
# QUESTION FUNCTIONS
# ============================================================
def ask_ordinal_question(question_text, min_val, max_val, allow_x=False):
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
                        time_half=None, fixed_top_y=None, spacing=None):
    if spacing is None:
        spacing = V_SCALE_SPACING

    clear_keyboard()
    selected_idx = start_idx

    if fixed_top_y is not None:
        start_y = fixed_top_y
    else:
        start_y = V_SCALE_FIRST_OPTION_Y

    while True:
        check_escape()
        draw_question_block(question_text, time_half=time_half)

        for idx, (option, label) in enumerate(zip(scale_options, scale_labels)):
            y_pos = start_y - idx * spacing
            color = COLOR_SELECTED if idx == selected_idx else COLOR_DEFAULT

            if idx == selected_idx:
                draw_selection_box((V_SCALE_X, y_pos))

            draw_text(option, height=FONT_OPTION, pos=(V_SCALE_X, y_pos), color=color)
            if label:
                draw_text(label.capitalize(), height=FONT_LABEL, wrap=V_SCALE_LABEL_WRAP,
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
    scale_options = ["X", "0", "1", "2", "3", "4"]
    scale_labels = [
        "I do not recall enough to answer this question.",
        "no, I did not recognize the Nature of Mind",
        "yes, once",
        "a few times",
        "many times",
        "most of the time",
    ]
    return ask_scale_vertical(question_text, scale_options, scale_labels, start_idx=1,
                               time_half=time_half, fixed_top_y=V_SCALE_FIRST_OPTION_Y)


def ask_scale_horizontal(question_text, scale_options, scale_labels, start_idx=1, time_half=None):
    clear_keyboard()
    selected_idx = start_idx

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
    general_txt = "Please answer the following questions using the arrow keys.\n\n" "Although the period was continuous, please think back on it as having a beginning, a middle and an end.\nFor each question, answer separately for each of these three moments."
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




def ask_question_for_time_half(question_text, time_half, ask_func, *args, **kwargs):
    kwargs['time_half'] = time_half
    return ask_func(question_text, *args, **kwargs)


def ask_phenomenology_three_moments(block_idx):
    # Show general instruction only on first block
    if block_idx == 0:
        show_general_instruction()
        show_time_half_explanation()

    responses = {"T1": {}, "T2": {}, "T3": {}}

    time_moments = ["T1", "T2", "T3"]

    # --- Vertical scale questions (0-10) ---

    # Q1: Eyes open percentage (0-10)
    q1_txt = "Estimate the percentage of time spent meditating with your eyes open."
    q1_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q1_labels = ["I do not recall anything about this", "0% of the time", "", "", "", "", "50% of the time", "", "", "", "", "100% of the time"]
    for moment in time_moments:
        responses[moment]["eyes_open_percent"] = ask_question_for_time_half(
            q1_txt, moment, ask_scale_vertical, q1_options, q1_labels, 1, spacing=50)

    # Q2: Follow instruction successfully (0-10)
    q2_txt = "In this induction, and based on your own personal best, how successfully did you follow the instruction?"
    q2_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q2_labels = ["I do not recall anything about this", "on average, unsuccessfully", "", "", "", "", " on average, somewhat successfully", "", "", "", "", "on average, very successfully"]
    for moment in time_moments:
        responses[moment]["follow_instruction"] = ask_question_for_time_half(
            q2_txt, moment, ask_scale_vertical, q2_options, q2_labels, 1, spacing=50)

    # Q3: Effort (0-10)
    q3_txt = "How much effort did you feel during the session?"
    q3_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q3_labels = ["I do not recall anything about this", "very effortful, was hard work", "", "", "significantly effortful", "", "average level of effort", "", "mostly effortless", "", "", "utterly effortless; felt the session was spontaneous"]
    for moment in time_moments:
        responses[moment]["effort"] = ask_question_for_time_half(
            q3_txt, moment, ask_scale_vertical, q3_options, q3_labels, 1, spacing=50)

    # Q4: Energy/arousal (0-10)
    q4_txt = "What was your level of energy or arousal during the session?"
    q4_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q4_labels = ["I do not recall anything about this", "very low energy (on the verge of falling asleep, or actually asleep)", "", "", "", "", "average level of energy or arousal", "", "", "", "", "very high energy or arousal (the high energy that comes from a strong cup of coffee or tea)"]
    for moment in time_moments:
        responses[moment]["energy"] = ask_question_for_time_half(
            q4_txt, moment, ask_scale_vertical, q4_options, q4_labels, 1, spacing=50)

    # Q5: Monitoring mind movements (0-10)
    q5_txt = "How much were you monitoring the movements and processes of the mind?"
    q5_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q5_labels = ["I do not recall anything about this", "never (0%)", "", "", "", "", "sometimes (50%)", "", "", "", "", "always (100%)"]
    for moment in time_moments:
        responses[moment]["monitoring_mind"] = ask_question_for_time_half(
            q5_txt, moment, ask_scale_vertical, q5_options, q5_labels, 1, spacing=50)

    # Q6: Field of awareness (0-10: 0=open/extended, 10=narrow)
    q6_txt = "Was your field of awareness open, extended, or spacious? Or rather focused and narrow?"
    q6_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q6_labels = ["I do not recall anything about this", "usually extremely open, extended, spacious", "", "", "", "", "somewhat open, extended, spacious", "", "", "", "", "usually narrow"]
    for moment in time_moments:
        responses[moment]["awareness_field"] = ask_question_for_time_half(
            q6_txt, moment, ask_scale_vertical, q6_options, q6_labels, 1, spacing=50)

    # Q7: Thoughts appearing real (0-10: 0=just thoughts, 10=real)
    q7_txt = "To what degree did thoughts appear to be real (10) as opposed to appearing just as thoughts (0)? For example, the thought of a strawberry can appear to be a real strawberry, or simply like a thought."
    q7_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q7_labels = ["I do not recall anything about this", "mostly appearing just as thoughts", "", "", "", "", "sometimes real, sometimes just as thoughts", "", "", "", "", "mostly appearing to be real"]
    for moment in time_moments:
        responses[moment]["thoughts_real"] = ask_question_for_time_half(
            q7_txt, moment, ask_scale_vertical, q7_options, q7_labels, 1, spacing=50)

    # Q8: Unrelated thoughts frequency (0-10)
    q8_txt = "How frequently did you have thoughts unrelated to your meditation (inner speech, mental imagery, memories)?"
    q8_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q8_labels = ["I do not recall anything about this", "never (0%)", "", "", "", "", "moderately (50%)", "", "", "", "", "all the time (100%)"]
    for moment in time_moments:
        responses[moment]["unrelated_thoughts"] = ask_question_for_time_half(
            q8_txt, moment, ask_scale_vertical, q8_options, q8_labels, 1, spacing=50)

    # Q9: Stability vs distraction (0-10)
    q9_txt = "During the session, how stable or distracted was your practice? (Distraction means attention being drawn away from your practice, for example by getting caught in a thought or losing track of your practice as when you fall asleep)."
    q9_options = ["X", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    q9_labels = ["I do not recall anything about this", "unstable, always distracted", "", "", "", "", "mostly stable, sometimes distracted", "", "", "", "", "the state was completely stable, no distraction (or attention capture)"]
    for moment in time_moments:
        responses[moment]["stability"] = ask_question_for_time_half(
            q9_txt, moment, ask_scale_vertical, q9_options, q9_labels, 1, spacing=50)

    # --- Vertical scale questions ---

    # Q10: Nature of Mind recognition (X, 0-4)
    q10_txt = "According to your own understanding, did you experience any moments during the session that you would describe as recognizing the Nature of Mind?"
    for moment in time_moments:
        responses[moment]["nom_recognition"] = ask_question_for_time_half(q10_txt, moment, ask_nom_recognition_vertical)

    # Q11: Confidence in NOM rating (only if NOM = 1, 2, 3, or 4)
    q11_txt = "How confident are you about your rating?"
    q11_options = ["X", "1", "2", "3"]
    q11_labels = ["I do not recall enough to answer this question.", "not confident", "a little confident", "confident"]

    for moment in time_moments:
        responses[moment]["nom_confidence"] = ""
        if responses[moment]["nom_recognition"] not in ["0", "X"]:
            responses[moment]["nom_confidence"] = ask_question_for_time_half(
                q11_txt, moment, ask_scale_vertical, q11_options, q11_labels, 1
            )

    # Q12: Time experience (X, 1-3)
    q12_txt = "How was time most frequently experienced?"
    q12_options = ["X", "1", "2", "3"]
    q12_labels = [
        "I do not recall anything about this",
        "experience seemed beyond time",
        "I was in the present moment",
        "I was lost in the future or the past",
    ]
    for moment in time_moments:
        responses[moment]["time_experience"] = ask_question_for_time_half(
            q12_txt, moment, ask_scale_vertical, q12_options, q12_labels, 1)

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
        responses = ask_phenomenology_three_moments(block_idx)
        all_responses.append(responses)

    print("\n\n=== RESULTS ===")
    for block_idx, responses in enumerate(all_responses):
        print(f"\n=== Block {block_idx + 1} ===")
        for moment in ["T1", "T2", "T3"]:
            print(f"\n{moment}:")
            for key, val in responses[moment].items():
                print(f"  {key}: {val}")

    print("\nTest complete. Closing window...")
    win.close()
    core.quit()