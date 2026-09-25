"""
Cybersecurity Agent — Mythos-level security analysis.
Inspired by Claude Mythos 5's actual capabilities:
- Autonomous vulnerability discovery
- Code reasoning (traces data flows, understands reachability)
- Exploit chain analysis
- CWE classification with confidence ratings
- Root cause tracing
- Patch generation with diffs
- Continuous security loop
- Attack surface analysis

This agent READS code like a security researcher. Finds vulnerabilities
that pattern-matching tools miss. Explains EXACTLY how an attacker
could exploit each finding.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.core.config import get_settings
from app.services.model_caller import ModelCaller

settings = get_settings()


class CybersecurityAgent:
    """
    Mythos-level cybersecurity agent.
    Reads code like a security researcher. Finds real vulnerabilities.
    Traces data flows. Explains exploit scenarios. Generates patches.
    """

    SECURITY_EXPERT = """You are an elite cybersecurity researcher with deep expertise in:
- Vulnerability research and exploit development
- Memory corruption, injection flaws, authentication bypasses
- Logic errors, race conditions, cryptographic weaknesses
- OWASP Top 10, CWE/SANS Top 25, CVE analysis
- Code reachability analysis and data flow tracing
- Browser, OS, network, and web application security

You READ code the way a security researcher does:
1. You TRACE data flows from input to sensitive operations
2. You check REACHABILITY — can user input actually reach the vulnerable code?
3. You assess EXPLOITABILITY — what would an attacker need to exploit this?
4. You CHAIN vulnerabilities — how do individual findings combine into attacks?
5. You THINK like an attacker — what's the easiest path to compromise?

For every finding you provide:
- CWE classification (CWE-ID)
- Severity with justification (critical/high/medium/low)
- Confidence rating (0-100%) based on code evidence
- Exact location (file, function, line range)
- Data flow trace (input → processing → vulnerable operation)
- Exploit scenario (step-by-step how an attacker would use this)
- Root cause (why this vulnerability exists)
- Sibling locations (other places with the same flaw)
- Fix with code diff
- Regression test

Never report false positives. If you're not sure, say so with your confidence level.
Be specific. Reference actual variable names, function names, and code paths."""

    # ============================================================
    # 1. AUTONOMOUS CODE VULNERABILITY SCANNING
    # ============================================================

    async def scan_code(self, code: str, filename: str = "", language: str = "auto") -> Dict[str, Any]:
        """
        Read code like Mythos — trace data flows, find real vulnerabilities.
        Not pattern matching. Real code understanding.
        """
        prompt = f"""Analyze this code for security vulnerabilities. READ it like a security researcher.

FILE: {filename}
LANGUAGE: {language}

CODE:
```
{code[:20000]}
```

For EACH vulnerability found:

1. VULNERABILITY NAME: Clear, specific name
2. CWE: CWE-ID (e.g., CWE-89, CWE-79, CWE-78)
3. SEVERITY: critical/high/medium/low — with justification
4. CONFIDENCE: 0-100% — how sure are you? What evidence?
5. LOCATION: Exact function and line range
6. DATA FLOW TRACE: User input → processing → vulnerable operation
   - Where does untrusted data enter?
   - How does it flow through the code?
   - Where does it reach a dangerous sink?
7. EXPLOIT SCENARIO: Step-by-step how an attacker exploits this
   - What does the attacker control?
   - What payload do they send?
   - What is the impact?
8. ROOT CAUSE: Why does this vulnerability exist? What coding mistake was made?
9. SIBLING LOCATIONS: Other places in this code with the same flaw
10. FIX: Exact code change (show the diff)
11. REGRESSION TEST: Code that would catch this bug

