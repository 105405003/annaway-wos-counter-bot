import os
from gtts import gTTS
import time

def generate_audio():
    """
    Generate English audio files for counting bot
    """
    output_dir = "assets/audio"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting audio generation in {output_dir}...")
    
    # 1. Generate Countdown (3, 2, 1, 0)
    # Filenames: 3.mp3, 2.mp3, 1.mp3, 0.mp3
    countdown_map = {
        3: "Three",
        2: "Two",
        1: "One",
        0: "Zero"
    }
    
    for num, text in countdown_map.items():
        filename = os.path.join(output_dir, f"{num}.mp3")
        print(f"Generating {filename} ('{text}')...")
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        time.sleep(0.5) # Avoid rate limiting
        
    # 2. Generate Count Up (1 to 100)
    # Filenames: 1p.mp3, 2p.mp3 ... 100p.mp3
    for i in range(1, 101):
        filename = os.path.join(output_dir, f"{i}p.mp3")
        text = str(i)
        print(f"Generating {filename} ('{text}')...")
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        
        if i % 10 == 0:
            print(f"Progress: {i}/100")
            time.sleep(1) # Avoid rate limiting
            
    print("✅ All audio files generated successfully!")

if __name__ == "__main__":
    try:
        generate_audio()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure to install gTTS: pip install gTTS")
