"""
Advanced Workflows — The intelligence layer for Mark and Jenny agents.
Inspired by GPT-6 Astra and Claude Mythos 5 capabilities.

These workflows don't depend on any specific model. They use WHATEVER
model the user has configured — OpenAI, Anthropic, Google, Ollama,
AirLLM, LM Studio, vLLM, anything. The workflows provide the
STRUCTURE, PLANNING, and DOMAIN EXPERTISE that makes Mark Imti
work like a frontier model, regardless of which model is behind it.

Each workflow:
1. Takes a user request
2. Breaks it into intelligent steps
3. Calls the configured model for reasoning at each step
4. Uses available tools (web search, file analysis, PubMed, etc.)
5. Validates and synthesizes results
6. Stores findings in memory/knowledge for future use
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from pathlib import Path

from app.core.config import get_settings
from app.services.model_caller import ModelCaller

settings = get_settings()


# ============================================================
# WORKFLOW 1: CYBERSECURITY
# ============================================================

class CybersecurityWorkflow:
    """
    Autonomous security analysis — like Claude Mythos 5's Claude Security
    and GPT-6 Astra's critical-level cybersecurity capabilities.

    The agent reads code, understands it, finds real vulnerabilities,
    classifies them by severity, and generates fixes.
    """

    SYSTEM_PROMPT = """You are an expert cybersecurity analyst with deep knowledge of:
- OWASP Top 10 (2021) vulnerabilities
- CWE/SANS Top 25 Most Dangerous Software Weaknesses
- Common vulnerability patterns in Python, JavaScript, TypeScript, Go, Java, Rust
- Authentication/authorization flaws
- Injection attacks (SQL, XSS, CSRF, SSRF, command injection)
- Insecure deserialization, path traversal, hardcoded secrets
- Cryptographic weaknesses
- Race conditions and concurrency bugs

For each vulnerability found, provide:
1. VULNERABILITY: Clear name
2. SEVERITY: critical/high/medium/low
3. CWE: CWE-ID if applicable
4. LOCATION: File and line number
5. DESCRIPTION: What the issue is and why it matters
6. EXPLOIT SCENARIO: How an attacker could exploit this
7. FIX: Specific code fix
8. CONFIDENCE: How confident you are (0-100%)

Also provide:
- Overall security score (0-100)
- Top 3 priority fixes
- Architecture-level security concerns"""

    async def scan_code(
        self,
        code: str,
        filename: str = "unknown",
        language: str = "auto",
    ) -> Dict[str, Any]:
        """Scan code for security vulnerabilities using AI reasoning."""
        prompt = f"""Analyze this code for security vulnerabilities:

FILE: {filename}
LANGUAGE: {language}

CODE:
```
{code[:12000]}
```

Provide a thorough security analysis with specific line references."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.1)

        if not response:
            return {"success": False, "error": "No AI model available. Start AirLLM or Ollama."}

        vulns = self._parse_vulnerabilities(response)
        score = self._extract_score(response)

        return {
            "success": True,
            "filename": filename,
            "language": language,
            "vulnerabilities": vulns,
            "score": score,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def scan_directory(self, dir_path: str) -> Dict[str, Any]:
        """Scan all code files in a directory."""
        path = Path(dir_path)
        if not path.exists():
            return {"success": False, "error": "Directory not found"}

        code_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
                          ".sql", ".php", ".java", ".go", ".rs", ".rb", ".env", ".yaml", ".yml"}

        files_to_scan = []
        for file in path.rglob("*"):
            if file.suffix in code_extensions and ".git" not in str(file) and "node_modules" not in str(file):
                files_to_scan.append(file)

        if not files_to_scan:
            return {"success": True, "files_scanned": 0, "message": "No code files found"}

        # Combine all code for efficient AI analysis
        combined = ""
        file_list = []
        for file in files_to_scan[:25]:
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
                rel = str(file.relative_to(path))
                combined += f"\n\n# FILE: {rel}\n{content}"
                file_list.append(rel)
            except Exception:
                pass

        prompt = f"""Analyze this codebase ({len(file_list)} files) for security vulnerabilities:

{combined[:20000]}

Provide:
1. Per-file vulnerability summary
2. Overall security score (0-100)
3. Most critical issues to fix first
4. Cross-file security concerns (e.g., auth flows, data exposure)
5. Architecture-level recommendations"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.1)

        return {
            "success": True,
            "files_scanned": len(files_to_scan),
            "files": file_list,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def generate_fix(self, code: str, vulnerability: str) -> Dict[str, Any]:
        """Generate a fix for a specific vulnerability."""
        prompt = f"""Fix this security vulnerability in the code:

