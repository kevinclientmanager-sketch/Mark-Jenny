# Mark Imti — Advanced Intelligence Build Plan
## Making Mark Imti Agents Work Like GPT-6 Astra & Claude Mythos 5

---

## Research Summary

### GPT-6 Astra (OpenAI, Sep 2026)
- **Multi-step agentic workflows**: Plans, executes, coordinates complex tasks end-to-end
- **Computer use**: Interacts with GUIs, forms, desktop apps — not just chat
- **Advanced coding**: 57.9% Terminal-Bench, 74.1% DeepSWE, navigates 80M+ line codebases
- **Deep reasoning**: 1M context, 128K output, 5 reasoning effort levels (low→max)
- **Context memory**: Maintains notes across context windows, searchable previous windows
- **Research & browsing**: Web search, file search, knowledge synthesis
- **Professional workflows**: Database migrations, data science, scientific workflows, CAD
- **Cybersecurity**: Critical level — finds unknown vulnerabilities, develops exploits autonomously

### Claude Mythos 5 (Anthropic, Jun 2026)
- **Biology research**: Drug design 10x faster, protein structure prediction, genomics across 138 species
- **Hypothesis generation**: Scientists preferred Mythos hypotheses 80% over Opus-class
- **Cybersecurity**: Claude Security scans, vulnerability detection with CWE classification
- **Adaptive thinking**: Always-on reasoning, effort-based depth control
- **Agentic work**: Long-horizon tasks, tool use, memory, code execution
- **Autonomous R&D**: Conducted week-long autonomous genomics research
- **Software engineering**: Compressed months of engineering into days (Stripe report)

---

## Core Insight: The Intelligence Is In The AGENTS, Not The Models

The user's vision: Mark and Jenny agents should be smart enough to do what Astra and Mythos do — **using whatever model the user configures (local or online)**. The agents contain the WORKFLOWS, DECISION LOGIC, and DOMAIN EXPERTISE. The model is just the brain that powers them.

**Architecture:**
```
User Request (plain language)
    ↓
Mark/Jenny Agent (contains the intelligence)
    ├── Classifies task type
    ├── Selects workflow (cyber, bio, coding, analysis)
    ├── Breaks into steps
    ├── Calls configured model (local/online) for each step
    ├── Uses tools (web search, file analysis, PubMed, etc.)
    ├── Validates results
    └── Returns intelligent output
```

---

## Feature Map: What To Build

### 1. CYBERSECURITY WORKFLOW (Inspired by Astra + Mythos)
**Agent capability: Autonomous security analysis**

Built-in workflow that handles:
- **Code vulnerability scanning** — Agent reads code, identifies OWASP Top 10, CWE classifications
- **Multi-step analysis** — Agent breaks code into sections, analyzes each, synthesizes findings
- **Severity classification** — Critical/High/Medium/Low withCVSS-like scoring
- **Fix generation** — Agent generates patched code for each vulnerability
- **Penetration testing guide** — Agent creates step-by-step attack plan
- **Web app audit** — Agent analyzes HTTP headers, cookies, content security
- **Continuous monitoring** — Agent watches for new vulnerabilities in codebase
- **Tool integration** — Uses bandit (Python), semgrep, npm audit when available

### 2. BIOLOGY RESEARCH WORKFLOW (Inspired by Mythos)
**Agent capability: Autonomous research and analysis**

Built-in workflow that handles:
- **Literature review** — Search PubMed + arXiv, synthesize findings, identify gaps
- **Sequence analysis** — Protein/DNA analysis with real biological reasoning
- **Hypothesis generation** — Agent proposes testable hypotheses from observations
- **Experiment design** — Agent designs complete experiments with controls, methods
- **Structure prediction** — Protein structure feature prediction
- **Pathway analysis** — Gene/protein pathway mapping
- **Drug target analysis** — Identify potential drug targets from protein data
- **Tool integration** — Uses BLAST, Clustal when available, falls back to AI reasoning

### 3. DEEP REASONING ENGINE (Inspired by Astra's reasoning levels)
**Agent capability: Multi-step chain-of-thought reasoning**

Built-in workflow that handles:
- **Task decomposition** — Break complex problems into manageable steps
- **Evidence gathering** — Collect relevant information from multiple sources
- **Chain-of-thought** — Step-by-step reasoning with visible thinking
- **Confidence scoring** — Rate certainty of conclusions
- **Counter-argument analysis** — Consider alternative explanations
- **Synthesis** — Combine findings into coherent conclusions
- **5 reasoning levels** — Fast/Balanced/Deep/Exhaustive/Maximum

