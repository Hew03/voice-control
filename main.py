import pyaudio
import wave
import tempfile
import whisper
import os
import keyboard
from pycorrector import Corrector

p = pyaudio.PyAudio()

for i in range(p.get_device_count()):
    d = p.get_device_info_by_index(i)
    if d['maxInputChannels'] > 0:
        print(i, d['name'], "-", d['defaultSampleRate'])

MIC_INDEX = 4
RATE = 48000
CHUNK = 4096
FORMAT = pyaudio.paInt16
CHANNELS = 1

model = whisper.load_model("base")
corrector = Corrector()
current_language = 'en'
is_recording = False


def toggle_recording():
    global is_recording
    is_recording = not is_recording


keyboard.add_hotkey('enter', toggle_recording)

try:
    print("\nPress Enter to start/stop recording (works globally)")
    print("Current language:", 'Chinese' if current_language == 'zh' else 'English')

    while True:
        if is_recording:
            print("\nRecording... (press Enter to stop)")
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=MIC_INDEX,
                frames_per_buffer=CHUNK
            )
            frames = []

            while is_recording:
                try:
                    frames.append(stream.read(CHUNK))
                except OSError as e:
                    print(f"Audio error: {e}")

            stream.stop_stream()
            stream.close()
            is_recording = False

            temp_path = None
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                temp_path = tf.name

            try:
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(p.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))

                res = model.transcribe(
                    temp_path, task='transcribe', language=None)
                detected_lang = res.get("language", "")
                raw = res["text"].strip()

                if detected_lang not in ['en', 'zh']:
                    print(
                        f"\n⚠️ Unsupported language: {detected_lang}" if detected_lang else "\n⚠️ No language detected")
                    print("Please speak English or Chinese")
                    continue

                current_language = detected_lang
                print(
                    f"\nDetected language: {'Chinese' if detected_lang == 'zh' else 'English'}")

                if detected_lang == 'zh':
                    print("📝 Raw transcript:", raw)
                    out = corrector.correct(raw)
                    corrected = out['target']
                    details = out.get('errors', [])

                    print("✅ Corrected:", corrected)
                    if details:
                        print("🔍 Corrections applied:")
                        for bad, good, idx in details:
                            print(f"  • '{bad}' → '{good}' @ idx {idx}")
                else:
                    print("Transcript:", raw)

            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

            print("\nPress Enter to start recording again...")

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    p.terminate()
    keyboard.unhook_all_hotkeys()