Also provide:
- ATTACK SURFACE MAP: What are all the entry points for untrusted input?
- OVERALL RISK SCORE: 0-100
- PRIORITY ORDER: Which findings should be fixed first and why?"""

        response = await ModelCaller.call(prompt, self.SECURITY_EXPERT, temperature=0.1)

        vulnerabilities = self._parse_vulnerabilities(response)
        import re
        secret_patterns = [
            (r"(?i)(api[_-]?key|secret|token|password)\\s*[:=]\\s*['\"][^'\"]{12,}['\"]", "Potential hard-coded secret", "high"),
            (r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----", "Private key material in source", "critical"),
        ]
        for pattern, name, severity in secret_patterns:
            if re.search(pattern, code):
                vulnerabilities.insert(0, {"name": name, "severity": severity, "confidence": 99, "cwe": "CWE-798", "location": filename, "fix": "Move the secret to the deployment secret manager and rotate it."})

        return {
            "success": True,
            "filename": filename,
            "language": language,
            "vulnerabilities": vulnerabilities,
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    async def security_posture(self, url: str) -> Dict[str, Any]:
        """Run a safe, passive web posture check; never sends exploit payloads."""
        from urllib.parse import urlparse
        import ipaddress
        parsed = urlparse(url if "://" in url else f"https://{url}")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return {"success": False, "error": "Only http and https URLs are supported."}
        try:
            resolved = ipaddress.ip_address(parsed.hostname)
            if resolved.is_private or resolved.is_loopback or resolved.is_link_local or resolved.is_reserved:
                return {"success": False, "error": "Private and loopback targets are blocked."}
        except ValueError:
            pass
        import httpx
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=True) as client:
            response = await client.get(parsed.geturl(), headers={"User-Agent": "Mark-Jenny-Mythos-Safety/1.0"})
        headers = {key.lower(): value for key, value in response.headers.items()}
        required = {
            "strict-transport-security": parsed.scheme == "https",
            "content-security-policy": "content-security-policy" in headers,
            "x-content-type-options": headers.get("x-content-type-options", "").lower() == "nosniff",
            "referrer-policy": "referrer-policy" in headers,
            "permissions-policy": "permissions-policy" in headers,
        }
        cookies = []
        for cookie in response.headers.get_list("set-cookie"):
            lowered = cookie.lower()
            cookies.append({"secure": "secure" in lowered, "httponly": "httponly" in lowered, "samesite": "samesite=" in lowered})
        findings = [{"control": name, "severity": "medium" if name in {"content-security-policy", "strict-transport-security"} else "low", "message": "Missing or weak security control."} for name, ok in required.items() if not ok]
        return {"success": True, "mode": "passive", "url": str(response.url), "status_code": response.status_code, "security_headers": required, "cookies": cookies, "findings": findings, "risk_score": min(100, len(findings) * 12), "safe_for_users": not any(item["severity"] == "high" for item in findings)}

    # ============================================================
    # 2. WHOLE CODEBASE SECURITY AUDIT
    # ============================================================

    async def scan_codebase(self, dir_path: str) -> Dict[str, Any]:
        """
        Scan an entire codebase. Prioritize files by bug likelihood.
        Like Mythos — it ranks files and starts with the most suspicious.
        """
        path = Path(dir_path)
        if not path.exists():
            return {"success": False, "error": "Directory not found"}

        code_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java",
                          ".rs", ".rb", ".php", ".c", ".cpp", ".h", ".cs", ".swift"}
        files = []
        for file in path.rglob("*"):
            if file.suffix in code_extensions and ".git" not in str(file) and "node_modules" not in str(file):
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    files.append({"path": str(file.relative_to(path)), "content": content, "language": file.suffix.lstrip(".")})
                except Exception:
                    pass

        if not files:
            return {"success": True, "files_scanned": 0, "message": "No code files found"}

        combined = ""
        for f in files[:30]:
            combined += f"\n\n# FILE: {f['path']} ({f['language']})\n{f['content']}"

        prompt = f"""You are an elite cybersecurity researcher scanning an entire codebase.

CODEBASE ({len(files)} files):
{combined[:30000]}

Perform a COMPLETE security audit:

1. FILE PRIORITY RANKING: Which files are most likely to have bugs? Why?
   - Files handling user input → highest priority
   - Files with complex logic → medium priority
   - Configuration files → check for secrets/misconfigurations

2. VULNERABILITY FINDINGS: For each vulnerability:
   - CWE classification
   - Severity and confidence
   - File and location
   - Data flow trace (input → vulnerable operation)
   - Exploit scenario
   - Root cause
   - Fix with code

3. CROSS-FILE VULNERABILITIES:
   - Authentication flows that span multiple files
   - Data exposure across file boundaries
   - Inconsistent security checks

4. ATTACK SURFACE MAP:
   - All entry points (API endpoints, form handlers, file uploads)
   - Data flows from entry to sensitive operations
   - Trust boundaries

5. ARCHITECTURAL SECURITY ISSUES:
   - Missing input validation patterns
   - Insecure defaults
   - Missing security controls

6. OVERALL SECURITY GRADE (A+ to F) with justification

7. TOP 10 PRIORITY FIXES

