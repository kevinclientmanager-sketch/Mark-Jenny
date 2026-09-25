'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { workAgentApi, WorkTask, WorkPattern, Prediction } from '@/lib/api/workAgent';
import { MessageSquare, Briefcase, Send, Loader2, CheckCircle2, Mail, FolderOpen, Bot, Brain, TrendingUp, Plus, ArrowLeft } from 'lucide-react';

type ImtiMode = 'chat' | 'work' | null;
type WorkTab = 'tasks' | 'files' | 'email' | 'patterns' | 'predict';

export default function ImtiPage() {
  const [mode, setMode] = useState<ImtiMode>(null);
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string; timestamp: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [activeTasks, setActiveTasks] = useState<WorkTask[]>([]);
  const [pendingTasks, setPendingTasks] = useState<WorkTask[]>([]);
  const [completedTasks, setCompletedTasks] = useState<WorkTask[]>([]);
  const [patterns, setPatterns] = useState<WorkPattern[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [workLoading, setWorkLoading] = useState(false);
  const [activeWorkTab, setActiveWorkTab] = useState<WorkTab>('tasks');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskType, setNewTaskType] = useState('file_manage');
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Always start fresh — new empty UI on every visit, no restored session
  useEffect(() => {
    if (mode === 'work') loadWorkData();
  }, [mode]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatMessages]);

  const selectMode = useCallback((m: ImtiMode) => {
    // Switching mode always starts a fresh empty UI for that mode
    setMode(m);
    setChatMessages([]);
    setChatInput('');
    setNewTaskDesc('');
    setActiveWorkTab('tasks');
  }, []);

  const loadWorkData = async () => {
    try {
      const [tasksRes, patternsRes, predictRes] = await Promise.all([
        workAgentApi.getTasks(), workAgentApi.getPatterns(), workAgentApi.predict(),
      ]);
      setPendingTasks(tasksRes.pending || []);
      setActiveTasks(tasksRes.active || []);
      setCompletedTasks(tasksRes.completed || []);
      setPatterns(patternsRes.patterns || []);
      setPredictions(predictRes.predictions || []);
    } catch (e) { console.error('Failed to load work data:', e); }
  };

  const handleChatSend = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg = { role: 'user', content: chatInput, timestamp: new Date().toISOString() };
    setChatMessages(prev => [...prev, userMsg]);
    const input = chatInput;
    setChatInput('');
    setChatLoading(true);
    try {
      const { api } = await import('@/lib/api/client');
      const res = await api.post<{ response: string }>('/chats/send', { message: input, mode: 'imti-chat' });
      setChatMessages(prev => [...prev, { role: 'assistant', content: res.response || 'I received your message.', timestamp: new Date().toISOString() }]);
    } catch {
      setChatMessages(prev => [...prev, { role: 'assistant', content: "I'm here to help. What would you like to chat about?", timestamp: new Date().toISOString() }]);
    } finally { setChatLoading(false); }
  };

  const handleCreateTask = async () => {
    if (!newTaskDesc.trim()) return;
    setWorkLoading(true);
    try { await workAgentApi.createTask(newTaskType, newTaskDesc); setNewTaskDesc(''); await loadWorkData(); }
    catch (e) { console.error('Failed to create task:', e); }
    finally { setWorkLoading(false); }
  };

  const handleApproveTask = async (taskId: string) => {
    try { await workAgentApi.approveTask(taskId); await loadWorkData(); }
    catch (e) { console.error('Failed to approve task:', e); }
  };

  const handleFileAction = async (action: string) => {
    setWorkLoading(true);
    try { const res = await workAgentApi.fileAction(action, {}); alert(JSON.stringify(res.result, null, 2)); }
    catch (e) { console.error('File action failed:', e); }
    finally { setWorkLoading(false); }
  };

  const handleDraftEmail = async () => {
    const to = prompt('To:'); if (!to) return;
    const subject = prompt('Subject:'); const context = prompt('What should the email say?');
    if (!subject || !context) return;
    setWorkLoading(true);
    try {
      const res = await workAgentApi.draftEmail(to, subject, context);
      alert('Draft created:\n\n' + ((res.result as Record<string, unknown>)?.draft || 'No draft'));
    } catch (e) { console.error('Email draft failed:', e); }
    finally { setWorkLoading(false); }
  };

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-zinc-950">
      {/* Chat/Work toggle — always visible */}
      <div className="h-14 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-center gap-3 px-4">
        <div className="flex gap-1 p-0.5 bg-zinc-100 dark:bg-zinc-800 rounded-full">
          <button onClick={() => selectMode('chat')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${mode === 'chat' ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>
            <MessageSquare className="h-3 w-3" /> Chat
          </button>
          <button onClick={() => selectMode('work')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${mode === 'work' ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>
            <Briefcase className="h-3 w-3" /> Work
          </button>
        </div>
      </div>

      {!mode && (
        <div className="flex-1 flex flex-col items-center justify-center gap-6">
          <Bot className="h-16 w-16 text-blue-600 dark:text-blue-400" />
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">What would you like to do?</h2>
          <p className="text-sm text-zinc-500 max-w-md text-center">Choose Chat or Work above to get started.</p>
        </div>
      )}

      {mode === 'chat' && (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatMessages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-zinc-400">
                <Bot className="h-12 w-12 mb-3" />
                <p className="text-lg font-medium">Hi, I am Imti</p>
                <p className="text-sm">Your AI assistant. How can I help?</p>
              </div>
            )}
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] rounded-lg px-4 py-2 ${msg.role === 'user' ? 'bg-sky-500 dark:bg-sky-600 text-white font-medium shadow-sm shadow-sky-500/20' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white'}`}>
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg px-4 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div className="border-t border-zinc-200 dark:border-zinc-800 p-3">
            <div className="flex gap-2">
              <input value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleChatSend()}
                placeholder="Message Imti..."
                className="flex-1 px-4 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <button onClick={handleChatSend} disabled={chatLoading || !chatInput.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {mode === 'work' && (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex border-b border-zinc-200 dark:border-zinc-800 px-4">
            {[
              { id: 'tasks' as WorkTab, label: 'Tasks', icon: CheckCircle2 },
              { id: 'files' as WorkTab, label: 'Files', icon: FolderOpen },
              { id: 'email' as WorkTab, label: 'Email', icon: Mail },
              { id: 'patterns' as WorkTab, label: 'Learned', icon: Brain },
              { id: 'predict' as WorkTab, label: 'Predict', icon: TrendingUp },
            ].map((tab) => (
              <button key={tab.id} onClick={() => setActiveWorkTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeWorkTab === tab.id ? 'border-green-600 text-green-600' : 'border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>
                <tab.icon className="h-4 w-4" /> {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {activeWorkTab === 'tasks' && (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <select value={newTaskType} onChange={(e) => setNewTaskType(e.target.value)}
                    className="px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800">
                    <option value="file_manage">File Management</option>
                    <option value="email">Email</option>
                    <option value="document">Document</option>
                    <option value="organize">Organize</option>
                    <option value="search">Search</option>
                    <option value="research">Research</option>
                    <option value="data_entry">Data Entry</option>
                    <option value="custom">Custom</option>
                  </select>
                  <input value={newTaskDesc} onChange={(e) => setNewTaskDesc(e.target.value)}
                    placeholder="Describe the task..."
                    className="flex-1 px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800" />
                  <button onClick={handleCreateTask} disabled={workLoading || !newTaskDesc.trim()}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-1">
                    <Plus className="h-4 w-4" /> Add
                  </button>
                </div>
                {pendingTasks.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-zinc-500 mb-2">Pending Approval</h3>
                    {pendingTasks.map((task) => (
                      <div key={task.id} className="flex items-center justify-between p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg mb-2">
                        <div>
                          <p className="text-sm font-medium">{task.description}</p>
                          <p className="text-xs text-zinc-500">{task.type}</p>
                        </div>
                        <button onClick={() => handleApproveTask(task.id)}
                          className="px-3 py-1 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">Approve</button>
                      </div>
                    ))}
                  </div>
                )}
                {activeTasks.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-zinc-500 mb-2">Active</h3>
                    {activeTasks.map((task) => (
                      <div key={task.id} className="p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg mb-2">
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin text-green-600" />
                          <p className="text-sm font-medium">{task.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {completedTasks.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-zinc-500 mb-2">Completed</h3>
                    {completedTasks.slice(0, 10).map((task) => (
                      <div key={task.id} className="p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg mb-2 opacity-70">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                          <p className="text-sm">{task.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {pendingTasks.length === 0 && activeTasks.length === 0 && (
                  <div className="text-center text-zinc-400 py-12">
                    <CheckCircle2 className="h-12 w-12 mx-auto mb-3" />
                    <p className="font-medium">No active tasks</p>
                    <p className="text-sm">Create a task to get started</p>
                  </div>
                )}
              </div>
            )}

            {activeWorkTab === 'files' && (
              <div className="space-y-3">
                <p className="text-sm text-zinc-500">Quick file management actions</p>
                {[
                  { action: 'organize', label: 'Organize Downloads', desc: 'Sort files by type into folders' },
                  { action: 'find', label: 'Find Files', desc: 'Search for files on your PC' },
                  { action: 'rename', label: 'Batch Rename', desc: 'Rename files with a pattern' },
                  { action: 'sort', label: 'Sort by Type', desc: 'Group files by extension' },
                  { action: 'backup', label: 'Backup', desc: 'Create a backup of important files' },
                  { action: 'list', label: 'List Files', desc: 'Browse directory contents' },
                ].map((item) => (
                  <button key={item.action} onClick={() => handleFileAction(item.action)}
                    disabled={workLoading}
                    className="w-full flex items-center gap-3 p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-900 text-left">
                    <FolderOpen className="h-5 w-5 text-green-600 shrink-0" />
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-zinc-500">{item.desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {activeWorkTab === 'email' && (
              <div className="space-y-3">
                <p className="text-sm text-zinc-500">Email management</p>
                <button onClick={handleDraftEmail} disabled={workLoading}
                  className="w-full flex items-center gap-3 p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg hover:bg-zinc-50 dark:hover:bg-zinc-900 text-left">
                  <Mail className="h-5 w-5 text-blue-600 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">Draft Email</p>
                    <p className="text-xs text-zinc-500">AI-assisted email composition</p>
                  </div>
                </button>
                <div className="p-4 border border-zinc-200 dark:border-zinc-800 rounded-lg text-center text-zinc-400">
                  <p className="text-sm">Connect Gmail or Outlook in Connectors to read emails</p>
                </div>
              </div>
            )}

            {activeWorkTab === 'patterns' && (
              <div className="space-y-3">
                <p className="text-sm text-zinc-500">Patterns Imti has learned</p>
                {patterns.length === 0 ? (
                  <div className="text-center text-zinc-400 py-12">
                    <Brain className="h-12 w-12 mx-auto mb-3" />
                    <p className="font-medium">No patterns learned yet</p>
                    <p className="text-sm">Imti learns as you use Work mode</p>
                  </div>
                ) : patterns.map((p) => (
                  <div key={p.id} className="p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{p.trigger} &rarr; {p.action}</p>
                      <span className="text-xs text-zinc-500">{p.frequency}x</span>
                    </div>
                    <div className="mt-1 w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-1.5">
                      <div className="bg-green-600 h-1.5 rounded-full" style={{ width: `${p.confidence * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeWorkTab === 'predict' && (
              <div className="space-y-3">
                <p className="text-sm text-zinc-500">Imti predicts what you might need</p>
                {predictions.length === 0 ? (
                  <div className="text-center text-zinc-400 py-12">
                    <TrendingUp className="h-12 w-12 mx-auto mb-3" />
                    <p className="font-medium">No predictions yet</p>
                    <p className="text-sm">Keep using Work mode to build predictions</p>
                  </div>
                ) : predictions.map((p, i) => (
                  <div key={i} className="p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{p.suggestion}</p>
                      <span className="text-xs text-zinc-500">{Math.round(p.confidence * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
