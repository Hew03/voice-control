import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import pyaudio
import wave
import tempfile
import whisper
import os
import keyboard
from pycorrector import Corrector
import argostranslate.package
import argostranslate.translate
import re
import time
import win32gui
import pyperclip
import warnings
from pathlib import Path
import json

warnings.filterwarnings("ignore")

class VoiceTranscriberGUI:
    CONFIG_FILE = "voice_transcriber_config.json"
    
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Transcriber for Roblox")
        self.root.geometry("900x700")
        
        self.default_config = {
            'mic_index': 4,
            'rate': 48000,
            'chunk': 4096,
            'format': pyaudio.paInt16,
            'channels': 1,
            'model_name': 'base',
            'hotkey': 'f2',
            'translation_trigger': 'translate to chinese',
            'stop_translation': 'stop translation',
            'roblox_window_title': 'Roblox',
            'enable_chinese_autocorrect': False
        }
        
        self.config = self.load_config()
        self.p = pyaudio.PyAudio()
        self.model = None
        self.corrector = Corrector()
        self.current_language = 'en'
        self.is_recording = False
        self.translation_mode = False
        self.stream = None
        self.message_queue = queue.Queue()
        
        self.setup_ui()
        self.load_model_async()
        self.setup_translation_async()
        self.setup_hotkey()
        self.process_messages()
    
    def load_config(self):
        try:
            if Path(self.CONFIG_FILE).exists():
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return {**self.default_config, **config}
        except Exception as e:
            print(f"Error loading config: {e}")
        return self.default_config
    
    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
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
        self.model_combo.set(self.config['model_name'])
        self.model_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        ttk.Label(settings_frame, text="Hotkey:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.hotkey_entry = ttk.Entry(settings_frame)
        self.hotkey_entry.insert(0, self.config['hotkey'])
        self.hotkey_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        trigger_frame = ttk.LabelFrame(main_frame, text="Trigger Phrases", padding="5")
        trigger_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(trigger_frame, text="Start Translation:").grid(row=0, column=0, sticky=tk.W)
        self.start_translation_entry = ttk.Entry(trigger_frame)
        self.start_translation_entry.insert(0, self.config['translation_trigger'])
        self.start_translation_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(trigger_frame, text="Stop Translation:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.stop_translation_entry = ttk.Entry(trigger_frame)
        self.stop_translation_entry.insert(0, self.config['stop_translation'])
        self.stop_translation_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        ttk.Label(trigger_frame, text="Roblox Window Title:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.roblox_title_entry = ttk.Entry(trigger_frame)
        self.roblox_title_entry.insert(0, self.config['roblox_window_title'])
        self.roblox_title_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        self.chinese_correct_var = tk.BooleanVar(value=self.config['enable_chinese_autocorrect'])
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
    
    def save_settings(self):
        self.config['translation_trigger'] = self.start_translation_entry.get()
        self.config['stop_translation'] = self.stop_translation_entry.get()
        self.config['roblox_window_title'] = self.roblox_title_entry.get()
        self.config['enable_chinese_autocorrect'] = self.chinese_correct_var.get()
        self.config['hotkey'] = self.hotkey_entry.get()
        self.config['model_name'] = self.model_combo.get()
        
        if self.save_config():
            try:
                keyboard.unhook_all()
                keyboard.hook(self._on_key_event)
                self.log_message("Settings saved successfully")
            except Exception as e:
                self.log_message(f"Error updating hotkey: {e}")
        else:
            self.log_message("Failed to save settings to file")
    
    def populate_microphones(self):
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append(f"{i}: {info['name']}")
        
        self.mic_combo['values'] = devices
        if devices:
            for device in devices:
                if device.startswith(str(self.config['mic_index'])):
                    self.mic_combo.set(device)
                    break
            else:
                self.mic_combo.set(devices[0])
    
    def load_model_async(self):
        def load_model():
            try:
                self.message_queue.put(("status", "Loading Whisper model..."))
                self.model = whisper.load_model(self.config['model_name'])
                self.message_queue.put(("status", "Model loaded successfully"))
                self.message_queue.put(("enable_controls", True))
            except Exception as e:
                self.message_queue.put(("error", f"Failed to load model: {e}"))
        
        threading.Thread(target=load_model, daemon=True).start()
    
    def setup_translation_async(self):
        def setup_translation():
            try:
                self.message_queue.put(("status", "Setting up translation..."))
                argostranslate.package.update_package_index()
                
                available_packages = argostranslate.package.get_available_packages()
                for pkg in available_packages:
                    if pkg.from_code == "en" and pkg.to_code == "zh":
                        argostranslate.package.install_from_path(pkg.download())
                        break
                
                self.message_queue.put(("log", "Translation setup complete"))
            except Exception as e:
                self.message_queue.put(("log", f"Translation setup failed: {e}"))
        
        threading.Thread(target=setup_translation, daemon=True).start()
    
    def setup_hotkey(self):
        try:
            keyboard.hook(self._on_key_event)
        except Exception as e:
            self.log_message(f"Hotkey setup failed: {e}")
    
    def _on_key_event(self, e):
        if e.name == self.config['hotkey'] and e.event_type == 'down':
            self.toggle_recording()
    
    def toggle_recording(self):
        if not self.model:
            messagebox.showwarning("Warning", "Model not loaded yet!")
            return
        
        self.is_recording = not self.is_recording
        
        if self.is_recording:
            self.record_button.config(text="Stop Recording (F2)")
            self.recording_indicator.config(text="🔴", foreground="red")
            self.start_recording()
        else:
            self.record_button.config(text="Start Recording (F2)")
            self.recording_indicator.config(text="⚫", foreground="gray")
    
    def start_recording(self):
        def record():
            try:
                frames = self.record_audio()
                if frames:
                    self.process_audio(frames)
            except Exception as e:
                self.message_queue.put(("error", f"Recording error: {e}"))
        
        threading.Thread(target=record, daemon=True).start()
    
    def record_audio(self):
        frames = []
        try:
            mic_selection = self.mic_combo.get()
            if mic_selection:
                mic_index = int(mic_selection.split(':')[0])
            else:
                mic_index = self.config['mic_index']
            
            self.stream = self.p.open(
                format=self.config['format'],
                channels=self.config['channels'],
                rate=self.config['rate'],
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=self.config['chunk']
            )
            
            self.message_queue.put(("log", "Recording... (press F2 to stop)"))
            
            while self.is_recording:
                try:
                    data = self.stream.read(self.config['chunk'])
                    frames.append(data)
                except OSError as e:
                    self.message_queue.put(("error", f"Audio error: {e}"))
                    break
                    
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        
        return frames
    
    def process_audio(self, frames):
        temp_path = None
        try:
            temp_path = self.save_temp_audio(frames)
            
            self.message_queue.put(("log", "Transcribing..."))
            result = self.model.transcribe(temp_path, task='transcribe', language=None)
            
            raw_text, lang = self.process_transcription(result)
            if raw_text is None:
                return
            
            corrected_text, corrections = self.correct_transcription(raw_text, lang)
            
            if self.check_trigger_phrases(corrected_text, lang):
                return
            
            if self.translation_mode and lang == 'en':
                translated_text = self.translate_to_chinese(corrected_text)
                self.message_queue.put(("log", f"Original: {corrected_text}"))
                self.message_queue.put(("log", f"Chinese: {translated_text}"))
                self.send_to_roblox(translated_text)
            else:
                self.message_queue.put(("log", f"Transcribed ({lang}): {corrected_text}"))
                self.send_to_roblox(corrected_text)
                
        except Exception as e:
            self.message_queue.put(("error", f"Processing error: {e}"))
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def save_temp_audio(self, frames):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            with wave.open(tf.name, 'wb') as wf:
                wf.setnchannels(self.config['channels'])
                wf.setsampwidth(self.p.get_sample_size(self.config['format']))
                wf.setframerate(self.config['rate'])
                wf.writeframes(b''.join(frames))
            return tf.name
    
    def process_transcription(self, result):
        detected_lang = result.get("language", "")
        raw_text = result["text"].strip()
        
        if detected_lang not in ['en', 'zh']:
            self.message_queue.put(("log", "Unsupported language detected. Please speak English or Chinese."))
            return None, None
        
        self.current_language = detected_lang
        return raw_text, detected_lang
    
    def correct_transcription(self, text, lang):
        if lang == 'zh' and self.config['enable_chinese_autocorrect']:
            result = self.corrector.correct(text)
            return result['target'], result.get('errors', [])
        return text, []
    
    def check_trigger_phrases(self, text, lang):
        if lang != 'en':
            return False
        
        trigger = self.config['translation_trigger'].lower()
        stop = self.config['stop_translation'].lower()
        
        if re.search(r'\b' + re.escape(trigger) + r'\b', text.lower()):
            self.translation_mode = True
            self.message_queue.put(("log", f"Translation mode activated by phrase: {trigger}"))
            self.update_translation_button()
            return True
        
        if re.search(r'\b' + re.escape(stop) + r'\b', text.lower()) and self.translation_mode:
            self.translation_mode = False
            self.message_queue.put(("log", f"Translation mode deactivated by phrase: {stop}"))
            self.update_translation_button()
            return True
        
        return False
        
    def translate_to_chinese(self, text):
        try:
            return argostranslate.translate.translate(text, "en", "zh")
        except Exception as e:
            self.message_queue.put(("error", f"Translation error: {e}"))
            return text
    
    def send_to_roblox(self, text):
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            
            if self.config['roblox_window_title'] not in title:
                self.message_queue.put(("log", "Roblox not focused. Message copied to clipboard."))
                pyperclip.copy(text)
                return
            
            pyperclip.copy(text)
            keyboard.press_and_release('/')
            time.sleep(0.1)
            keyboard.press_and_release('ctrl+v')
            time.sleep(0.1)
            keyboard.press_and_release('enter')
            
            self.message_queue.put(("log", "Message sent to Roblox"))
            
        except Exception as e:
            self.message_queue.put(("error", f"Failed to send to Roblox: {e}"))
            pyperclip.copy(text)
            self.message_queue.put(("log", "Message copied to clipboard instead"))
    
    def toggle_translation_mode(self):
        self.translation_mode = not self.translation_mode
        self.update_translation_button()
        status = "activated" if self.translation_mode else "deactivated"
        self.log_message(f"Translation mode {status}")
    
    def update_translation_button(self):
        status = "ON" if self.translation_mode else "OFF"
        self.translation_button.config(text=f"Translation Mode: {status}")
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def process_messages(self):
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
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.process_messages)
    
    def on_closing(self):
        try:
            keyboard.unhook_all()
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
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