# MISRA Compliance Reviewer — Workflow Documentation

## Project Overview

**MISRA Compliance Reviewer** is a GenAI-powered system that analyzes C code for MISRA compliance violations and generates intelligent fix suggestions. It combines semantic retrieval (Qdrant + BGE embeddings), local LLM inference (Mistral 7B), and self-critiquing evaluation to deliver high-quality MISRA compliance remediation.

---

## Architecture Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Flask | REST API + Web UI (HTML/JS/CSS) |
| **File Upload** | Werkzeug | Multi-file handling (Excel, C source) |
| **LLM Generation** | llama-cpp-python | Local Mistral 7B inference |
| **Embeddings** | BGE (BAAI/bge-base-en-v1.5) | Semantic encoding for MISRA rules |
| **Vector DB** | Qdrant | Fast semantic retrieval of rules |
| **Caching** | SQLite | Retrieval cache + result cache |
| **Knowledge Base** | Excel → JSON | MISRA rules structured data |

---

## End-to-End Workflow

### Entry Point: Web Server
```
User → Browser (127.0.0.1:5000)
  ↓
Flask server listens for:
  - POST /api/analyse (file upload)
  - GET /api/progress/<job_id> (SSE stream)
  - GET /api/runs (list completed runs)
```

### Step 1: User Uploads Files
**Endpoint:** `POST /api/analyse`

**Input Files:**
1. **Excel Warning Report** (`*.xlsx`)
   - Contains Polyspace warnings from static analysis
   - Columns: Warning ID, Rule ID, Severity, File Path, Line Numbers, Message

2. **C Source Code** (`.zip` or directory)
   - Complete source tree for the project
   - Used to extract code context around violations

**Processing:**
```python
# app/web/server.py
1. Validate file types
2. Generate unique job_id (UUID)
3. Extract files to temp location: data/_upload_tmp/<job_id>/
4. Launch orchestrator as subprocess:
   python orchestrator.py <excel> <source_dir> --run-id <job_id>
5. Monitor subprocess progress via shared JSON file
6. Return job_id to frontend for polling
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Analysis started"
}
```

---

### Step 2-5: Pipeline Orchestrator (4 Phases)

**File:** [`app/pipeline/orchestrator.py`](app/pipeline/orchestrator.py)

The orchestrator executes 4 sequential phases:

---

## Phase 6a: Parse Polyspace Report

**Purpose:** Extract warnings and code context from Excel report

**Input:**
- Excel warning report file
- C source code directory

**Process:**
```python
from app.ingestion.parse_polyspace import parse_report

warnings = parse_report(xlsx_path, source_dir)
```

**Details:**
1. Read Excel file using pandas
2. For each warning row:
   - Extract: rule_id, line, severity, message, file path
   - Fetch source code lines around violation
   - Parse code context (40 lines max)
   - Extract warning metadata

**Output:** `phase_6a_parsed.json`
```json
{
  "warning_count": 125,
  "warnings": [
    {
      "warning_id": "W001",
      "rule_id": "MISRA-2012-2.1",
      "severity": "High",
      "file_path": "src/main.c",
      "line_start": 42,
      "line_end": 45,
      "message": "Empty statement",
      "checker_name": "Polyspace",
      "source_context": {
        "context_text": "void foo() {\n  if (x > 0) ;\n  return;\n}",
        "start_line": 40,
        "end_line": 48
      }
    }
  ]
}
```

---

## Phase 6b: Retrieve MISRA Context

**Purpose:** Enrich warnings with relevant MISRA rule information via semantic search

**Components:**
- **Qdrant:** Vector database storing MISRA rule embeddings
- **BGE Model:** BAAI/bge-base-en-v1.5 for encoding
- **Retrieval Cache:** SQLite to prevent duplicate queries

**Process:**

```python
def phase_6b_retrieve(warnings, out_path):
    for warning in warnings:
        # 1. Try cache first
        cached_rules = retrieval_cache.get(warning['rule_id'])
        if cached_rules:
            enriched.append({**warning, "misra_context": cached_rules})
            continue
        
        # 2. Semantic search in Qdrant
        retrieved_rules = retrieve_rules(warning)  # 10 top-k results
        
        # 3. Postprocess & filter
        clean_rules = postprocess_retrieved_rules(retrieved_rules)
        
        # 4. Cache result
        retrieval_cache.store(warning['rule_id'], clean_rules)
        
        enriched.append({**warning, "misra_context": clean_rules})
```

