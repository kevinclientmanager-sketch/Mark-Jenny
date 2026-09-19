"""
Advanced Intelligence API — All advanced workflows exposed as endpoints.
Cybersecurity, Biology Research, Deep Reasoning, Autonomous Research,
Coding Intelligence, Context Memory.

All endpoints use whatever model is configured (local or online).
The intelligence is in the WORKFLOW, not the model.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.advanced_workflows import (
    cybersecurity_workflow,
    bio_research_workflow,
    deep_reasoning_workflow,
    autonomous_research_workflow,
    coding_intelligence_workflow,
    context_memory_workflow,
    ModelCaller,
    DeepReasoningWorkflow,
)

router = APIRouter()


# === Model Status ===

@router.get("/model/status")
async def model_status(current_user: User = Depends(get_current_user)):
    """Check which AI model is currently available."""
    return ModelCaller.get_model_info()


# === CYBERSECURITY ===

class CyberScanCodeRequest(BaseModel):
    code: str
    filename: str = "unknown"
    language: str = "auto"

class CyberScanDirRequest(BaseModel):
    dir_path: str

class CyberFixRequest(BaseModel):
    code: str
    vulnerability: str

class CyberPentestRequest(BaseModel):
    target: str
    scope: str = "web"

class CyberWebAuditRequest(BaseModel):
    url: str

class CyberCookieRequest(BaseModel):
    url: str

class CyberSafetyRequest(BaseModel):
    url: str

class CyberFullAssessmentRequest(BaseModel):
    url: str


@router.post("/cybersecurity/scan")
async def cyber_scan_code(data: CyberScanCodeRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.scan_code(data.code, data.filename, data.language)

@router.post("/cybersecurity/scan-directory")
async def cyber_scan_dir(data: CyberScanDirRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.scan_directory(data.dir_path)

@router.post("/cybersecurity/fix")
async def cyber_fix(data: CyberFixRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.generate_fix(data.code, data.vulnerability)

@router.post("/cybersecurity/pentest")
async def cyber_pentest(data: CyberPentestRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.pentest_guide(data.target, data.scope)

@router.post("/cybersecurity/web-audit")
async def cyber_web_audit(data: CyberWebAuditRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.web_audit(data.url)

@router.post("/cybersecurity/analyze-cookies")
async def cyber_cookies(data: CyberCookieRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.analyze_cookies(data.url)

@router.post("/cybersecurity/site-safety")
async def cyber_safety(data: CyberSafetyRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.site_safety_check(data.url)

@router.post("/cybersecurity/full-assessment")
async def cyber_full(data: CyberFullAssessmentRequest, current_user: User = Depends(get_current_user)):
    return await cybersecurity_workflow.full_security_assessment(data.url)


# === BIOLOGY RESEARCH ===

class BioLiteratureRequest(BaseModel):
    query: str
    max_results: int = 10

class BioSequenceRequest(BaseModel):
    sequence: str
    seq_type: str = "protein"

class BioHypothesisRequest(BaseModel):
    observation: str
    domain: str = "general"

class BioExperimentRequest(BaseModel):
    research_question: str

class BioStructureRequest(BaseModel):
    sequence: str

class BioPathwayRequest(BaseModel):
    genes: List[str]


@router.post("/biology/literature-review")
async def bio_literature(data: BioLiteratureRequest, current_user: User = Depends(get_current_user)):
    return await bio_research_workflow.literature_review(data.query, data.max_results)

@router.post("/biology/sequence-analysis")
async def bio_sequence(data: BioSequenceRequest, current_user: User = Depends(get_current_user)):
    return await bio_research_workflow.analyze_sequence(data.sequence, data.seq_type)

@router.post("/biology/generate-hypothesis")
async def bio_hypothesis(data: BioHypothesisRequest, current_user: User = Depends(get_current_user)):
    return await bio_research_workflow.generate_hypothesis(data.observation, data.domain)

@router.post("/biology/design-experiment")
async def bio_experiment(data: BioExperimentRequest, current_user: User = Depends(get_current_user)):
    return await bio_research_workflow.design_experiment(data.research_question)

@router.post("/biology/predict-structure")
async def bio_structure(data: BioStructureRequest, current_user: User = Depends(get_current_user)):
    return await bio_research_workflow.predict_structure(data.sequence)

@router.post("/biology/pathway-analysis")
async def bio_pathway(data: BioPathwayRequest, current_user: User = Depends(get_current_user)):
    return await bio_research_workflow.pathway_analysis(data.genes)


# === DEEP REASONING ===

class ReasoningAnalyzeRequest(BaseModel):
    query: str
    level: str = "balanced"
    context: Optional[Dict[str, Any]] = None

class ReasoningCompareRequest(BaseModel):
    options: List[str]
    criteria: List[str]
    context: str = ""

class ReasoningSolveRequest(BaseModel):
    problem: str
    approach: str = "systematic"


@router.post("/reasoning/analyze")
async def reasoning_analyze(data: ReasoningAnalyzeRequest, current_user: User = Depends(get_current_user)):
    return await deep_reasoning_workflow.analyze(data.query, data.level, data.context)

@router.post("/reasoning/compare")
async def reasoning_compare(data: ReasoningCompareRequest, current_user: User = Depends(get_current_user)):
    return await deep_reasoning_workflow.compare_options(data.options, data.criteria, data.context)

@router.post("/reasoning/solve")
async def reasoning_solve(data: ReasoningSolveRequest, current_user: User = Depends(get_current_user)):
    return await deep_reasoning_workflow.solve_problem(data.problem, data.approach)

@router.get("/reasoning/levels")
async def reasoning_levels():
    return {"levels": list(DeepReasoningWorkflow.LEVELS.keys())}


# === AUTONOMOUS RESEARCH ===

class ResearchTopicRequest(BaseModel):
    topic: str
    depth: str = "standard"


@router.post("/research/topic")
async def research_topic(data: ResearchTopicRequest, current_user: User = Depends(get_current_user)):
    return await autonomous_research_workflow.research_topic(data.topic, data.depth)


# === CODING INTELLIGENCE ===

class CodeAnalyzeRequest(BaseModel):
    code: str
    filename: str = ""

class CodeBugRequest(BaseModel):
    code: str
    error: str
    context: str = ""

class CodeRefactorRequest(BaseModel):
    code: str
    goal: str = "improve quality"

class CodeTestRequest(BaseModel):
    code: str
    filename: str = ""

class CodeExplainRequest(BaseModel):
    code: str
    level: str = "detailed"


@router.post("/coding/analyze")
async def coding_analyze(data: CodeAnalyzeRequest, current_user: User = Depends(get_current_user)):
    return await coding_intelligence_workflow.analyze_codebase(data.code, data.filename)

@router.post("/coding/fix-bug")
async def coding_fix_bug(data: CodeBugRequest, current_user: User = Depends(get_current_user)):
    return await coding_intelligence_workflow.fix_bug(data.code, data.error, data.context)

@router.post("/coding/refactor")
async def coding_refactor(data: CodeRefactorRequest, current_user: User = Depends(get_current_user)):
    return await coding_intelligence_workflow.refactor(data.code, data.goal)

@router.post("/coding/generate-tests")
async def coding_tests(data: CodeTestRequest, current_user: User = Depends(get_current_user)):
    return await coding_intelligence_workflow.generate_tests(data.code, data.filename)

@router.post("/coding/explain")
async def coding_explain(data: CodeExplainRequest, current_user: User = Depends(get_current_user)):
    return await coding_intelligence_workflow.explain_code(data.code, data.level)


# === CONTEXT MEMORY ===

class StoreMemoryRequest(BaseModel):
    content: str
    context: str = ""
    importance: int = 70
    project_id: Optional[int] = None

class StoreResearchRequest(BaseModel):
    topic: str
    finding: str
    sources: List[str]
    project_id: Optional[int] = None

class GetContextRequest(BaseModel):
    query: str
    project_id: Optional[int] = None


@router.post("/memory/store")
async def memory_store(data: StoreMemoryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await context_memory_workflow.store_working_memory(
        db, current_user.id, data.content, data.context, data.importance, data.project_id
    )

@router.post("/memory/store-research")
async def memory_store_research(data: StoreResearchRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await context_memory_workflow.store_research_finding(
        db, current_user.id, data.topic, data.finding, data.sources, data.project_id
    )

@router.post("/memory/context")
async def memory_context(data: GetContextRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await context_memory_workflow.get_context(db, current_user.id, data.query, data.project_id)
