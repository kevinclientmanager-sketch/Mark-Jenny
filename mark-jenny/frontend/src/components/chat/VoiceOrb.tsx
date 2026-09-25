"use client";
import { AudioWaveform } from "lucide-react";
import { cn } from "@/lib/utils";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

export function VoiceOrb({
  state,
  level,
  lastText,
  muted,
  onMuteToggle,
  onEnd,
}: {
  state: OrbState;
  level: number;
  lastText?: string;
  muted: boolean;
  onMuteToggle: () => void;
  onEnd: () => void;
}) {
  const listening = state === "listening" && !muted;
  const speaking = state === "speaking";
  const thinking = state === "thinking";
  const scale = listening ? 1 + Math.min(level, 100) / 250 : 1;

  const label =
    state === "listening" ? (muted ? "Muted" : "Listening…") : state === "thinking" ? "Thinking…" : state === "speaking" ? "Speaking…" : "Connecting…";

  return (
    <div className="flex flex-col items-center gap-2 py-2">
      {lastText && (
        <div className="max-w-[220px] rounded-2xl border border-zinc-200 dark:border-zinc-700 bg-white/95 dark:bg-zinc-900/95 px-3 py-2 text-xs text-zinc-600 dark:text-zinc-300 shadow-lg backdrop-blur">
          <p className="line-clamp-3">{lastText}</p>
        </div>
      )}
      <div className="relative h-16 w-16">
        {/* Listening: expanding blue rings */}
        {listening && (
          <>
            <span className="absolute inset-0 rounded-full bg-blue-500/40 animate-ping" style={{ animationDuration: "1.4s" }} />
            <span className="absolute inset-0 rounded-full bg-blue-500/25 animate-ping" style={{ animationDuration: "1.4s", animationDelay: "0.45s" }} />
          </>
        )}
        {/* Speaking: radiating waves (different effect) */}
        {speaking && (
          <>
            <span className="absolute -inset-1 rounded-full border-2 border-sky-400/70 animate-ping" style={{ animationDuration: "1s" }} />
            <span className="absolute -inset-2.5 rounded-full border border-sky-400/40 animate-ping" style={{ animationDuration: "1s", animationDelay: "0.3s" }} />
          </>
        )}
        {/* Thinking: slow spinning ring */}
        {thinking && (
          <span className="absolute -inset-1 rounded-full border-2 border-transparent border-t-blue-400 animate-spin" style={{ animationDuration: "1.2s" }} />
        )}
        <div
          className="absolute inset-0 rounded-full bg-gradient-to-br from-sky-400 via-blue-500 to-blue-700 shadow-lg shadow-blue-500/40 transition-transform duration-150"
          style={{ transform: `scale(${scale})` }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          {speaking ? (
            <span className="flex items-end gap-0.5 h-5">
              {[0, 1, 2, 3].map((i) => (
                <span
                  key={i}
                  className="w-1 rounded-full bg-white animate-pulse"
                  style={{ height: `${8 + ((level / 12 + i * 5) % 12)}px`, animationDelay: `${i * 0.12}s` }}
                />
              ))}
            </span>
          ) : (
            <AudioWaveform className={cn("h-6 w-6 text-white", listening && "animate-pulse")} />
          )}
        </div>
      </div>
      <div className="flex items-center gap-1.5 rounded-full border border-zinc-200 dark:border-zinc-700 bg-white/95 dark:bg-zinc-900/95 px-2 py-1 shadow-lg backdrop-blur">
        <span className={cn("h-1.5 w-1.5 rounded-full", listening ? "bg-blue-500 animate-pulse" : speaking ? "bg-sky-400 animate-pulse" : thinking ? "bg-amber-400 animate-pulse" : "bg-zinc-400")} />
        <span className="text-[11px] font-medium text-zinc-600 dark:text-zinc-300">{label}</span>
        <button onClick={onMuteToggle} className="rounded-full px-1.5 py-0.5 text-[11px] font-medium text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30" title={muted ? "Unmute" : "Mute"}>
          {muted ? "Unmute" : "Mute"}
        </button>
        <button onClick={onEnd} className="rounded-full px-1.5 py-0.5 text-[11px] font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30" title="End voice conversation">
          End
        </button>
      </div>
    </div>
  );
}
