"""
Mark-Imti Task Decomposition — DAG-based task graph
Based on Manus AI's task decomposition pattern
Supports parallel execution and dependency tracking
"""

import asyncio
import json
import uuid
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class DAGNodeState(Enum):
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGNode:
    id: str
    task: str
    tool: str
    params: dict = field(default_factory=dict)
    state: DAGNodeState = DAGNodeState.WAITING
    result: Optional[dict] = None
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2


class TaskDAG:
    """
    Directed Acyclic Graph for task decomposition.
    Supports parallel execution of independent tasks.
    """

    def __init__(self, model_caller=None):
        self.model = model_caller
        self.nodes: dict[str, DAGNode] = {}
        self.execution_log: list[dict] = []

    def add_node(self, task: str, tool: str = "auto", params: dict = None,
                 dependencies: list[str] = None) -> str:
        node_id = f"node-{uuid.uuid4().hex[:8]}"
        node = DAGNode(
            id=node_id,
            task=task,
            tool=tool,
            params=params or {},
            dependencies=dependencies or [],
        )
        self.nodes[node_id] = node

        for dep_id in node.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.append(node_id)

        return node_id

    def add_dependency(self, node_id: str, depends_on: str):
        if node_id in self.nodes and depends_on in self.nodes:
            self.nodes[node_id].dependencies.append(depends_on)
            self.nodes[depends_on].dependents.append(node_id)

    def get_ready_nodes(self) -> list[DAGNode]:
        ready = []
        for node in self.nodes.values():
            if node.state != DAGNodeState.WAITING:
                continue

            all_deps_met = all(
                self.nodes[dep].state == DAGNodeState.COMPLETED
                for dep in node.dependencies
                if dep in self.nodes
            )

            if all_deps_met:
                node.state = DAGNodeState.READY
                ready.append(node)

        return ready

    async def decompose(self, request: str) -> "TaskDAG":
        if not self.model:
            self.add_node(request, "auto")
            return self

        prompt = f"""Decompose this task into a directed acyclic graph of subtasks.
Each subtask should be independently executable where possible.

TASK: {request}

Return JSON:
{{
    "nodes": [
        {{
            "task": "description",
            "tool": "tool_name",
            "dependencies": []
        }}
    ]
}}"""

        try:
            response = await self.model.complete(prompt, max_tokens=2000)
            data = json.loads(response)
            for node_data in data.get("nodes", []):
                self.add_node(
                    task=node_data["task"],
                    tool=node_data.get("tool", "auto"),
                    dependencies=node_data.get("dependencies", []),
                )
        except Exception:
            self.add_node(request, "auto")

        return self

    async def execute(self, executor) -> dict:
        completed = 0
        total = len(self.nodes)
        max_iterations = total * 2

        for _ in range(max_iterations):
            ready = self.get_ready_nodes()
            if not ready:
                if all(n.state in (DAGNodeState.COMPLETED, DAGNodeState.FAILED, DAGNodeState.SKIPPED)
                       for n in self.nodes.values()):
                    break
                await asyncio.sleep(0.1)
                continue

            tasks = [self._execute_node(node, executor) for node in ready]
            await asyncio.gather(*tasks)

            for node in ready:
                if node.state == DAGNodeState.COMPLETED:
                    completed += 1

        return {
            "total_nodes": total,
            "completed": completed,
            "failed": sum(1 for n in self.nodes.values() if n.state == DAGNodeState.FAILED),
            "results": {
                nid: {
                    "task": n.task,
                    "state": n.state.value,
                    "result": n.result,
                    "error": n.error,
                }
                for nid, n in self.nodes.items()
            },
            "execution_log": self.execution_log,
        }

    async def _execute_node(self, node: DAGNode, executor):
        node.state = DAGNodeState.RUNNING
        node.started_at = datetime.utcnow().isoformat()

        self.execution_log.append({
            "node_id": node.id,
            "action": "start",
            "task": node.task,
            "timestamp": node.started_at,
        })

        try:
            context = {}
            for dep_id in node.dependencies:
                if dep_id in self.nodes and self.nodes[dep_id].result:
                    context[dep_id] = self.nodes[dep_id].result

            result = await executor(node.task, node.tool, node.params, context)
            node.result = result
            node.state = DAGNodeState.COMPLETED
        except Exception as e:
            node.error = str(e)
            if node.retry_count < node.max_retries:
                node.retry_count += 1
                node.state = DAGNodeState.WAITING
            else:
                node.state = DAGNodeState.FAILED

        node.completed_at = datetime.utcnow().isoformat()

        self.execution_log.append({
            "node_id": node.id,
            "action": "complete" if node.state == DAGNodeState.COMPLETED else "fail",
            "task": node.task,
            "timestamp": node.completed_at,
        })

    def get_execution_order(self) -> list[str]:
        visited = set()
        order = []

        def dfs(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                for dep in node.dependencies:
                    dfs(dep)
                order.append(node_id)

        for nid in self.nodes:
            dfs(nid)

        return order

    def visualize(self) -> str:
        lines = ["Task DAG:"]
        for nid, node in self.nodes.items():
            deps = ", ".join(node.dependencies) if node.dependencies else "none"
            lines.append(f"  {nid}: {node.task} [{node.state.value}] (deps: {deps})")
        return "\n".join(lines)