**Retrieval Process:**
1. **Embed warning:** BGE encoder converts warning metadata + message to vector
2. **Query Qdrant:** Find 10 semantically similar MISRA rules
3. **Score filtering:** Keep only results with similarity ≥ 0.70
4. **Rerank:** Sort by relevance
5. **Extract:** Get rule text, examples, and applicability

**Files Involved:**
- [`app/retrieval/retrieve_rules.py`](app/retrieval/retrieve_rules.py) — Qdrant query logic
- [`app/retrieval/retrieval_postprocessor.py`](app/retrieval/retrieval_postprocessor.py) — Filter & rank
- [`app/retrieval/cache_service.py`](app/retrieval/cache_service.py) — Cache management

**Output:** `phase_6b_enriched.json`
```json
{
  "warning_count": 125,
  "warnings": [
    {
      "warning_id": "W001",
      "rule_id": "MISRA-2012-2.1",
      "severity": "High",
      "source_context": {...},
      "misra_context": [
        {
          "rule_id": "MISRA-2012-2.1",
          "title": "Empty Statement Prohibited",
          "description": "An empty statement shall not be a null statement.",
          "example": "int x; ; // violation: empty statement",
          "fix_guidance": "Remove the semicolon or add a compound statement.",
          "severity_level": "Mandatory",
          "score": 0.95
        }
      ]
    }
  ]
}
```

---

## Phase 7: Generate Fix Suggestions

**Purpose:** Use local Llama model to generate intelligent MISRA fixes

**Model:** Mistral 7B Instruct v0.3 (Q4_K_M quantized)

**Process:**

```python
def phase_7_generate(enriched, out_path):
    config = GenerationConfig(
        model_path=LOCAL_MODEL_PATH,  # Q4_K_M GGUF
        n_ctx=4096,
        temperature=0.0,  # Deterministic output
        max_tokens=1400
    )
    
    for warning in enriched:
        # Skip if already generated (resume capability)
        if warning['warning_id'] in completed:
            continue
        
        # Prepare prompt context
        bundle = generate_misra_response(
            rule_id=warning['rule_id'],
            warning_message=warning['message'],
            code_snippet=warning['source_context']['context_text'],
            checker_name=warning['checker_name'],
            misra_rules=warning['misra_context'],  # Retrieved rules
            config=config
        )
        
        results.append(bundle['result'])
```

**Prompt Structure:**
```
CONTEXT:
- MISRA Rule: [rule_id + full rule text]
- Code Violation: [original code]
- Warning Message: [Polyspace message]

TASK:
Generate a corrected code snippet that:
1. Fixes the MISRA violation
2. Preserves original functionality
3. Follows MISRA guidelines

OUTPUT FORMAT (JSON):
{
  "fixed_code": "...",
  "explanation": "...",
  "compliance_status": "COMPLIANT|NON_COMPLIANT|UNCERTAIN"
}
```

**Runtime:**
- Single GPU fallback to CPU (n_gpu_layers=0)
- ~8 threads for inference
- ~3-5 seconds per warning
- Seed=42 for reproducibility

**Result Processing:**
1. Generate raw LLM output
2. Parse JSON response
3. Validate code syntax (basic)
4. Generic validation (schema check)

**Files Involved:**
- [`app/generation/generate_misra_response.py`](app/generation/generate_misra_response.py) — LLM wrapper
- [`app/generation/response_validator.py`](app/generation/response_validator.py) — Output validation

**Output:** `phase_7_generated.json`
```json
{
  "warning_count": 125,
  "results": [
    {
      "warning_id": "W001",
      "rule_id": "MISRA-2012-2.1",
      "fixed_code": "void foo() {\n  if (x > 0) { /* empty */ }\n  return;\n}",
      "explanation": "Replaced null statement with compound statement per MISRA-2012-2.1",
      "compliance_status": "COMPLIANT",
      "confidence": "HIGH",
      "generation_time_ms": 3200,
      "parse_error": null
    }
  ]
}
```

