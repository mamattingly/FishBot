import pyautogui
import time
from pynput import mouse, keyboard
import os
import random
import threading
import cv2 as cv
import numpy as np
import mss

# =========================================================
# CONFIG
# =========================================================
fishing_button = "f1"
lure_length = 10
cast_waterwalking = True
BITE_TIMEOUT = 21            # seconds max to wait for bite
TEMPLATE_RELOAD_SECONDS =  3600  # 1 hour (set to small for testing)

# =========================================================
# INTERNAL GLOBALS
# =========================================================
running = True
paused = False
templates = []
last_template_load = 0
run_time = 7200 # Time in Minutes 3600 per Hour
end_time = time.time() + run_time
random_recast_delay = random.uniform(0.5, 1.5)

# =========================================================
# FOLDER HELPERS
# =========================================================
def script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def stock_dir():
    p = os.path.join(script_dir(), "stock")
    os.makedirs(p, exist_ok=True)
    return p

def fail_dir():
    p = os.path.join(script_dir(), "failed_bobbers")
    os.makedirs(p, exist_ok=True)
    return p

def end_dir():
    p = os.path.join(script_dir(), "end_results")
    os.makedirs(p, exist_ok=True)
    return p

def ui_dir():
    p = os.path.join(script_dir(), "ui")
    return p

# =========================================================
# LOAD TEMPLATES
# =========================================================
def load_templates():
    global templates, last_template_load
    folder = stock_dir()
    print(f"🔄 Reloading templates from: {folder}")

    templates = []
    for f in os.listdir(folder):
        if f.lower().endswith(".jpg") or f.lower().endswith(".png"):
            path = os.path.join(folder, f)
            img = cv.imread(path, cv.IMREAD_GRAYSCALE)
            if img is not None:
                templates.append(img)
                print(f"   ✔ Loaded template: {f}")

    last_template_load = time.time()

    if not templates:
        print("❌ No templates found in /stock/. Add images first.")
        exit(1)

# =========================================================
# SAVE FAILURE SCREENSHOTS
# =========================================================
def save_failed_bobber_screenshot():
    folder = fail_dir()
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"bobber_fail_{ts}.png")

    screenshot = pyautogui.screenshot()
    screenshot.save(path)

    print(f"💾 Saved: {path}")

def save_no_bite_screenshot(bx, by):
    folder = fail_dir()
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"no_bite_{ts}.png")

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        img = np.array(sct.grab(monitor))
        cv.imwrite(path, cv.cvtColor(img, cv.COLOR_BGRA2BGR))

    print(f"💾 Saved: {path}")
    
def save_end_screenshot():
    folder = end_dir()
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"end_results_{ts}.png")
    
    screenshot = pyautogui.screenshot()
    screenshot.save(path)
    
    print(f"💾 Saved end results: {path}")

# =========================================================
# KEYBOARD & MOUSE
# =========================================================
def on_key_press(key):
    global running, paused
    try:
        if key.char == '`':
            running = False
            print("🛑 Stop key pressed.")
        elif key.char == 'p':
            paused = not paused
            print("⏸ Paused." if paused else "▶ Resumed.")
    except:
        pass

def start_key_listener():
    from pynput import keyboard
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()

def wait_if_paused():
    while paused and running:
        time.sleep(0.2)

# =========================================================
# BOBBER DETECTION
# =========================================================
def find_bobber():
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
                cx = max_loc[0] + w // 2
                cy = max_loc[1] + h // 2
                return (cx, cy)

    return None

# ============================================================
#  HUMAN-LIKE SLEEP (Gaussian + micro-hesitation)
# ============================================================
def human_sleep(base, sigma=0.15, max_jitter=0.40):
    """
    Sleeps with human-like timing variability.
    base: average time
    sigma: timing variability (default 150ms)
    max_jitter: clamp limit
    """
    jitter = random.gauss(0, sigma)
    jitter = max(min(jitter, max_jitter), -max_jitter)

    duration = max(0.01, base + jitter)

    # micro-hesitation (very small random extra pause)
    if random.random() < 0.10:
        duration += random.uniform(0.01, 0.20)

    time.sleep(duration)
    return duration


