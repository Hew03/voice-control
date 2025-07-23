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

def clear_keyboard_buffer():
    while msvcrt.kbhit():
        msvcrt.getch()

try:
    while True:
        print("\nPress Enter to start recording...")
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

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            temp_path = tf.name
        
        with wave.open(temp_path, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        res = model.transcribe(temp_path, language='zh', task='transcribe')
        os.unlink(temp_path)

        detected_lang = res.get("language", "")
        if detected_lang == 'zh':
            raw = res["text"].strip()
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
            print("⚠️ Detected language is not Chinese:", detected_lang)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    p.terminate()
