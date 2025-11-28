import os
import sys
from gtts import gTTS
import time

def generate_audio(output_dir="assets/audio", lang="en"):
    """
    Generate audio files for counting bot
    
    Args:
        output_dir: Output directory path (default: assets/audio)
        lang: Language code (en for English, zh-TW for Chinese)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Starting audio generation in {output_dir}...")
    print(f"Language: {lang}")
    
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
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filename)
        time.sleep(0.5) # Avoid rate limiting
        
    # 2. Generate Count Up (1 to 100)
    # Filenames: 1p.mp3, 2p.mp3 ... 100p.mp3
    for i in range(1, 101):
        filename = os.path.join(output_dir, f"{i}p.mp3")
        text = str(i)
        print(f"Generating {filename} ('{text}')...")
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filename)
        
        if i % 10 == 0:
            print(f"Progress: {i}/100")
            time.sleep(1) # Avoid rate limiting
            
    print("✅ All audio files generated successfully!")

if __name__ == "__main__":
    try:
        # Get output directory from command line argument or use default
        output_dir = sys.argv[1] if len(sys.argv) > 1 else "assets/audio_en"
        lang = sys.argv[2] if len(sys.argv) > 2 else "en"
        
        print(f"Output directory: {output_dir}")
        print(f"Language: {lang}")
        generate_audio(output_dir, lang)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure to install gTTS: pip install gTTS")
        print("\nUsage: python tools/generate_audio.py [output_dir] [lang]")
        print("Example: python tools/generate_audio.py assets/audio_en en")
