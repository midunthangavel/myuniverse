"""
Server-Side Neural Voice Engine using Microsoft Edge-TTS
Generates natural, human-like expressive neural speech without API keys.
"""

import io
import base64
import edge_tts
from typing import AsyncGenerator

# Curated High-Fidelity Neural Voices
AVAILABLE_VOICES = {
    "aria": "en-US-AriaNeural",           # Clear, professional, expressive female
    "guy": "en-US-GuyNeural",             # Natural, warm male
    "christopher": "en-US-ChristopherNeural", # Energetic, modern male
    "jenny": "en-US-JennyNeural"          # Friendly, conversational female
}

DEFAULT_VOICE = "en-US-AriaNeural"

class NeuralTTS:
    def __init__(self, default_voice: str = DEFAULT_VOICE):
        self.default_voice = default_voice

    async def generate_audio_stream(self, text: str, voice: str = None) -> AsyncGenerator[bytes, None]:
        selected_voice = voice or self.default_voice
        communicate = edge_tts.Communicate(text, selected_voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    async def generate_audio_base64(self, text: str, voice: str = None) -> str:
        selected_voice = voice or self.default_voice
        communicate = edge_tts.Communicate(text, selected_voice)
        audio_buffer = bytearray()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.extend(chunk["data"])
        
        b64_audio = base64.b64encode(audio_buffer).decode("utf-8")
        return f"data:audio/mp3;base64,{b64_audio}"
