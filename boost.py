import random
import time
import pyautogui

def random_key_press():
    """Press a random key every 1-5 seconds"""
    while True:
        delay = random.uniform(1, 120)
        time.sleep(delay)
        pyautogui.press("d")
        print(f"Key pressed after {delay:.2f} seconds")

if __name__ == "__main__":
    print("Starting bot... Press Ctrl+C to stop")
    try:
        random_key_press()
    except KeyboardInterrupt:
        print("Bot stopped")