VULNERABILITY: {vulnerability}

ORIGINAL CODE:
```
{code[:8000]}
```

Provide:
1. The complete fixed code
2. Explanation of what was changed
3. Why the fix works
4. Any side effects or testing recommendations"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "original_code": code[:500],
            "fix": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def pentest_guide(self, target: str, scope: str = "web") -> Dict[str, Any]:
        """Generate a custom penetration testing plan."""
        prompt = f"""Create a detailed penetration testing plan for:

TARGET: {target}
SCOPE: {scope}

Provide:
1. Pre-engagement (permissions, scope, rules of engagement)
2. Reconnaissance (OSINT, DNS, subdomain enumeration — specific tools)
3. Scanning (port scanning, service detection — nmap commands)
4. Enumeration (finding attack surfaces, user enumeration)
5. Exploitation (specific attack vectors with commands)
6. Post-exploitation (privilege escalation, lateral movement)
7. Reporting (structure, executive summary, technical findings)
8. Remediation guidance for each finding

Include specific tool names, commands, and techniques."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "target": target,
            "scope": scope,
            "guide": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def web_audit(self, url: str) -> Dict[str, Any]:
        """Full security audit — gathers all data, sends to AI for REAL analysis."""
        page_content = ""
        headers = {}
        cookies = []
        status_code = 0
        redirect_chain = []
        ssl_info = {}

        # Gather raw data — NO analysis here
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
                r = await client.get(url)
                page_content = r.text[:10000]
                headers = dict(r.headers)
                status_code = r.status_code
                cookies = [{"name": c.name, "value": c.value[:20], "domain": c.domain,
                           "path": c.path, "secure": c.secure,
                           "samesite": str(c.same_site)} for c in r.cookies.jar]
                redirect_chain = [str(redirect.url) for redirect in r.history]
        except Exception as e:
            return {"success": False, "error": str(e)}

        # Gather SSL data
        try:
            from urllib.parse import urlparse
            import ssl, socket
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if parsed.scheme == "https":
                ctx = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=5) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        ssl_info = {
                            "valid": True,
                            "issuer": dict(x[0] for x in cert.get("issuer", [])),
                            "subject": dict(x[0] for x in cert.get("subject", [])),
                            "expires": cert.get("notAfter", ""),
                            "protocol": ssock.version(),
                        }
        except Exception:
            ssl_info = {"valid": False, "error": "Could not verify SSL"}

        # Send EVERYTHING to AI — AI does ALL the analysis
        prompt = f"""You are an expert cybersecurity analyst performing a complete security audit.

URL: {url}
STATUS CODE: {status_code}

SSL/TLS CERTIFICATE:
{json.dumps(ssl_info, indent=2)}

ALL HTTP HEADERS (raw):
{json.dumps(headers, indent=2)}

ALL COOKIES ({len(cookies)}):
{json.dumps(cookies, indent=2)}

REDIRECT CHAIN: {redirect_chain}

PAGE HTML (first 5000 chars):
{page_content[:5000]}

You have ALL the data. Now perform a COMPLETE security audit:

1. Analyze EVERY security header — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, COEP, COOP, CORP. For each: is it present? Is it configured correctly? What's wrong?

2. Analyze EVERY cookie — HttpOnly, Secure, SameSite, domain scope, path, expiry. Which cookies are dangerous?

3. Analyze SSL/TLS — certificate validity, protocol, issuer trust, expiration.

4. Check for information disclosure — server versions, X-Powered-By, error details, directory listing.

5. Analyze page content — mixed content, suspicious scripts, malicious redirects, phishing indicators.

6. SITE SAFETY: Is this site safe for users? What should users avoid?

7. SECURITY SCORE: 0-100 with detailed justification.

8. CRITICAL FIXES: Ranked by importance, with specific code/config changes.

9. USER SAFETY VERDICT: Safe / Caution / Dangerous — and why.

