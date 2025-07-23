import pyaudio
import wave
import tempfile
import whisper
import os
import threading

class AudioHandler:
    def __init__(self, config_manager, message_queue):
        self.config_manager = config_manager
        self.message_queue = message_queue
        self.p = pyaudio.PyAudio()
        self.model = None
        self.stream = None
        self.is_recording = False
    
    def get_audio_devices(self):
        """Get list of available audio input devices"""
        devices = []
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append(f"{i}: {info['name']}")
        return devices
    
    def load_model_async(self):
        """Load Whisper model asynchronously"""
        def load_model():
            try:
                self.message_queue.put(("status", "Loading Whisper model..."))
                self.model = whisper.load_model(self.config_manager.get('model_name'))
                self.message_queue.put(("status", "Model loaded successfully"))
                self.message_queue.put(("enable_controls", True))
            except Exception as e:
                self.message_queue.put(("error", f"Failed to load model: {e}"))
        
        threading.Thread(target=load_model, daemon=True).start()
    
    def start_recording(self, mic_index=None):
        """Start recording audio"""
        if not self.model:
            self.message_queue.put(("error", "Model not loaded yet!"))
            return False
        
        def record():
            try:
                frames = self.record_audio(mic_index)
                if frames:
                    self.process_audio(frames)
            except Exception as e:
                self.message_queue.put(("error", f"Recording error: {e}"))
        
        threading.Thread(target=record, daemon=True).start()
        return True
    
    def record_audio(self, mic_index=None):
        """Record audio frames"""
        frames = []
        try:
            if mic_index is None:
                mic_index = self.config_manager.get('mic_index')
            
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.config_manager.get('channels'),
                rate=self.config_manager.get('rate'),
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=self.config_manager.get('chunk')
            )
            
            self.message_queue.put(("log", "Recording... (press F2 to stop)"))
            self.is_recording = True
            
            while self.is_recording:
                try:
                    data = self.stream.read(self.config_manager.get('chunk'))
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
    
    def stop_recording(self):
        """Stop recording audio"""
        self.is_recording = False
    
    def save_temp_audio(self, frames):
        """Save audio frames to temporary WAV file"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            with wave.open(tf.name, 'wb') as wf:
                wf.setnchannels(self.config_manager.get('channels'))
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.config_manager.get('rate'))
                wf.writeframes(b''.join(frames))
            return tf.name
    
    def process_audio(self, frames):
        """Process recorded audio frames and transcribe"""
        temp_path = None
        try:
            temp_path = self.save_temp_audio(frames)
            
            self.message_queue.put(("log", "Transcribing..."))
            result = self.model.transcribe(temp_path, task='transcribe', language=None)
            
            raw_text, lang = self.process_transcription(result)
            if raw_text is None:
                return
            
            self.message_queue.put(("audio_processed", (raw_text, lang)))
                
        except Exception as e:
            self.message_queue.put(("error", f"Processing error: {e}"))
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def process_transcription(self, result):
        """Process Whisper transcription result"""
        detected_lang = result.get("language", "")
        raw_text = result["text"].strip()
        
        if detected_lang not in ['en', 'zh']:
            self.message_queue.put(("log", "Unsupported language detected. Please speak English or Chinese."))
            return None, None
        
        return raw_text, detected_lang
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
        except:
            pass