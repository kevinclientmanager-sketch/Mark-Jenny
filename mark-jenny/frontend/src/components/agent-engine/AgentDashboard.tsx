'use client';

import { useState } from 'react';
import { agentEngineApi, ProcessResult, RouteResult, ProactiveSuggestion } from '@/lib/api/agentEngine';

interface AgentDashboardProps {
  onClose?: () => void;
}

export default function AgentDashboard({ onClose }: AgentDashboardProps) {
  const [activeTab, setActiveTab] = useState<'process' | 'sandbox' | 'route' | 'proactive' | 'decompose'>('process');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string>('');

  const tabs = [
    { id: 'process' as const, label: 'Multi-Agent' },
    { id: 'sandbox' as const, label: 'Sandbox' },
    { id: 'route' as const, label: 'Model Router' },
    { id: 'proactive' as const, label: 'Proactive' },
    { id: 'decompose' as const, label: 'Decompose' },
  ];

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-900 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <h3 className="font-semibold text-zinc-900 dark:text-white">Agent Engine</h3>
        {onClose && (
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="flex border-b border-zinc-200 dark:border-zinc-800">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-4 max-h-[500px] overflow-y-auto">
        {activeTab === 'process' && <ProcessTab loading={loading} setLoading={setLoading} result={result} setResult={setResult} />}
        {activeTab === 'sandbox' && <SandboxTab loading={loading} setLoading={setLoading} result={result} setResult={setResult} />}
        {activeTab === 'route' && <RouteTab loading={loading} setLoading={setLoading} result={result} setResult={setResult} />}
        {activeTab === 'proactive' && <ProactiveTab loading={loading} setLoading={setLoading} result={result} setResult={setResult} />}
        {activeTab === 'decompose' && <DecomposeTab loading={loading} setLoading={setLoading} result={result} setResult={setResult} />}
      </div>
    </div>
  );
}

function ProcessTab({ loading, setLoading, result, setResult }: { loading: boolean; setLoading: (v: boolean) => void; result: string; setResult: (v: string) => void }) {
  const [request, setRequest] = useState('');

  const handleProcess = async () => {
    if (!request.trim()) return;
    setLoading(true);
    try {
      const res = await agentEngineApi.process({ request });
      setResult(JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-zinc-500">Multi-agent processing with Planner → Executor → Verifier pattern</p>
      <textarea
        value={request}
        onChange={(e) => setRequest(e.target.value)}
        placeholder="Enter a complex task to process..."
        className="w-full h-20 px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800 resize-none"
      />
      <button
        onClick={handleProcess}
        disabled={loading || !request.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Processing...' : 'Process Task'}
      </button>
      {result && (
        <pre className="p-3 text-xs bg-zinc-50 dark:bg-zinc-800 rounded-lg overflow-x-auto max-h-[300px] overflow-y-auto border border-zinc-200 dark:border-zinc-700">
          {result}
        </pre>
      )}
    </div>
  );
}

function SandboxTab({ loading, setLoading, result, setResult }: { loading: boolean; setLoading: (v: boolean) => void; result: string; setResult: (v: string) => void }) {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');

  const handleExecute = async () => {
    if (!code.trim()) return;
    setLoading(true);
    try {
      const res = await agentEngineApi.sandboxExecute({ code, language });
      setResult(JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-zinc-500">Isolated code execution in sandbox environment</p>
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
        className="px-3 py-1.5 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800"
      >
        <option value="python">Python</option>
        <option value="shell">Shell</option>
        <option value="node">Node.js</option>
      </select>
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter code to execute..."
        className="w-full h-32 px-3 py-2 text-sm font-mono border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800 resize-none"
      />
      <button
        onClick={handleExecute}
        disabled={loading || !code.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? 'Executing...' : 'Execute'}
      </button>
      {result && (
        <pre className="p-3 text-xs bg-zinc-50 dark:bg-zinc-800 rounded-lg overflow-x-auto max-h-[300px] overflow-y-auto border border-zinc-200 dark:border-zinc-700">
          {result}
        </pre>
      )}
    </div>
  );
}

function RouteTab({ loading, setLoading, result, setResult }: { loading: boolean; setLoading: (v: boolean) => void; result: string; setResult: (v: string) => void }) {
  const [text, setText] = useState('');

  const handleRoute = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await agentEngineApi.route(text);
      setResult(JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-zinc-500">Route tasks to the best model based on domain analysis</p>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter text to classify and route..."
        className="w-full px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800"
      />
      <button
        onClick={handleRoute}
        disabled={loading || !text.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50"
      >
        {loading ? 'Routing...' : 'Route Task'}
      </button>
      {result && (
        <pre className="p-3 text-xs bg-zinc-50 dark:bg-zinc-800 rounded-lg overflow-x-auto max-h-[300px] overflow-y-auto border border-zinc-200 dark:border-zinc-700">
          {result}
        </pre>
      )}
    </div>
  );
}

function ProactiveTab({ loading, setLoading, result, setResult }: { loading: boolean; setLoading: (v: boolean) => void; result: string; setResult: (v: string) => void }) {
  const handleEvaluate = async () => {
    setLoading(true);
    try {
      const res = await agentEngineApi.proactiveEvaluate({ last_activity_time: Date.now() / 1000 - 600 });
      setResult(JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-zinc-500">Proactive suggestions based on context analysis</p>
      <button
        onClick={handleEvaluate}
        disabled={loading}
        className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 disabled:opacity-50"
      >
        {loading ? 'Evaluating...' : 'Check for Suggestions'}
      </button>
      {result && (
        <pre className="p-3 text-xs bg-zinc-50 dark:bg-zinc-800 rounded-lg overflow-x-auto max-h-[300px] overflow-y-auto border border-zinc-200 dark:border-zinc-700">
          {result}
        </pre>
      )}
    </div>
  );
}

function DecomposeTab({ loading, setLoading, result, setResult }: { loading: boolean; setLoading: (v: boolean) => void; result: string; setResult: (v: string) => void }) {
  const [request, setRequest] = useState('');

  const handleDecompose = async () => {
    if (!request.trim()) return;
    setLoading(true);
    try {
      const res = await agentEngineApi.decompose(request);
      setResult(JSON.stringify(res, null, 2));
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-zinc-500">Decompose complex tasks into DAG of subtasks</p>
      <textarea
        value={request}
        onChange={(e) => setRequest(e.target.value)}
        placeholder="Enter a task to decompose..."
        className="w-full h-20 px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800 resize-none"
      />
      <button
        onClick={handleDecompose}
        disabled={loading || !request.trim()}
        className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? 'Decomposing...' : 'Decompose Task'}
      </button>
      {result && (
        <pre className="p-3 text-xs bg-zinc-50 dark:bg-zinc-800 rounded-lg overflow-x-auto max-h-[300px] overflow-y-auto border border-zinc-200 dark:border-zinc-700">
          {result}
        </pre>
      )}
    </div>
  );
}
