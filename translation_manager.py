import threading
import argostranslate.package
import argostranslate.translate
from pycorrector import Corrector
import re

class TranslationManager:
    def __init__(self, config_manager, message_queue):
        self.config_manager = config_manager
        self.message_queue = message_queue
        self.corrector = Corrector()
        self.translation_mode = False
    
    def setup_translation_async(self):
        """Setup translation packages asynchronously"""
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
    
    def correct_transcription(self, text, lang):
        """Apply text correction based on language"""
        if lang == 'zh' and self.config_manager.get('enable_chinese_autocorrect'):
            result = self.corrector.correct(text)
            return result['target'], result.get('errors', [])
        return text, []
    
    def check_trigger_phrases(self, text, lang):
        """Check if text contains translation trigger phrases"""
        if lang != 'en':
            return False
        
        trigger = self.config_manager.get('translation_trigger').lower()
        stop = self.config_manager.get('stop_translation').lower()
        
        if re.search(r'\b' + re.escape(trigger) + r'\b', text.lower()):
            self.translation_mode = True
            self.message_queue.put(("log", f"Translation mode activated by phrase: {trigger}"))
            self.message_queue.put(("translation_mode_changed", True))
            return True
        
        if re.search(r'\b' + re.escape(stop) + r'\b', text.lower()) and self.translation_mode:
            self.translation_mode = False
            self.message_queue.put(("log", f"Translation mode deactivated by phrase: {stop}"))
            self.message_queue.put(("translation_mode_changed", False))
            return True
        
        return False
    
    def translate_to_chinese(self, text):
        """Translate English text to Chinese"""
        try:
            return argostranslate.translate.translate(text, "en", "zh")
        except Exception as e:
            self.message_queue.put(("error", f"Translation error: {e}"))
            return text
    
    def toggle_translation_mode(self):
        """Toggle translation mode on/off"""
        self.translation_mode = not self.translation_mode
        status = "activated" if self.translation_mode else "deactivated"
        self.message_queue.put(("log", f"Translation mode {status}"))
        self.message_queue.put(("translation_mode_changed", self.translation_mode))
        return self.translation_mode
    
    def is_translation_active(self):
        """Check if translation mode is active"""
        return self.translation_mode