Be exhaustive. Read every line. Think like an attacker."""

        response = await ModelCaller.call(prompt, self.SECURITY_EXPERT, temperature=0.1)

        return {
            "success": True,
            "files_scanned": len(files),
            "files": [f["path"] for f in files],
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    # ============================================================
    # 3. WEB APPLICATION DEEP SECURITY AUDIT
    # ============================================================

    async def deep_web_audit(self, url: str) -> Dict[str, Any]:
        """
        Not just header checking. Real web app security analysis:
        - Fetch the page AND its resources
        - Analyze JavaScript for vulnerabilities
        - Check for injection points
        - Test for common web vulnerabilities
        - Analyze authentication flows
        """
        page_content = ""
        headers = {}
        cookies = []
        status_code = 0
        scripts = []
        forms = []
        links = []

        try:
            import httpx
            async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
                r = await client.get(url)
                page_content = r.text[:20000]
                headers = dict(r.headers)
                status_code = r.status_code
                cookies = [{"name": c.name, "value": c.value[:30], "domain": c.domain,
                           "path": c.path, "secure": c.secure,
                           "samesite": str(c.same_site)} for c in r.cookies.jar]

                import re
                forms = re.findall(r'<form[^>]*>(.*?)</form>', page_content, re.DOTALL | re.IGNORECASE)
                form_actions = re.findall(r'action=["\']([^"\']+)["\']', page_content, re.IGNORECASE)
                form_inputs = re.findall(r'<input[^>]*name=["\']([^"\']+)["\']', page_content, re.IGNORECASE)

                scripts = re.findall(r'<script[^>]*>(.*?)</script>', page_content, re.DOTALL | re.IGNORECASE)
                script_srcs = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', page_content, re.IGNORECASE)

                links = re.findall(r'href=["\']([^"\']+)["\']', page_content)

                js_content = ""
                for src in script_srcs[:5]:
                    try:
                        if src.startswith("/"):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            src = f"{parsed.scheme}://{parsed.netloc}{src}"
                        elif not src.startswith("http"):
                            continue
                        js_r = await client.get(src, timeout=10)
                        if js_r.status_code == 200:
                            js_content += f"\n// FILE: {src}\n{js_r.text[:5000]}"
                    except Exception:
                        pass

        except Exception as e:
            return {"success": False, "error": str(e)}

        ssl_info = {}
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
                        ssl_info = {"valid": True, "protocol": ssock.version(),
                                   "expires": cert.get("notAfter", "")}
        except Exception:
            ssl_info = {"valid": False}

        prompt = f"""You are an elite web application security researcher performing a DEEP security audit.

TARGET: {url}
STATUS: {status_code}
SSL: {json.dumps(ssl_info)}

HEADERS: {json.dumps(headers, indent=2)}

COOKIES ({len(cookies)}): {json.dumps(cookies, indent=2)}

FORMS FOUND ({len(forms)}):
Actions: {form_actions}
Input fields: {form_inputs}

SCRIPTS ({len(script_srcs)} external):
{js_content[:10000] if js_content else "No inline/external scripts captured"}

PAGE HTML: {page_content[:10000]}

Now perform a MYTHOS-LEVEL web application security audit:

1. INJECTION ATTACK SURFACE:
   - SQL Injection: Analyze form inputs, URL parameters, headers for SQL injection points
   - XSS: Analyze all input fields, URL parameters, headers for reflected/stored XSS
   - Command Injection: Any place user input reaches system commands?
   - Template Injection: Any template rendering with user input?
   - LDAP/XML/NoSQL Injection: Other injection types?

2. AUTHENTICATION & SESSION:
   - Session management analysis
   - Cookie security (HttpOnly, Secure, SameSite)
   - Password handling
   - Multi-factor authentication status
   - Session fixation/hijacking risks

3. AUTHORIZATION:
   - Access control analysis
   - Privilege escalation risks
   - IDOR (Insecure Direct Object References)

4. JAVASCRIPT SECURITY:
   - Client-side validation bypass
   - Sensitive data in JavaScript
   - Insecure DOM manipulation
   - Third-party script risks

5. BUSINESS LOGIC:
   - Race conditions
   - Price manipulation
   - Workflow bypass

6. CRYPTOGRAPHIC ISSUES:
   - Weak algorithms
   - Key management
   - Data exposure

7. CONFIGURATION:
   - Security headers analysis
   - Error handling information disclosure
   - Debug mode status
   - Directory listing

8. EXPLOIT CHAINS:
   - How can individual vulnerabilities be chained?
   - What's the maximum impact scenario?

9. SECURITY SCORE: 0-100 with detailed justification

10. PRIORITY FIXES: Ranked by exploitability and impact