### 4. AUTONOMOUS RESEARCH AGENT (Inspired by Mythos's week-long research)
**Agent capability: Extended autonomous research tasks**

Built-in workflow that handles:
- **Multi-session research** — Research tasks that span hours/days
- **Web research** — Real-time web search for current information
- **Paper discovery** — Find and summarize relevant papers
- **Data collection** — Gather data from multiple sources
- **Report generation** — Produce comprehensive research reports
- **Progress tracking** — Resume interrupted research sessions
- **Source verification** — Validate credibility of sources

### 5. CODING INTELLIGENCE (Inspired by Astra's coding)
**Agent capability: Advanced software engineering**

Built-in workflow that handles:
- **Code analysis** — Understand codebases, find patterns, identify issues
- **Bug detection** — Find and fix bugs with root cause analysis
- **Refactoring** — Suggest and implement code improvements
- **Architecture review** — Analyze system design, suggest improvements
- **Test generation** — Create comprehensive test suites
- **Documentation** — Generate documentation from code
- **CI/CD integration** — Work with build systems, tests, deployments

### 6. CONTEXT MEMORY SYSTEM (Inspired by Astra's context memory)
**Agent capability: Persistent memory across sessions**

Built-in system that handles:
- **Session notes** — Agent maintains working notes during tasks
- **Cross-session memory** — Remember previous work and decisions
- **Knowledge base** — Build and query accumulated knowledge
- **Learning** — Improve from past interactions and corrections
- **User preferences** — Remember how the user likes things done

---

## Implementation Plan

### Phase 1: Agent Core (Week 1)
1. **Agent Brain v2** — Enhanced decision engine with workflow selection
2. **Workflow registry** — Register available workflows per agent
3. **Step executor** — Execute multi-step plans with model calls
4. **Result validator** — Verify quality of AI outputs

### Phase 2: Cybersecurity Workflow (Week 2)
1. **Code scanner** — Read and analyze code files
2. **Vulnerability classifier** — CWE/OWASP mapping
3. **Fix generator** — Produce patched code
4. **Report builder** — Generate security reports

### Phase 3: Biology Workflow (Week 2)
1. **PubMed/arXiv search** — Real paper search
2. **Sequence analyzer** — Protein/DNA analysis
3. **Hypothesis engine** — Generate research hypotheses
4. **Experiment designer** — Create experimental plans

### Phase 4: Reasoning & Research (Week 3)
1. **Multi-step planner** — Break tasks into steps
2. **Evidence collector** — Gather information
3. **Chain-of-thought** — Step-by-step reasoning
4. **Research orchestrator** — Long-running research tasks

### Phase 5: Memory & Integration (Week 3)
1. **Context memory** — Cross-session persistence
2. **Tool integration** — Connect external tools
3. **Web research** — Real-time online research
4. **Progress tracking** — Resume interrupted work

---

## How It Works (User Perspective)

**Example: Security Scan**
1. User: "Scan my backend code for security issues"
2. Agent (Jenny): Classifies as cybersecurity task → activates security workflow
3. Agent: Reads all Python files in backend
4. Agent: For each file, calls the configured model with security analysis prompt
5. Agent: Collects all findings, deduplicates, classifies severity
6. Agent: Generates fix suggestions for each vulnerability
7. Agent: Produces comprehensive security report
8. Jenny: Presents report to user with severity ratings and fixes

**Example: Biology Research**
1. User: "Research protein folding mechanisms and suggest hypotheses"
2. Agent (Mark): Classifies as biology task → activates bio workflow
3. Agent: Searches PubMed for recent papers on protein folding
4. Agent: Synthesizes findings from 20+ papers
5. Agent: Identifies research gaps and contradictions
6. Agent: Generates 5 novel hypotheses with supporting evidence
7. Agent: Designs experiments to test each hypothesis
8. Mark: Presents research summary with hypotheses and experiment plans

---

## Model Agnostic Design

The agents work the same way regardless of model:
- **Local (AirLLM/Ollama)**: Agent calls local model for each step
- **Cloud (OpenAI/Anthropic)**: Agent calls API for each step
- **Hybrid**: Agent uses local for simple steps, cloud for complex ones

The intelligence is in the WORKFLOW, not the model. The model provides the reasoning ability, but the agent decides WHAT to reason about and HOW to structure the analysis.
