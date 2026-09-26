"""
Voice WebSocket — Real-time voice conversation endpoint.
Handles streaming audio, STT, AI processing, and TTS.
"""
import asyncio
import json
import base64
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.voice_engine import voice_engine
from app.services.model_caller import ModelCaller

router = APIRouter()


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    Real-time voice conversation WebSocket.

    Protocol:
    Client sends JSON:
      {"type": "audio", "data": "<base64 audio>", "format": "webm", "language": "en"}
      {"type": "text", "text": "hello"}  (for text input during voice mode)
      {"type": "config", "agent": "imti", "voice": "en-US-AriaNeural"}

    Server sends JSON:
      {"type": "transcript", "text": "user said...", "role": "user"}
      {"type": "response", "text": "agent response...", "role": "assistant"}
      {"type": "audio", "data": "<base64 mp3>", "format": "mp3"}
      {"type": "status", "state": "listening|thinking|speaking"}
      {"type": "error", "message": "..."}
    """
    await websocket.accept()

    conversation_history = []
    agent_type = "imti"
    voice_name = "en-US-AriaNeural"

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            # ---- Configuration ----
            if msg_type == "config":
                agent_type = msg.get("agent", "imti")
                voice_name = msg.get("voice", "en-US-AriaNeural")
                await websocket.send_json({
                    "type": "status",
                    "state": "ready",
                    "agent": agent_type,
                    "voice": voice_name,
                    "providers": voice_engine.get_status()["providers"],
                })

            # ---- Audio input (STT → AI → TTS) ----
            elif msg_type == "audio":
                await websocket.send_json({"type": "status", "state": "thinking"})

                audio_b64 = msg.get("data", "")
                format = msg.get("format", "webm")
                language = msg.get("language", "en")

                if not audio_b64:
                    await websocket.send_json({"type": "error", "message": "No audio data"})
                    continue

                # Decode base64 audio
                try:
                    audio_data = base64.b64decode(audio_b64)
                except Exception:
                    await websocket.send_json({"type": "error", "message": "Invalid audio data"})
                    continue

                # Run voice conversation turn
                result = await voice_engine.voice_conversation_turn(
                    audio_data=audio_data,
                    format=format,
                    language=language,
                    conversation_history=conversation_history,
                    agent_type=agent_type,
                )

                if result.get("success"):
                    user_text = result["user_text"]
                    agent_text = result["agent_text"]

                    # Send transcript
                    await websocket.send_json({
                        "type": "transcript",
                        "text": user_text,
                        "role": "user",
                    })

                    # Send response text
                    await websocket.send_json({
                        "type": "response",
                        "text": agent_text,
                        "role": "assistant",
                    })

                    # Send audio if available
                    if result.get("audio"):
                        await websocket.send_json({
                            "type": "audio",
                            "data": result["audio"],
                            "format": result.get("audio_format", "mp3"),
                        })

                    # Update conversation history
                    conversation_history.append({"role": "user", "content": user_text})
                    conversation_history.append({"role": "assistant", "content": agent_text})

                    # Keep history manageable
                    if len(conversation_history) > 20:
                        conversation_history = conversation_history[-12:]

                    await websocket.send_json({"type": "status", "state": "listening"})
                else:
                    # If STT failed, try using the browser's built-in STT
                    error = result.get("error", "Unknown error")
                    if result.get("stt_result", {}).get("instruction") == "use_browser_stt":
                        await websocket.send_json({
                            "type": "status",
                            "state": "use_browser_stt",
                            "message": "Switch to browser-side transcription",
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Voice processing failed: {error}",
                        })

            # ---- Text input during voice mode ----
            elif msg_type == "text":
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                await websocket.send_json({"type": "status", "state": "thinking"})

                # Send transcript
                await websocket.send_json({
                    "type": "transcript",
                    "text": user_text,
                    "role": "user",
                })

                # Process with AI
                system = voice_engine._get_voice_system_prompt(agent_type)
                history_text = ""
                for h in conversation_history[-6:]:
                    history_text += f"\n{h['role']}: {h['content']}"

                prompt = f"Conversation so far:{history_text}\n\nUser said: {user_text}\n\nRespond naturally and concisely."

                agent_text = await ModelCaller.call(prompt, system, temperature=0.4, max_tokens=500)

                if agent_text:
                    await websocket.send_json({
                        "type": "response",
                        "text": agent_text,
                        "role": "assistant",
                    })

                    # TTS
                    tts_result = await voice_engine.synthesize_speech(
                        agent_text, voice=voice_name
                    )
                    if tts_result.get("audio"):
                        await websocket.send_json({
                            "type": "audio",
                            "data": tts_result["audio"],
                            "format": tts_result.get("format", "mp3"),
                        })

                    conversation_history.append({"role": "user", "content": user_text})
                    conversation_history.append({"role": "assistant", "content": agent_text})

                await websocket.send_json({"type": "status", "state": "listening"})

            # ---- Ping/keepalive ----
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ============================================================
# REST endpoints for voice configuration
# ============================================================

@router.get("/status")
async def voice_status():
    """Get voice engine status and available providers."""
    return voice_engine.get_status()


@router.get("/voices")
async def list_voices(provider: str = "edge_tts"):
    """List available voices for a TTS provider."""
    return await voice_engine.list_voices(provider)


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    request: Request,
    audio: Optional[str] = None,
    format: str = "webm",
    language: str = "en",
):
    """Transcribe audio to text.

    Accepts either multipart/form-data (what the browser recorder actually
    sends) or a base64 `audio` field. Previously only a query/form string was
    accepted, so the browser upload always failed with 422.
    """
    import base64

    audio_bytes: Optional[bytes] = None
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("audio") or form.get("file")
        language = str(form.get("language") or language)
        fmt = str(form.get("format") or format)
        if upload is None:
            raise HTTPException(status_code=400, detail="No audio file in the request (expected field 'audio' or 'file').")
        if hasattr(upload, "read"):
            audio_bytes = await upload.read()
            filename = getattr(upload, "filename", "") or ""
            if not fmt or fmt == "webm":
                fmt = filename.rsplit(".", 1)[-1] if "." in filename else "webm"
        else:
            audio_bytes = base64.b64decode(str(upload))
    elif audio:
        try:
            audio_bytes = base64.b64decode(audio)
        except Exception:
            raise HTTPException(status_code=400, detail="`audio` must be base64 encoded.")
    else:
        raise HTTPException(status_code=400, detail="Send multipart/form-data with an `audio` file, or a base64 `audio` field.")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio payload was empty.")

    result = await voice_engine.transcribe_audio(audio_bytes, format, language)
    if isinstance(result, dict) and not result.get("success", True):
        raise HTTPException(status_code=503, detail=result.get("error") or "Transcription engine unavailable")
    return result


@router.post("/synthesize")
async def synthesize_speech_endpoint(
    text: str,
    voice: str = "default",
    speed: float = 1.0,
):
    """Convert text to speech (REST endpoint for single-shot TTS)."""
    return await voice_engine.synthesize_speech(text, voice, speed)
