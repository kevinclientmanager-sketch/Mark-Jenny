"use client";
import { useEffect, useRef, useState } from "react";
import { Bot, User, Wrench, Copy, Check, Volume2, VolumeX, Pencil, Trash2 } from "lucide-react";
import { Message } from "@/lib/api/chat";
import { chatApi } from "@/lib/api/chat";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import { toast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import { ToolConsole, parseToolSteps, parseReasoningTrace } from "./ToolConsole";

function tailTime(ts: string) {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ActionBar({ m, copied, onCopy }: { m: Message; copied: boolean; onCopy: () => void }) {
  const [speaking, setSpeaking] = useState(false);

  const readAloud = () => {
    if ("speechSynthesis" in window === false) {
      toast.add({ title: "Read aloud unavailable", type: "error" });
      return;
    }
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utter = new SpeechSynthesisUtterance(m.content || "");
    utter.onend = () => setSpeaking(false);
    utter.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utter);
  };

  return (
    <div className="flex items-center gap-0.5">
      <Button variant="ghost" size="icon-xs" onClick={onCopy} title="Copy">
        {copied ? <Check className="text-emerald-500" /> : <Copy />}
      </Button>
      <Button variant="ghost" size="icon-xs" onClick={readAloud} title={speaking ? "Stop reading" : "Read aloud"}>
        {speaking ? <VolumeX /> : <Volume2 />}
      </Button>
    </div>
  );
}

export function MessageList({
  messages,
  chatId,
  onMessagesChanged,
}: {
  messages: Message[];
  chatId: number;
  onMessagesChanged?: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [menuId, setMenuId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  useEffect(() => {
    if (!menuId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuId]);

  const copyMessage = async (m: Message) => {
    try {
      await navigator.clipboard.writeText(m.content || "");
      setCopiedId(m.id);
      setTimeout(() => setCopiedId((c) => (c === m.id ? null : c)), 1500);
    } catch {
      toast.add({ title: "Couldn't copy", description: "Clipboard is unavailable.", type: "error" });
    }
  };

  const startEdit = (m: Message) => {
    setEditingId(m.id);
    setEditText(m.content || "");
    setMenuId(null);
    setConfirmDeleteId(null);
  };

  const saveEdit = async () => {
    if (editingId === null) return;
    try {
      await chatApi.updateMessage(chatId, editingId, editText);
      setEditingId(null);
      toast.add({ title: "Message updated", type: "success" });
      onMessagesChanged?.();
    } catch {
      toast.add({ title: "Couldn't update message", type: "error" });
    }
  };

  const recallMessage = async (m: Message) => {
    if (confirmDeleteId !== m.id) {
      setConfirmDeleteId(m.id);
      return;
    }
    try {
      await chatApi.deleteMessage(chatId, m.id);
      setMenuId(null);
      setConfirmDeleteId(null);
      toast.add({ title: "Message recalled", type: "success" });
      onMessagesChanged?.();
    } catch {
      toast.add({ title: "Couldn't recall message", type: "error" });
    }
  };

  const closeMenu = () => {
    setMenuId(null);
    setConfirmDeleteId(null);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="flex min-h-full flex-col gap-5 px-4 py-6 md:px-6 lg:px-12">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center text-zinc-500 py-12 text-center">
            <Bot className="h-12 w-12 mb-3 text-zinc-300 dark:text-zinc-700" />
            <p className="text-lg font-medium">No messages yet</p>
            <p className="text-sm">Ask anything — or let Mark work by itself.</p>
          </div>
        )}
        {messages.map((m) => {
          const isUser = m.role === "USER";
          const isTool = m.role === "TOOL";
          const time = tailTime(m.created_at);
          const menuOpen = menuId === m.id;
          const editing = editingId === m.id;

          return (
            <div key={m.id} className={cn("flex items-start gap-3", isUser ? "justify-end" : "justify-start")}>
              {!isUser && (
                <div className="h-8 w-8 shrink-0 rounded-full bg-blue-600 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-white" />
                </div>
              )}
              <div className={cn("flex min-w-0 flex-col gap-1", isUser ? "items-end max-w-[82%]" : "items-start flex-1")}>
                <div className="relative w-full">
                  {isUser ? (
                    editing ? (
                      <div className="flex w-full flex-col gap-1.5 rounded-2xl border-2 border-blue-400 bg-white p-2 dark:bg-zinc-800">
                        <textarea
                          autoFocus
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={Math.max(2, Math.min(8, (editText.match(/\n/g)?.length || 0) + 1))}
                          className="w-full resize-none rounded-lg border border-zinc-200 bg-transparent p-2 text-sm text-zinc-900 outline-none dark:border-zinc-700 dark:text-zinc-100"
                        />
                        <div className="flex justify-end gap-1.5">
                          <Button size="sm" onClick={saveEdit}>Save</Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div
                          onClick={() => (menuOpen ? closeMenu() : setMenuId(m.id))}
                          title="Click for options"
                          className="cursor-pointer rounded-2xl bg-sky-500 dark:bg-sky-600 px-4 py-3 text-sm font-medium whitespace-pre-wrap break-words text-white shadow-sm shadow-sky-500/20"
                        >
                          {m.content || ""}
                        </div>
                        {menuOpen && (
                          <>
                            <div className="fixed inset-0 z-10" onClick={closeMenu} />
                            <div className="absolute right-0 top-6 z-20 min-w-[170px] overflow-hidden rounded-xl border bg-white shadow-lg dark:bg-zinc-900 dark:border-zinc-700">
                              <MenuButton label="Edit message" icon={<Pencil className="h-4 w-4" />} onClick={() => startEdit(m)} />
                              <MenuButton label={copiedId === m.id ? "Copied" : "Copy message"} icon={<Copy className="h-4 w-4" />} onClick={() => copyMessage(m)} />
                              <MenuButton danger label={confirmDeleteId === m.id ? "Confirm recall" : "Recall message"} icon={<Trash2 className="h-4 w-4" />} onClick={() => recallMessage(m)} />
                            </div>
                          </>
                        )}
                      </>
                    )
                   ) : (
                    <>
                      <div
                        onClick={() => (menuOpen ? closeMenu() : setMenuId(m.id))}
                        title="Click for options"
                        className={cn("cursor-pointer", isTool && "rounded-2xl border border-dashed px-4 py-3")}
                      >
                        {isTool && (
                          <Badge variant="outline" className="mb-1">
                            <Wrench className="mr-1 h-3 w-3" /> Tool
                          </Badge>
                        )}

                        {isTool && (m.tool_calls || m.message_metadata) ? (
                          <ToolConsole
                            steps={parseToolSteps(m.tool_calls, m.content, m.message_metadata)}
                            title={m.message_metadata?.tool_name || m.tool_calls?.[0]?.name || "Tool execution"}
                            strategy={m.message_metadata?.plan?.strategy}
                            compact
                          />
                        ) : !isTool && (m.tool_calls || m.message_metadata?.trace || m.message_metadata?.steps) ? (
                          <div className="space-y-2">
                            {parseReasoningTrace(m.message_metadata).length > 0 && (
                              <div className="rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 px-3 py-2">
                                <p className="text-[10px] font-medium text-zinc-500 mb-1 uppercase tracking-wide">Reasoning</p>
                                {parseReasoningTrace(m.message_metadata).map((line, i) => (
                                  <p key={i} className="text-[11px] text-zinc-600 dark:text-zinc-400 font-mono">→ {line}</p>
                                ))}
                              </div>
                            )}
                            <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-pre:bg-zinc-900 prose-pre:text-zinc-100">
                              {m.content || ""}
                            </div>
                            {(m.tool_calls || m.message_metadata?.steps) && (
                              <ToolConsole
                                steps={parseToolSteps(m.tool_calls, m.content, m.message_metadata)}
                                title="Execution"
                                strategy={m.message_metadata?.plan?.strategy}
                                model={m.message_metadata?.model_used || m.message_metadata?.model?.name}
                                compact
                              />
                            )}
                          </div>
                        ) : (
                          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-pre:bg-zinc-900 prose-pre:text-zinc-100">
                            {m.content || ""}
                          </div>
                        )}

                        {m.message_metadata && (
                          <div className="mt-2 flex flex-wrap gap-1 text-xs opacity-70">
                            {m.message_metadata.task_id && (
                              <Badge variant="secondary">Task #{m.message_metadata.task_id}</Badge>
                            )}
                            {m.message_metadata.attachments?.map((a: any) => (
                              <Badge key={a.id} variant="outline">
                                {a.name}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      {menuOpen && (
                        <>
                          <div className="fixed inset-0 z-10" onClick={closeMenu} />
                          <div className="absolute right-0 top-6 z-20 min-w-[170px] overflow-hidden rounded-xl border bg-white shadow-lg dark:bg-zinc-900 dark:border-zinc-700">
                            <MenuButton label={copiedId === m.id ? "Copied" : "Copy message"} icon={<Copy className="h-4 w-4" />} onClick={() => copyMessage(m)} />
                            <MenuButton danger label={confirmDeleteId === m.id ? "Confirm recall" : "Recall message"} icon={<Trash2 className="h-4 w-4" />} onClick={() => recallMessage(m)} />
                          </div>
                        </>
                      )}
                    </>
                  )}
                </div>

                <div className={cn("flex w-full max-w-full items-center gap-1.5", isUser ? "justify-end" : "justify-start")}>
                  {!isUser && <ActionBar m={m} copied={copiedId === m.id} onCopy={() => copyMessage(m)} />}
                  {time && <span className="text-[11px] leading-none opacity-50">{time}</span>}
                </div>
              </div>
              {isUser && (
                <div className="h-9 w-9 shrink-0 self-center rounded-full bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center shadow-sm shadow-sky-500/30">
                  <User className="h-5 w-5 text-white" />
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function MenuButton({
  label,
  icon,
  onClick,
  danger,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors",
        danger
          ? "text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
          : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-200 dark:hover:bg-zinc-800"
      )}
    >
      {icon}
      {label}
    </button>
  );
}