11. USER SAFETY: Is this site safe? What should users avoid?

Be THOROUGH. Think like an attacker. Find what scanners miss."""

        response = await ModelCaller.call(prompt, self.SECURITY_EXPERT, temperature=0.1)

        return {
            "success": True,
            "url": url,
            "status_code": status_code,
            "ssl": ssl_info,
            "headers": headers,
            "cookies": cookies,
            "forms_found": len(forms),
            "scripts_found": len(script_srcs),
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    # ============================================================
    # 4. VULNERABILITY EXPLOIT ANALYSIS
    # ============================================================

    async def analyze_exploit(self, code: str, vulnerability: str, filename: str = "") -> Dict[str, Any]:
        """
        Given a vulnerability, analyze HOW it could be exploited.
        Trace the full attack path. Like Mythos building working exploits.
        """
        prompt = f"""You are analyzing a specific vulnerability for exploitability.

FILE: {filename}
VULNERABILITY: {vulnerability}

CODE:
```
{code[:15000]}
```

Perform a DEEP exploit analysis:

1. VULNERABILITY CLASSIFICATION:
   - CWE-ID and name
   - CVSS score estimate with vector string
   - Severity: critical/high/medium/low

2. REACHABILITY ANALYSIS:
   - Can user input reach this code path?
   - What conditions must be true?
   - Are there any guards/checks that prevent exploitation?

3. EXPLOIT DEVELOPMENT:
   - What does the attacker control?
   - What payload is needed?
   - Step-by-step exploitation process
   - What primitives does this vulnerability provide? (read, write, execute, info leak)

4. EXPLOIT CHAIN POTENTIAL:
   - What other vulnerabilities could this chain with?
   - What's the maximum impact if chained?

5. IMPACT ANALYSIS:
   - Confidentiality impact
   - Integrity impact
   - Availability impact
   - Business impact

6. ATTACK COMPLEXITY:
   - How easy is this to exploit?
   - What knowledge does the attacker need?
   - Is it remotely exploitable?

7. PROOF OF CONCEPT:
   - Show example attack payload
   - Show example request that triggers the vulnerability

8. REMEDIATION:
   - Specific code fix
   - Defense-in-depth measures
   - Detection strategies

Be specific. Show the actual attack path."""

        response = await ModelCaller.call(prompt, self.SECURITY_EXPERT, temperature=0.1)

        return {
            "success": True,
            "filename": filename,
            "vulnerability": vulnerability,
            "exploit_analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    # ============================================================
    # 5. CONTINUOUS SECURITY LOOP
    # ============================================================

    async def security_loop(self, code: str, filename: str = "") -> Dict[str, Any]:
        """
        The Mythos continuous security loop:
        Threat modeling → Discovery → Verification → Triage → Patching
        One continuous loop carrying context across every stage.
        """
        stages = {}

        # Stage 1: Threat Modeling
        threat_prompt = f"""THREAT MODELING — Analyze this code for potential security threats.

FILE: {filename}
CODE:
```
{code[:15000]}
```

Identify:
1. All entry points for untrusted input
2. All sensitive operations (DB queries, file ops, system commands, auth checks)
3. Data flows from entry points to sensitive operations
4. Trust boundaries crossed
5. Potential threat agents and their motivations
6. Risk ranking of identified threats"""

        threat_model = await ModelCaller.call(threat_prompt, self.SECURITY_EXPERT, temperature=0.1)
        stages["threat_model"] = threat_model

        # Stage 2: Vulnerability Discovery
        discovery_prompt = f"""VULNERABILITY DISCOVERY — Based on this threat model, find actual vulnerabilities.

THREAT MODEL:
{threat_model[:3000]}

CODE:
```
{code[:15000]}
```

For each vulnerability found:
- CWE classification
- Severity and confidence
- Exact location
- Data flow trace
- Exploit scenario"""

        discovery = await ModelCaller.call(discovery_prompt, self.SECURITY_EXPERT, temperature=0.1)
        stages["discovery"] = discovery

        # Stage 3: Verification
        verify_prompt = f"""VERIFICATION — Validate each finding. Eliminate false positives.

DISCOVERED VULNERABILITIES:
{discovery[:5000]}

CODE:
```
{code[:15000]}
```

For EACH finding:
1. Is this a TRUE POSITIVE? Evidence?
2. Can user input ACTUALLY reach this code path?
3. Are there existing guards that prevent exploitation?
4. Confidence adjustment (increase or decrease)
5. Remove any false positives

