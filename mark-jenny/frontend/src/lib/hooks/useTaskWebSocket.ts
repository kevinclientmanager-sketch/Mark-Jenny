"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Task, TaskStatus } from "@/lib/api/tasks";

interface TaskUpdateMessage {
  type: "task_update";
  event: string;
  task: {
    id: number;
    title: string;
    status: TaskStatus;
    current_step: number;
    total_steps: number;
    error: string | null;
    result: Record<string, unknown> | null;
    updated_at: string | null;
  };
  timestamp: string;
}

interface TaskRunUpdateMessage {
  type: "task_run_update";
  event: string;
  task_run: {
    id: number;
    task_id: number;
    run_number: number;
    status: string;
    steps_completed: number;
    duration_seconds: number | null;
    completed_at: string | null;
  };
  timestamp: string;
}

type WebSocketMessage = TaskUpdateMessage | TaskRunUpdateMessage | { type: string; [key: string]: unknown };

function isTaskUpdate(msg: WebSocketMessage): msg is TaskUpdateMessage {
  return msg.type === "task_update" && "event" in msg && "task" in msg && "timestamp" in msg;
}

function isTaskRunUpdate(msg: WebSocketMessage): msg is TaskRunUpdateMessage {
  return msg.type === "task_run_update" && "event" in msg && "task_run" in msg && "timestamp" in msg;
}

export function useTaskWebSocket(taskId?: number) {
  const [connected, setConnected] = useState(false);
  const [taskUpdate, setTaskUpdate] = useState<TaskUpdateMessage | null>(null);
  const [taskRunUpdate, setTaskRunUpdate] = useState<TaskRunUpdateMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const token = localStorage.getItem("access_token");
    if (!token) {
      setError("No authentication token");
      return;
    }

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws"}/tasks?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
      
      if (taskId) {
        ws.send(JSON.stringify({ type: "subscribe_task", task_id: taskId }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        
        if (isTaskUpdate(message)) {
          setTaskUpdate(message);
        } else if (isTaskRunUpdate(message)) {
          setTaskRunUpdate(message);
        } else if (message.type === "subscribed") {
          console.log("Subscribed to task:", (message as { task_id?: number }).task_id);
        } else if (message.type === "error") {
          setError((message as { message?: string }).message || "Unknown error");
        }
      } catch (err) {
        console.error("Failed to parse websocket message:", err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;

      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      } else {
        setError("Max reconnection attempts reached");
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("WebSocket connection error");
    };
  }, [taskId]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      if (taskId) {
        wsRef.current.send(JSON.stringify({ type: "unsubscribe_task", task_id: taskId }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, [taskId]);

  const subscribe = useCallback((newTaskId: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "subscribe_task", task_id: newTaskId }));
    }
  }, []);

  const unsubscribe = useCallback((taskIdToUnsubscribe: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "unsubscribe_task", task_id: taskIdToUnsubscribe }));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connected,
    taskUpdate,
    taskRunUpdate,
    error,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
  };
}

export function useTaskRealTime(taskId?: number) {
  const { connected, taskUpdate, taskRunUpdate, error, subscribe, unsubscribe } = useTaskWebSocket(taskId);
  
  // Auto-subscribe when taskId changes
  useEffect(() => {
    if (taskId) {
      subscribe(taskId);
      return () => unsubscribe(taskId);
    }
  }, [taskId, subscribe, unsubscribe]);

  return {
    connected,
    taskUpdate,
    taskRunUpdate,
    error,
    isLoading: !connected && !error,
  };
}