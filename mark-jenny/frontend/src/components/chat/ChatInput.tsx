"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, AudioWaveform, Loader2, Square, Sparkles, Mic, MicOff, Phone, PhoneOff, Gamepad2, Trophy, Brain, Eye, Shield, Zap } from "lucide-react";
import { plusPromptTemplates, PlusAction, PlusMenu } from "./PlusMenu";
import { VoiceOrb } from "./VoiceOrb";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api/client";
import { toast } from "@/components/ui/toast";

interface LiveRecorderState {
  recording: boolean;
  timer: number;
  permission: "unknown" | "granted" | "denied";
}

interface VoiceMessage {
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}

export function ChatInput({
  onSend,
  onFile,
  disabled,
  placeholder,
  mode = "chat",
  chips,
  onVoiceAsk,
}: {
  onSend: (text: string, opts?: { think?: boolean; model?: string }) => void;
  onFile?: (f: File) => void;
  disabled?: boolean;
  placeholder?: string;
  mode?: "chat" | "work" | "browse";
  chips?: { label: string; icon: React.ComponentType<{ className?: string }>; prompt: string }[];
  onVoiceAsk?: (text: string) => Promise<string | null>;
}) {
  const [text, setText] = useState("");
  const [think, setThink] = useState(false);
  const [sending, setSending] = useState(false);
  const [inputMode, setInputMode] = useState<"text" | "voice">("text");

  // Voice conversation state
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceState, setVoiceState] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [voiceMessages, setVoiceMessages] = useState<VoiceMessage[]>([]);
  const [voiceLevel, setVoiceLevel] = useState(0);
  const [useBrowserSTT, setUseBrowserSTT] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const voiceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const speechRecognitionRef = useRef<any>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (voiceTimerRef.current) clearTimeout(voiceTimerRef.current);
      audioCtxRef.current?.close();
      mediaRef.current?.stream?.getTracks?.().forEach((t) => t.stop());
      speechRecognitionRef.current?.stop?.();
      wsRef.current?.close();
      if (synthRef.current) synthRef.current.cancel();
      currentAudioRef.current?.pause();
    };
  }, []);

  // ============================================================
  // VOICE CONVERSATION — WebSocket
  // ============================================================

  const startVoiceConversation = useCallback(() => {
    // Connect straight to the backend — Next.js dev rewrites do not proxy WebSocket upgrades
    const wsUrl = `${API_BASE.replace(/^http/, "ws")}/voice/ws/voice`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setVoiceActive(true);
        setVoiceState("listening");
        setVoiceMessages([]);

        // Send config
        ws.send(JSON.stringify({
          type: "config",
          agent: mode === "work" ? "mark" : "imti",
          voice: "en-US-AriaNeural",
        }));

        toast.add({ title: "Voice conversation started", description: "Speak naturally — I'm listening.", type: "success" });

        // Start listening
        startListening();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleVoiceMessage(msg);
        } catch {}
      };

      ws.onclose = () => {
        setVoiceActive(false);
        setVoiceState("idle");
        stopListening();
      };

      ws.onerror = () => {
        // Fallback to browser-side voice
        setUseBrowserSTT(true);
        setVoiceActive(true);
        setVoiceState("listening");
        startBrowserVoice();
      };
    } catch {
      // WebSocket failed, use browser-side voice
      setUseBrowserSTT(true);
      setVoiceActive(true);
      setVoiceState("listening");
      startBrowserVoice();
    }
  }, [mode]);

  const stopVoiceConversation = useCallback(() => {
    setVoiceActive(false);
    setVoiceState("idle");
    setVoiceMuted(false);
    stopListening();
    wsRef.current?.close();
    wsRef.current = null;
    if (synthRef.current) synthRef.current.cancel();
    currentAudioRef.current?.pause();
    currentAudioRef.current = null;
  }, []);

  const handleVoiceMessage = (msg: any) => {
    switch (msg.type) {
      case "transcript":
        setVoiceMessages((prev) => [
          ...prev,
          { role: "user", text: msg.text, timestamp: Date.now() },
        ]);
        break;
      case "response":
        setVoiceMessages((prev) => [
          ...prev,
          { role: "assistant", text: msg.text, timestamp: Date.now() },
        ]);
        // If server sends text but no audio, use browser TTS
        if (!voiceMessages.some((m) => m.text === msg.text)) {
          speakWithBrowser(msg.text);
        }
        break;
      case "audio":
        playAudioBase64(msg.data, msg.format);
        break;
      case "status":
        if (msg.state === "listening") setVoiceState("listening");
        else if (msg.state === "thinking") setVoiceState("thinking");
        else if (msg.state === "speaking") setVoiceState("speaking");
        else if (msg.state === "use_browser_stt") {
          setUseBrowserSTT(true);
          startBrowserVoice();
        }
        break;
      case "error":
        toast.add({ title: "Voice error", description: msg.message, type: "error" });
        break;
    }
  };

  // ============================================================
  // AUDIO RECORDING & STT
  // ============================================================

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      chunksRef.current = [];

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      rec.onstop = async () => {
        if (!voiceActive || !wsRef.current) return;

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size < 500) {
          // Too short, restart listening
          if (voiceActive) startListening();
          return;
        }

        // Send audio to server via WebSocket
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(",")[1];
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: "audio",
              data: base64,
              format: "webm",
              language: "en",
            }));
          }
        };
        reader.readAsDataURL(blob);
      };

      mediaRef.current = rec;
      rec.start();

      // Auto-stop after 30 seconds max
      setTimeout(() => {
        if (rec.state === "recording") rec.stop();
      }, 30000);

      // Start level meter
      startLevelMeter(stream);
    } catch {
      setVoice((v) => ({ ...v, permission: "denied" }));
    }
  };

  const stopListening = () => {
    if (mediaRef.current && mediaRef.current.state === "recording") {
      mediaRef.current.stop();
    }
    mediaRef.current?.stream?.getTracks?.().forEach((t) => t.stop());
    audioCtxRef.current?.close();
    analyserRef.current = null;
    setVoiceLevel(0);
  };

  const startLevelMeter = (stream: MediaStream) => {
    try {
      const AC = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AC();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      audioCtxRef.current = ctx;
      analyserRef.current = analyser;

      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(data);
          const avg = data.reduce((a, b) => a + b, 0) / data.length;
          setVoiceLevel(Math.min(100, (avg / 128) * 100));
          requestAnimationFrame(tick);
        }
      };
      tick();
    } catch {
      // No analyser available (browser blocked WebAudio) - show no level
      // rather than a fake moving bar.
      setVoiceLevel(0);
    }
  };

  // ============================================================
  // BROWSER-SIDE STT/TTS (fallback)
  // ============================================================

  const startBrowserVoice = () => {
    // Use Web Speech API for STT
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        const last = event.results[event.results.length - 1];
        if (last.isFinal) {
          const transcript = last[0].transcript;
          setVoiceMessages((prev) => [
            ...prev,
            { role: "user", text: transcript, timestamp: Date.now() },
          ]);

          // Send to AI via WebSocket if available
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "text", text: transcript }));
          } else {
            // Direct AI call
            processVoiceText(transcript);
          }
        }
      };

      recognition.onerror = () => {
        // Restart on error
        if (voiceActive) {
          setTimeout(() => {
            try { recognition.start(); } catch {}
          }, 500);
        }
      };

      recognition.onend = () => {
        if (voiceActive) {
          try { recognition.start(); } catch {}
        }
      };

      speechRecognitionRef.current = recognition;
      try { recognition.start(); } catch {}
    }

    // Use Web Speech Synthesis for TTS
    synthRef.current = window.speechSynthesis;
  };

  const authHeaders = (): HeadersInit => {
    const token = typeof window !== "undefined" ? window.localStorage.getItem("access_token") : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const processVoiceText = async (text: string) => {
    setVoiceState("thinking");

    // Ask the AI for a real reply (no more echoing the user's own words)
    try {
      if (onVoiceAsk) {
        const reply = await onVoiceAsk(text);
        if (reply && reply.trim()) {
          setVoiceMessages((prev) => [...prev, { role: "assistant", text: reply, timestamp: Date.now() }]);
          speakWithBrowser(reply);
          return;
        }
      }
    } catch {}

    try {
      const params = new URLSearchParams({ text, voice: "default", speed: "1" });
      const res = await fetch(`${API_BASE}/voice/synthesize?${params.toString()}`, {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await res.json();

      if (data.audio) {
        playAudioBase64(data.audio, data.format);
      } else {
        // Backend has no TTS voice — speak the AI reply if we got one, else say so
        speakWithBrowser("I heard you, but I could not generate a spoken reply right now.");
      }
    } catch {
      speakWithBrowser("I heard you, but I could not generate a spoken reply right now.");
    }
  };

  const speakWithBrowser = (text: string) => {
    if (!text.trim()) return;
    if (!synthRef.current && typeof window !== "undefined") synthRef.current = window.speechSynthesis;
    if (synthRef.current) {
      synthRef.current.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      utterance.rate = 1.0;
      utterance.onstart = () => setVoiceState("speaking");
      utterance.onend = () => setVoiceState("listening");
      synthRef.current.speak(utterance);
    }
  };

  const playAudioBase64 = (base64: string, format: string) => {
    try {
      currentAudioRef.current?.pause();
      const audio = new Audio(`data:audio/${format};base64,${base64}`);
      currentAudioRef.current = audio;
      audio.onplay = () => setVoiceState("speaking");
      audio.onended = () => {
        setVoiceState("listening");
        currentAudioRef.current = null;
      };
      audio.play().catch(() => speakWithBrowser(""));
    } catch {
      setVoiceState("listening");
    }
  };

  // ============================================================
  // TEXT INPUT HANDLERS
  // ============================================================

  const [voice, setVoice] = useState<LiveRecorderState>({ recording: false, timer: 0, permission: "unknown" });

  const stopRecording = () => {
    if (mediaRef.current && voice.recording) mediaRef.current.stop();
    setInputMode("text");
    setVoice((v) => ({ ...v, recording: false, timer: 0 }));
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setVoice((v) => ({ ...v, permission: "granted", recording: true, timer: 0 }));
      setInputMode("voice");
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      rec.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const secs = Math.round(voice.timer) || Math.max(1, Math.round(blob.size / 20000));

        // Send to voice engine for transcription
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(",")[1];
          // Use the transcribe endpoint
          fetch(`${API_BASE}/voice/transcribe?${new URLSearchParams({ audio: base64, format: "webm", language: "en" }).toString()}`, {
            method: "POST",
            headers: authHeaders(),
          })
            .then((r) => r.json())
            .then((data) => {
              if (data.text) {
                setText((prev) => (prev ? prev + " " + data.text : data.text));
              } else {
                setText((prev) => (prev ? prev + ` [Voice: ${secs}s]` : `[Voice: ${secs}s]`));
              }
            })
            .catch(() => {
              setText((prev) => (prev ? prev + ` [Voice: ${secs}s]` : `[Voice: ${secs}s]`));
            });
        };
        reader.readAsDataURL(blob);
      };
      mediaRef.current = rec;
      rec.start();
      intervalRef.current = setInterval(() => setVoice((v) => ({ ...v, timer: v.timer + 1 })), 1000);
    } catch {
      setVoice((v) => ({ ...v, permission: "denied", recording: false }));
      toast.add({ title: "Microphone unavailable", description: "Allow mic access in your browser settings.", type: "error" });
    }
  };

  const handlePlus = (id: PlusAction) => {
    const tpl = plusPromptTemplates[id];
    setText((prev) => (prev ? prev + " " + tpl : tpl));
  };

  const handleFilePick = (f: File) => {
    if (onFile) onFile(f);
    setText((prev) => (prev ? `${prev}\n[Attached: ${f.name} (${Math.round(f.size / 1024)}KB)]` : `[Attached: ${f.name}]`));
  };

  const handleSend = async () => {
    if (!text.trim() || disabled || sending) return;
    setSending(true);
    const toSend = text;
    setText("");
    try { await onSend(toSend, { think }); } finally { setSending(false); }
  };

  // ============================================================
  // VOICE CONVERSATION — floating orb (ChatGPT-style), composer stays usable
  // ============================================================

  const [voiceMuted, setVoiceMuted] = useState(false);

  const toggleVoiceMute = () => {
    if (voiceState === "listening") {
      stopListening();
      setVoiceState("idle");
      setVoiceMuted(true);
    } else {
      if (useBrowserSTT) startBrowserVoice();
      else startListening();
      setVoiceState("listening");
      setVoiceMuted(false);
    }
  };

  // Stop voice when switching toggles (chat / work / browse) — one conversation at a time
  const modeRef = useRef(mode);
  useEffect(() => {
    if (modeRef.current !== mode) {
      modeRef.current = mode;
      stopVoiceConversation();
    }
  }, [mode, stopVoiceConversation]);

  const lastVoiceText = voiceMessages.length > 0 ? voiceMessages[voiceMessages.length - 1]?.text : undefined;

  // ============================================================
  // NORMAL TEXT INPUT
  // ============================================================

  return (
    <div className="border-t bg-white dark:bg-zinc-900 px-3 py-3">
      <div className="mx-auto w-full max-w-3xl">
        {voiceActive ? (
          <VoiceOrb
            state={voiceState}
            level={voiceLevel}
            lastText={lastVoiceText}
            muted={voiceMuted}
            onMuteToggle={toggleVoiceMute}
            onEnd={stopVoiceConversation}
          />
        ) : (
        <>
        <div className="mb-2 flex flex-col items-center gap-1.5">
          {chips && chips.length > 0 && (
            <div className="flex flex-wrap justify-center gap-1.5">
              {chips.map((c) => (
                <button
                  key={c.label}
                  onClick={() => onSend(c.prompt)}
                  className="flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium text-zinc-600 hover:bg-white dark:text-zinc-300 dark:hover:bg-zinc-800"
                >
                  <c.icon className="h-3 w-3 text-emerald-600" /> {c.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-[26px] border bg-white dark:bg-zinc-900 shadow-sm transition-colors focus-within:ring-2 focus-within:ring-ring/40">
          {inputMode === "voice" ? (
            <div className="flex min-h-[64px] items-center gap-3 px-3 py-2">
              <Button size="icon" variant="destructive" className="h-9 w-9 rounded-full shrink-0" onClick={stopRecording} title="Stop and use">
                <Square className="h-4 w-4" />
              </Button>
              <div className="flex-1">
                <div className="h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 transition-[width] duration-75" style={{ width: `${voiceLevel}%` }} />
                </div>
                <p className="text-xs text-zinc-500 mt-1 flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                  Listening {voice.timer}s — tap stop to send
                </p>
              </div>
              <span className="text-xs text-zinc-400 shrink-0">{voice.timer}s</span>
            </div>
          ) : (
            <div className="flex items-end gap-1.5 p-1.5">
              <PlusMenu onSelect={handlePlus} onFilePick={handleFilePick} mode={mode} />
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && e.keyCode !== 229) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={
                  placeholder ||
                  (mode === "work"
                    ? "Tell Mark what to build…"
                    : mode === "browse"
                      ? "Ask Mark to browse the web…"
                      : "Ask anything, / for commands, @ for context…")
                }
                className="min-h-[38px] flex-1 resize-none border-none bg-transparent py-2.5 shadow-none focus-visible:ring-0 file:hidden"
                disabled={disabled}
              />
              <div className="flex shrink-0 items-center gap-1 pb-0.5">
                {/* Think button */}
                <button
                  onClick={() => setThink((v) => !v)}
                  className={cn(
                    "flex h-8 items-center gap-1 rounded-full border px-2.5 text-xs font-medium transition-colors",
                    think
                      ? "border-blue-600/40 bg-blue-600/10 text-blue-600"
                      : "border-zinc-200 dark:border-zinc-700 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
                  )}
                  title="Think — deep reasoning before answering"
                >
                  <Sparkles className={cn("h-3.5 w-3.5", think && "text-blue-600")} />
                  {think ? "Thinking…" : "Think"}
                </button>

                {/* Voice conversation button (wave icon) */}
                <Button
                  size="icon-sm"
                  variant="ghost"
                  className="h-8 w-8 rounded-full"
                  onClick={startVoiceConversation}
                  disabled={disabled}
                  title="Start voice conversation — talk to Mark or Imti"
                >
                  <AudioWaveform className="h-4 w-4" />
                </Button>

                {/* Send */}
                {text.trim() && (
                  <Button
                    onClick={handleSend}
                    disabled={disabled || sending}
                    size="icon-sm"
                    className="h-8 w-8 rounded-full bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
                  >
                    {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
        <p className="mt-2 text-center text-[11px] text-zinc-400">
          {mode === "work"
            ? "Work mode — Mark plans, writes code, runs tools, and reports back live."
            : mode === "browse"
              ? "Browse mode — Mark opens the browser, searches, reads pages, and brings back answers."
              : "Wave icon = voice conversation. Talk naturally to Mark or Imti."}
        </p>
        </>
        )}
      </div>
    </div>
  );
}