Be thorough. Analyze every detail. Give specific, actionable findings."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "url": url,
            "status_code": status_code,
            "ssl": ssl_info,
            "headers": headers,
            "cookies": cookies,
            "redirects": redirect_chain,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def analyze_cookies(self, url: str) -> Dict[str, Any]:
        """Gather all cookie data — AI does the analysis."""
        cookies = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(url)
                for cookie in r.cookies.jar:
                    cookies.append({
                        "name": cookie.name,
                        "value": cookie.value[:50],
                        "domain": cookie.domain,
                        "path": cookie.path,
                        "secure": cookie.secure,
                        "expires": cookie.expires,
                        "samesite": str(cookie.same_site) if cookie.same_site else "None",
                    })
        except Exception as e:
            return {"success": False, "error": str(e)}

        prompt = f"""You are an expert cookie security analyst.

URL: {url}
COOKIES ({len(cookies)}):
{json.dumps(cookies, indent=2)}

Analyze EVERY cookie for security issues:
- HttpOnly flag (XSS protection)
- Secure flag (HTTPS only)
- SameSite attribute (CSRF protection)
- Domain scope (too broad?)
- Path scope
- Session vs persistent
- Sensitive data exposure

For each cookie: is it secure? What's the risk? What's the fix?
Overall cookie security score (0-100).
Priority recommendations."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "url": url,
            "cookies": cookies,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def site_safety_check(self, url: str) -> Dict[str, Any]:
        """Gather all page data — AI assesses safety."""
        page_content = ""
        headers = {}
        links = []
        scripts = []

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(url)
                page_content = r.text[:15000]
                headers = dict(r.headers)
                import re
                links = re.findall(r'href=["\']([^"\']+)["\']', page_content)
                scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', page_content)
        except Exception as e:
            return {"success": False, "error": str(e)}

        prompt = f"""You are an expert web safety analyst. Assess if this site is SAFE for users.

URL: {url}

SECURITY HEADERS:
{json.dumps({k: v for k, v in headers.items()}, indent=2)}

EXTERNAL LINKS ({len(links)}):
{json.dumps(links[:30], indent=2)}

EXTERNAL SCRIPTS ({len(scripts)}):
{json.dumps(scripts[:15], indent=2)}

PAGE HTML (first 8000 chars):
{page_content[:8000]}

Analyze:
1. Is this site SAFE TO VISIT? (Yes/No/Caution)
2. Malicious indicators — any suspicious patterns?
3. Phishing indicators — fake login forms, impersonation?
4. Mixed content — HTTP resources on HTTPS page?
5. Suspicious redirects — where does it redirect?
6. Data collection — what data does it collect?
7. Third-party trackers — how many, who are they?
8. User data exposure risks
9. SAFETY SCORE (0-100)
10. Should users visit? What to avoid? What NOT to enter?