---

## Phase 8: Evaluate & Self-Critique Fixes

**Purpose:** Verify generated fixes are correct and fully compliant

**Approach:** Self-evaluation using same LLM

**Process:**

```python
def phase_8_evaluate(generated_results, enriched_warnings):
    evaluator_config = GenerationConfig(
        model_path=LOCAL_MODEL_PATH,
        max_tokens=3000,
        temperature=0.0
    )
    
    evaluated = []
    
    for result in generated_results:
        matching_warning = find_warning(result['warning_id'], enriched_warnings)
        
        # 4-point evaluation
        evaluation = evaluate_fix(
            original_code=matching_warning['source_context']['context_text'],
            fixed_code=result['fixed_code'],
            misra_rule=matching_warning['misra_context'][0],  # Primary rule
            config=evaluator_config
        )
        
        # Merge evaluation results
        result.update({
            "evaluation": evaluation,
            "final_confidence": determine_confidence(evaluation),
            "ready_for_deployment": evaluation['is_correct'] and 
                                    evaluation['confidence'] == "HIGH"
        })
        
        evaluated.append(result)
    
    return evaluated
```

**Evaluation Criteria:**
1. **Correctness:** Does the fix resolve the violation per rule definition?
2. **No Regressions:** Does the fix introduce new MISRA violations?
3. **Syntax Validity:** Is the corrected code syntactically valid C?
4. **Confidence Score:** HIGH / MEDIUM / LOW

**Evaluation Prompt:**
```
Given the MISRA rule:
[Full rule text + examples]

Original code with violation:
[code]

Proposed fix:
[fixed_code]

Question 1: Does this fix resolve the violation? (YES/NO/PARTIAL)
Question 2: Does it introduce new violations? (YES/NO)
Question 3: Is the C code syntactically valid? (YES/NO)
Question 4: Confidence level? (HIGH/MEDIUM/LOW)

If confidence is LOW or fix is wrong: provide corrected version.

JSON output: {
  "is_correct": bool,
  "no_regressions": bool,
  "syntax_valid": bool,
  "confidence": "HIGH|MEDIUM|LOW",
  "reasoning": "...",
  "corrected_code": "..." (if needed)
}
```

**Files Involved:**
- [`app/pipeline/evaluate_fixes.py`](app/pipeline/evaluate_fixes.py) — Evaluation logic

**Output:** `phase_8_evaluated.json`
```json
{
  "results_count": 125,
  "high_confidence": 98,
  "medium_confidence": 20,
  "low_confidence": 7,
  "results": [
    {
      "warning_id": "W001",
      "rule_id": "MISRA-2012-2.1",
      "fixed_code": "void foo() {\n  if (x > 0) { /* empty */ }\n  return;\n}",
      "explanation": "...",
      "compilation_status": "COMPLIANT",
      "evaluation": {
        "is_correct": true,
        "no_regressions": true,
        "syntax_valid": true,
        "confidence": "HIGH",
        "reasoning": "Fix correctly replaces null statement with empty compound statement. No new violations.",
        "corrected_code": null
      },
      "final_confidence": "HIGH",
      "ready_for_deployment": true,
      "evaluation_time_ms": 2800
    }
  ]
}
```

---

## Output & Reporting

### Directory Structure
```
data/output/<job_id>/
├── phase_6a_parsed.json          # Parsed warnings
├── phase_6b_enriched.json        # With MISRA context
├── phase_7_generated.json        # Generated fixes
├── phase_8_evaluated.json        # Evaluated & finalized
├── audit.json                    # Processing metadata
├── summary.json                  # Stats and summary
├── MISRA_Compliance_Report.pdf   # PDF export
└── MISRA_Compliance_Report.docx  # Word export
```