# ============================================================
#  HUMAN-LIKE MOUSE MOVEMENT (Bezier curve, variable speed)
# ============================================================
def move_mouse_human(x, y):
    """
    Move the mouse using:
    - Bezier curve
    - Variable velocity profile
    - Micro jitter at end
    """
    start = pyautogui.position()
    sx, sy = start

    # Random mid control point for curve
    cx = (sx + x) / 2 + random.randint(-60, 60)
    cy = (sy + y) / 2 + random.randint(-60, 60)

    steps = random.randint(25, 55)

    for i in range(steps):
        t = i / (steps - 1)

        # non-linear easing (humans accelerate/decelerate)
        t = t**2 * (3 - 2 * t)

        # quadratic Bezier formula
        px = int((1 - t)**2 * sx + 2 * (1 - t) * t * cx + t**2 * x)
        py = int((1 - t)**2 * sy + 2 * (1 - t) * t * cy + t**2 * y)

        pyautogui.moveTo(px, py)

        # human-like speed variation each step
        time.sleep(random.uniform(0.002, 0.010))

    # micro adjustments at the end
    if random.random() < 0.7:
        pyautogui.moveTo(x + random.randint(-1, 1), y + random.randint(-1, 1))
        time.sleep(random.uniform(0.01, 0.05))
        pyautogui.moveTo(x, y)


# ============================================================
#  HUMAN-LIKE CLICKING (hesitation + off-center micro-aim)
# ============================================================
def human_click(button="left"):
    """
    Click with:
    - micro-offset
    - hesitation
    - variable press duration
    """
    if random.random() < 0.35:
        human_sleep(random.uniform(0.03, 0.15))

    # press length
    press_time = random.uniform(0.04, 0.12)

    pyautogui.mouseDown(button=button)
    time.sleep(press_time)
    pyautogui.mouseUp(button=button)


# ============================================================
# HUMAN-LIKE MISTARGETING OFFSET
# ============================================================
def jitter_point(x, y, amount=2):
    """
    Apply ± pixel drift to mimic imperfect human precision.
    """
    return (
        x + random.randint(-amount, amount),
        y + random.randint(-amount, amount)
    )


# ============================================================
# HUMAN-LIKE KEY PRESS (hesitation + random hold time)
# ============================================================
def human_keypress(key):
    if random.random() < 0.20:  # occasional hesitation
        human_sleep(random.uniform(0.05, 0.30))

    hold = random.uniform(0.04, 0.12)

    pyautogui.keyDown(key)
    time.sleep(hold)
    pyautogui.keyUp(key)


def human_sleep(base):
    jitter = random.gauss(mu=0, sigma=0.12)

    jitter = max(min(jitter, 0.35), -0.35) 

    duration = base + jitter

    duration = max(duration, 0.01)

    time.sleep(duration)
    return duration  

# =========================================================
# BITE DETECTION (IMPROVED)
# =========================================================

def detect_bite(bx, by, threshold=25000):

    print("🎣 Watching for bite...")

    start_time = time.time()

    with mss.mss() as sct:
        region = {
            "left": bx - 25,
            "top": by - 25,
            "width": 50,
            "height": 50
        }

        # Stability delay after cursor movement
        time.sleep(0.5)

        # Warmup frames
        prev_gray = None
        for _ in range(8):
            frame = np.array(sct.grab(region))
            prev_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            time.sleep(0.03)

        consecutive = 0

        while running:

            if time.time() - start_time > BITE_TIMEOUT:
                print("⏰ Bite timeout.")
                return False

            wait_if_paused()

            frame = np.array(sct.grab(region))
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

            diff = cv.absdiff(prev_gray, gray)
            score = np.sum(diff)

            if score > threshold:
                consecutive += 1
            else:
                consecutive = 0

            if consecutive >= 3:
                print("🎣 Bite detected (confirmed)")
                pyautogui.mouseDown(button='right')
                time.sleep(random.uniform(0.15, 0.25))
                pyautogui.mouseUp(button='right')
                time.sleep(random.uniform(0.5, 1.0))
                return True

            prev_gray = gray
            time.sleep(0.03)

    return False

