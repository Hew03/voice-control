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

MIC_INDEX = 4
RATE = 48000
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
MODEL_NAME = "base"
HOTKEY = 'f2'
TRANSLATION_TRIGGER_PHRASE = "translate to chinese"
ROBLOX_WINDOW_TITLE = "Roblox"

class VoiceTranscriber:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.model = whisper.load_model(MODEL_NAME)
        self.corrector = Corrector()
        self.current_language = 'en'
        self.is_recording = False
        self.stream = None
        self.translation_mode = False
        self.setup_translation()
        keyboard.hook(self._on_key_event)

    def _on_key_event(self, e):
        """Global hook callback for all key events."""
        if e.name == HOTKEY and e.event_type == 'down':
            self.toggle_recording()

    def setup_translation(self):
        argostranslate.package.update_package_index()
        for pkg in argostranslate.package.get_available_packages():
            if pkg.from_code == "en" and pkg.to_code == "zh":
                argostranslate.package.install_from_path(pkg.download())
                break
        
    def translate_to_chinese(self, text):
        """Translate English text to Chinese"""
        return argostranslate.translate.translate(text, "en", "zh")
    
    def list_audio_devices(self):
        """List available audio input devices"""
        print("\nAvailable input devices:")
        for i in range(self.p.get_device_count()):
            d = self.p.get_device_info_by_index(i)
            if d['maxInputChannels'] > 0:
                print(f"{i}: {d['name']} - {d['defaultSampleRate']}Hz")
    
    def start_audio_stream(self):
        """Initialize and start audio input stream"""
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK
        )
    
    def toggle_recording(self):
        """Toggle recording state"""
        self.is_recording = not self.is_recording
    
    def record_audio(self):
        """Capture audio while recording is active"""
        frames = []
        print("\nRecording... (press F2 to stop)")
        
        try:
            self.start_audio_stream()
            while self.is_recording:
                try:
                    frames.append(self.stream.read(CHUNK))
                except OSError as e:
                    print(f"Audio error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        
        return frames
    
    def save_temp_audio(self, frames):
        """Save recorded frames to temporary WAV file"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            with wave.open(tf.name, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            return tf.name
    
    def transcribe_audio(self, file_path):
        """Transcribe audio using Whisper model"""
        return self.model.transcribe(file_path, task='transcribe', language=None)
    
    def correct_transcription(self, text, lang):
        """Apply text correction based on detected language"""
        if lang == 'zh':
            result = self.corrector.correct(text)
            return result['target'], result.get('errors', [])
        return text, []
    
    def process_transcription(self, res):
        """Handle transcription results and corrections"""
        detected_lang = res.get("language", "")
        raw_text = res["text"].strip()

        if detected_lang not in ['en', 'zh']:
            print(f"\n⚠️ {'Unsupported language' if detected_lang else 'No language detected'}")
            print("Please speak English or Chinese")
            return None, None

        self.current_language = detected_lang
        lang_name = 'Chinese' if detected_lang == 'zh' else 'English'
        print(f"\nDetected language: {lang_name}")
        
        return raw_text, detected_lang
    
    def print_results(self, raw_text, corrected_text, corrections, lang):
        """Print transcription results with formatting"""
        if lang == 'zh':
            print("📝 Raw transcript:", raw_text)
            print("✅ Corrected:", corrected_text)
            if corrections:
                print("🔍 Corrections applied:")
                for bad, good, idx in corrections:
                    print(f"  • '{bad}' → '{good}' @ position {idx}")
        else:
            print("📝 Transcript:", corrected_text)
    
    def cleanup_temp_file(self, file_path):
        """Remove temporary audio file"""
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)

    def normalize_text(self, text):
        """Normalize text for comparison: lowercase and remove non-alphabetic chars"""
        text = text.lower()
        text = re.sub(r'[^a-z]', '', text)
        return text

    def is_roblox_focused(self):
        """Check if Roblox is the currently focused window"""
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            return ROBLOX_WINDOW_TITLE in title
        except Exception:
            return False

    def send_to_roblox(self, text):
        """Send text to Roblox chat using simulated keystrokes"""
        if not self.is_roblox_focused():
            print("Roblox not focused. Message not sent.")
            return False

        pyperclip.copy(text)
        
        keyboard.press('/')
        keyboard.release('/')
        time.sleep(0.1)
        
        keyboard.press('ctrl')
        keyboard.press('v')
        keyboard.release('v')
        keyboard.release('ctrl')
        time.sleep(0.1)
        
        keyboard.press('enter')
        keyboard.release('enter')
        
        print("Message sent to Roblox")
        return True

    def run(self):
        print(f"\nPress {HOTKEY} to start/stop recording")
        try:
            while True:
                if self.is_recording:
                    frames = self.record_audio()
                    self.is_recording = False

                    temp_path = self.save_temp_audio(frames)
                    try:
                        res = self.transcribe_audio(temp_path)
                        raw_text, lang = self.process_transcription(res)
                        if raw_text is None:
                            continue
                        corrected_text, corrections = self.correct_transcription(raw_text, lang)

                        normalized_input = self.normalize_text(corrected_text)
                        normalized_trigger = self.normalize_text(TRANSLATION_TRIGGER_PHRASE)

                        if lang == 'en' and normalized_trigger in normalized_input:
                            self.translation_mode = True
                            print("\n🔁 Translation mode activated. Next English input will be translated.")
                            continue

                        if self.translation_mode and lang == 'en':
                            translated_text = self.translate_to_chinese(corrected_text)
                            print("\n🌐 Translation to Chinese:")
                            print(translated_text)
                            self.translation_mode = False
                            self.send_to_roblox(translated_text)
                        else:
                            self.print_results(raw_text, corrected_text, corrections, lang)
                            self.send_to_roblox(corrected_text)

                    finally:
                        self.cleanup_temp_file(temp_path)
                        print(f"\nPress {HOTKEY} to start recording again...")

        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            keyboard.unhook_all()
            self.p.terminate()

if __name__ == "__main__":
    transcriber = VoiceTranscriber()
    transcriber.list_audio_devices()    
    transcriber.run()