### Summary Report
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-31T11:07:47",
  "input": {
    "excel_report": "warning_report.xlsx",
    "source_directory": "src/",
    "total_warnings": 125
  },
  "results": {
    "total_processed": 125,
    "high_confidence": 98,
    "medium_confidence": 20,
    "low_confidence": 7,
    "processing_time_seconds": 485
  },
  "by_severity": {
    "High": {"total": 40, "high_conf": 38, "medium_conf": 2},
    "Medium": {"total": 60, "high_conf": 45, "medium_conf": 15},
    "Low": {"total": 25, "high_conf": 15, "medium_conf": 10}
  },
  "by_rule": {
    "MISRA-2012-2.1": {"count": 12, "high_conf_avg": 0.92},
    "MISRA-2012-5.2": {"count": 18, "high_conf_avg": 0.88}
  },
  "exports_generated": ["PDF", "Word", "JSON"]
}
```

---

## Web UI Workflow

### Frontend Architecture

**Files:**
- [`app/web/templates/index.html`](app/web/templates/index.html) — Upload form
- [`app/web/templates/results.html`](app/web/templates/results.html) — Results display
- [`app/web/static/script.js`](app/web/static/script.js) — Form handling & polling
- [`app/web/static/style.css`](app/web/static/style.css) — Styling
- [`app/web/static/config_modal.js`](app/web/static/config_modal.js) — Configuration UI

### User Journey

1. **Upload Page**
   ```
   User opens http://127.0.0.1:5000/
   ↓
   Uploads Excel report + C source files
   ↓
   Clicks "Analyze"
   ↓
   POST /api/analyse (multipart form data)
   ↓
   Server returns: {"job_id": "...", "status": "processing"}
   ↓
   Browser redirects to /results.html?job_id=...
   ```

2. **Progress Monitoring** (SSE Stream)
   ```
   Browser connects: GET /api/progress/<job_id> (EventSource)
   ↓
   Server streams real-time progress:
   {
     "status": "running",
     "current_phase": "Phase 7",
     "progress_percent": 45,
     "message": "Generating fixes... 56/125 complete"
   }
   ↓
   When complete:
   {
     "status": "complete",
     "progress_percent": 100,
     "output_dir": "data/output/<job_id>"
   }
   ```

3. **Results Page**
   ```
   Fetches: GET /api/run/<job_id>/results (JSON)
   ↓
   Displays:
   - Summary statistics
   - List of warnings with fixes
   - Grouped by severity/rule
   - Filter & search
   - Download options (PDF, Word)
   ```

---

## Caching Strategy

### 1. Retrieval Cache
**File:** `data/cache/retrieval_cache.sqlite3`

**Purpose:** Avoid redundant Qdrant queries for same rule IDs

**Schema:**
```sql
CREATE TABLE retrieval_cache (
    cache_key TEXT PRIMARY KEY,
    rule_id TEXT,
    retrieved_rules JSON,
    timestamp DATETIME,
    hits_count INT
)
```

**Hit Logic:**
```python
cache_key = hash(rule_id + warning_message)
if cache_key in cache:
    use_cached_rules()
else:
    query_qdrant()
    store_in_cache()
```

### 2. Result Cache
**File:** `data/cache/results_cache.db`

**Purpose:** Store final recommendations for re-use

**Lookup:**
```python
result_key = hash(rule_id + code_snippet)
if result_key in cache:
    return_cached_fix()
else:
    generate_new_fix()
    cache_result()
```

---

## Configuration & Settings

**File:** [`app/config/settings.py`](app/config/settings.py)

Key configurations:

```python
# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "data" / "output"
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
QDRANT_INDEX_DIR = KNOWLEDGE_DIR / "qdrant_index"

# LLM Model
LOCAL_MODEL_PATH = r"C:\models\Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"
LLM_TEMPERATURE = 0.0  # Deterministic
LLM_MAX_TOKENS = 3500

# Retrieval
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
COLLECTION_NAME = "misra_excel_kb"
TOP_K_EXACT = 10
TOP_K_SEMANTIC = 6
RETRIEVAL_MIN_SCORE = 0.70  # Similarity threshold

# Web Server
LLAMA_HOST = "127.0.0.1"
LLAMA_PORT = 8080