Return only VERIFIED findings with updated confidence."""

        verification = await ModelCaller.call(verify_prompt, self.SECURITY_EXPERT, temperature=0.1)
        stages["verification"] = verification

        # Stage 4: Triage
        triage_prompt = f"""TRIAGE — Rank verified findings by risk and exploitability.

VERIFIED FINDINGS:
{verification[:5000]}

Rank by:
1. Exploitability (how easy to exploit)
2. Impact (damage if exploited)
3. Pre-requisites needed
4. Business risk

Provide a prioritized fix list with reasoning."""

        triage = await ModelCaller.call(triage_prompt, self.SECURITY_EXPERT, temperature=0.1)
        stages["triage"] = triage

        # Stage 5: Patching
        patch_prompt = f"""PATCHING — Generate fixes for all prioritized findings.

TRIAGED FINDINGS:
{triage[:5000]}

CODE:
```
{code[:15000]}
```

For EACH finding:
1. Root cause explanation
2. Minimal code fix (show the diff)
3. Defense-in-depth improvement
4. Regression test code
5. Sibling locations to check

Show the COMPLETE patched code."""

        patching = await ModelCaller.call(patch_prompt, self.SECURITY_EXPERT, temperature=0.1)
        stages["patching"] = patching

        return {
            "success": True,
            "filename": filename,
            "stages": stages,
            "summary": f"Security loop complete: {len(stages)} stages executed",
            "model_used": ModelCaller.get_model_info(),
        }

    # ============================================================
    # 6. SITE SAFETY — Is this site safe for users?
    # ============================================================

    async def site_safety(self, url: str) -> Dict[str, Any]:
        """Assess if a site is safe for users to visit."""
        page_content = ""
        headers = {}
        scripts = []
        links = []

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(url)
                page_content = r.text[:15000]
                headers = dict(r.headers)
                import re
                scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', page_content)
                links = re.findall(r'href=["\']([^"\']+)["\']', page_content)
        except Exception as e:
            return {"success": False, "error": str(e)}

        prompt = f"""You are a web safety expert. Assess if this site is SAFE for users.

URL: {url}
HEADERS: {json.dumps(headers, indent=2)}
SCRIPTS ({len(scripts)}): {json.dumps(scripts[:15], indent=2)}
LINKS ({len(links)}): {json.dumps(links[:30], indent=2)}
PAGE: {page_content[:10000]}

Analyze:
1. MALICIOUS INDICATORS: phishing, malware, drive-by downloads
2. SCRIPT ANALYSIS: suspicious third-party scripts, crypto miners, keyloggers
3. REDIRECT ANALYSIS: where does it redirect? malicious redirects?
4. FORM ANALYSIS: fake login forms, data harvesting
5. MIXED CONTENT: HTTP resources on HTTPS
6. TRACKER ANALYSIS: what data is collected?
7. SITE REPUTATION: known malicious domain patterns

VERDICT: Safe / Caution / Dangerous
SAFETY SCORE: 0-100
USER RECOMMENDATIONS: what to do/avoid"""

        response = await ModelCaller.call(prompt, self.SECURITY_EXPERT, temperature=0.2)

        return {
            "success": True,
            "url": url,
            "scripts_count": len(scripts),
            "links_count": len(links),
            "analysis": response,
            "model_used": ModelCaller.get_model_info(),
        }

    def _parse_vulnerabilities(self, response: str) -> List[Dict]:
        vulns = []
        current = {}
        for line in response.split("\n"):
            ll = line.lower().strip()
            if any(kw in ll for kw in ["vulnerability:", "finding:", "issue:", "bug:", "flaw:"]):
                if current:
                    vulns.append(current)
                current = {"name": line.split(":", 1)[-1].strip()}
            elif "cwe" in ll and ":" in ll:
                current["cwe"] = line.split(":", 1)[-1].strip()
            elif "severity:" in ll:
                current["severity"] = line.split(":", 1)[-1].strip().lower()
            elif "confidence:" in ll:
                current["confidence"] = line.split(":", 1)[-1].strip()
            elif "location:" in ll or "file:" in ll:
                current["location"] = line.split(":", 1)[-1].strip()
            elif "fix:" in ll or "remediation:" in ll or "patch:" in ll:
                current["fix"] = line.split(":", 1)[-1].strip()
            elif "exploit" in ll and ":" in ll:
                current["exploit"] = line.split(":", 1)[-1].strip()
        if current:
            vulns.append(current)
        return vulns


# Singleton
cybersecurity_agent = CybersecurityAgent()
