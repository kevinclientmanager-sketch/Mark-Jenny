from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
import json
import re

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.skill import Skill, SkillSource, SkillStatus, SkillVersion
from app.utils.audit import log_audit

router = APIRouter()

def _skill(name, display_name, description, tools, permissions, deps=None, config_schema=None):
    return {
        "name": name,
        "display_name": display_name,
        "description": description,
        "version": "1.0.0",
        "source": "OFFICIAL",
        "manifest": {"name": name, "version": "1.0.0", "tools": tools},
        "instructions": (
            f"You are an expert {display_name}. Execute the '{name}' skill: plan the workflow, "
            f"use the required tools ({', '.join(tools)}) as needed, follow industry best practices, "
            "verify outputs against the original goal, and deliver a polished, production-ready result."
        ),
        "tools": tools,
        "permissions": permissions,
        "config_schema": config_schema or {},
        "dependencies": deps or [],
    }


# Curated official registry — production-grade capabilities researched from the 2026 agent-skills
# ecosystem (Anthropic skills, Claude Code skills, awesome-agent-skills, skill marketplaces).
# Categories: Research & Knowledge, Data & Analysis, Content & Creative, Software Engineering,
# DevOps & Security, Product & Design, Business & Growth, Automation & Integration, AI Engineering.
OFFICIAL_REGISTRY = [
    # ---------- Research & Knowledge ----------
    _skill("research-agent", "Research Agent", "Wide research: query planning, parallel search, citation tracking, synthesis, report", ["web_search","extract","deduplicate","synthesize","cite"], ["network:search","file:write"]),
    _skill("deep-research", "Deep Research", "In-depth multi-source investigation with evidence scoring and source depth analysis", ["web_search","extract","summarize","cite"], ["network:search","file:write"]),
    _skill("competitor-research", "Competitor Research", "Analyze competitors' positioning, pricing, traffic, and marketing strategies", ["web_search","scrape","spreadsheet","synthesize"], ["network:search","file:write"]),
    _skill("market-research-analyst", "Market Research Analyst", "Market sizing (TAM/SAM/SOM), segments, trends, and opportunity analysis", ["web_search","data_analysis","spreadsheet"], ["network:search","file:write"]),
    _skill("seo-audit", "SEO Audit", "Technical/content SEO audit with actionable priority fix list", ["web_search","scrape","analysis"], ["network:search","file:write"]),
    _skill("academic-search", "Academic Research", "Scholarly literature search with proper citation and gap analysis", ["web_search","extract","cite"], ["network:search"]),
    _skill("news-monitoring", "News Monitoring", "Track topics and produce daily briefing digests from news sources", ["web_search","extract","summarize"], ["network:search"]),
    _skill("document-qa", "Document Q&A", "Answer questions from uploaded documents with citations to sources", ["document","file_read","retrieve"], ["file:read"]),
    _skill("pdf-specialist", "PDF Specialist", "Generate, merge, split, extract, and annotate PDF documents", ["document","file_write","extract"], ["file:read","file:write"]),
    _skill("docx-pro", "Word Document Pro", "Create polished .docx reports, contracts, and proposals", ["document","file_write"], ["file:write"]),
    _skill("pptx-pro", "PowerPoint Pro", "Design professional slide decks with structure, layout, and narrative flow", ["slides","image"], ["file:write"]),
    _skill("xlsx-pro", "Excel Pro", "Advanced spreadsheets: formulas, conditional formatting, charts, dashboards", ["create_workbook","spreadsheet"], ["file:write"]),
    _skill("knowledge-base-builder", "Knowledge Base Builder", "Extract, organize, and publish a searchable knowledge base", ["file_read","retrieve","document"], ["file:read","file:write"]),
    _skill("rag-specialist", "RAG Specialist", "Design retrieval pipelines: chunking, embeddings, reranking, grounded generation", ["code","sql","retrieve"], ["code:python","db:sql"]),
    _skill("graphrag-patterns", "Knowledge Graph RAG", "Knowledge-graph + RAG patterns for multi-hop reasoning", ["code","retrieve","analyze"], ["code:python","db:sql"]),
    _skill("summarization", "Summarization Expert", "Multi-length summaries: TL;DR, executive summary, bullet briefs, meeting minutes", ["extract","document"], ["file:read","file:write"]),
    _skill("translation-agent", "Translation Agent", "High-quality human-grade translation and localization with glossary support", ["text","document"], ["network:search"]),
    _skill("language-tutor", "Language Tutor", "Interactive lessons, grammar drills, and fluency coaching", ["text","audio"], []),
    _skill("meeting-notes", "Meeting Notes", "Convert transcripts into structured actions, decisions, and owners", ["audio","extract","document"], ["file:write"]),

    # ---------- Data & Analysis ----------
    _skill("data-analyst", "Data Analyst", "Clean, explore, and analyze datasets with statistical rigor", ["data_analysis","code","document"], ["code:python","file:read","file:write"]),
    _skill("data-visualizer", "Data Visualization", "Chart selection, color, layout, and story-first dashboard design", ["data_analysis","chart","document"], ["file:write"]),
    _skill("sql-analyst", "SQL Analyst", "Write, optimize, and explain SQL queries against local and remote DBs", ["sql","code"], ["db:sql"]),
    _skill("data-cleaning", "Data Cleaning", "Dedupe, normalize, validate, and profile messy datasets", ["data_analysis","code","spreadsheet"], ["code:python","file:read","file:write"]),
    _skill("financial-analyst", "Financial Analyst", "Financial statements, ratios, DCF, and investment memo writing", ["spreadsheet","data_analysis","document"], ["file:write"]),
    _skill("marketing-analyst", "Marketing Analytics", "Campaign performance, funnel analysis, and channel attribution", ["data_analysis","spreadsheet"], ["file:read","file:write"]),
    _skill("saas-metrics", "SaaS Metrics", "MRR/ARR, churn, CAC/LTV, retention cohort analysis", ["data_analysis","spreadsheet"], ["file:write"]),
    _skill("crypto-analyst", "Crypto Analyst", "Token fundamentals, on-chain data, market structure analysis", ["web_search","data_analysis"], ["network:search"]),
    _skill("real-estate-analyst", "Real Estate Analyst", "Property comps, rent surveys, cap-rate and ROI analysis", ["web_search","scrape","spreadsheet"], ["network:search","file:write"]),

    # ---------- Content & Creative ----------
    _skill("seo-blog-writer", "SEO Blog Writer", "SEO-optimized blog posts with keyword strategy and structure", ["web_search","text"], ["network:search","file:write"]),
    _skill("technical-writer", "Technical Writer", "Clear technical documentation: API refs, tutorials, guides", ["document","text"], ["file:write"]),
    _skill("copywriter", "Copywriter", "Persuasive copy: landing pages, email nurture, product pages", ["text"], ["file:write"]),
    _skill("ad-creative-engine", "Ad Creative Engine", "Ad variant generation across angles: pain, desire, social proof, urgency; platform constraints", ["text","analysis"], ["network:search"]),
    _skill("email-marketer", "Email Marketer", "Email sequences, subject-line optimization, and deliverability-aware copy", ["text","email"], ["email:read","email:send"]),
    _skill("social-media-manager", "Social Media Manager", "Platform-native posts, hashtags, content calendars", ["text","image"], ["network:http"]),
    _skill("press-release-writer", "Press Release Writer", "Newsworthy press releases with hook, quotes, and boilerplate", ["text","document"], ["file:write"]),
    _skill("script-writer", "Script Writer", "Video and podcast scripts with pacing and structure", ["text","audio"], []),
    _skill("story-writer", "Story Writer", "Fiction and storytelling craft: arcs, voices, worldbuilding", ["text"], []),
    _skill("resume-writer", "ATS Resume Tailor", "Tailor resumes to job posts, clear ATS keyword screens, quantify impact", ["text","extract"], ["file:read","file:write"]),
    _skill("cover-letter-writer", "Cover Letter Writer", "Personalized cover letters mapped to role requirements", ["text"], ["file:write"]),
    _skill("brand-kit", "Brand Kit Builder", "Brand voice, colors, typography, and messaging rules", ["text","image"], ["file:write"]),
    _skill("video-editor", "Video Edit Assistant", "Edit plans, cut lists, transcription-based timeline structuring", ["video","audio"], ["file:read"]),
    _skill("image-generation", "Image Generation", "Concept-to-final image prompting and editing workflows", ["image","image_edit"], ["network:http","file:write"]),

    # ---------- Software Engineering ----------
    _skill("code-reviewer", "Code Review", "Review code for bugs, security, performance, and readability", ["code","analysis"], ["code:python","code:js","file:read"]),
    _skill("code-explanation-generator", "Code Explainer", "Clear explanations of complex code with diagrams and walkthroughs", ["code","document"], ["file:read","file:write"]),
    _skill("bug-debugger", "Structured Debugging", "Hypothesize -> verify -> fix with root-cause analysis", ["code","execution"], ["code:python","code:js"]),
    _skill("github-actions", "GitHub Actions Specialist", "CI/CD workflows, secrets, caching, and release automation", ["code","github"], ["file:write","network:http"]),
    _skill("git-workflow", "Git Workflow Master", "Atomic commits, clean history, cherry-picks, and safe rebasing", ["code","shell"], ["file:write","file:read"]),
    _skill("api-designer", "API Designer", "Design REST/GraphQL APIs with full contract-first specs", ["code","document"], ["file:write"]),
    _skill("api-documentation", "API Documentation", "Write reference docs from OpenAPI specs or code", ["document","code"], ["file:write"]),
    _skill("playwright-pro", "Playwright Pro", "Reliable E2E test suites: selectors, waits, retries, reporting", ["browser","code"], ["code:js","browser:automate"]),
    _skill("unit-test-generator", "Unit Test Generator", "Meaningful unit tests with edge cases and mocks", ["code","execution"], ["code:python","code:js"]),
    _skill("frontend-design", "Frontend Design", "Pixel-perfect HTML/CSS/Tailwind UIs and component libraries", ["code","browser"], ["code:js","browser:automate","file:write"]),
    _skill("theme-factory", "UI Theme Factory", "Complete UI themes: color tokens, type scales, dark/light variants", ["code","image"], ["code:js","file:write"]),
    _skill("react-specialist", "React Specialist", "Production React patterns: state, data fetching, performance", ["code"], ["code:js","file:write"]),
    _skill("nextjs-architect", "Next.js Architect", "Next.js app structure, data patterns, and route design", ["code"], ["code:js","file:write"]),
    _skill("typescript-refactor", "TypeScript Refactor", "Type-safe refactors with migration plans", ["code"], ["code:js","file:read","file:write"]),
    _skill("performance-profiler", "Performance Profiler", "Profile and fix CPU/memory/network bottlenecks", ["code","execution","browser"], ["code:python","code:js","computer:control"]),
    _skill("sql-optimizer", "SQL Optimizer", "Indexing, query rewrites, and EXPLAIN-plan analysis", ["sql"], ["db:sql"]),

    # ---------- DevOps & Security ----------
    _skill("security-auditor", "Security Auditor", "OWASP Top 10 analysis, vuln scanning, and remediation plans", ["code","analysis","web_search"], ["file:read","network:search"]),
    _skill("secure-push", "Secure Push", "Pre-push scans: secret detection, SAST, dependency CVEs", ["code","shell"], ["file:read","code:python"]),
    _skill("devops-engineer", "DevOps Engineer", "Docker, CI/CD pipelines, and cloud infrastructure as code", ["code","shell"], ["code:python","network:http"]),
    _skill("docker-specialist", "Docker Specialist", "Efficient Dockerfiles, compose stacks, and image hardening", ["code","shell"], ["code:python","network:http"]),
    _skill("kubernetes-specialist", "Kubernetes Specialist", "Manifests, Helm charts, and cluster troubleshooting", ["code","shell"], ["code:python","network:http"]),
    _skill("backup-planner", "Backup & Recovery Planner", "3-2-1 backup strategies and disaster-recovery runbooks", ["document","shell"], ["file:read","file:write"]),
    _skill("sensitive-data-protection", "Data Protection", "Encryption, masking, and secure storage patterns", ["code","analysis"], ["code:python","file:read"]),
    _skill("infrastructure-troubleshooter", "Infra Troubleshooter", "Diagnose and fix infrastructure incidents with blameless runbooks", ["shell","analysis"], ["code:python"]),

    # ---------- Product & Design ----------
    _skill("product-manager", "Product Manager", "Vision, strategy, roadmaps, and user story synthesis", ["document","analysis"], ["file:write"]),
    _skill("prd-writer", "PRD Writer", "Investor-free PRDs: goals, personas, user stories, acceptance criteria", ["document"], ["file:write"]),
    _skill("roadmap-planner", "Roadmap Planner", "Sequenced deliverables with dependencies and milestones", ["document","spreadsheet"], ["file:write"]),
    _skill("user-research", "User Research", "Interview guides, survey design, and insight synthesis", ["web_search","document"], ["network:search","file:write"]),
    _skill("a-b-test-designer", "A/B Test Designer", "Hypothesis, sample size, variant design, and evaluation plans", ["analysis","spreadsheet"], ["file:write"]),
    _skill("pricing-strategist", "Pricing Strategist", "Value-based pricing, tiering, and price-testing frameworks", ["web_search","analysis","spreadsheet"], ["network:search","file:write"]),
    _skill("ui-ux-advisor", "UI/UX Advisor", "Design feedback with accessibility, usability, and modern patterns", ["browser","analysis"], ["browser:automate","file:read"]),
    _skill("design-system-builder", "Design System Builder", "Tokens, components, and documentation for scalable UI", ["code","document"], ["file:write","code:js"]),
    _skill("accessibility-auditor", "Accessibility Auditor", "WCAG 2.2 audit and remediation roadmap", ["browser","analysis"], ["browser:automate","file:read"]),

    # ---------- Business & Growth ----------
    _skill("business-plan-writer", "Business Plan Writer", "Investor-ready plans with financial projections", ["document","spreadsheet"], ["file:write"]),
    _skill("growth-strategy", "Growth Strategy", "Funnels, retention loops, and channel playbooks", ["web_search","analysis"], ["network:search"]),
    _skill("competitor-tracker", "Competitor Tracker", "Ongoing competitor monitoring with alert-ready briefs", ["web_search","schedules"], ["network:search","file:write"]),
    _skill("sales-crm-specialist", "Sales & CRM Specialist", "Pipeline hygiene, deal hygiene, and CRM automations", ["spreadsheet","email"], ["email:read","email:send"]),
    _skill("lead-scoring", "Lead Scoring", "Lead scoring models with prioritization logic", ["data_analysis","spreadsheet"], ["file:write"]),
    _skill("customer-support-agent", "Customer Support Agent", "Ticket triage, empathetic responses, KB-driven resolution", ["email","memory","web_search"], ["email:read","email:send","memory:read"]),
    _skill("community-manager", "Community Manager", "Engagement calendars, tone guides, and growth mechanics", ["text","email"], ["email:send"]),
    _skill("fundraising-advisor", "Fundraising Advisor", "Pitch deck structure, investor outreach, and term-sheet literacy", ["document","email"], ["file:write","email:send"]),

    # ---------- Automation & Integration ----------
    _skill("web-scraper", "Web Scraper", "Ethical scraping: extraction mapping, pagination, and rate-limit awareness", ["scrape","extract","browser"], ["network:search","browser:automate"]),
    _skill("browser-automation", "Browser Automation", "Form filling, workflows, and multi-step browser tasks", ["browser"], ["browser:automate"]),
    _skill("email-inbox-ai", "Email Inbox AI", "Triage, draft replies, follow-up reminders, and inbox zero", ["email","memory"], ["email:read","email:send"]),
    _skill("calendar-optimizer", "Calendar Optimizer", "Schedule blocking, meeting prep, and time-review", ["calendar"], ["calendar:read","calendar:write"]),
    _skill("slack-ops", "Slack Operations", "Channel summaries, digests, and bot workflows", ["slack","text"], ["network:http"]),
    _skill("computer-control", "Computer Control", "Mouse/keyboard/screenshot-driven OS task automation", ["computer","execution"], ["computer:control"]),
    _skill("file-organizer", "File Organizer", "Automated folder structures and file migration rules", ["files","shell"], ["file:read","file:write"]),
    _skill("photo-organizer", "Photo Organizer", "Dedupe, tag, and reorganize photo libraries", ["files","image"], ["file:read","file:write"]),
    _skill("workflow-builder", "Workflow Builder", "Design repeatable multi-step agent workflows", ["code","document"], ["file:write","code:python"]),
    _skill("sqlite-specialist", "SQLite Specialist", "Local database design, queries, and migrations", ["sql","code"], ["db:sql","file:write"]),

    # ---------- AI Engineering ----------
    _skill("prompt-engineer", "Prompt Engineer", "Effective prompt design: structure, constraints, few-shot, eval-driven iteration", ["code","analysis"], ["file:write"]),
    _skill("model-routing-strategy", "Model Router", "Route queries to appropriate models by cost/latency/quality", ["code","analysis"], ["code:python"]),
    _skill("token-cost-analyzer", "Token Cost Analyzer", "Usage audits with current pricing; cost reduction recommendations", ["data_analysis","code"], ["file:read","file:write"]),
    _skill("prompt-caching-patterns", "Prompt Caching", "Semantic caching to cut latency and cost", ["code"], ["code:python"]),
    _skill("eval-engineer", "Eval Engineer", "Benchmark suites, grading rubrics, and regression evals", ["code","data_analysis"], ["code:python","file:write"]),
    _skill("fine-tuning-architect", "Fine-tuning Architect", "Dataset prep, training recipes, and evaluation for fine-tunes", ["code","data_analysis"], ["code:python"]),
    _skill("mcp-server-builder", "MCP Server Builder", "Build, test, and document MCP servers", ["code","execution"], ["code:python"]),
    _skill("skill-creator", "Skill Creator", "Author production-grade skills: SKILL.md, validation, and tests", ["code","document"], ["file:write","code:python"]),
    _skill("self-improving-agent", "Self-Improving Agent", "Curate successes into reusable memory and instructions over time", ["memory","code"], ["memory:read","memory:write"]),
    _skill("ml-deployer", "ML Deployer", "Model serving, endpoints, and monitoring", ["code","shell"], ["code:python","network:http"]),

    # ---------- markimti Plugins ----------
    _skill("playwright-cli", "PlaywrightCLI", "Full browser automation: navigate, click, fill, screenshot, scrape, test — CLI-grade control of headless and headed browsers", ["browser_navigate","browser_click","browser_type","browser_screenshot","browser_extract","browser_wait","code"], ["browser:automate","file:write","network:http"]),
    _skill("supabase", "Supabase", "Supabase platform integration: project management, database queries, auth flows, edge functions, storage buckets, and real-time subscriptions via REST API", ["code","sql","http_request","file_read","file_write"], ["network:http","db:sql","file:read","file:write"]),
    _skill("strix-security", "StrixSecurity", "Security scanning suite: reconnaissance, port scanning, vulnerability detection, dependency auditing, secret-leak checks, and hardened-config analysis", ["web_search","code","shell","analysis","browser"], ["network:search","file:read","file:write"]),
    _skill("skill-ui-replicator", "Skill: UI Replicator", "Reverse-engineer any website's design system: extract colors, typography, spacing, components, and layout patterns, then replicate the style in new builds", ["browser_navigate","browser_extract","browser_screenshot","code","image"], ["browser:automate","file:write","network:http"]),
    _skill("context7", "Context7", "Context management hub: long-memory retrieval, document chunking, RAG-powered recall, session-state tracking, and cross-conversation knowledge persistence", ["memory","retrieve","code","document","file_read"], ["memory:read","memory:write","file:read","file:write"]),

    # ---------- ECC / Claudex Skills (Everything Claude Code) ----------
    _skill("ecc-fastapi-patterns", "FastAPI Patterns (ECC)", "Production-grade FastAPI: project structure, Pydantic v2, dependency injection, async handlers, auth, transactional services, testing", ["code","sql","browser"], ["code:python","db:sql","file:write"]),
    _skill("ecc-react-patterns", "React Patterns (ECC)", "React 18/19 patterns: hooks discipline, server/client boundaries, Suspense, error boundaries, form actions, state management, accessibility", ["code","browser"], ["code:js","file:write"]),
    _skill("ecc-tdd-workflow", "TDD Workflow (ECC)", "Test-driven development with 80%+ coverage: unit, integration, and E2E tests. Red-green-refactor cycle enforced", ["code","execution"], ["code:python","code:js"]),
    _skill("ecc-security-review", "Security Review (ECC)", "OWASP Top 10 checklist, input validation, auth patterns, secrets handling, dependency scanning, penetration testing basics", ["code","analysis","web_search"], ["file:read","file:write"]),
    _skill("ecc-code-review", "Code Review (ECC)", "Systematic code review: bugs, security, performance, readability, maintainability. Structured feedback with severity levels", ["code","analysis"], ["file:read","file:write"]),
    _skill("ecc-database-migrations", "Database Migrations (ECC)", "Schema migration strategies: versioned migrations, rollbacks, data migrations, zero-downtime patterns for SQLite/PostgreSQL", ["sql","code"], ["db:sql","file:write"]),
    _skill("ecc-deployment-patterns", "Deployment Patterns (ECC)", "CI/CD pipelines, blue-green deployments, canary releases, rollback strategies, health checks, monitoring", ["code","shell"], ["network:http","file:write"]),
    _skill("ecc-error-handling", "Error Handling (ECC)", "Structured error handling: error boundaries, retry patterns, circuit breakers, graceful degradation, user-friendly error messages", ["code","analysis"], ["file:write"]),
    _skill("ecc-coding-standards", "Coding Standards (ECC)", "Enforce consistent code style: naming conventions, file structure, import ordering, comment standards, linting rules", ["code","analysis"], ["file:read","file:write"]),
    _skill("ecc-search-first", "Search First (ECC)", "Research before building: search existing patterns, check dependencies, review similar implementations before writing new code", ["web_search","code"], ["network:search","file:read"]),
    _skill("ecc-verification-loop", "Verification Loop (ECC)", "Continuous verification: type checking, linting, tests, build validation after every change. Catch issues early", ["code","execution"], ["code:python","code:js"]),
    _skill("ecc-plan-canvas", "Plan Canvas (ECC)", "Structured planning: break goals into milestones, identify dependencies, estimate effort, create actionable task lists", ["document","analysis"], ["file:write"]),
    _skill("ecc-orch-build-mvp", "Build MVP (ECC)", "Rapid MVP development: core features only, time-boxed sprints, iterative feedback, ship fast then refine", ["code","document"], ["file:write","code:python"]),
    _skill("ecc-orch-fix-defect", "Fix Defect (ECC)", "Structured debugging: reproduce → hypothesize → isolate → fix → verify → prevent recurrence. Root cause analysis", ["code","execution","analysis"], ["code:python","code:js"]),
    _skill("ecc-orch-refine-code", "Refine Code (ECC)", "Incremental refactoring: extract functions, simplify conditionals, remove duplication, improve naming, add types", ["code","analysis"], ["file:read","file:write"]),
    _skill("ecc-design-system", "Design System (ECC)", "Build scalable design systems: tokens, components, patterns, documentation, accessibility, dark mode support", ["code","document","image"], ["code:js","file:write"]),
    _skill("ecc-deep-research", "Deep Research (ECC)", "Multi-source investigation: query planning, parallel search, evidence scoring, citation tracking, synthesis", ["web_search","extract","document"], ["network:search","file:write"]),
    _skill("ecc-documentation-lookup", "Documentation Lookup (ECC)", "Find and reference official docs: framework docs, API references, library guides, version-specific notes", ["web_search","extract"], ["network:search"]),
    _skill("ecc-production-audit", "Production Audit (ECC)", "Pre-deployment audit: security scan, performance check, error handling review, logging verification, config validation", ["code","analysis","shell"], ["file:read","file:write"]),
    _skill("ecc-python-patterns", "Python Patterns (ECC)", "Pythonic code: type hints, dataclasses, async/await, context managers, generators, protocols, modern Python 3.12+ patterns", ["code","analysis"], ["code:python","file:write"]),
    _skill("ecc-api-design", "API Design (ECC)", "RESTful API design: resource modeling, URL structure, status codes, pagination, filtering, versioning, OpenAPI specs", ["code","document"], ["file:write"]),
    _skill("ecc-architecture-decision-records", "ADR Manager (ECC)", "Document architectural decisions: context, options considered, decision, consequences. Track rationale over time", ["document","analysis"], ["file:write"]),
    _skill("ecc-frontend-patterns", "Frontend Patterns (ECC)", "Modern frontend: component composition, state management, data fetching, performance optimization, accessibility", ["code","browser"], ["code:js","file:write"]),
    _skill("ecc-backend-patterns", "Backend Patterns (ECC)", "Backend architecture: service layers, repository pattern, dependency injection, middleware, caching, rate limiting", ["code","sql"], ["code:python","file:write"]),
    _skill("ecc-claude-devfleet", "DevFleet (ECC)", "Multi-agent orchestration: parallel task execution, agent coordination, result aggregation, conflict resolution", ["code","execution"], ["file:write"]),
    _skill("ecc-continuous-learning", "Continuous Learning (ECC)", "Auto-extract patterns from sessions: capture decisions, log failures, build reusable knowledge base over time", ["memory","code"], ["memory:read","memory:write"]),
    _skill("ecc-prompt-optimizer", "Prompt Optimizer (ECC)", "Design effective prompts: structure, constraints, few-shot examples, evaluation-driven iteration", ["code","analysis"], ["file:write"]),
    _skill("ecc-token-budget-advisor", "Token Budget (ECC)", "Manage context window: prioritize information, compress history, summarize when approaching limits", ["analysis","code"], ["file:read"]),
    _skill("ecc-mcp-server-patterns", "MCP Server Builder (ECC)", "Build MCP servers: tool definitions, resource endpoints, prompt templates, stdio/SSE transport, testing", ["code","execution"], ["code:python","file:write"]),

    # ---------- Claudex Skills (Autonomous Agent) ----------
    _skill("claudex-code-review", "Code Review (Claudex)", "Automated code review with severity scoring: bugs, security, performance, style. Inline suggestions with fix examples", ["code","analysis"], ["file:read","file:write"]),
    _skill("claudex-arch-diagram", "Architecture Diagram (Claudex)", "Generate architecture diagrams from code: component diagrams, sequence diagrams, data flow, deployment maps", ["code","document","image"], ["file:write"]),
    _skill("claudex-api-tester", "API Tester (Claudex)", "Automated API testing: endpoint discovery, request building, response validation, contract testing, performance benchmarks", ["code","browser","execution"], ["network:http","file:write"]),
    _skill("claudex-security-audit", "Security Audit (Claudex)", "Comprehensive security audit: OWASP scanning, dependency CVEs, secrets detection, auth bypass checks, input validation", ["code","analysis","shell"], ["file:read","file:write"]),
    _skill("claudex-performance-profiler", "Performance Profiler (Claudex)", "Profile applications: CPU/memory/network bottlenecks, query optimization, caching opportunities, load testing", ["code","execution","analysis"], ["file:write"]),
    _skill("claudex-db-optimizer", "DB Optimizer (Claudex)", "Database optimization: index analysis, query plans, N+1 detection, connection pooling, migration safety", ["sql","code"], ["db:sql","file:write"]),
    _skill("claudex-ci-cd", "CI/CD Pipeline (Claudex)", "Build CI/CD: GitHub Actions, testing gates, deployment automation, secrets management, rollback procedures", ["code","shell"], ["network:http","file:write"]),
    _skill("claudex-error-recovery", "Error Recovery (Claudex)", "Graceful error handling: retry strategies, fallback chains, user-friendly messages, error reporting, monitoring integration", ["code","analysis"], ["file:write"]),
    _skill("claudex-refactoring-guide", "Refactoring Guide (Claudex)", "Safe refactoring: extract method, inline, rename, move, convert. Test-backed refactoring with behavior preservation", ["code","execution"], ["file:read","file:write"]),
    _skill("claudex-monitoring-setup", "Monitoring Setup (Claudex)", "Application monitoring: logging, metrics, alerts, dashboards, health checks, uptime monitoring, error tracking", ["code","shell","analysis"], ["file:write"]),
    _skill("claudex-test-data-gen", "Test Data Generator (Claudex)", "Generate realistic test data: fixtures, factories, seeds, edge cases, performance test datasets", ["code","execution"], ["file:write"]),
    _skill("claudex-static-analysis", "Static Analysis (Claudex)", "Code quality analysis: complexity metrics, duplication detection, dead code, type coverage, lint violations", ["code","analysis"], ["file:read","file:write"]),
    _skill("claudex-schema-evolver", "Schema Evolver (Claudex)", "Database schema evolution: backward-compatible changes, column additions, type changes, data migrations", ["sql","code"], ["db:sql","file:write"]),
    _skill("claudex-webhook-manager", "Webhook Manager (Claudex)", "Webhook management: endpoint setup, payload validation, retry logic, event routing, debugging", ["code","shell"], ["network:http","file:write"]),
    _skill("claudex-release-manager", "Release Manager (Claudex)", "Release automation: changelog generation, version bumping, tag creation, deployment coordination, rollback plans", ["code","shell"], ["file:write"]),
]

