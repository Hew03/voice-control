import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import queue
import time
import warnings
from config_manager import ConfigManager
from audio_handler import AudioHandler
from translation_manager import TranslationManager
from roblox_interface import RobloxInterface
from hotkey_manager import HotkeyManager

warnings.filterwarnings("ignore")

class VoiceTranscriberGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Transcriber for Roblox")
        self.root.geometry("900x700")
        
        self.config_manager = ConfigManager()
        self.message_queue = queue.Queue()
        
        self.audio_handler = AudioHandler(self.config_manager, self.message_queue)
        self.translation_manager = TranslationManager(self.config_manager, self.message_queue)
        self.roblox_interface = RobloxInterface(self.config_manager, self.message_queue)
        self.hotkey_manager = HotkeyManager(self.config_manager, self.message_queue)
        
        self.is_recording = False
        
        self.setup_ui()
        self.setup_components()
        self.process_messages()
    
    def setup_components(self):
        """Initialize all components"""
        self.audio_handler.load_model_async()
        
        self.translation_manager.setup_translation_async()
        
        self.hotkey_manager.register_hotkey('recording_toggle', self.toggle_recording)
        self.hotkey_manager.setup_hotkeys()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="5")
        status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Initializing...")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.recording_indicator = ttk.Label(status_frame, text="⚫", foreground="red")
        self.recording_indicator.grid(row=0, column=1, sticky=tk.E)
        
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="5")
        controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.record_button = ttk.Button(controls_frame, text="Start Recording (F2)", command=self.toggle_recording)
        self.record_button.grid(row=0, column=0, padx=(0, 5))
        
        self.translation_button = ttk.Button(controls_frame, text="Toggle Translation Mode", command=self.toggle_translation_mode)
        self.translation_button.grid(row=0, column=1, padx=(0, 5))
        
        self.clear_button = ttk.Button(controls_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.grid(row=0, column=2)
        
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(settings_frame, text="Microphone:").grid(row=0, column=0, sticky=tk.W)
        self.mic_combo = ttk.Combobox(settings_frame, width=30)
        self.mic_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        self.populate_microphones()
        
        ttk.Label(settings_frame, text="Model:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.model_combo = ttk.Combobox(settings_frame, values=['tiny', 'base', 'small', 'medium', 'large'])
        self.model_combo.set(self.config_manager.get('model_name'))
        self.model_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        ttk.Label(settings_frame, text="Hotkey:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.hotkey_entry = ttk.Entry(settings_frame)
        self.hotkey_entry.insert(0, self.config_manager.get('hotkey'))
        self.hotkey_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        trigger_frame = ttk.LabelFrame(main_frame, text="Trigger Phrases", padding="5")
        trigger_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(trigger_frame, text="Start Translation:").grid(row=0, column=0, sticky=tk.W)
        self.start_translation_entry = ttk.Entry(trigger_frame)
        self.start_translation_entry.insert(0, self.config_manager.get('translation_trigger'))
        self.start_translation_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(trigger_frame, text="Stop Translation:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.stop_translation_entry = ttk.Entry(trigger_frame)
        self.stop_translation_entry.insert(0, self.config_manager.get('stop_translation'))
        self.stop_translation_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        ttk.Label(trigger_frame, text="Roblox Window Title:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.roblox_title_entry = ttk.Entry(trigger_frame)
        self.roblox_title_entry.insert(0, self.config_manager.get('roblox_window_title'))
        self.roblox_title_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        self.chinese_correct_var = tk.BooleanVar(value=self.config_manager.get('enable_chinese_autocorrect'))
        self.chinese_correct_cb = ttk.Checkbutton(trigger_frame, text="Enable Chinese Autocorrect", variable=self.chinese_correct_var)
        self.chinese_correct_cb.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        self.save_settings_btn = ttk.Button(trigger_frame, text="Save Settings", command=self.save_settings)
        self.save_settings_btn.grid(row=4, column=0, columnspan=2, pady=(5, 0))
        
        log_frame = ttk.LabelFrame(main_frame, text="Transcription Log", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        trigger_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def populate_microphones(self):
        """Populate microphone dropdown"""
        devices = self.audio_handler.get_audio_devices()
        self.mic_combo['values'] = devices
        
        if devices:
            for device in devices:
                if device.startswith(str(self.config_manager.get('mic_index'))):
                    self.mic_combo.set(device)
                    break
            else:
                self.mic_combo.set(devices[0])
    
    def save_settings(self):
        """Save all settings to configuration"""
        mic_selection = self.mic_combo.get()
        mic_index = self.config_manager.get('mic_index')
        if mic_selection:
            try:
                mic_index = int(mic_selection.split(':')[0])
            except (ValueError, IndexError):
                pass
        
        self.config_manager.update({
            'mic_index': mic_index,
            'translation_trigger': self.start_translation_entry.get(),
            'stop_translation': self.stop_translation_entry.get(),
            'roblox_window_title': self.roblox_title_entry.get(),
            'enable_chinese_autocorrect': self.chinese_correct_var.get(),
            'hotkey': self.hotkey_entry.get(),
            'model_name': self.model_combo.get(),
            'rate': self.config_manager.get('rate'),
            'chunk': self.config_manager.get('chunk'),
            'channels': self.config_manager.get('channels')
        })
        
        if self.config_manager.save_config():
            self.hotkey_manager.update_hotkey(self.hotkey_entry.get())
            self.log_message("Settings saved successfully")
            self.log_message(f"Saved config: mic_index={self.config_manager.get('mic_index')}, model={self.config_manager.get('model_name')}")
        else:
            self.log_message("Failed to save settings to file")
    
    def toggle_recording(self):
        """Toggle audio recording on/off"""
        if not self.audio_handler.model:
            messagebox.showwarning("Warning", "Model not loaded yet!")
            return
        
        self.is_recording = not self.is_recording
        
        if self.is_recording:
            self.record_button.config(text="Stop Recording (F2)")
            self.recording_indicator.config(text="🔴", foreground="red")
            
            mic_selection = self.mic_combo.get()
            mic_index = None
            if mic_selection:
                try:
                    mic_index = int(mic_selection.split(':')[0])
                except (ValueError, IndexError):
                    mic_index = self.config_manager.get('mic_index')
            
            self.audio_handler.start_recording(mic_index)
        else:
            self.record_button.config(text="Start Recording (F2)")
            self.recording_indicator.config(text="⚫", foreground="gray")
            self.audio_handler.stop_recording()
    
    def toggle_translation_mode(self):
        """Toggle translation mode on/off"""
        mode = self.translation_manager.toggle_translation_mode()
        self.update_translation_button(mode)
    
    def update_translation_button(self, translation_active=None):
        """Update translation button text"""
        if translation_active is None:
            translation_active = self.translation_manager.is_translation_active()
        
        status = "ON" if translation_active else "OFF"
        self.translation_button.config(text=f"Translation Mode: {status}")
    
    def clear_log(self):
        """Clear the log text area"""
        self.log_text.delete(1.0, tk.END)
    
    def log_message(self, message):
        """Add a timestamped message to the log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def process_audio_result(self, raw_text, lang):
        """Process the result from audio transcription"""
        if raw_text is None or lang is None:
            return
        
        corrected_text, corrections = self.translation_manager.correct_transcription(raw_text, lang)
        
        if self.translation_manager.check_trigger_phrases(corrected_text, lang):
            return
        
        if self.translation_manager.is_translation_active() and lang == 'en':
            translated_text = self.translation_manager.translate_to_chinese(corrected_text)
            self.log_message(f"Original: {corrected_text}")
            self.log_message(f"Chinese: {translated_text}")
            self.roblox_interface.send_message(translated_text)
        else:
            self.log_message(f"Transcribed ({lang}): {corrected_text}")
            self.roblox_interface.send_message(corrected_text)
    
    def process_messages(self):
        """Process messages from the message queue"""
        try:
            while True:
                msg_type, content = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self.status_label.config(text=content)
                elif msg_type == "log":
                    self.log_message(content)
                elif msg_type == "error":
                    self.log_message(f"ERROR: {content}")
                elif msg_type == "enable_controls":
                    self.record_button.config(state="normal")
                    self.status_label.config(text="Ready - Press F2 to start recording")
                elif msg_type == "translation_mode_changed":
                    self.update_translation_button(content)
                elif msg_type == "audio_processed":
                    raw_text, lang = content
                    self.process_audio_result(raw_text, lang)
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_messages)
    
    def on_closing(self):
        """Handle application closing"""
        try:
            self.hotkey_manager.cleanup()
            self.audio_handler.cleanup()
        except:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = VoiceTranscriberGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()