Be thorough. Protect the user."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "url": url,
            "links_count": len(links),
            "scripts_count": len(scripts),
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def full_security_assessment(self, url: str) -> Dict[str, Any]:
        """Complete security assessment — all data gathered, AI produces comprehensive report."""
        # Gather ALL raw data
        page_content = ""
        headers = {}
        cookies = []
        status_code = 0
        redirect_chain = []
        ssl_info = {}
        links = []
        scripts = []

        try:
            import httpx
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
                r = await client.get(url)
                page_content = r.text[:15000]
                headers = dict(r.headers)
                status_code = r.status_code
                cookies = [{"name": c.name, "value": c.value[:20], "domain": c.domain,
                           "path": c.path, "secure": c.secure,
                           "samesite": str(c.same_site)} for c in r.cookies.jar]
                redirect_chain = [str(redirect.url) for redirect in r.history]
                import re
                links = re.findall(r'href=["\']([^"\']+)["\']', page_content)
                scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', page_content)
        except Exception as e:
            return {"success": False, "error": str(e)}

        try:
            from urllib.parse import urlparse
            import ssl, socket
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if parsed.scheme == "https":
                ctx = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=5) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        ssl_info = {"valid": True, "issuer": dict(x[0] for x in cert.get("issuer", [])),
                                   "expires": cert.get("notAfter", ""), "protocol": ssock.version()}
        except Exception:
            ssl_info = {"valid": False}

        # ONE massive prompt — AI does EVERYTHING
        prompt = f"""You are an elite cybersecurity analyst performing a COMPLETE security assessment.

TARGET URL: {url}
STATUS: {status_code}

SSL/TLS: {json.dumps(ssl_info, indent=2)}

ALL HEADERS: {json.dumps(headers, indent=2)}

ALL COOKIES ({len(cookies)}): {json.dumps(cookies, indent=2)}

REDIRECTS: {redirect_chain}

LINKS ({len(links)}): {json.dumps(links[:30], indent=2)}

SCRIPTS ({len(scripts)}): {json.dumps(scripts[:15], indent=2)}

PAGE HTML: {page_content[:8000]}

You have EVERYTHING. Now deliver a COMPREHENSIVE security assessment:

1. EXECUTIVE SUMMARY — overall security posture in 3 sentences
2. HEADER ANALYSIS — for EACH security header: present? correct? risks?
3. COOKIE ANALYSIS — for EACH cookie: secure? risks? fixes?
4. SSL/TLS ANALYSIS — certificate, protocol, trust
5. CONTENT ANALYSIS — mixed content, malicious scripts, phishing
6. SITE SAFETY — safe for users? what to avoid?
7. VULNERABILITIES FOUND — each with severity, CWE, exploit scenario, fix
8. OVERALL GRADE (A+ to F) with justification
9. USER SAFETY VERDICT — Safe/Caution/Dangerous
10. TOP 10 ACTIONS to improve security
11. USER RECOMMENDATIONS — what should users do/avoid on this site?

Be exhaustive. Leave no stone unturned."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "url": url,
            "headers": headers,
            "cookies": cookies,
            "ssl": ssl_info,
            "redirects": redirect_chain,
            "links_count": len(links),
            "scripts_count": len(scripts),
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    def _parse_vulnerabilities(self, response: str) -> List[Dict]:
        vulns = []
        current = {}
        for line in response.split("\n"):
            ll = line.lower().strip()
            if any(kw in ll for kw in ["vulnerability:", "issue:", "finding:", "bug:"]):
                if current:
                    vulns.append(current)
                current = {"name": line.split(":", 1)[-1].strip()}
            elif "severity:" in ll:
                current["severity"] = line.split(":", 1)[-1].strip().lower()
            elif "cwe" in ll and ":" in ll:
                current["cwe"] = line.split(":", 1)[-1].strip()
            elif "location:" in ll or "line" in ll and ":" in ll:
                current["location"] = line.split(":", 1)[-1].strip()
            elif "fix:" in ll or "remediation:" in ll:
                current["fix"] = line.split(":", 1)[-1].strip()
        if current:
            vulns.append(current)
        return vulns

    def _extract_score(self, response: str) -> int:
        patterns = [r"score[:\s]*(\d+)", r"(\d+)/100", r"(\d+)%\s*security"]
        for p in patterns:
            m = re.search(p, response, re.IGNORECASE)
            if m:
                return min(int(m.group(1)), 100)
        return 50


# ============================================================
# WORKFLOW 2: BIOLOGY RESEARCH
# ============================================================

class BioResearchWorkflow:
    """
    Autonomous biology research — like Claude Mythos 5's capabilities
    in drug design, protein analysis, genomics, and hypothesis generation.

    The agent searches real papers, analyzes sequences, generates
    hypotheses, and designs experiments.
    """

    SYSTEM_PROMPT = """You are an expert biological researcher with deep knowledge of:
- Molecular biology, genetics, biochemistry
- Protein structure and function
- Genomics and transcriptomics
- Drug design and development
- Bioinformatics and computational biology
- Cell signaling pathways
- Disease mechanisms

Provide accurate, detailed scientific analysis. Be precise about
molecular mechanisms. Cite specific pathways, proteins, and processes.
Generate novel, testable hypotheses based on evidence."""

    async def literature_review(
        self, query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Search PubMed + arXiv and synthesize findings."""
        # Search real databases
        papers = await self._search_pubmed(query, max_results)
        arxiv = await self._search_arxiv(query, max_results)
        papers.extend(arxiv)

        # AI synthesizes all findings
        papers_text = "\n".join([
            f"- {p.get('title', 'Untitled')} [{p.get('source', '?')}]: {p.get('abstract', 'No abstract')[:200]}"
            for p in papers[:15]
        ])

        prompt = f"""Perform a literature review on: {query}

Found {len(papers)} papers:
{papers_text}

Provide:
1. Executive summary of current knowledge
2. Key findings across papers
3. Areas of agreement and disagreement
4. Research gaps and future directions
5. Recommended reading (top 5 most relevant)
6. Novel hypotheses that emerge from synthesis"""

        synthesis = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "query": query,
            "papers_found": len(papers),
            "papers": papers[:15],
            "synthesis": synthesis,
            "model_used": ModelCaller.get_model_info(),
        }

    async def analyze_sequence(
        self, sequence: str, seq_type: str = "protein"
    ) -> Dict[str, Any]:
        """Analyze a biological sequence using AI reasoning."""
        prompt = f"""Analyze this {seq_type} sequence in detail:

SEQUENCE: {sequence[:3000]}

Provide:
1. Length and basic composition
2. Notable motifs and patterns
3. Functional predictions (domains, binding sites, active sites)
4. Structural predictions (secondary structure, transmembrane regions)
5. Evolutionary conservation clues
6. Disease associations if applicable
7. Potential research directions"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "sequence_length": len(sequence),
            "type": seq_type,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def generate_hypothesis(
        self, observation: str, domain: str = "general"
    ) -> Dict[str, Any]:
        """Generate novel research hypotheses from observations."""
        prompt = f"""Based on this observation in {domain}:

OBSERVATION: {observation}

Generate:
1. 5 novel, testable hypotheses
2. For each hypothesis:
   a. Clear, falsifiable statement
   b. Rationale based on known biology
   c. Suggested experiment to test it
   d. Expected results if hypothesis is true
   e. Alternative explanations to rule out
3. Priority ranking (most impactful first)
4. Potential clinical or research implications
5. Which model/technique would best test each hypothesis"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.5)

        return {
            "success": True,
            "observation": observation,
            "domain": domain,
            "hypotheses": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def design_experiment(self, research_question: str) -> Dict[str, Any]:
        """Design a complete experiment."""
        prompt = f"""Design a complete experiment for this research question:

QUESTION: {research_question}

Provide:
1. Hypothesis being tested
2. Experimental design (controls, variables, sample size justification)
3. Materials and methods (detailed protocol)
4. Expected results and interpretation
5. Statistical analysis plan
6. Potential pitfalls and how to address them
7. Timeline and resources needed
8. Ethical considerations
9. How to present results (figures, tables)"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "research_question": research_question,
            "experiment_design": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def predict_structure(self, sequence: str) -> Dict[str, Any]:
        """Predict protein structure features."""
        prompt = f"""Predict structural features for this protein sequence:

SEQUENCE: {sequence[:3000]}

Provide:
1. Secondary structure prediction (helix, sheet, coil percentages)
2. Transmembrane regions
3. Signal peptides
4. Disulfide bond predictions
5. Active site and binding domain predictions
6. Protein family classification
7. Structural stability predictions"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "sequence_length": len(sequence),
            "prediction": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def pathway_analysis(self, genes: List[str]) -> Dict[str, Any]:
        """Analyze biological pathways for given genes."""
        prompt = f"""Analyze biological pathways involving these genes: {', '.join(genes)}

Provide:
1. Known pathways these genes participate in
2. Protein-protein interaction networks
3. Signaling cascades and regulatory mechanisms
4. Disease associations
5. Drug targets and therapeutic potential
6. Key regulatory nodes and bottlenecks
7. Cross-pathway interactions"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "genes": genes,
            "pathway_analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def _search_pubmed(self, query: str, max_results: int) -> List[Dict]:
        papers = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={
                    "db": "pubmed", "term": query, "retmax": max_results, "retmode": "json",
                })
                if r.status_code == 200:
                    ids = r.json().get("esearchresult", {}).get("idlist", [])
                    if ids:
                        r2 = await client.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params={
                            "db": "pubmed", "id": ",".join(ids[:10]), "retmode": "json",
                        })
                        if r2.status_code == 200:
                            data = r2.json().get("result", {})
                            for pid in ids[:10]:
                                if pid in data:
                                    info = data[pid]
                                    papers.append({
                                        "id": pid, "source": "pubmed",
                                        "title": info.get("title", ""),
                                        "authors": [a.get("name", "") for a in info.get("authors", [])[:3]],
                                        "date": info.get("pubdate", ""),
                                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                                    })
        except Exception:
            pass
        return papers

    async def _search_arxiv(self, query: str, max_results: int) -> List[Dict]:
        papers = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get("http://export.arxiv.org/api/query", params={
                    "search_query": f"all:{query}", "max_results": max_results, "sortBy": "relevance",
                })
                if r.status_code == 200:
                    entries = re.findall(r"<entry>(.*?)</entry>", r.text, re.DOTALL)
                    for entry in entries[:10]:
                        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
                        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
                        link = re.search(r"<id>(.*?)</id>", entry)
                        arxiv_id = re.search(r"abs/(\d+\.\d+)", entry)
                        authors = re.findall(r"<name>(.*?)</name>", entry)
                        papers.append({
                            "id": arxiv_id.group(1) if arxiv_id else "",
                            "source": "arxiv",
                            "title": title.group(1).strip() if title else "",
                            "abstract": summary.group(1).strip()[:300] if summary else "",
                            "authors": authors[:3],
                            "url": link.group(1) if link else "",
                        })
        except Exception:
            pass
        return papers


# ============================================================
# WORKFLOW 3: DEEP REASONING
# ============================================================

class DeepReasoningWorkflow:
    """
    Multi-step chain-of-thought reasoning — like GPT-6 Astra's
    5 reasoning levels and Claude Mythos 5's adaptive thinking.

    Breaks complex problems into steps, gathers evidence,
    considers alternatives, and synthesizes conclusions.
    """

    SYSTEM_PROMPT = """You are an expert analyst performing deep reasoning.
Think through problems step by step. For each step:
1. State what you're examining
2. Present evidence
3. Consider alternatives
4. Draw intermediate conclusions

Be thorough, consider multiple perspectives, and acknowledge uncertainty.
Rate your confidence and identify limitations."""

    LEVELS = {
        "fast": {"steps": 2, "depth": "brief"},
        "balanced": {"steps": 4, "depth": "moderate"},
        "deep": {"steps": 6, "depth": "thorough"},
        "exhaustive": {"steps": 10, "depth": "comprehensive"},
        "maximum": {"steps": 15, "depth": "exhaustive"},
    }

    async def analyze(
        self,
        query: str,
        level: str = "balanced",
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Deep multi-step reasoning."""
        config = self.LEVELS.get(level, self.LEVELS["balanced"])

        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context, indent=2)[:2000]}"

        prompt = f"""Perform a {config['depth']} analysis ({config['steps']} steps):

QUESTION: {query}
{context_str}

Structure your analysis as:
1. UNDERSTANDING: What is being asked and why it matters
2. DECOMPOSITION: Break into {config['steps']} key components
3. ANALYSIS: Think through each component carefully
4. EVIDENCE: What supports your findings
5. ALTERNATIVES: Consider other explanations
6. SYNTHESIS: Combine into coherent conclusion
7. CONFIDENCE: Rate certainty (0-100%) with reasoning
8. LIMITATIONS: What you couldn't determine

Show your complete thinking process."""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        confidence = self._extract_confidence(response)
        chain = self._parse_chain(response)

        return {
            "success": True,
            "query": query,
            "level": level,
            "analysis": response,
            "reasoning_chain": chain,
            "confidence": confidence,
            "steps_count": config["steps"],
            "model_used": ModelCaller.get_model_info(),
        }

    async def compare_options(
        self, options: List[str], criteria: List[str], context: str = ""
    ) -> Dict[str, Any]:
        """Compare multiple options with structured evaluation."""
        options_str = "\n".join(f"- {i+1}. {opt}" for i, opt in enumerate(options))
        criteria_str = ", ".join(criteria)

        prompt = f"""Compare these options using criteria: {criteria_str}

OPTIONS:
{options_str}

CONTEXT: {context}

Provide:
1. Evaluation of each option against each criteria
2. Scoring (1-10) for each option on each criterion
3. Weighted total scores
4. Recommendation with reasoning
5. Risks and trade-offs for the recommended option
6. When each option would be the best choice"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "options": options,
            "criteria": criteria,
            "comparison": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def solve_problem(
        self, problem: str, approach: str = "systematic"
    ) -> Dict[str, Any]:
        """Solve a complex problem with structured approach."""
        prompt = f"""Solve this problem using a {approach} approach:

