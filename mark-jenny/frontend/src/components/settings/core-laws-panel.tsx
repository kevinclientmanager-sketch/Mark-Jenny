"use client";
import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { coreLawsApi } from "@/lib/api/coreLaws";
import { toast } from "@/components/ui/toast";
import {
  Lock, Unlock, Plus, Trash2, Shield, ShieldCheck, Eye, EyeOff,
  Save, RefreshCw, CheckCircle2, AlertTriangle, Loader2, X
} from "lucide-react";

interface CoreLaw {
  id: string;
  plain_text: string;
  code: string;
  enabled: boolean;
  category: string;
  created_at?: string;
  immutable?: boolean;
}

const CATEGORY_COLORS: Record<string, string> = {
  general: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  security: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  behavior: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  data: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  autonomy: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  scope: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
};

const DEFAULT_LAWS: CoreLaw[] = [
  { id: "law_1", plain_text: "Never delete user data without explicit confirmation", code: "BLOCK: destructive_operations", enabled: true, category: "security" },
  { id: "law_2", plain_text: "Always log all agent actions for audit trail", code: "ENFORCE: audit_logging", enabled: true, category: "behavior" },
  { id: "law_3", plain_text: "Never share credentials or API keys with external services", code: "RESTRICT: data_access", enabled: true, category: "security" },
  { id: "law_4", plain_text: "Require user approval before any deployment or publish action", code: "REQUIRE: user_confirmation", enabled: true, category: "autonomy" },
  { id: "law_5", plain_text: "Always encrypt sensitive data at rest and in transit", code: "ENFORCE: encryption", enabled: true, category: "data" },
  { id: "law_6", plain_text: "Mark agent cannot modify core laws or override Imti monitoring", code: "IMMUTABLE: core_configuration", enabled: true, category: "scope" },
];

function generateLawCode(plainText: string): string {
  const text = plainText.toLowerCase();
  if (/never|don't|do not|no access|forbidden|blocked/.test(text)) {
    if (/delete|remove|drop|destroy/.test(text)) return "BLOCK: destructive_operations";
    if (/access|read|view|see|show/.test(text)) return "RESTRICT: data_access";
    if (/send|email|publish|deploy|push/.test(text)) return "BLOCK: external_actions";
    if (/change|modify|edit|update|alter/.test(text)) return "IMMUTABLE: core_configuration";
    return `BLOCK: ${text.slice(0, 50)}`;
  }
  if (/always|must|required?|need|should/.test(text)) {
    if (/ask|confirm|approve|permission/.test(text)) return "REQUIRE: user_confirmation";
    if (/encrypt|secure|protect|hash/.test(text)) return "ENFORCE: encryption";
    if (/log|record|audit|track/.test(text)) return "ENFORCE: audit_logging";
    return `ENFORCE: ${text.slice(0, 50)}`;
  }
  if (/autonomy|independent|self|automatic/.test(text)) return `POLICY: autonomy_${text.slice(0, 30)}`;
  if (/data|information|file|document/.test(text)) {
    if (/store|keep|save|retain/.test(text)) return "POLICY: data_retention";
    if (/share|send|transfer|export/.test(text)) return "POLICY: data_sharing";
    return `POLICY: data_${text.slice(0, 30)}`;
  }
  return `RULE: ${plainText.slice(0, 100)}`;
}