def find_logout_button():
    """Search the screen for the logout button using template matching."""
    logout_img_path = os.path.join(script_dir(), "ui", "logout_button.jpg")

    if not os.path.exists(logout_img_path):
        print("❌ Logout button image not found:", logout_img_path)
        return None

    template = cv.imread(logout_img_path, cv.IMREAD_GRAYSCALE)
    if template is None:
        print("❌ Could not load logout template.")
        return None

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        gray = cv.cvtColor(screenshot, cv.COLOR_BGR2GRAY)

        result = cv.matchTemplate(gray, template, cv.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(result)

        # You may adjust threshold if necessary
        if max_val >= 0.65:
            h, w = template.shape
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            print(f"✔ Logout button found at {cx}, {cy}")
            return (cx, cy)

    return None

def click_logout_button():
    pos = find_logout_button()
    if pos is None:
        print("❌ Logout button not found.")
        return False

    (x, y) = pos
    pyautogui.moveTo(x, y, duration=random.uniform(0.2, 0.4))
    pyautogui.click()
    print("🔘 Logout button clicked.")

    return True

def logout():
    pyautogui.press("Esc")
    human_sleep(1)
    find_logout_button()
    human_sleep(1)
    click_logout_button()
    
    
def end_fishing():
    return time.time() >= end_time

# =========================================================
# MAIN LOOP
# =========================================================
def fish():
    global running

    running = True

    # Start key listener thread
    threading.Thread(target=start_key_listener, daemon=True).start()

    # Initial load
    load_templates()

    print("Bot will start in 5 seconds. Switch to target window.")
    human_sleep(5)

    waterwalking_expiration = time.time() + 600
    lure_expiration = time.time() + (lure_length * 60)

    pyautogui.press("F5")
    
    human_sleep(5)
    
    while running:
        wait_if_paused()
        
        # END TIMER CHECK
        if end_fishing():
            print("⏰ Time limit reached — stopping.")
            save_end_screenshot()
            logout()
            running = False
            break 
        # Reload templates every hour (or test interval)
        if time.time() - last_template_load >= TEMPLATE_RELOAD_SECONDS:
            load_templates()

        # # Refresh lure
        # if time.time() > waterwalking_expiration:
        #     pyautogui.press("f2")
        #     human_sleep(2)
        #     lure_expiration = time.time() + 600

        if time.time() > lure_expiration:
            pyautogui.press("f5")
            human_sleep(2)
            lure_expiration = time.time() + (lure_length * 60)

        # Cast
        pyautogui.press(fishing_button)
        print("🎣 Casting...")
        human_sleep(2)

        # Bobber search
        bobber = None
        timeout = time.time() + 10

        while running and time.time() < timeout and bobber is None:
            bobber = find_bobber()
            if bobber is None:
                human_sleep(0.2)

        if bobber is None:
            print("❌ No bobber detected — saving screenshot")
            save_failed_bobber_screenshot()
            continue

        (bx, by) = bobber
        print(f"✔ Bobber found at {bx}, {by}")

        pyautogui.moveTo(bx, by, duration=random.uniform(0.3, 0.7))

        # Bite detection
        bite = detect_bite(bx, by)

        if not bite:
            print("❌ Bobber found but no bite — saving screenshot")
            save_no_bite_screenshot(bx, by)
            continue

        time.sleep(random_recast_delay)

    print("🛑 Script stopped.")


# =========================================================
fish()