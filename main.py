import pyautogui
import time
from pynput import mouse, keyboard
import os
import random
import threading

# Global state variables
right_click_detected = False
running = True
DECIBEL_THRESHOLD = -45
lure_length = 15


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

    # Start listening for mouse events
    with mouse.Listener(on_click=on_click) as listener:
        while not right_click_detected and running:
            time.sleep(0.1)  # Avoid high CPU usage with a small sleep
        listener.stop()  # Stop listening once right-click is detected or bot is stopped
    if running:
        print("Right-click detected. Resuming...")
    else:
        print("Bot stopped. Exiting right-click wait loop.")


def set_current_directory():
    """Sets and returns the current working directory."""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_directory)
    print("Current directory set to:", current_directory)
    return current_directory


def get_jpg_files(directory):
    """Returns a list of all .jpg files in the given directory."""
    return [file for file in os.listdir(directory) if file.endswith(".jpg")]


def choose_image(path):
    """Prompts the user to choose an image file for the bobber."""
    jpg_files = get_jpg_files(path)
    print("Choose the image to use for the bobber.")
    for i, file in enumerate(jpg_files):
        print(f"{i + 1}. {file}")
    while True:
        try:
            choice = int(input("Enter the number of the image: "))
            if 1 <= choice <= len(jpg_files):
                return jpg_files[choice - 1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def on_key_press(key):
    """Handles key press events, stopping the bot if the backquote key is pressed."""
    global running
    try:
        if key.char == '`':  # Stop the bot when the backquote key is pressed
            print("Backquote key pressed. Stopping the bot.")
            running = False
    except AttributeError:
        pass


def start_key_listener():
    """Starts a separate thread to listen for key press events."""
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()


def fish():

    """Main function to handle the fishing bot operations."""
    global running
    key_listener_thread = threading.Thread(target=start_key_listener, daemon=True)
    key_listener_thread.start()

    time.sleep(2)
    path = set_current_directory()
    image = choose_image(path)
    duration = random.uniform(0.5, 1)
    cleaned_img_path = f"{path}\\{image}"
    print(f"Selected image: {cleaned_img_path}")

    # Placeholder for switching to the World of Warcraft window
    print("Bot will start in 5 seconds. Switch to Wow Window")
    # switch_to_wow_window()
    time.sleep(5)
    
    pyautogui.press("F5")

    lure_expiration = time.time() + 60*15 # 15 minutes 

    while running:
        if time.time() > lure_expiration:
            print("Lure expired. Refreshing...")
            pyautogui.press("f5")
            lure_expiration = time.time() + 60*lure_length
            
        pyautogui.press("q")  # Cast the fishing line
        time.sleep(2)
    
    
        # Locate the bobber on the screen
        try:
            location = pyautogui.locateOnScreen(cleaned_img_path, confidence=0.4)
            if location:
                print("Bobber found.")
                bobber_x, bobber_y = pyautogui.center(location)
                pyautogui.moveTo(x=bobber_x, y=bobber_y, duration=duration)
                wait_for_right_click()
            else:
                print("Bobber not found. Retrying...")
                time.sleep(2)
        except pyautogui.ImageNotFoundException:
            print("Error: Could not locate the image.")

        time.sleep(1)

    print("Fishing bot stopped.")


# Start the fishing bot
fish()