PROBLEM: {problem}

Provide:
1. Problem definition and constraints
2. Breaking down the problem
3. Identifying key variables and relationships
4. Solution approach and methodology
5. Step-by-step solution
6. Verification of the solution
7. Alternative solutions considered
8. Final recommendation with confidence level"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "problem": problem,
            "approach": approach,
            "solution": response,
            "model_used": ModelCaller.get_model_info(),
        }

    def _extract_confidence(self, response: str) -> float:
        patterns = [r"confidence[:\s]*(\d+)%", r"confidence[:\s]*(\d+)", r"(\d+)%\s*confiden"]
        for p in patterns:
            m = re.search(p, response, re.IGNORECASE)
            if m:
                return min(int(m.group(1)), 100) / 100.0
        return 0.6

    def _parse_chain(self, response: str) -> List[Dict]:
        chain = []
        for i, section in enumerate(response.split("\n\n")):
            if section.strip():
                chain.append({"step": i + 1, "content": section.strip()[:400]})
        return chain[:12]


# ============================================================
# WORKFLOW 4: AUTONOMOUS RESEARCH
# ============================================================

class AutonomousResearchWorkflow:
    """
    Extended autonomous research — like Claude Mythos 5's week-long
    autonomous genomics research capability.

    Searches the web, discovers papers, collects data,
    and produces comprehensive research reports.
    """

    SYSTEM_PROMPT = """You are an expert researcher. Synthesize information from multiple sources.
Identify key findings, consensus views, and research gaps.
Provide balanced, evidence-based assessments with proper attribution.
Always distinguish between established facts and speculation."""

    async def research_topic(
        self, topic: str, depth: str = "standard"
    ) -> Dict[str, Any]:
        """Conduct autonomous research on a topic."""
        # Search the web
        web_results = await self._web_search(topic)

        # Search academic sources
        papers = await self._search_academic(topic)

        # AI synthesizes everything
        web_text = "\n".join([
            f"- {r.get('title', '')}: {r.get('snippet', '')[:150]} [{r.get('url', '')}]"
            for r in web_results[:10]
        ])
        papers_text = "\n".join([
            f"- {p.get('title', '')} [{p.get('source', '')}]: {p.get('abstract', '')[:150]}"
            for p in papers[:10]
        ])

        prompt = f"""Research this topic comprehensively: {topic}

WEB RESULTS:
{web_text}

ACADEMIC PAPERS:
{papers_text}

Provide:
1. Executive Summary (key findings in 3-5 sentences)
2. Current State of Knowledge
3. Key Findings (organized by theme)
4. Areas of Consensus
5. Areas of Debate/Uncertainty
6. Research Gaps
7. Future Directions
8. Key Sources (cited)
9. Confidence Assessment (how reliable is this information)"""

        synthesis = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "topic": topic,
            "depth": depth,
            "web_results": web_results[:10],
            "papers": papers[:10],
            "synthesis": synthesis,
            "model_used": ModelCaller.get_model_info(),
        }

    async def _web_search(self, query: str) -> List[Dict]:
        results = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                # Try DuckDuckGo
                r = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1},
                )
                if r.status_code == 200:
                    data = r.json()
                    for topic in data.get("RelatedTopics", [])[:10]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append({
                                "title": topic.get("Text", "")[:100],
                                "snippet": topic.get("Text", ""),
                                "url": topic.get("FirstURL", ""),
                            })
        except Exception:
            pass
        return results

    async def _search_academic(self, query: str) -> List[Dict]:
        papers = []
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get("https://api.semanticscholar.org/graph/v1/paper/search", params={
                    "query": query, "limit": 10, "fields": "title,abstract,year,authors,url",
                })
                if r.status_code == 200:
                    for p in r.json().get("data", [])[:10]:
                        papers.append({
                            "title": p.get("title", ""),
                            "abstract": (p.get("abstract") or "")[:300],
                            "year": p.get("year"),
                            "authors": [a.get("name", "") for a in (p.get("authors") or [])[:3]],
                            "url": p.get("url", ""),
                            "source": "semantic_scholar",
                        })
        except Exception:
            pass
        return papers