# Generation limits
MAX_SOURCE_LINES = 40
MAX_KB_CHARS = 2500
```

---

## Command-Line Usage

### Run via CLI
```bash
# Basic analysis
python app/pipeline/orchestrator.py data/input/warnings.xlsx data/input/source_code/

# With custom run ID
python app/pipeline/orchestrator.py warnings.xlsx src/ --run-id my_analysis_001

# Resume from checkpoint
python app/pipeline/orchestrator.py warnings.xlsx src/ --resume 20260331_110747_4d20ca

# Skip evaluation (faster)
python app/pipeline/orchestrator.py warnings.xlsx src/ --skip-eval
```

### Start Web Server
```bash
python app/web/server.py
# Open: http://127.0.0.1:5000
```

---

## Data Flow Diagram

```
┌─────────────────────┐
│  User Browser       │
│  (Upload Form)      │
└──────────┬──────────┘
           │ POST /api/analyse
           │ (Excel + Source Files)
           ↓
┌──────────────────────────────────────┐
│  Flask Web Server                    │
│  (app/web/server.py)                 │
│  - Validates files                   │
│  - Generates job_id                  │
│  - Launches subprocess               │
└──────────┬───────────────────────────┘
           │ Spawns
           ↓
┌──────────────────────────────────────┐
│  Pipeline Orchestrator               │
│  (app/pipeline/orchestrator.py)      │
└──────────┬───────────────────────────┘
           │
    ┌──────┼──────┬──────┬──────┐
    ↓      ↓      ↓      ↓      ↓
