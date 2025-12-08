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
paused = False
DECIBEL_THRESHOLD = -45
lure_length = 10
fishing_button = "f1"
use_lure = False

BITE_TIMEOUT = 15  # seconds

# ---------------------------------------------------------
# LISTENERS
# ---------------------------------------------------------
def on_click(x, y, button, pressed):
    global right_click_detected
    if button == mouse.Button.right and pressed:
        right_click_detected = True

def wait_for_right_click():
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
    global running, paused
    try:
        if key.char == '`':
            print("` key pressed. Stopping bot.")
            running = False
        elif key.char == 'p':
            paused = not paused
            print("⏸ Bot paused." if paused else "▶ Bot resumed.")
    except AttributeError:
        pass

def start_key_listener():
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()

def wait_if_paused():
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
    return [file for file in os.listdir(directory) if file.lower().endswith(".jpg")]

def load_templates(path):
    jpg_files = get_jpg_files(path)
    templates = []

    if not jpg_files:
        print("❌ No .jpg images found in directory!")
        exit(1)

    for file in jpg_files:
        full_path = os.path.join(path, file)
        img = cv.imread(full_path, cv.IMREAD_GRAYSCALE)
        if img is not None:
            templates.append(img)
            print(f"Loaded template: {file}")

    return templates

# ---------------------------------------------------------
# SAVE FAILED BOBBER SCREENSHOT
# ---------------------------------------------------------
def save_failed_bobber_screenshot():
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder_path = os.path.join(parent_dir, "failed_bobbers")
    os.makedirs(folder_path, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f"bobber_fail_{timestamp}.png")
    screenshot = pyautogui.screenshot()
    screenshot.save(file_path)
    print(f"💾 Failed bobber screenshot saved: {file_path}")

# ---------------------------------------------------------
# BOBBER DETECTION
# ---------------------------------------------------------
def find_bobber(templates):
    wait_if_paused()
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        gray = cv.cvtColor(screenshot, cv.COLOR_BGR2GRAY)
        for template in templates:
            result = cv.matchTemplate(gray, template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)
            if max_val >= 0.55:
                h, w = template.shape
                center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                return center
    return None

# ---------------------------------------------------------
# IMPROVED BITE DETECTION
# ---------------------------------------------------------
def detect_bite(bx, by, threshold=25000):
    print("Monitoring region for motion...")
    start_time = time.time()

    with mss.mss() as sct:
        region = {
            "left": bx - 25,
            "top": by - 25,
            "width": 50,
            "height": 50
        }

        # 1. Stabilization delay
        time.sleep(0.5)

        # 2. Warm-up frames
        prev_gray = None
        for _ in range(8):
            frame = np.array(sct.grab(region))
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            prev_gray = gray
            time.sleep(0.03)

        # 3. Motion detection loop
        motion_frames = 0
        required_frames = 3

        while running:
            if time.time() - start_time > BITE_TIMEOUT:
                print(f"⏰ No motion detected after {BITE_TIMEOUT}s. Recasting...")
                return False

            wait_if_paused()

            frame = np.array(sct.grab(region))
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            diff = cv.absdiff(prev_gray, gray)
            score = np.sum(diff)

            if score > threshold:
                motion_frames += 1
            else:
                motion_frames = 0

            if motion_frames >= required_frames:
                print("🎣 Motion detected! (confirmed)")
                pyautogui.mouseDown(button='right')
                time.sleep(random.uniform(0.15, 0.25))
                pyautogui.mouseUp(button='right')
                time.sleep(random.uniform(0.5, 1.0))
                return True

            prev_gray = gray
            time.sleep(0.03)

    return False

# ---------------------------------------------------------
# MAIN FISHING LOOP
# ---------------------------------------------------------
def fish():
    global running
    key_listener_thread = threading.Thread(target=start_key_listener, daemon=True)
    key_listener_thread.start()

    time.sleep(2)
    path = set_current_directory()

    print("Loading all bobber templates...")
    templates = load_templates(path)
    print(f"{len(templates)} templates loaded.")

    print("Bot will start in 5 seconds. Switch to target window.")
    time.sleep(5)

    pyautogui.press("F5")
    lure_expiration = time.time() + 60 * 10

    while running:
        wait_if_paused()

        if time.time() > lure_expiration:
            print("Refreshing lure...")
            pyautogui.press("f5")
            lure_expiration = time.time() + 60 * lure_length

        pyautogui.press(fishing_button)
        print("Casting line...")
        time.sleep(2)

        # Bobber search timeout
        bobber = None
        timeout = time.time() + 10
        while not bobber and running and time.time() < timeout:
            wait_if_paused()
            bobber = find_bobber(templates)
            if not bobber:
                time.sleep(0.2)

        if not bobber:
            print("❌ Bobber not found after casting. Saving screenshot...")
            save_failed_bobber_screenshot()
            print("🔁 Recasting...")
            continue

        bx, by = bobber
        print("Bobber found at", bx, by)
        pyautogui.moveTo(bx, by, duration=random.uniform(0.3, 0.7))

        # Detect bite
        bite = detect_bite(bx, by)
        if not bite:
            print("🔁 No bite detected. Recasting...")
            continue

        time.sleep(1)

    print("Fishing bot stopped.")

# ---------------------------------------------------------
# START
# ---------------------------------------------------------
fish()
