import pyaudio, wave, tempfile, whisper, msvcrt, os
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

def clear_keyboard_buffer():
    while msvcrt.kbhit():
        msvcrt.getch()

try:
    while True:
        print(f"\nCurrent language: {'Chinese' if current_language == 'zh' else 'English'}")
        print("Press Enter to start recording...")
        clear_keyboard_buffer()
        while not (msvcrt.kbhit() and msvcrt.getch() == b'\r'):
            pass
                
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, input_device_index=MIC_INDEX,
                        frames_per_buffer=CHUNK)
        
        frames = []
        print("Recording... press Enter to stop.")
        clear_keyboard_buffer()
        
        while True:
            try:
                frames.append(stream.read(CHUNK))
            except OSError as e:
                print(f"Audio error: {e}")
                break
                
            if msvcrt.kbhit() and msvcrt.getch() == b'\r':
                break

        stream.stop_stream()
        stream.close()

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
                temp_path,
                task='transcribe',
                language=None
            )
            detected_lang = res.get("language", "")
            raw = res["text"].strip()

            if detected_lang not in ['en', 'zh']:
                if detected_lang:
                    print(f"\n⚠️ Unsupported language detected: {detected_lang}")
                else:
                    print("\n⚠️ No language detected")
                print("Please speak English or Chinese")
                continue

            current_language = detected_lang
            print(f"\nDetected language: {'Chinese' if detected_lang == 'zh' else 'English'}")

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

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    p.terminate()