# ============================================================
# WORKFLOW 5: CODING INTELLIGENCE
# ============================================================

class CodingIntelligenceWorkflow:
    """
    Advanced software engineering — like GPT-6 Astra's coding
    capabilities (57.9% Terminal-Bench, 74.1% DeepSWE).

    Analyzes codebases, finds bugs, suggests improvements,
    generates tests, and creates documentation.
    """

    SYSTEM_PROMPT = """You are an expert software engineer with deep knowledge of:
- Clean code principles, SOLID, DRY, KISS
- Design patterns and architecture
- Performance optimization
- Security best practices
- Testing strategies
- Code review and refactoring

Write clean, efficient, well-documented code. Follow language-specific
best practices. Explain your reasoning."""

    async def analyze_codebase(self, code: str, filename: str = "") -> Dict[str, Any]:
        """Analyze code for quality, patterns, and issues."""
        prompt = f"""Analyze this code thoroughly:

FILE: {filename}

```
{code[:12000]}
```

Provide:
1. Code quality assessment (readability, maintainability)
2. Design patterns used (or should be used)
3. Potential bugs and edge cases
4. Performance issues
5. Security concerns
6. Test coverage recommendations
7. Refactoring suggestions (specific code changes)
8. Overall quality score (0-100)"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "filename": filename,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def fix_bug(self, code: str, error: str, context: str = "") -> Dict[str, Any]:
        """Diagnose and fix a bug."""
        prompt = f"""Fix this bug:

