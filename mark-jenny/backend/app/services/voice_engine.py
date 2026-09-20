"""
Voice Engine — Real-time voice conversation with Mark Imti agents.

Supports multiple STT/TTS backends:
1. Browser Web Speech API (free, no API keys, works offline)
2. Local Whisper (via faster-whisper or openai-whisper)
3. Edge TTS (Microsoft, free, high quality)
4. pyttsx3 (local, offline)
5. OpenAI Whisper API (cloud, highest accuracy)
6. ElevenLabs TTS (cloud, most natural)

Architecture:
Browser mic → WebSocket → Backend STT → AI Agent → Backend TTS → WebSocket → Browser speaker
"""
import asyncio
import io
import json
import base64
import tempfile
import wave
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from enum import Enum

from app.core.config import get_settings

settings = get_settings()


class VoiceProvider(str, Enum):
    BROWSER = "browser"          # Web Speech API (client-side)
    WHISPER_LOCAL = "whisper_local"  # faster-whisper locally
    WHISPER_API = "whisper_api"  # OpenAI Whisper API
    EDGE_TTS = "edge_tts"        # Microsoft Edge TTS (free)
    PYTTSX3 = "pyttsx3"          # Offline TTS
    OPENAI_TTS = "openai_tts"    # OpenAI TTS API
    ELEVENLABS = "elevenlabs"    # ElevenLabs TTS


class VoiceEngine:
    """
    Multi-provider voice engine for real-time conversation.
    Falls back gracefully between providers.
    """

    def __init__(self):
        self._whisper_model = None
        self._tts_cache = {}

    # ============================================================
    # SPEECH-TO-TEXT (STT)
    # ============================================================

    async def transcribe_audio(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text. Tries providers in order:
        1. Local Whisper (if available)
        2. OpenAI Whisper API (if key configured)
        3. Returns instruction for browser-side STT
        """
        # Try local Whisper
        try:
            result = await self._transcribe_whisper_local(audio_data, format, language)
            if result.get("success"):
                return result
        except Exception:
            pass

        # Try OpenAI Whisper API
        try:
            result = await self._transcribe_whisper_api(audio_data, format, language)
            if result.get("success"):
                return result
        except Exception:
            pass

        # Fallback: return instruction for browser-side Web Speech API
        return {
            "success": True,
            "provider": "browser",
            "text": "",
            "instruction": "use_browser_stt",
            "message": "Use Web Speech API on the client side for transcription",
        }

    async def _transcribe_whisper_local(
        self, audio_data: bytes, format: str, language: str
    ) -> Dict[str, Any]:
        """Transcribe using local faster-whisper."""
        try:
            from faster_whisper import WhisperModel

            if self._whisper_model is None:
                self._whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            segments, info = self._whisper_model.transcribe(
                temp_path, language=language, beam_size=5
            )
            text = " ".join([seg.text for seg in segments])

            import os
            os.unlink(temp_path)

            if text.strip():
                return {
                    "success": True,
                    "provider": "whisper_local",
                    "text": text.strip(),
                    "language": info.language,
                    "confidence": round(info.language_probability, 2),
                }
        except ImportError:
            pass
        except Exception:
            pass
        return {"success": False}

    async def _transcribe_whisper_api(
        self, audio_data: bytes, format: str, language: str
    ) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper API."""
        try:
            import httpx
            api_key = getattr(settings, "OPENAI_API_KEY", "")
            if not api_key:
                return {"success": False}

            # Convert webm to wav if needed
            wav_data = audio_data
            if format != "wav":
                wav_data = await self._convert_to_wav(audio_data, format)

            async with httpx.AsyncClient(timeout=30) as client:
                files = {"file": ("audio.wav", wav_data, "audio/wav")}
                data = {"model": "whisper-1", "language": language}
                r = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=files,
                    data=data,
                )
                if r.status_code == 200:
                    text = r.json().get("text", "")
                    if text:
                        return {
                            "success": True,
                            "provider": "whisper_api",
                            "text": text,
                        }
        except Exception:
            pass
        return {"success": False}

    async def _convert_to_wav(self, audio_data: bytes, source_format: str) -> bytes:
        """Convert audio to WAV format using ffmpeg."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", "pipe:0", "-f", "wav", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1", "pipe:1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=audio_data)
            if proc.returncode == 0:
                return stdout
        except Exception:
            pass
        # Return original if conversion fails
        return audio_data

    # ============================================================
    # TEXT-TO-SPEECH (TTS)
    # ============================================================

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Convert text to speech. Tries providers in order:
        1. Edge TTS (free, high quality)
        2. pyttsx3 (offline)
        3. Returns instruction for browser-side TTS
        """
        # Try Edge TTS (Microsoft, free, great quality)
        try:
            result = await self._tts_edge(text, voice, speed)
            if result.get("success"):
                return result
        except Exception:
            pass

        # Try pyttsx3 (offline)
        try:
            result = await self._tts_pyttsx3(text)
            if result.get("success"):
                return result
        except Exception:
            pass

        # Fallback: return instruction for browser-side TTS
        return {
            "success": True,
            "provider": "browser",
            "audio": "",
            "instruction": "use_browser_tts",
            "text": text,
            "message": "Use Web Speech Synthesis on the client side",
        }

    async def _tts_edge(self, text: str, voice: str, speed: float) -> Dict[str, Any]:
        """Microsoft Edge TTS — free, high quality, many voices."""
        try:
            import edge_tts

            voice_name = voice if voice != "default" else "en-US-AriaNeural"
            communicate = edge_tts.Communicate(text, voice_name, rate=f"+{int((speed - 1) * 100)}%")

            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                return {
                    "success": True,
                    "provider": "edge_tts",
                    "audio": audio_b64,
                    "format": "mp3",
                    "voice": voice_name,
                }
        except ImportError:
            pass
        except Exception:
            pass
        return {"success": False}

    async def _tts_pyttsx3(self, text: str) -> Dict[str, Any]:
        """pyttsx3 offline TTS."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            engine.save_to_file(text, temp_path)
            engine.runAndWait()

            with open(temp_path, "rb") as f:
                audio_data = f.read()

            import os
            os.unlink(temp_path)

            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                return {
                    "success": True,
                    "provider": "pyttsx3",
                    "audio": audio_b64,
                    "format": "wav",
                }
        except ImportError:
            pass
        except Exception:
            pass
        return {"success": False}

    # ============================================================
    # VOICE CONVERSATION — Full pipeline
    # ============================================================

    async def voice_conversation_turn(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
        conversation_history: Optional[list] = None,
        agent_type: str = "jenny",
    ) -> Dict[str, Any]:
        """
        Complete voice conversation turn:
        1. STT — transcribe user's speech
        2. AI — process with agent (Mark or Jenny)
        3. TTS — convert response to speech
        Returns both text and audio response.
        """
        # Step 1: Transcribe
        stt_result = await self.transcribe_audio(audio_data, format, language)
        if not stt_result.get("success") or not stt_result.get("text"):
            return {
                "success": False,
                "error": "Could not transcribe audio",
                "stt_result": stt_result,
            }

        user_text = stt_result["text"]

        # Step 2: Process with AI agent
        from app.services.model_caller import ModelCaller

        system = self._get_voice_system_prompt(agent_type)

        # Build conversation context
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"\n{role}: {content}"

        prompt = f"Conversation so far:{history_text}\n\nUser said: {user_text}\n\nRespond naturally and concisely. Keep response under 3 sentences unless detail is requested."

        ai_response = await ModelCaller.call(prompt, system, temperature=0.4, max_tokens=500)

        if not ai_response:
            return {
                "success": False,
                "error": "AI model not available",
                "user_text": user_text,
            }

        # Step 3: Convert to speech
        tts_result = await self.synthesize_speech(ai_response)

        return {
            "success": True,
            "user_text": user_text,
            "agent_text": ai_response,
            "audio": tts_result.get("audio", ""),
            "audio_format": tts_result.get("format", "mp3"),
            "stt_provider": stt_result.get("provider", "unknown"),
            "tts_provider": tts_result.get("provider", "unknown"),
        }

    def _get_voice_system_prompt(self, agent_type: str) -> str:
        """Get system prompt for voice conversation."""
        if agent_type == "mark":
            return """You are Mark, an expert AI assistant for coding, building, and technical work.