export function CoreLawsPanel() {
  const [unlocked, setUnlocked] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [laws, setLaws] = useState<CoreLaw[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [editCode, setEditCode] = useState("");
  const [editCategory, setEditCategory] = useState("general");
  const [saving, setSaving] = useState(false);
  const [tamperStatus, setTamperStatus] = useState<{ tamper_free: boolean } | null>(null);
  const [newLawText, setNewLawText] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  useEffect(() => {
    coreLawsApi.status().then((r: any) => {
      setConfigured(r.configured);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleUnlock = async () => {
    if (!password) { toast.add({ title: "Password required", type: "error" }); return; }
    try {
      const r: any = await coreLawsApi.unlock(password);
      setLaws(r.laws);
      setUnlocked(true);
      toast.add({ title: "Core Laws unlocked", type: "success" });
    } catch (e: any) {
      toast.add({ title: e?.message || "Invalid password", type: "error" });
    }
  };

  const handleSetup = async () => {
    if (!password) { toast.add({ title: "Password required", type: "error" }); return; }
    try {
      const r: any = await coreLawsApi.setup(password, DEFAULT_LAWS.map(l => ({
        plain_text: l.plain_text, code: l.code, category: l.category,
      })));
      setLaws(DEFAULT_LAWS);
      setConfigured(true);
      setUnlocked(true);
      toast.add({ title: `${r.law_count} Core Laws established`, type: "success" });
    } catch (e: any) {
      toast.add({ title: e?.message || "Setup failed", type: "error" });
    }
  };

  const handleSaveLaw = async (lawId: string) => {
    setSaving(true);
    try {
      await coreLawsApi.update(lawId, editText, editCode, password);
      setLaws(laws.map(l => l.id === lawId ? { ...l, plain_text: editText, code: editCode, category: editCategory } : l));
      setEditingId(null);
      toast.add({ title: "Law updated", type: "success" });
    } catch (e: any) {
      toast.add({ title: e?.message || "Update failed", type: "error" });
    } finally { setSaving(false); }
  };

  const handleAddLaw = async () => {
    if (!newLawText.trim()) { toast.add({ title: "Enter a law", type: "error" }); return; }
    setSaving(true);
    try {
      const code = generateLawCode(newLawText);
      const r: any = await coreLawsApi.add(newLawText, code, editCategory, password);
      setLaws([...laws, r.law]);
      setNewLawText("");
      setShowAddForm(false);
      toast.add({ title: "Law added", type: "success" });
    } catch (e: any) {
      toast.add({ title: e?.message || "Add failed", type: "error" });
    } finally { setSaving(false); }
  };

  const handleDeleteLaw = async (lawId: string) => {
    if (!confirm("Delete this Core Law? This requires password.")) return;
    setSaving(true);
    try {
      await coreLawsApi.delete(lawId, password);
      setLaws(laws.filter(l => l.id !== lawId));
      toast.add({ title: "Law deleted", type: "success" });
    } catch (e: any) {
      toast.add({ title: e?.message || "Delete failed", type: "error" });
    } finally { setSaving(false); }
  };

  const handleVerify = async () => {
    try {
      const r: any = await coreLawsApi.verify();
      setTamperStatus(r);
      toast.add({ title: r.tamper_free ? "Laws verified — no tampering detected" : "WARNING: Laws may have been tampered with!", type: r.tamper_free ? "success" : "error" });
    } catch { toast.add({ title: "Verification failed", type: "error" }); }
  };

  if (loading) return <div className="flex items-center gap-2 p-4"><Loader2 className="h-4 w-4 animate-spin" /> Loading Core Laws...</div>;

  // Password gate
  if (!unlocked) {
    return (
      <Card className="border-red-200 dark:border-red-900">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-5 w-5 text-red-500" /> Core Laws — Immutable Agent Rules
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-zinc-500">
            Core Laws are immutable rules that govern Mark and Imti agents. No agent, model, or system can modify these laws.
            Enter your password to {configured ? "unlock and edit" : "set up"} Core Laws.
          </p>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="Core Laws password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (configured ? handleUnlock() : handleSetup())}
              />
              <button onClick={() => setShowPassword(!showPassword)} className="absolute right-2 top-1/2 -translate-y-1/2">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {configured ? (
              <Button onClick={handleUnlock} className="bg-red-600 hover:bg-red-700">
                <Unlock className="h-4 w-4 mr-1" /> Unlock
              </Button>
            ) : (
              <Button onClick={handleSetup} className="bg-red-600 hover:bg-red-700">
                <Lock className="h-4 w-4 mr-1" /> Set Up Laws
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Unlocked — show law boxes
  return (
    <Card className="border-red-200 dark:border-red-900">
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-green-500" /> Core Laws ({laws.length})
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleVerify}>
              <RefreshCw className="h-3 w-3 mr-1" /> Verify Integrity
            </Button>
            <Button variant="outline" size="sm" onClick={() => { setUnlocked(false); setPassword(""); }}>
              <Lock className="h-3 w-3 mr-1" /> Lock
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {tamperStatus && (
          <div className={`flex items-center gap-2 p-2 rounded text-sm ${tamperStatus.tamper_free ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            {tamperStatus.tamper_free ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            {tamperStatus.tamper_free ? "All laws verified — no tampering" : "WARNING: Tampering detected!"}
          </div>
        )}

        {laws.map((law) => (
          <div key={law.id} className="border rounded-lg p-3 space-y-2 bg-zinc-50 dark:bg-zinc-900">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                {editingId === law.id ? (
                  <div className="space-y-2">
                    <textarea
                      className="w-full p-2 border rounded text-sm"
                      rows={2}
                      value={editText}
                      onChange={(e) => {
                        setEditText(e.target.value);
                        setEditCode(generateLawCode(e.target.value));
                      }}
                    />
                    <div className="flex gap-2 items-center">
                      <select value={editCategory} onChange={(e) => setEditCategory(e.target.value)} className="text-xs border rounded p-1">
                        {Object.keys(CATEGORY_COLORS).map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                      <code className="text-xs bg-zinc-200 dark:bg-zinc-800 px-2 py-1 rounded flex-1 font-mono">{editCode}</code>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" onClick={() => handleSaveLaw(law.id)} disabled={saving}>
                        <Save className="h-3 w-3 mr-1" /> Save
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className={CATEGORY_COLORS[law.category] || CATEGORY_COLORS.general}>{law.category}</Badge>
                      {law.immutable && <Badge variant="outline" className="text-xs"><Shield className="h-3 w-3 mr-1" /> Immutable</Badge>}
                    </div>
                    <p className="text-sm font-medium">{law.plain_text}</p>
                    <code className="text-xs bg-zinc-200 dark:bg-zinc-800 px-2 py-1 rounded block font-mono mt-1">{law.code}</code>
                  </>
                )}
              </div>
              {editingId !== law.id && (
                <div className="flex gap-1 shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => { setEditingId(law.id); setEditText(law.plain_text); setEditCode(law.code); setEditCategory(law.category); }}>
                    <span className="text-xs">Edit</span>
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDeleteLaw(law.id)} className="text-red-500 hover:text-red-700">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Add new law */}
        {showAddForm ? (
          <div className="border rounded-lg p-3 space-y-2 border-dashed border-blue-300">
            <textarea
              className="w-full p-2 border rounded text-sm"
              rows={2}
              placeholder="Write a new law in plain language..."
              value={newLawText}
              onChange={(e) => setNewLawText(e.target.value)}
            />
            <div className="flex gap-2 items-center">
              <select value={editCategory} onChange={(e) => setEditCategory(e.target.value)} className="text-xs border rounded p-1">
                {Object.keys(CATEGORY_COLORS).map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <code className="text-xs bg-zinc-200 dark:bg-zinc-800 px-2 py-1 rounded flex-1 font-mono">
                {newLawText ? generateLawCode(newLawText) : "Auto-generated code appears here"}
              </code>
            </div>
            <div className="flex gap-1">
              <Button size="sm" onClick={handleAddLaw} disabled={saving || !newLawText.trim()}>
                <Plus className="h-3 w-3 mr-1" /> Add Law
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setShowAddForm(false); setNewLawText(""); }}>
                <X className="h-3 w-3 mr-1" /> Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="outline" className="w-full border-dashed" onClick={() => setShowAddForm(true)}>
            <Plus className="h-4 w-4 mr-1" /> Add Core Law
          </Button>
        )}

        <p className="text-xs text-zinc-400 mt-2">
          Core Laws are enforced by Imti. Mark agent cannot modify or bypass these rules.
          Each law has a plain language description (left) and auto-generated code enforcement (right).
        </p>
      </CardContent>
    </Card>
  );
}
