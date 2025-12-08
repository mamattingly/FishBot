import pyautogui
import time
from pynput import mouse, keyboard
import os
import random
import threading
import cv2 as cv
import numpy as np
import mss

# ---------------------------------------------------------
# GLOBAL VARIABLES
# ---------------------------------------------------------
right_click_detected = False
running = True
paused = False  # new: pause flag
DECIBEL_THRESHOLD = -45
lure_length = 10
fishing_button = "f1"
use_lure = False

# ---------------------------------------------------------
# LISTENERS
# ---------------------------------------------------------
def on_click(x, y, button, pressed):
    """Handles mouse click events, detecting right-clicks."""
    global right_click_detected
    if button == mouse.Button.right and pressed:
        right_click_detected = True


def wait_for_right_click():
    """Waits until the user right-clicks or the bot is stopped."""
    global right_click_detected, running
    print("Please right-click to continue...")
    right_click_detected = False

    with mouse.Listener(on_click=on_click) as listener:
        while not right_click_detected and running:
            wait_if_paused()
            time.sleep(0.1)
        listener.stop()

    if running:
        print("Right-click detected. Resuming...")
    else:
        print("Bot stopped.")


def on_key_press(key):
    """Stops or pauses the bot."""
    global running, paused
    try:
        if key.char == '`':  # stop bot
            print("` key pressed. Stopping bot.")
            running = False
        elif key.char == 'p':  # pause/resume
            paused = not paused
            if paused:
                print("⏸ Bot paused.")
            else:
                print("▶ Bot resumed.")
    except AttributeError:
        pass


def start_key_listener():
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()


def wait_if_paused():
    """Pauses the script until resumed."""
    global paused
    while paused and running:
        time.sleep(0.2)

# ---------------------------------------------------------
# FILE & IMAGE HELPERS
# ---------------------------------------------------------
def set_current_directory():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_directory)
    print("Current directory set to:", current_directory)
    return current_directory


def get_jpg_files(directory):
    return [file for file in os.listdir(directory) if file.endswith(".jpg")]


def choose_image(path):
    """Prompts user to choose an image for bobber template."""
    jpg_files = get_jpg_files(path)
    print("Choose the image to use for the bobber:")

    for i, file in enumerate(jpg_files):
        print(f"{i + 1}. {file}")

    while True:
        try:
            choice = int(input("Enter number: "))
            if 1 <= choice <= len(jpg_files):
                return jpg_files[choice - 1]
        except ValueError:
            pass
        print("Invalid input. Try again.")

# ---------------------------------------------------------
# BOBBER DETECTION (OpenCV + MSS)
# ---------------------------------------------------------
def find_bobber(template):
    """Locate bobber using modern OpenCV template matching."""
    wait_if_paused()
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # main screen
        screenshot = np.array(sct.grab(monitor))
        gray = cv.cvtColor(screenshot, cv.COLOR_BGR2GRAY)

        result = cv.matchTemplate(gray, template, cv.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(result)

        if max_val >= 0.55:
            h, w = template.shape
            center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
            return center

    return None

# ---------------------------------------------------------
# MOTION-BASED BITE DETECTION
# ---------------------------------------------------------
def detect_bite(bx, by, threshold=25000):
    """Detect a fishing bite by motion in a 50x50 region around bobber."""
    print("Monitoring bobber for bite...")

    with mss.mss() as sct:
        region = {
            "left": bx - 25,
            "top": by - 25,
            "width": 50,
            "height": 50
        }

        prev = np.array(sct.grab(region))
        prev_gray = cv.cvtColor(prev, cv.COLOR_BGR2GRAY)

        while running:
            wait_if_paused()
            frame = np.array(sct.grab(region))
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

            diff = cv.absdiff(prev_gray, gray)
            score = np.sum(diff)

            if score > threshold:
                print("🎣 Bite detected! Clicking...")
                # human-like click
                pyautogui.mouseDown(button='right')
                time.sleep(random.uniform(0.15, 0.25))  # hold for 150–250 ms
                pyautogui.mouseUp(button='right')
                time.sleep(random.uniform(0.5, 1.0))  # extra cooldown
                return True


            prev_gray = gray
            time.sleep(0.03)

    return False

# ---------------------------------------------------------
# MAIN FISHING BOT
# ---------------------------------------------------------
def fish():
    global running
    key_listener_thread = threading.Thread(target=start_key_listener, daemon=True)
    key_listener_thread.start()

    time.sleep(2)
    path = set_current_directory()
    image_name = choose_image(path)
    cleaned_img_path = os.path.join(path, image_name)

    print(f"Selected image: {cleaned_img_path}")
    print("Bot will start in 5 seconds. Switch to WoW window.")
    time.sleep(5)

    pyautogui.press("F5")

    template = cv.imread(cleaned_img_path, cv.IMREAD_GRAYSCALE)

    lure_expiration = time.time() + 60 * 10  # 15 min lure

    while running:
        wait_if_paused()

        # refresh lure
        if time.time() > lure_expiration:
            print("Refreshing lure...")
            pyautogui.press("f5")
            lure_expiration = time.time() + 60 * lure_length

        # cast line
        wait_if_paused()
        pyautogui.press(fishing_button)
        print("Casting line...")
        time.sleep(2)

        # wait for bobber to appear
        bobber = None
        timeout = time.time() + 10
        while not bobber and running and time.time() < timeout:
            wait_if_paused()
            bobber = find_bobber(template)
            if not bobber:
                time.sleep(0.2)

        if not bobber:
            print("Bobber not found after casting, retrying...")
            continue

        bx, by = bobber
        print("Bobber found at", bx, by)
        pyautogui.moveTo(bx, by, duration=random.uniform(0.3, 0.7))

        # wait for automatic bite detection
        detect_bite(bx, by)

        time.sleep(1)

    print("Fishing bot stopped.")

# ---------------------------------------------------------
# START BOT
# ---------------------------------------------------------
fish()