def validate_skill_package(data: dict) -> List[str]:
    errors = []
    if not data.get("name") or not re.match(r"^[a-z0-9\-_]+$", data.get("name","")):
        errors.append("name required, lowercase alphanumeric + -_")
    if not data.get("version") or not re.match(r"^\d+\.\d+\.\d+$", data.get("version","")):
        errors.append("version required semver x.y.z")
    if not data.get("manifest"):
        errors.append("manifest required")
    if not data.get("tools") or not isinstance(data.get("tools"), list):
        errors.append("tools must be list")
    if "permissions" not in data:
        errors.append("permissions required")
    return errors

class SkillCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0.0"
    source: SkillSource = SkillSource.UPLOADED
    source_url: Optional[str] = None
    manifest: Optional[dict] = None
    instructions: Optional[str] = None
    tools: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    config_schema: Optional[dict] = None
    default_config: Optional[dict] = None
    dependencies: Optional[List[str]] = None

class SkillUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    instructions: Optional[str] = None
    tools: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    config_schema: Optional[dict] = None
    default_config: Optional[dict] = None
    dependencies: Optional[List[str]] = None

class SkillResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    version: str
    source: str
    source_url: Optional[str]
    status: str
    manifest: Optional[dict]
    instructions: Optional[str]
    tools: Optional[List[str]]
    permissions: Optional[List[str]]
    config_schema: Optional[dict]
    default_config: Optional[dict]
    dependencies: Optional[List[str]]
    owner_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    installed_at: Optional[datetime]
    class Config:
        from_attributes = True

