import { spawn } from "child_process";

export const CrewAIHermesPlugin = async ({ project, client, $, directory, worktree }) => {
  const log = (msg) => console.log(`[CrewAI-Hermes] ${msg}`);
  
  log("Plugin initialized - CrewAI & Hermes bridges active");

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "bash") {
        const cmd = output.args?.command || "";
        
        // Auto-route complex tasks to CrewAI
        if (cmd.includes("--crewai") || cmd.includes("--crew")) {
          log("Detected CrewAI request, routing to bridge...");
          const topic = cmd.replace(/--crew(ai)?\s*/i, "").trim();
          if (topic) {
            output.args.command = `node "C:\\Users\\LAP TECH\\.opencode\\mcp-servers\\crewai-bridge.mjs" "${topic}"`;
          }
        }
        
        // Auto-route autonomous tasks to Hermes
        if (cmd.includes("--hermes") || cmd.includes("--auto")) {
          log("Detected Hermes request, routing to bridge...");
          const task = cmd.replace(/--(hermes|auto)\s*/i, "").trim();
          if (task) {
            output.args.command = `node "C:\\Users\\LAP TECH\\.opencode\\mcp-servers\\hermes-bridge.mjs" "${task}"`;
          }
        }
      }
    },

    "session.created": async (input, output) => {
      log("New session created - CrewAI & Hermes tools available");
    },
  };
};

export default CrewAIHermesPlugin;
