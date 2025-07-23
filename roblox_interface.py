import win32gui
import pyperclip
import keyboard
import time

class RobloxInterface:
    def __init__(self, config_manager, message_queue):
        self.config_manager = config_manager
        self.message_queue = message_queue
    
    def is_roblox_focused(self):
        """Check if Roblox window is currently focused"""
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            return self.config_manager.get('roblox_window_title') in title
        except Exception:
            return False
    
    def send_message(self, text):
        """Send message to Roblox or copy to clipboard"""
        try:
            if not self.is_roblox_focused():
                self.message_queue.put(("log", "Roblox not focused. Message copied to clipboard."))
                pyperclip.copy(text)
                return False
            
            pyperclip.copy(text)
            keyboard.press_and_release('/')
            time.sleep(0.1)
            keyboard.press_and_release('ctrl+v')
            time.sleep(0.1)
            keyboard.press_and_release('enter')
            
            self.message_queue.put(("log", "Message sent to Roblox"))
            return True
            
        except Exception as e:
            self.message_queue.put(("error", f"Failed to send to Roblox: {e}"))
            pyperclip.copy(text)
            self.message_queue.put(("log", "Message copied to clipboard instead"))
            return False
    
    def get_focused_window_title(self):
        """Get the title of the currently focused window"""
        try:
            window = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(window)
        except Exception:
            return "Unknown"