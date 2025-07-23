import pyaudio
import wave
import tempfile
import whisper
import os
import keyboard
from pycorrector import Corrector

# Configuration Constants
MIC_INDEX = 4
RATE = 48000
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1
MODEL_NAME = "base"
HOTKEY = 'enter'

class VoiceTranscriber:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.model = whisper.load_model(MODEL_NAME)
        self.corrector = Corrector()
        self.current_language = 'en'
        self.is_recording = False
        self.stream = None
        
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
        print("\nRecording... (press Enter to stop)")
        
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

        # Handle unsupported languages
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
    
    def run(self):
        """Main application loop"""
        keyboard.add_hotkey(HOTKEY, self.toggle_recording)
        print(f"\nPress {HOTKEY} to start/stop recording (works globally)")
        
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
                            
                        corrected_text, corrections = self.correct_transcription(
                            raw_text, lang
                        )
                        
                        self.print_results(
                            raw_text, corrected_text, corrections, lang
                        )
                    
                    finally:
                        self.cleanup_temp_file(temp_path)
                    
                    print(f"\nPress {HOTKEY} to start recording again...")
        
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            self.p.terminate()
            keyboard.unhook_all_hotkeys()


if __name__ == "__main__":
    transcriber = VoiceTranscriber()
    transcriber.list_audio_devices()
    transcriber.run()