ERROR: {error}
{f'CONTEXT: {context}' if context else ''}

CODE:
```
{code[:10000]}
```

Provide:
1. Root cause analysis
2. Why this bug occurs
3. The complete fixed code
4. Explanation of the fix
5. How to prevent similar bugs
6. Test cases to verify the fix"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "error": error,
            "fix": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def refactor(self, code: str, goal: str = "improve quality") -> Dict[str, Any]:
        """Refactor code for better quality."""
        prompt = f"""Refactor this code to {goal}:

```
{code[:12000]}
```

Provide:
1. Issues with current code
2. Refactoring strategy
3. Complete refactored code
4. Before/after comparison
5. Any behavioral changes to be aware of
6. How to verify the refactor didn't break anything"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.2)

        return {
            "success": True,
            "goal": goal,
            "refactored": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def generate_tests(self, code: str, filename: str = "") -> Dict[str, Any]:
        """Generate comprehensive tests."""
        prompt = f"""Generate comprehensive tests for this code:

FILE: {filename}

```
{code[:10000]}
```

Provide:
1. Unit tests covering all functions/methods
2. Edge cases and boundary conditions
3. Error handling tests
4. Integration test suggestions
5. Test data fixtures
6. Coverage analysis (what's covered, what's not)"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "filename": filename,
            "tests": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def explain_code(self, code: str, level: str = "detailed") -> Dict[str, Any]:
        """Explain code at the specified level."""
        prompt = f"""Explain this code at {level} level:

```
{code[:10000]}
```

Provide:
1. High-level purpose
2. How it works (step by step)
3. Key functions/classes and their roles
4. Data flow
5. Dependencies and integrations
6. Potential improvements
7. Usage examples"""

        response = await ModelCaller.call(prompt, self.SYSTEM_PROMPT, temperature=0.3)

        return {
            "success": True,
            "explanation": response,
            "model_used": ModelCaller.get_model_info(),
        }


# ============================================================
# WORKFLOW 6: CONTEXT MEMORY
# ============================================================

class ContextMemoryWorkflow:
    """
    Persistent context across sessions — like GPT-6 Astra's
    searchable context memory across windows.

    Maintains working notes, learns from interactions,
    and builds a knowledge base over time.
    """

    async def store_working_memory(
        self, db, user_id: int, content: str, context: str = "",
        importance: int = 70, project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Store something the agent learned or decided."""
        from app.models.knowledge import Memory, MemoryType

        memory = Memory(
            type=MemoryType.SEMANTIC,
            content=content[:2000],
            source=f"agent_workflow:{context}" if context else "agent_workflow",
            confidence=85,
            importance=importance,
            enabled=True,
            owner_id=user_id,
            project_id=project_id,
            memory_metadata={"context": context, "timestamp": datetime.utcnow().isoformat()},
        )
        db.add(memory)
        db.commit()

        return {"success": True, "memory_id": memory.id}

    async def store_research_finding(
        self, db, user_id: int, topic: str, finding: str,
        sources: List[str], project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Store a research finding with sources."""
        from app.models.knowledge import Knowledge

        knowledge = Knowledge(
            name=f"Research: {topic[:100]}",
            use_when=f"User asks about {topic[:100]}",
            content=f"Research finding: {finding}\n\nSources: {', '.join(sources[:5])}",
            enabled=True,
            owner_id=user_id,
            project_id=project_id,
            source="autonomous_research",
            confidence=80,
            importance=75,
            tags=["research", "auto-generated"],
        )
        db.add(knowledge)
        db.commit()

        return {"success": True, "knowledge_id": knowledge.id}

    async def get_context(
        self, db, user_id: int, query: str, project_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get relevant context for a query."""
        from app.services.agent_brain import recall_scored
        recalled = recall_scored(db, user_id, query, project_id, limit=5)

        return {
            "success": True,
            "context_items": recalled,
            "total": len(recalled),
        }


# ============================================================
# SINGLETONS
# ============================================================

cybersecurity_workflow = CybersecurityWorkflow()
bio_research_workflow = BioResearchWorkflow()
deep_reasoning_workflow = DeepReasoningWorkflow()
autonomous_research_workflow = AutonomousResearchWorkflow()
coding_intelligence_workflow = CodingIntelligenceWorkflow()
context_memory_workflow = ContextMemoryWorkflow()