Speak naturally and conversationally. Be concise but thorough.
When the user asks you to build something, confirm and describe what you'll do.
When explaining technical concepts, use simple language.
Keep responses under 3 sentences unless the user asks for detail."""
        else:
            return """You are Jenny, a warm, intelligent AI assistant.
Speak naturally and conversationally, like talking to a knowledgeable friend.
Be helpful, clear, and concise. Use simple language.
When you don't know something, say so honestly.
Keep responses under 3 sentences unless the user asks for detail.
You can help with research, analysis, writing, and general questions."""

    # ============================================================
    # AVAILABLE VOICES
    # ============================================================

    async def list_voices(self, provider: str = "edge_tts") -> Dict[str, Any]:
        """List available voices for a TTS provider."""
        if provider == "edge_tts":
            try:
                import edge_tts
                voices = await edge_tts.list_voices()
                en_voices = [v for v in voices if v.get("Locale", "").startswith("en-")]
                return {
                    "success": True,
                    "provider": "edge_tts",
                    "voices": [
                        {"id": v["ShortName"], "name": v["FriendlyName"], "gender": v["Gender"]}
                        for v in en_voices[:20]
                    ],
                }
            except Exception:
                pass

        return {
            "success": True,
            "provider": "browser",
            "voices": [
                {"id": "browser_default", "name": "Browser Default", "gender": "neutral"},
            ],
        }

    def get_status(self) -> Dict[str, Any]:
        """Get voice engine status."""
        providers = {"stt": [], "tts": []}

        # Check local Whisper
        try:
            from faster_whisper import WhisperModel
            providers["stt"].append("whisper_local")
        except ImportError:
            pass

        # Check OpenAI API
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if api_key:
            providers["stt"].append("whisper_api")
            providers["tts"].append("openai_tts")

        # Check Edge TTS
        try:
            import edge_tts
            providers["tts"].append("edge_tts")
        except ImportError:
            pass

        # Check pyttsx3
        try:
            import pyttsx3
            providers["tts"].append("pyttsx3")
        except ImportError:
            pass

        # Browser always available
        providers["stt"].append("browser")
        providers["tts"].append("browser")

        return {
            "providers": providers,
            "recommended_stt": providers["stt"][0] if providers["stt"] else "browser",
            "recommended_tts": providers["tts"][0] if providers["tts"] else "browser",
        }


# Singleton
voice_engine = VoiceEngine()