class SkillListResponse(BaseModel):
    skills: List[SkillResponse]
    total: int
    page: int
    page_size: int

class BuildRequest(BaseModel):
    prompt: str
    project_id: Optional[int] = None

class ValidateRequest(BaseModel):
    package: dict

@router.get("", response_model=SkillListResponse)
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: Optional[str] = None,
    source: Optional[SkillSource] = None,
    status: Optional[SkillStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Skill).filter((Skill.owner_id == current_user.id) | (Skill.owner_id.is_(None)))
    if search:
        q = q.filter(or_(Skill.name.ilike(f"%{search}%"), Skill.display_name.ilike(f"%{search}%"), Skill.description.ilike(f"%{search}%")))
    if source:
        q = q.filter(Skill.source == source)
    if status:
        q = q.filter(Skill.status == status)
    q = q.order_by(desc(Skill.updated_at))
    total = q.count()
    items = q.offset((page-1)*page_size).limit(page_size).all()
    return SkillListResponse(skills=[SkillResponse.model_validate(s) for s in items], total=total, page=page, page_size=page_size)

@router.get("/official", response_model=List[SkillResponse])
async def list_official(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # return static registry + any OFFICIAL in DB
    db_official = db.query(Skill).filter(Skill.source == SkillSource.OFFICIAL).all()
    # merge: if not in DB, return registry as virtual
    existing_names = {s.name for s in db_official}
    virtual = []
    for reg in OFFICIAL_REGISTRY:
        if reg["name"] not in existing_names:
            # create virtual SkillResponse without DB id (use 0)
            virtual.append(SkillResponse(
                id=0, name=reg["name"], display_name=reg["display_name"], description=reg["description"],
                version=reg["version"], source="OFFICIAL", source_url=None, status="NOT_INSTALLED",
                manifest=reg["manifest"], instructions=reg["instructions"], tools=reg["tools"],
                permissions=reg["permissions"], config_schema=reg["config_schema"], default_config=None,
                dependencies=reg["dependencies"], owner_id=None, created_at=datetime.utcnow(), updated_at=None, installed_at=None
            ))
    db_responses = [SkillResponse.model_validate(s) for s in db_official]
    return virtual + db_responses

@router.post("/official/{name}/install", response_model=SkillResponse)
async def install_official(name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reg = next((r for r in OFFICIAL_REGISTRY if r["name"]==name), None)
    if not reg:
        raise HTTPException(status_code=404, detail="Official skill not found")
    existing = db.query(Skill).filter(Skill.name==name, Skill.owner_id==current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already installed")
    errs = validate_skill_package(reg)
    if errs:
        raise HTTPException(status_code=400, detail=f"Invalid package: {errs}")
    skill = Skill(
        name=reg["name"], display_name=reg["display_name"], description=reg["description"],
        version=reg["version"], source=SkillSource.OFFICIAL, status=SkillStatus.INSTALLED,
        manifest=reg["manifest"], instructions=reg["instructions"], tools=reg["tools"],
        permissions=reg["permissions"], config_schema=reg["config_schema"], dependencies=reg["dependencies"],
        owner_id=current_user.id
    )
    db.add(skill); db.commit(); db.refresh(skill)

    # Replace the generic template body with a real, model-authored playbook.
    from app.services.skill_playbook import author_playbook, is_template
    if is_template(skill.instructions):
        try:
            pb = await author_playbook(
                name=reg["name"], description=reg["description"],
                tools=reg["tools"], permissions=reg["permissions"],
                db=db, user_id=current_user.id,
            )
            skill.instructions = pb["instructions"]
            manifest = dict(skill.manifest or {})
            manifest["playbook_source"] = pb["source"]
            if pb["error"]:
                manifest["playbook_note"] = pb["error"]
            skill.manifest = manifest
            db.commit(); db.refresh(skill)
        except Exception:
            db.rollback()

    # version snapshot
    ver = SkillVersion(skill_id=skill.id, version=skill.version, manifest=skill.manifest, instructions=skill.instructions, tools=skill.tools, permissions=skill.permissions, config_schema=skill.config_schema, dependencies=skill.dependencies, changelog="Initial install")
    db.add(ver); db.commit()
    await log_audit(db, user_id=current_user.id, action="SKILL_INSTALL", resource_type="skill", resource_id=str(skill.id), success=True)
    return SkillResponse.model_validate(skill)

@router.post("/upload", response_model=SkillResponse)
async def upload_skill(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        data = json.loads(content.decode())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    errs = validate_skill_package(data)
    if errs:
        raise HTTPException(status_code=400, detail=f"Validation failed: {errs}")
    skill = Skill(
        name=data["name"], display_name=data.get("display_name"), description=data.get("description"),
        version=data.get("version","1.0.0"), source=SkillSource.UPLOADED, status=SkillStatus.INSTALLED,
        manifest=data.get("manifest"), instructions=data.get("instructions"), tools=data.get("tools"),
        permissions=data.get("permissions"), config_schema=data.get("config_schema"), default_config=data.get("default_config"),
        dependencies=data.get("dependencies"), owner_id=current_user.id
    )
    db.add(skill); db.commit(); db.refresh(skill)
    ver = SkillVersion(skill_id=skill.id, version=skill.version, manifest=skill.manifest, instructions=skill.instructions, tools=skill.tools, permissions=skill.permissions, config_schema=skill.config_schema, dependencies=skill.dependencies, changelog="Uploaded")
    db.add(ver); db.commit()
    await log_audit(db, user_id=current_user.id, action="SKILL_INSTALL", resource_type="skill", resource_id=str(skill.id), success=True)
    return SkillResponse.model_validate(skill)

class GithubImport(BaseModel):
    url: str

@router.post("/github", response_model=SkillResponse)
async def import_github(data: GithubImport, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import httpx
    # support raw github url or api url; fetch manifest
    url = data.url.strip()
    # transform github.com/.../blob/... to raw
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            pkg = r.json() if "json" in r.headers.get("content-type","") else json.loads(r.text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fetch failed: {e}")
    errs = validate_skill_package(pkg)
    if errs:
        raise HTTPException(status_code=400, detail=f"Validation failed: {errs}")
    skill = Skill(
        name=pkg["name"], display_name=pkg.get("display_name"), description=pkg.get("description"),
        version=pkg.get("version","1.0.0"), source=SkillSource.GITHUB, source_url=data.url, status=SkillStatus.INSTALLED,
        manifest=pkg.get("manifest"), instructions=pkg.get("instructions"), tools=pkg.get("tools"),
        permissions=pkg.get("permissions"), config_schema=pkg.get("config_schema"), dependencies=pkg.get("dependencies"),
        owner_id=current_user.id
    )
    db.add(skill); db.commit(); db.refresh(skill)
    ver = SkillVersion(skill_id=skill.id, version=skill.version, manifest=skill.manifest, instructions=skill.instructions, tools=skill.tools, permissions=skill.permissions, config_schema=skill.config_schema, dependencies=skill.dependencies, changelog="GitHub import")
    db.add(ver); db.commit()
    await log_audit(db, user_id=current_user.id, action="SKILL_INSTALL", resource_type="skill", resource_id=str(skill.id), success=True)
    return SkillResponse.model_validate(skill)

@router.post("/build", response_model=SkillResponse)
async def build_skill(data: BuildRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prompt = data.prompt.strip()
    if len(prompt) < 10:
        raise HTTPException(status_code=400, detail="Prompt too short - describe the skill")
    # MARK self-build: synthesize package from prompt (template + validation)
    # In production this would call Model Router (Mythos) to generate manifest/tools
    slug = re.sub(r'[^a-z0-9]+','-', prompt.lower())[:30].strip('-')
    name = f"mark-generated-{slug}"
    # heuristic: infer tools
    tools = []
    if any(k in prompt.lower() for k in ["research","compare","search"]): tools += ["web_search","extract","synthesize"]
    if any(k in prompt.lower() for k in ["excel","spreadsheet","sheet"]): tools += ["create_workbook","spreadsheet"]
    if any(k in prompt.lower() for k in ["property","crm"]): tools += ["scrape","document"]
    if not tools: tools = ["web_search","file_write"]
    pkg = {
        "name": name,
        "display_name": prompt[:40].title(),
        "description": f"Auto-generated from: {prompt}",
        "version": "1.0.0",
        "manifest": {"name": name, "version":"1.0.0", "tools": tools, "prompt": prompt},
        "instructions": f"You are a skill that: {prompt}. Follow the validated workflow, use tools {tools}, respect permissions.",
        "tools": tools,
        "permissions": ["network:search","file:write"],
        "config_schema": {"output_project": {"type":"string"}},
        "dependencies": []
    }
    errs = validate_skill_package(pkg)
    if errs:
        raise HTTPException(status_code=400, detail=f"Generated package invalid: {errs}")
    skill = Skill(
        name=pkg["name"], display_name=pkg["display_name"], description=pkg["description"],
        version=pkg["version"], source=SkillSource.CREATED_BY_MARK, status=SkillStatus.INSTALLED,
        manifest=pkg["manifest"], instructions=pkg["instructions"], tools=pkg["tools"],
        permissions=pkg["permissions"], config_schema=pkg["config_schema"], dependencies=pkg["dependencies"],
        owner_id=current_user.id
    )
    db.add(skill); db.commit(); db.refresh(skill)
    ver = SkillVersion(skill_id=skill.id, version=skill.version, manifest=skill.manifest, instructions=skill.instructions, tools=skill.tools, permissions=skill.permissions, config_schema=skill.config_schema, dependencies=skill.dependencies, changelog="Built by Mark from prompt")
    db.add(ver); db.commit()
    await log_audit(db, user_id=current_user.id, action="SKILL_INSTALL", resource_type="skill", resource_id=str(skill.id), success=True)
    return SkillResponse.model_validate(skill)

@router.post("/validate")
async def validate_package(data: ValidateRequest, current_user: User = Depends(get_current_user)):
    errs = validate_skill_package(data.package)
    return {"valid": len(errs)==0, "errors": errs}

@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, (Skill.owner_id==current_user.id)|(Skill.owner_id.is_(None))).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    return SkillResponse.model_validate(s)

@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: int, data: SkillUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    for k,v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    await log_audit(db, user_id=current_user.id, action="SKILL_UPDATE", resource_type="skill", resource_id=str(s.id), success=True)
    return SkillResponse.model_validate(s)

@router.post("/{skill_id}/enable", response_model=SkillResponse)
async def enable_skill(skill_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    s.status = SkillStatus.ENABLED
    db.commit(); db.refresh(s)
    await log_audit(db, user_id=current_user.id, action="SKILL_ENABLE", resource_type="skill", resource_id=str(s.id), success=True)
    return SkillResponse.model_validate(s)

@router.post("/{skill_id}/disable", response_model=SkillResponse)
async def disable_skill(skill_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    s.status = SkillStatus.DISABLED
    db.commit(); db.refresh(s)
    await log_audit(db, user_id=current_user.id, action="SKILL_DISABLE", resource_type="skill", resource_id=str(s.id), success=True)
    return SkillResponse.model_validate(s)

@router.post("/{skill_id}/configure", response_model=SkillResponse)
async def configure_skill(skill_id: int, config: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    s.default_config = config
    db.commit(); db.refresh(s)
    return SkillResponse.model_validate(s)

@router.post("/{skill_id}/update", response_model=SkillResponse)
async def update_skill_version(skill_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a skill from a real source.

    Previously this blindly applied whatever the client posted and flipped the
    status to INSTALLED, so an "update" could fetch nothing at all. Now a
    `source_url` is fetched and validated; a body without one is recorded as a
    local edit rather than passed off as an upgrade.
    """
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")

    source_url = (data or {}).get("source_url") or (data or {}).get("url")
    fetched = None
    update_kind = "local_edit"

    if source_url:
        if not str(source_url).startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="source_url must be an http/https URL")
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                r = await client.get(source_url, headers={"User-Agent": "Mark-Imti/1.0"})
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Could not fetch the skill package: {exc}")
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code,
                                detail=f"Skill source returned HTTP {r.status_code}")
        try:
            fetched = r.json()
        except Exception:
            raise HTTPException(status_code=422,
                                detail="Skill package is not valid JSON - nothing was applied")

        if not isinstance(fetched, dict):
            raise HTTPException(status_code=422, detail="Skill package must be a JSON object")

        # Validate before touching the stored skill.
        candidate = {
            "name": fetched.get("name", s.name),
            "version": fetched.get("version", s.version),
            "manifest": fetched.get("manifest", {}),
            "instructions": fetched.get("instructions", ""),
            "tools": fetched.get("tools", []),
            "permissions": fetched.get("permissions", []),
            "config_schema": fetched.get("config_schema", {}),
            "dependencies": fetched.get("dependencies", []),
        }
        if not candidate["instructions"]:
            raise HTTPException(status_code=422, detail="Skill package has no 'instructions' - rejected")
        errs = validate_skill_package(candidate)
        if errs:
            raise HTTPException(status_code=422, detail=f"Skill package failed validation: {errs}; nothing was applied")
        update_kind = "remote"

    s.status = SkillStatus.UPDATING
    db.commit()

    # snapshot current so rollback works
    ver = SkillVersion(skill_id=s.id, version=s.version, manifest=s.manifest, instructions=s.instructions, tools=s.tools, permissions=s.permissions, config_schema=s.config_schema, dependencies=s.dependencies, changelog="Before update")
    db.add(ver)

    if update_kind == "remote":
        new_version = str(fetched.get("version") or s.version)
        manifest = dict(fetched.get("manifest") or {})
        manifest["updated_from"] = source_url
        s.version = new_version
        s.manifest = manifest
        s.instructions = fetched.get("instructions")
        s.tools = fetched.get("tools", [])
        s.permissions = fetched.get("permissions", [])
        s.config_schema = fetched.get("config_schema", {})
        s.dependencies = fetched.get("dependencies", [])
        changelog = (fetched.get("changelog")
                     or f"Updated from {source_url}")
    else:
        # No remote source: apply the supplied fields, but label it honestly.
        manifest = dict(s.manifest or {})
        manifest["last_update_kind"] = "local_edit"
        s.manifest = manifest
        for k in ["version","manifest","instructions","tools","permissions","config_schema","default_config","dependencies"]:
            if k in data and k != "source_url":
                setattr(s, k, data[k])
        changelog = data.get("changelog", "Local edit (no remote source supplied)")

    s.status = SkillStatus.INSTALLED
    db.commit(); db.refresh(s)

    ver2 = SkillVersion(skill_id=s.id, version=s.version, manifest=s.manifest, instructions=s.instructions, tools=s.tools, permissions=s.permissions, config_schema=s.config_schema, dependencies=s.dependencies, changelog=changelog)
    db.add(ver2); db.commit()
    await log_audit(db, user_id=current_user.id, action="SKILL_UPDATE", resource_type="skill", resource_id=str(s.id), success=True)
    return SkillResponse.model_validate(s)

@router.post("/{skill_id}/rollback", response_model=SkillResponse)
async def rollback_skill(skill_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    vers = db.query(SkillVersion).filter(SkillVersion.skill_id==skill_id).order_by(desc(SkillVersion.created_at)).all()
    if len(vers) < 2:
        raise HTTPException(status_code=400, detail="No previous version to rollback")
    prev = vers[1]
    s.version = prev.version
    s.manifest = prev.manifest
    s.instructions = prev.instructions
    s.tools = prev.tools
    s.permissions = prev.permissions
    s.config_schema = prev.config_schema
    s.dependencies = prev.dependencies
    db.commit(); db.refresh(s)
    return SkillResponse.model_validate(s)

@router.delete("/{skill_id}")
async def remove_skill(skill_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, Skill.owner_id==current_user.id).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(s); db.commit()
    await log_audit(db, user_id=current_user.id, action="SKILL_REMOVE", resource_type="skill", resource_id=str(skill_id), success=True)
    return {"message":"Skill removed"}

# ---------- Self-Builder: Discover & Auto-Install Skills ----------

class DiscoverRequest(BaseModel):
    query: Optional[str] = None
    url: Optional[str] = None  # GitHub repo/folder/file URL
    urls: Optional[List[str]] = None  # List of raw URLs to fetch skills from
    auto_install: bool = False

class DiscoverResponse(BaseModel):
    skills: List[dict]
    repos: List[dict]
    installed: int
    message: str

@router.post("/discover", response_model=DiscoverResponse)
async def discover_skills(data: DiscoverRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Browse GitHub, discover skill repos, parse SKILL.md files, and optionally auto-install."""
    from app.services.self_builder import (
        search_and_discover, discover_from_url, discover_from_known_repos
    )

    all_skills = []
    repos = []

    if data.urls:
        # Discover from a list of raw URLs
        from app.services.self_builder import discover_from_raw_urls
        all_skills = await discover_from_raw_urls(data.urls)
    elif data.url:
        # Discover from a specific URL
        all_skills = await discover_from_url(data.url)
    elif data.query:
        # Search GitHub for skills
        all_skills, repos = await search_and_discover(data.query)
    else:
        # Scan all known repos
        all_skills = await discover_from_known_repos()

    # Deduplicate by name
    seen = set()
    unique_skills = []
    for s in all_skills:
        if s.name not in seen:
            seen.add(s.name)
            unique_skills.append(s)

    installed_count = 0
    if data.auto_install:
        # Auto-install discovered skills
        installed_names = {s.name for s in db.query(Skill).all()}
        for skill in unique_skills:
            if skill.name not in installed_names:
                db_skill = Skill(
                    name=skill.name,
                    display_name=skill.display_name,
                    description=skill.description,
                    version="1.0.0",
                    source=SkillSource.GITHUB,
                    source_url=skill.source_url,
                    status=SkillStatus.INSTALLED,
                    manifest={"name": skill.name, "tools": skill.tools, "origin": skill.origin},
                    instructions=skill.content[:2000],
                    tools=skill.tools,
                    permissions=["network:search", "file:write"],
                    owner_id=current_user.id,
                )
                db.add(db_skill)
                installed_count += 1
        db.commit()

    return DiscoverResponse(
        skills=[{
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "source_repo": s.source_repo,
            "source_url": s.source_url,
            "tools": s.tools,
            "category": s.category,
            "origin": s.origin,
        } for s in unique_skills[:50]],
        repos=[{
            "full_name": r.get("full_name"),
            "description": r.get("description"),
            "stars": r.get("stargazers_count", 0),
            "url": r.get("html_url"),
        } for r in repos[:10]],
        installed=installed_count,
        message=f"Found {len(unique_skills)} skills, {len(repos)} repos" + (f", installed {installed_count}" if installed_count else ""),
    )


class AutoInstallRequest(BaseModel):
    skills: List[str]  # list of skill names to install from discovered

@router.post("/auto-install")
async def auto_install_skills(data: AutoInstallRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Install specific skills by name from the discovered pool."""
    from app.services.self_builder import discover_from_known_repos

    discovered = await discover_from_known_repos()
    discovered_map = {s.name: s for s in discovered}
    installed_names = {s.name for s in db.query(Skill).all()}

    installed = 0
    for name in data.skills:
        if name in discovered_map and name not in installed_names:
            s = discovered_map[name]
            db_skill = Skill(
                name=s.name,
                display_name=s.display_name,
                description=s.description,
                version="1.0.0",
                source=SkillSource.GITHUB,
                source_url=s.source_url,
                status=SkillStatus.INSTALLED,
                manifest={"name": s.name, "tools": s.tools, "origin": s.origin},
                instructions=s.content[:2000],
                tools=s.tools,
                permissions=["network:search", "file:write"],
                owner_id=current_user.id,
            )
            db.add(db_skill)
            installed += 1

    db.commit()
    return {"installed": installed, "message": f"Installed {installed} skills"}


@router.post("/fill-gaps")
async def fill_skill_gaps(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Auto-discover and install skills that agents need but don't have."""
    from app.services.self_builder import discover_from_known_repos

    # Get all agent skill needs
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    needed_skills = set()
    for agent in agents:
        if agent.available_skills:
            needed_skills.update(agent.available_skills)

    # Get installed skill names
    installed_names = {s.name for s in db.query(Skill).all()}

    # Find gaps
    gaps = needed_skills - installed_names
    if not gaps:
        return {"message": "No skill gaps found", "filled": 0}

    # Discover and install
    discovered = await discover_from_known_repos()
    discovered_map = {s.name: s for s in discovered}

    filled = 0
    for gap_name in gaps:
        if gap_name in discovered_map:
            s = discovered_map[gap_name]
            db_skill = Skill(
                name=s.name,
                display_name=s.display_name,
                description=s.description,
                version="1.0.0",
                source=SkillSource.GITHUB,
                source_url=s.source_url,
                status=SkillStatus.INSTALLED,
                manifest={"name": s.name, "tools": s.tools, "origin": s.origin},
                instructions=s.content[:2000],
                tools=s.tools,
                permissions=["network:search", "file:write"],
                owner_id=current_user.id,
            )
            db.add(db_skill)
            filled += 1

    db.commit()
    return {"filled": filled, "gaps": list(gaps), "message": f"Filled {filled} skill gaps"}


class LocalImportRequest(BaseModel):
    directory: str  # Path to skills directory
    limit: int = 50

@router.post("/import-local")
async def import_local_skills(data: LocalImportRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Import skills from a local directory (e.g., ~/.config/opencode/skills)."""
    import os
    from app.services.self_builder import parse_skill_md

    directory = data.directory
    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail=f"Directory not found: {directory}")

    installed_names = {s.name for s in db.query(Skill).all()}
    imported = 0
    errors = []

    # Scan for SKILL.md files
    for root, dirs, files in os.walk(directory):
        if "SKILL.md" in files:
            skill_path = os.path.join(root, "SKILL.md")
            try:
                with open(skill_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                parsed = parse_skill_md(content, f"file://{skill_path}", "local")
                if parsed and parsed.name not in installed_names:
                    db_skill = Skill(
                        name=parsed.name,
                        display_name=parsed.display_name,
                        description=parsed.description,
                        version="1.0.0",
                        source=SkillSource.UPLOADED,
                        source_url=f"file://{skill_path}",
                        status=SkillStatus.INSTALLED,
                        manifest={"name": parsed.name, "tools": parsed.tools, "origin": parsed.origin},
                        instructions=parsed.content[:2000],
                        tools=parsed.tools,
                        permissions=["network:search", "file:write"],
                        owner_id=current_user.id,
                    )
                    db.add(db_skill)
                    installed_names.add(parsed.name)
                    imported += 1

                    if imported >= data.limit:
                        break
            except Exception as e:
                errors.append(f"{skill_path}: {str(e)[:100]}")

        if imported >= data.limit:
            break

    db.commit()
    return {
        "imported": imported,
        "errors": errors[:10],
        "message": f"Imported {imported} skills from {directory}" + (f" ({len(errors)} errors)" if errors else ""),
    }

@router.get("/{skill_id}/versions")
async def list_versions(skill_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Skill).filter(Skill.id==skill_id, (Skill.owner_id==current_user.id)|(Skill.owner_id.is_(None))).first()
    if not s: raise HTTPException(status_code=404, detail="Skill not found")
    vers = db.query(SkillVersion).filter(SkillVersion.skill_id==skill_id).order_by(desc(SkillVersion.created_at)).all()
    return [{"id":v.id, "version":v.version, "changelog":v.changelog, "created_at":v.created_at} for v in vers]
