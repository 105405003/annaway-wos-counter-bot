"""
Audio Player Module
Manages and plays counting audio files
"""
import discord
import os
import asyncio
from typing import Optional
from utils.config import AUDIO_DIR

class AudioPlayer:
    """Audio Player Class"""
    
    def __init__(self, audio_dir: str = AUDIO_DIR):
        self.audio_dir = audio_dir
        self.current_source: Optional[discord.FFmpegPCMAudio] = None
        
    def get_audio_path(self, number: int) -> Optional[str]:
        """
        Get audio path for specific number
        Countdown: 3, 2, 1, 0
        Count up: 1, 2... 100
        """
        if number <= 0:
            # Countdown: -3 -> 3, -2 -> 2...
            base_name = f"{abs(number)}"
        else:
            # Count up: 1 -> 1p, 2 -> 2p...
            base_name = f"{number}p"
            
        # Check for .mp3 first (gTTS output), then .wav
        for ext in ['.mp3', '.wav']:
            filename = f"{base_name}{ext}"
            path = os.path.join(self.audio_dir, filename)
            if os.path.exists(path):
                return path
        
        print(f"⚠️ Audio file not found for number: {number}")
        return None
    
    async def play_audio(self, voice_client: discord.VoiceClient, 
                        number: int) -> bool:
        """
        Play audio for specific number
        
        Args:
            voice_client: Discord Voice Client
            number: Number to play
            
        Returns:
            bool: Success
        """
        audio_path = self.get_audio_path(number)
        
        if not audio_path:
            print(f"⚠️ Audio file missing: {number}")
            return False
            
        try:
            # Stop current playing
            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(0.05)  # Brief wait
                
            # Use FFmpeg volume filter (200%)
            ffmpeg_options = {
                'options': '-filter:a "volume=2"'
            }
            
            source = discord.FFmpegPCMAudio(
                audio_path,
                executable=self._find_ffmpeg(),
                **ffmpeg_options
            )
            
            # Create event for playback completion
            done_event = asyncio.Event()
            
            def after_playing(error):
                if error:
                    print(f"❌ Playback error ({number}): {error}")
                else:
                    pass # print(f"✅ Playback complete ({number})")
                done_event.set()
            
            # Start playing
            voice_client.play(source, after=after_playing)
            # print(f"🎵 Playing: {number} ({audio_path})")
            
            # Wait for completion
            await done_event.wait()
                
            return True
            
        except Exception as e:
            print(f"❌ Playback failed ({number}): {e}")
            return False
    
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable"""
        import shutil
        
        # Use system ffmpeg
        system_ffmpeg = shutil.which('ffmpeg')
        if system_ffmpeg:
            return system_ffmpeg
        
        # Default
        return 'ffmpeg'
    
    def cleanup(self):
        """Cleanup resources"""
        if self.current_source:
            self.current_source.cleanup()
            self.current_source = None
