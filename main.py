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
import logging
import warnings

warnings.filterwarnings("ignore")

MIC_INDEX = 4
RATE = 48000
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
MODEL_NAME = "base"
HOTKEY = 'f2'
TRANSLATION_TRIGGER_PHRASE = "translate to chinese"
STOP_TRANSLATION_PHRASE = "stop translation"
ROBLOX_WINDOW_TITLE = "Roblox"
DEBUG_MODE = True
ENABLE_CHINESE_AUTOCORRECT = False

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.CRITICAL,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        if e.name == HOTKEY and e.event_type == 'down':
            self.toggle_recording()

    def setup_translation(self):
        argostranslate.package.update_package_index()
        for pkg in argostranslate.package.get_available_packages():
            if pkg.from_code == "en" and pkg.to_code == "zh":
                argostranslate.package.install_from_path(pkg.download())
                break

    def translate_to_chinese(self, text):
        return argostranslate.translate.translate(text, "en", "zh")

    def list_audio_devices(self):
        logger.info("Available input devices:")
        for i in range(self.p.get_device_count()):
            d = self.p.get_device_info_by_index(i)
            if d['maxInputChannels'] > 0:
                logger.info(f"{i}: {d['name']} - {d['defaultSampleRate']}Hz")

    def start_audio_stream(self):
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK
        )

    def toggle_recording(self):
        self.is_recording = not self.is_recording

    def record_audio(self):
        frames = []
        logger.info("Recording... (press F2 to stop)")
        try:
            self.start_audio_stream()
            while self.is_recording:
                try:
                    frames.append(self.stream.read(CHUNK))
                except OSError as e:
                    logger.error(f"Audio error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
        return frames

    def save_temp_audio(self, frames):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            with wave.open(tf.name, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            return tf.name

    def transcribe_audio(self, file_path):
        return self.model.transcribe(file_path, task='transcribe', language=None)

    def correct_transcription(self, text, lang):
        if lang == 'zh' and ENABLE_CHINESE_AUTOCORRECT:
            result = self.corrector.correct(text)
            return result['target'], result.get('errors', [])
        return text, []

    def process_transcription(self, res):
        detected_lang = res.get("language", "")
        raw_text = res["text"].strip()
        if detected_lang not in ['en', 'zh']:
            logger.warning(f"{'Unsupported language' if detected_lang else 'No language detected'}")
            logger.warning("Please speak English or Chinese")
            return None, None
        self.current_language = detected_lang
        logger.info(f"Detected language: {'Chinese' if detected_lang == 'zh' else 'English'}")
        return raw_text, detected_lang

    def print_results(self, raw_text, corrected_text, corrections, lang):
        if lang == 'zh':
            logger.info("Raw transcript: %s", raw_text)
            logger.info("Corrected: %s", corrected_text)
            if corrections and ENABLE_CHINESE_AUTOCORRECT:
                logger.info("Corrections applied:")
                for bad, good, idx in corrections:
                    logger.info(f"  • '{bad}' → '{good}' @ position {idx}")
        else:
            logger.info("Transcript: %s", corrected_text)

    def cleanup_temp_file(self, file_path):
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)

    def normalize_text(self, text):
        text = text.lower()
        text = re.sub(r'[^a-z]', '', text)
        return text

    def check_trigger_phrases(self, text, lang):
        normalized_text = self.normalize_text(text)
        normalized_trigger = self.normalize_text(TRANSLATION_TRIGGER_PHRASE)
        normalized_stop = self.normalize_text(STOP_TRANSLATION_PHRASE)
        
        if lang == 'en':
            if normalized_trigger in normalized_text:
                self.translation_mode = True
                logger.info("Translation mode activated. All English will be translated until 'stop translation' is said.")
                return True
            if normalized_stop in normalized_text and self.translation_mode:
                self.translation_mode = False
                logger.info("Translation mode deactivated.")
                return True
        return False

    def is_roblox_focused(self):
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            return ROBLOX_WINDOW_TITLE in title
        except Exception:
            return False

    def send_to_roblox(self, text):
        if not self.is_roblox_focused():
            logger.warning("Roblox not focused. Message not sent.")
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
        logger.info("Message sent to Roblox")
        return True

    def run(self):
        logger.info(f"Press {HOTKEY} to start/stop recording")
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
                        
                        if self.check_trigger_phrases(corrected_text, lang):
                            continue
                            
                        if self.translation_mode and lang == 'en':
                            translated_text = self.translate_to_chinese(corrected_text)
                            logger.info("Translation to Chinese:")
                            logger.info(translated_text)
                            self.send_to_roblox(translated_text)
                        else:
                            self.print_results(raw_text, corrected_text, corrections, lang)
                            self.send_to_roblox(corrected_text)
                            
                    finally:
                        self.cleanup_temp_file(temp_path)
                        logger.info(f"Press {HOTKEY} to start recording again...")
        except KeyboardInterrupt:
            logger.info("Exiting...")
        finally:
            keyboard.unhook_all()
            self.p.terminate()

if __name__ == "__main__":
    transcriber = VoiceTranscriber()
    transcriber.list_audio_devices()
    transcriber.run()