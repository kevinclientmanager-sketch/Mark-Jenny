"use client";
import { useState, useRef, useEffect } from "react";
import { Mic, Square, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";

type VoiceMode = "direct" | "meeting";

export function VoiceRecorder({ onTranscribed, onModeChange }: { onTranscribed: (text:string, mode:VoiceMode)=>void; onModeChange?: (m:VoiceMode)=>void }) {
  const [mode, setMode] = useState<VoiceMode>("direct");
  const [recording, setRecording] = useState(false);
  const [timer, setTimer] = useState(0);
  const [permission, setPermission] = useState<"unknown"|"granted"|"denied">("unknown");
  const mediaRef = useRef<MediaRecorder|null>(null);
  const intervalRef = useRef<NodeJS.Timeout|null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(()=>{ onModeChange?.(mode); },[mode]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio:true });
      setPermission("granted");
      const rec = new MediaRecorder(stream);
      chunksRef.current=[];
      rec.ondataavailable = e=>{ if(e.data.size>0) chunksRef.current.push(e.data); };
      rec.onstop = async ()=>{
        const blob = new Blob(chunksRef.current, {type:'audio/webm'});
        let text = "";
        try {
          const formData = new FormData();
          formData.append("audio", blob, "recording.webm");
          formData.append("format", "webm");
          const token = localStorage.getItem("access_token");
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/voice/transcribe`, {
            method: "POST",
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
          });
          if (res.ok) {
            const data = await res.json();
            text = data.text || data.transcript || "";
          }
        } catch {}
        if (!text) text = `[Voice ${mode}: ${Math.round(timer)}s audio - ${blob.size} bytes]`;
        onTranscribed(text, mode);
        stream.getTracks().forEach(t=>t.stop());
        setTimer(0);
      };
      mediaRef.current=rec;
      rec.start();
      setRecording(true);
      intervalRef.current=setInterval(()=>setTimer(t=>t+1),1000);
    } catch (e) {
      setPermission("denied");
      toast.add({ title: "Microphone unavailable", description: "Allow mic access in your browser settings.", type: "error" });
    }
  };
  const stop = ()=> {
    if (mediaRef.current && recording) {
      mediaRef.current.stop();
      setRecording(false);
      if(intervalRef.current) clearInterval(intervalRef.current);
    }
  };

  return (
    <div className="flex flex-col gap-2 p-2 border rounded-xl bg-zinc-50 dark:bg-zinc-900">
      <div className="flex gap-2">
        <Button variant={mode==="direct"?"default":"outline"} size="sm" onClick={()=>setMode("direct")}>Direct Task Execution</Button>
        <Button variant={mode==="meeting"?"default":"outline"} size="sm" onClick={()=>setMode("meeting")}>Meeting Minutes</Button>
      </div>
      {permission==="denied" && <p className="text-xs text-red-600">Permission denied - check browser settings.</p>}
      <div className="flex items-center gap-3">
        {!recording ? (
          <Button onClick={start} size="icon" className="rounded-full bg-red-600 hover:bg-red-700"><Mic className="h-4 w-4"/></Button>
        ) : (
          <Button onClick={stop} size="icon" variant="destructive" className="rounded-full"><Square className="h-4 w-4"/></Button>
        )}
        <div className="flex-1">
          <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded overflow-hidden">
            <div className={`h-full bg-blue-600 transition-all ${recording?"animate-pulse w-full":"w-0"}`}/>
          </div>
          <p className="text-xs text-zinc-500 mt-1">{recording?`● Recording ${timer}s - Speak now`:"Tap mic to start - permission will be requested"}</p>
        </div>
        {recording && <Loader2 className="h-4 w-4 animate-spin"/>}
      </div>
      <p className="text-[11px] text-zinc-400">Audio stays on device until transcribed. Uses backend Whisper/STT when available.</p>
    </div>
  );
}