┌───────────────────────────────────────┐
│ Phase 6a: Parse                       │
│ → parse_polyspace.py                  │
│ Output: phase_6a_parsed.json          │
└────────────┬────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│ Phase 6b: Retrieve                     │
│ → retrieve_rules.py (Qdrant query)     │
│ → retrieval_postprocessor.py (filter)  │
│ → cache_service.py (caching)           │
│ Output: phase_6b_enriched.json         │
└────────────┬────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│ Phase 7: Generate                      │
│ → generate_misra_response.py (Llama)   │
│ → response_validator.py (validate)     │
│ Output: phase_7_generated.json         │
└────────────┬────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│ Phase 8: Evaluate                      │
│ → evaluate_fixes.py (self-critique)    │
│ Output: phase_8_evaluated.json         │
└────────────┬────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│  Output & Export                       │
│  - export_pdf.py (PDF report)          │
│  - export_word.py (Word report)        │
│  - summary.json                        │
└────────────┬────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│  Results Directory                     │
│  (data/output/<job_id>/)               │
│  - All JSON outputs                    │
│  - PDF & Word reports                  │
│  - Audit trail                         │
└────────────────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│  Browser (Results Page)                │
│  GET /api/run/<job_id>/results         │
│  - Displays summary                    │
│  - Fixes grouped by severity           │
│  - Download options                    │
└────────────────────────────────────────┘
```

---

## Error Handling & Resume

### Checkpointing
Each phase saves output before proceeding. On failure or user request, the system can resume:

```bash
python orchestrator.py warnings.xlsx src/ --resume 20260331_110747_4d20ca
```

**Resume Logic:**
1. Load `phase_8_evaluated.json` from previous run
2. Extract warning IDs already processed
3. Skip generation/evaluation for completed warnings
4. Continue with remaining warnings

### Error Scenarios

| Scenario | Handling |
|----------|----------|
| Missing source file | Skip warning, log error, continue |
| Qdrant connection fails | Fallback to empty context, continue |
| LLM inference timeout | Retry with reduced context, or skip |
| Invalid JSON output | Mark as `parse_error`, continue |
| OOM during generation | Reduce batch size, retry |

---

## Performance Metrics

Typical run times (125 warnings):

| Phase | Time | Notes |
|-------|------|-------|
| **6a: Parse** | ~2s | I/O + text extraction |
| **6b: Retrieve** | ~8s | With caching, ~0.06s per warning |
| **7: Generate** | ~400s | ~3.2s per warning (Mistral 7B) |
| **8: Evaluate** | ~60s | ~0.5s per warning (verification) |
| **Total** | ~470s (~8 min) | Sequential phases |

**Optimization opportunities:**
- Batch processing in Phase 7
- GPU acceleration (n_gpu_layers > 0)
- Parallel warning processing (limited by model)
- Increased TOP_K_SEMANTIC for better retrieval

---

## Knowledge Base Initialization

### Building Qdrant Index
```bash
python scripts/build_qdrant_index.py
```

**Process:**
1. Load Excel KB: `data/knowledge/excel_kb/misra_excel_kb.json`
2. Parse MISRA rules into structured format
3. Encode each rule with BGE embeddings
4. Store vectors in Qdrant collection
5. Create index for fast retrieval

---

## Testing

### Manual Testing Scripts
- [`tests/test_phase1_ingest_manual.py`](tests/test_phase1_ingest_manual.py) — Test parsing
- [`tests/test_phase2_retrieve_manual.py`](tests/test_phase2_retrieve_manual.py) — Test retrieval
- [`scripts/test_retrieval.py`](scripts/test_retrieval.py) — Test Qdrant query
- [`scripts/test_generation.py`](scripts/test_generation.py) — Test LLM generation

### Running Tests
```bash
python tests/test_phase1_ingest_manual.py
python tests/test_phase2_retrieve_manual.py
python scripts/test_retrieval_cache.py
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/web/server.py` | Flask web server, file handling, job management |
| `app/pipeline/orchestrator.py` | Main pipeline runner, phase sequencing |
| `app/ingestion/parse_polyspace.py` | Excel parsing, code extraction |
| `app/retrieval/retrieve_rules.py` | Qdrant query + semantic search |
| `app/retrieval/retrieval_postprocessor.py` | Rule filtering & reranking |
| `app/generation/generate_misra_response.py` | LLM inference, prompt building |
| `app/generation/response_validator.py` | JSON validation, syntax checking |
| `app/pipeline/evaluate_fixes.py` | Self-critique evaluation |
| `app/config/settings.py` | Central configuration |
| `app/web/templates/index.html` | Upload form UI |
| `app/web/templates/results.html` | Results display UI |
| `app/web/static/script.js` | Frontend logic |

---

## Deployment Checklist

- [ ] Mistral 7B GGUF model downloaded and path set in `settings.py`
- [ ] Qdrant index built: `python scripts/build_qdrant_index.py`
- [ ] Excel KB file prepared: `data/knowledge/excel_kb/misra_excel_kb.json`
- [ ] Virtual environment activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Flask server tested: `python app/web/server.py`
- [ ] Web browser accessible: http://127.0.0.1:5000
- [ ] Sample Excel report + source code prepared for testing

---

## Future Enhancements

1. **Batch Processing:** Process multiple warnings in parallel LLM calls
2. **GPU Acceleration:** Configure n_gpu_layers for CUDA/Metal support
3. **Advanced Caching:** Multi-level caching (rule → rule family → domain)
4. **Integration APIs:** CI/CD pipeline integration (GitHub Actions, Jenkins)
5. **Export Formats:** Add HTML, Markdown, CSV export options
6. **Dashboard:** Real-time progress dashboard with metrics
7. **Feedback Loop:** Capture user corrections to improve model
8. **Multi-user:** Queue management for concurrent analysis runs

---

## Troubleshooting

### Model Not Found
```
FileNotFoundError: Local model file not found: C:\models\Mistral-7B...
→ Download GGUF model and update LOCAL_MODEL_PATH in settings.py
```

### Qdrant Connection Failed
```
Error: QdrantClient connection refused
→ Run: python scripts/build_qdrant_index.py (recreates index)
```

### Empty Rules Retrieved
```
0 rule(s) retrieved
→ Lower RETRIEVAL_MIN_SCORE from 0.70 to 0.50 in settings.py
→ Or rebuild Qdrant index with updated KB
```

### Memory Issues During Generation
```
CUDA out of memory / Killed process
→ Set n_gpu_layers=0 (CPU only) in GenerationConfig
→ Reduce LLM_MAX_TOKENS in settings.py
→ Process smaller batches
```

---

**Document Version:** 1.0  
**Last Updated:** April 1, 2026  
**System:** MISRA Compliance Reviewer GenAI
