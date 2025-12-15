# Invoice Processing Workflow - Strategy Document

## 📋 Deliverables Checklist

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `workflow.json` | LangGraph agent configuration with all 12 stages |
| 2 | LangGraph Implementation | Python code with nodes, state, checkpoints |
| 3 | MCP Client Integration | COMMON & ATLAS server routing |
| 4 | Bigtool Integration | Dynamic tool selection per stage |
| 5 | HITL API | `/human-review/pending` and `/human-review/decision` endpoints |
| 6 | Database Layer | Checkpoint & review queue persistence |
| 7 | Demo Run | Sample input → output with full logs |
| 8 | Demo Video | Self-intro + working solution walkthrough |

---

## 🧠 Mind Map

```
                            ┌─────────────────────────────────────────┐
                            │     INVOICE PROCESSING WORKFLOW         │
                            │           (LangGraph Agent)             │
                            └───────────────┬─────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        │                                   │                                   │
        ▼                                   ▼                                   ▼
┌───────────────┐                 ┌─────────────────┐                 ┌─────────────────┐
│  CORE ENGINE  │                 │  INTEGRATIONS   │                 │   HUMAN LAYER   │
└───────┬───────┘                 └────────┬────────┘                 └────────┬────────┘
        │                                  │                                   │
        ├── LangGraph Nodes (12)           ├── MCP Clients                     ├── Checkpoint Store
        ├── State Management               │   ├── COMMON Server               ├── Review Queue
        ├── Conditional Routing            │   └── ATLAS Server                ├── Decision API
        └── Checkpoint/Resume              │                                   └── Resume Token
                                           ├── Bigtool Picker
                                           │   ├── OCR Pool
                                           │   ├── Enrichment Pool
                                           │   ├── ERP Pool
                                           │   ├── DB Pool
                                           │   └── Email Pool
                                           │
                                           └── External Services
                                               ├── Google Vision / Tesseract
                                               ├── Clearbit / PDL
                                               └── SAP / NetSuite
```

---

## 📊 Graph Structure (Node Flow)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                  LANGGRAPH WORKFLOW                                   │
└──────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐     ┌────────────┐     ┌─────────┐     ┌──────────┐     ┌───────────────┐
    │ INTAKE  │────▶│ UNDERSTAND │────▶│ PREPARE │────▶│ RETRIEVE │────▶│ MATCH_TWO_WAY │
    │   📥    │     │     🧠     │     │   🛠️    │     │    📚    │     │      ⚖️       │
    └─────────┘     └────────────┘     └─────────┘     └──────────┘     └───────┬───────┘
                                                                                │
                                               ┌────────────────────────────────┼────────────────────┐
                                               │                                │                    │
                                               ▼                                ▼                    │
                                    ┌─────────────────────┐          ┌──────────────────┐           │
                                    │  match_score >= 0.9 │          │ match_score < 0.9│           │
                                    │      (MATCHED)      │          │    (FAILED)      │           │
                                    └──────────┬──────────┘          └────────┬─────────┘           │
                                               │                              │                      │
                                               │                              ▼                      │
                                               │                   ┌─────────────────┐              │
                                               │                   │ CHECKPOINT_HITL │              │
                                               │                   │       ⏸️        │              │
                                               │                   │  (Pause + Save) │              │
                                               │                   └────────┬────────┘              │
                                               │                            │                        │
                                               │                            ▼                        │
                                               │                   ┌─────────────────┐              │
                                               │                   │  HITL_DECISION  │              │
                                               │                   │      👨‍💼        │              │
                                               │                   └────────┬────────┘              │
                                               │                            │                        │
                                               │              ┌─────────────┴─────────────┐          │
                                               │              │                           │          │
                                               │              ▼                           ▼          │
                                               │    ┌─────────────────┐       ┌───────────────────┐ │
                                               │    │ decision=ACCEPT │       │ decision=REJECT   │ │
                                               │    └────────┬────────┘       └─────────┬─────────┘ │
                                               │             │                          │           │
                                               │             │                          ▼           │
                                               ▼             │              ┌───────────────────────┐
                                    ┌──────────────────┐     │              │    END (MANUAL)       │
                                    │    RECONCILE     │◀────┘              │ REQUIRES_MANUAL_HANDLING
                                    │       📘        │                     └───────────────────────┘
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │     APPROVE      │
                                    │       🔄        │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │     POSTING      │
                                    │       🏃        │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │      NOTIFY      │
                                    │       ✉️        │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │    COMPLETE      │
                                    │       ✅        │
                                    └──────────────────┘
```

---

## 🔧 Tool Integration Architecture

### MCP Server Routing

```
┌────────────────────────────────────────────────────────────────────┐
│                         MCP CLIENT ROUTER                          │
└────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │   COMMON SERVER   │           │   ATLAS SERVER    │
        │ (No External Data)│           │ (External Systems)│
        └─────────┬─────────┘           └─────────┬─────────┘
                  │                               │
    ┌─────────────┼─────────────┐     ┌───────────┼───────────┐
    │             │             │     │           │           │
    ▼             ▼             ▼     ▼           ▼           ▼
┌────────┐ ┌──────────┐ ┌────────┐ ┌─────┐ ┌──────────┐ ┌─────────┐
│validate│ │normalize │ │compute │ │ OCR │ │ enrich   │ │ERP fetch│
│schema  │ │vendor    │ │flags   │ │     │ │ vendor   │ │PO/GRN   │
└────────┘ └──────────┘ └────────┘ └─────┘ └──────────┘ └─────────┘
```

### Stage → Server Mapping

| Stage | COMMON Server | ATLAS Server |
|-------|---------------|--------------|
| INTAKE | ✅ validate, persist | - |
| UNDERSTAND | ✅ parse | ✅ OCR |
| PREPARE | ✅ normalize, flags | ✅ enrich |
| RETRIEVE | - | ✅ ERP fetch |
| MATCH_TWO_WAY | ✅ match engine | - |
| CHECKPOINT_HITL | ✅ DB, queue | - |
| HITL_DECISION | - | ✅ Auth |
| RECONCILE | ✅ accounting | - |
| APPROVE | - | ✅ workflow |
| POSTING | - | ✅ ERP post |
| NOTIFY | - | ✅ email/slack |
| COMPLETE | ✅ audit log | - |

---

## 🎯 Bigtool Integration Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BIGTOOL PICKER                                │
│                    BigtoolPicker.select(capability, context)            │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  OCR POOL    │ │ ENRICHMENT   │ │ ERP CONNECTOR│ │  DB POOL     │ │ EMAIL POOL   │
│              │ │    POOL      │ │    POOL      │ │              │ │              │
├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤ ├──────────────┤
│google_vision │ │ clearbit     │ │ sap_sandbox  │ │ postgres     │ │ sendgrid     │
│tesseract     │ │ people_data  │ │ netsuite     │ │ sqlite       │ │ smartlead    │
│aws_textract  │ │ vendor_db    │ │ mock_erp     │ │ dynamodb     │ │ ses          │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
      ▲                ▲                ▲                ▲                ▲
      │                │                │                │                │
  UNDERSTAND       PREPARE          RETRIEVE         CHECKPOINT        NOTIFY
                                    POSTING          COMPLETE
```

### Selection Logic

```python
def select_tool(capability: str, context: dict) -> str:
    """
    Bigtool selection based on:
    1. Availability (health check)
    2. Cost optimization
    3. Context requirements (file type, size, etc.)
    4. Fallback chain
    """
    pools = {
        "ocr": ["google_vision", "aws_textract", "tesseract"],
        "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
        "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
        "db": ["postgres", "sqlite", "dynamodb"],
        "email": ["sendgrid", "ses", "smartlead"]
    }
    # Selection algorithm with fallback
```

---

## 💾 State Schema

```python
class InvoiceWorkflowState(TypedDict):
    # Input
    invoice_payload: dict
    
    # INTAKE output
    raw_id: str
    ingest_ts: str
    validated: bool
    
    # UNDERSTAND output
    parsed_invoice: dict
    
    # PREPARE output
    vendor_profile: dict
    normalized_invoice: dict
    flags: dict
    
    # RETRIEVE output
    matched_pos: list
    matched_grns: list
    history: list
    
    # MATCH_TWO_WAY output
    match_score: float
    match_result: str  # "MATCHED" | "FAILED"
    
    # CHECKPOINT_HITL output
    checkpoint_id: Optional[str]
    review_url: Optional[str]
    paused_reason: Optional[str]
    
    # HITL_DECISION output
    human_decision: Optional[str]  # "ACCEPT" | "REJECT"
    reviewer_id: Optional[str]
    resume_token: Optional[str]
    
    # RECONCILE output
    accounting_entries: list
    reconciliation_report: dict
    
    # APPROVE output
    approval_status: str
    approver_id: Optional[str]
    
    # POSTING output
    posted: bool
    erp_txn_id: str
    scheduled_payment_id: str
    
    # NOTIFY output
    notify_status: dict
    notified_parties: list
    
    # COMPLETE output
    final_payload: dict
    audit_log: list
    status: str  # "COMPLETED" | "REQUIRES_MANUAL_HANDLING"
    
    # Workflow metadata
    current_stage: str
    bigtool_selections: dict  # Track which tools were selected
    error_log: list
```

---

## 🔄 HITL Checkpoint Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HITL FLOW DETAIL                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. MATCH_TWO_WAY returns match_score < 0.9
              │
              ▼
2. CHECKPOINT_HITL node triggered
   ┌──────────────────────────────────────┐
   │ • Serialize full workflow state      │
   │ • Store in checkpoints table         │
   │ • Create review ticket               │
   │ • Push to human_review_queue         │
   │ • Generate review_url                │
   │ • Set workflow status = PAUSED       │
   └──────────────────────────────────────┘
              │
              ▼
3. Workflow PAUSES (LangGraph interrupt)
              │
              ▼
4. Human accesses review_url
   ┌──────────────────────────────────────┐
   │ GET /human-review/pending            │
   │ • Lists all pending reviews          │
   │ • Shows invoice details              │
   │ • Shows match evidence               │
   └──────────────────────────────────────┘
              │
              ▼
5. Human makes decision
   ┌──────────────────────────────────────┐
   │ POST /human-review/decision          │
   │ {                                    │
   │   "checkpoint_id": "...",            │
   │   "decision": "ACCEPT" | "REJECT",   │
   │   "notes": "...",                    │
   │   "reviewer_id": "..."               │
   │ }                                    │
   └──────────────────────────────────────┘
              │
              ▼
6. HITL_DECISION node processes
              │
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
 ACCEPT              REJECT
    │                   │
    ▼                   ▼
 Resume at         Finalize with
 RECONCILE         MANUAL_HANDOFF
```

---

## 📁 Project Structure

```
Invoice-Processing-Workflow/
├── docs/
│   └── STRATEGY.md              # This document
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── workflow.py          # LangGraph definition
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── intake.py
│   │   │   ├── understand.py
│   │   │   ├── prepare.py
│   │   │   ├── retrieve.py
│   │   │   ├── match.py
│   │   │   ├── checkpoint.py
│   │   │   ├── hitl_decision.py
│   │   │   ├── reconcile.py
│   │   │   ├── approve.py
│   │   │   ├── posting.py
│   │   │   ├── notify.py
│   │   │   └── complete.py
│   │   └── state.py             # State schema
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── router.py            # MCP client router
│   │   ├── common_server.py     # COMMON server client
│   │   └── atlas_server.py      # ATLAS server client
│   ├── bigtool/
│   │   ├── __init__.py
│   │   ├── picker.py            # Bigtool selection logic
│   │   └── pools/
│   │       ├── ocr.py
│   │       ├── enrichment.py
│   │       ├── erp.py
│   │       ├── db.py
│   │       └── email.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy models
│   │   └── checkpoint_store.py  # LangGraph checkpoint store
│   └── api/
│       ├── __init__.py
│       ├── app.py               # FastAPI app
│       └── routes/
│           ├── invoice.py       # Invoice submission
│           └── human_review.py  # HITL endpoints
├── config/
│   ├── workflow.json            # Workflow configuration
│   └── tools.yaml               # Tool pool configuration
├── tests/
│   ├── test_workflow.py
│   ├── test_nodes.py
│   └── sample_invoice.json
├── requirements.txt
├── README.md
└── demo.db                      # SQLite for demo
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Day 1-2)
- [ ] Set up project structure
- [ ] Define state schema
- [ ] Create database models
- [ ] Implement checkpoint store

### Phase 2: Core Nodes (Day 2-3)
- [ ] Implement all 12 nodes
- [ ] Add state transitions
- [ ] Build LangGraph workflow

### Phase 3: Integrations (Day 3-4)
- [ ] MCP client router
- [ ] Bigtool picker
- [ ] Mock tool implementations

### Phase 4: HITL Flow (Day 4-5)
- [ ] Checkpoint/resume logic
- [ ] Human review API
- [ ] Frontend integration points

### Phase 5: Demo & Polish (Day 5-6)
- [ ] End-to-end testing
- [ ] Logging improvements
- [ ] Demo video recording
- [ ] Documentation

---

## 🎬 Demo Scenario

**Input:** Invoice from "Acme Corp" for $15,000 with PO reference

**Flow:**
1. INTAKE → Validates and persists
2. UNDERSTAND → OCR (Bigtool selects google_vision)
3. PREPARE → Enriches vendor (Bigtool selects clearbit)
4. RETRIEVE → Fetches PO from ERP (Bigtool selects mock_erp)
5. MATCH_TWO_WAY → Score = 0.85 (below 0.90 threshold) ❌
6. CHECKPOINT_HITL → Creates review ticket, pauses
7. Human reviews → ACCEPTS
8. HITL_DECISION → Resumes workflow
9. RECONCILE → Creates accounting entries
10. APPROVE → Auto-approved (under $50k threshold)
11. POSTING → Posts to ERP, schedules payment
12. NOTIFY → Sends confirmation emails
13. COMPLETE → Final payload with full audit log

**Expected Logs:**
```
[2024-XX-XX] INTAKE: Validated invoice INV-001, raw_id=abc123
[2024-XX-XX] BIGTOOL: Selected google_vision for OCR
[2024-XX-XX] UNDERSTAND: Parsed 5 line items, detected PO-456
[2024-XX-XX] BIGTOOL: Selected clearbit for enrichment
[2024-XX-XX] PREPARE: Vendor enriched, risk_score=0.2
[2024-XX-XX] BIGTOOL: Selected mock_erp for ERP
[2024-XX-XX] RETRIEVE: Found PO-456, 2 GRNs
[2024-XX-XX] MATCH_TWO_WAY: Score=0.85, result=FAILED
[2024-XX-XX] CHECKPOINT_HITL: Created checkpoint cp-789, PAUSED
[2024-XX-XX] HITL_DECISION: Human ACCEPTED, resuming...
[2024-XX-XX] RECONCILE: Created 4 accounting entries
[2024-XX-XX] APPROVE: Auto-approved (amount < threshold)
[2024-XX-XX] POSTING: Posted to ERP, txn=TXN-001
[2024-XX-XX] NOTIFY: Notified vendor@acme.com, finance@company.com
[2024-XX-XX] COMPLETE: Workflow finished, status=COMPLETED
```

---

## 🔧 Bigtool Implementation Strategy (DETAILED)

### Do We Need to Implement Bigtool?

**YES** - But as a **mock/abstraction layer**. The task requires:

1. ✅ **Demonstrate tool selection logic** - Show how tools are picked dynamically
2. ✅ **Log tool selections** - Record which tool was chosen and why
3. ✅ **Fallback mechanism** - Handle when primary tool is unavailable
4. ❌ **NOT required** - Actual integrations with Google Vision, Clearbit, SAP (use mocks)

### What Bigtool Actually Does

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BIGTOOL PICKER FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

  Stage (e.g., UNDERSTAND)
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  BigtoolPicker.select(capability="ocr", context={...})          │
  │                                                                  │
  │  1. Look up pool for "ocr" capability                           │
  │     pool = ["google_vision", "aws_textract", "tesseract"]       │
  │                                                                  │
  │  2. Apply selection criteria:                                   │
  │     • Availability check (is tool healthy?)                     │
  │     • Context match (file type, size)                           │
  │     • Cost optimization (prefer cheaper if quality same)        │
  │     • Priority order (first available wins)                     │
  │                                                                  │
  │  3. Return selected tool + log the decision                     │
  └─────────────────────────────────────────────────────────────────┘
           │
           ▼
  Selected: "google_vision" → Execute mock OCR function
```

### Implementation Approach (Mock Layer)

```python
# This is what we implement - NO real API calls needed

class BigtoolPicker:
    """
    Mock Bigtool implementation that simulates tool selection.
    Real implementation would have health checks, API calls, etc.
    """
    
    POOLS = {
        "ocr": ["google_vision", "aws_textract", "tesseract"],
        "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
        "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
        "db": ["postgres", "sqlite", "dynamodb"],
        "email": ["sendgrid", "ses", "smartlead"],
        "storage": ["s3", "gcs", "local_fs"]
    }
    
    # Simulated availability (in real system, this would be health checks)
    AVAILABILITY = {
        "google_vision": True,
        "aws_textract": True,
        "tesseract": True,
        "clearbit": True,
        "people_data_labs": False,  # Simulate unavailable
        "vendor_db": True,
        "sap_sandbox": False,  # Simulate unavailable
        "netsuite": True,
        "mock_erp": True,  # Always available for demo
        "postgres": True,
        "sqlite": True,  # Default for demo
        "dynamodb": False,
        "sendgrid": True,
        "ses": True,
        "smartlead": False,
        "s3": True,
        "gcs": True,
        "local_fs": True
    }
    
    @classmethod
    def select(cls, capability: str, context: dict = None) -> dict:
        """
        Select best available tool for given capability.
        
        Returns:
            {
                "selected_tool": "google_vision",
                "capability": "ocr",
                "reason": "First available in priority order",
                "fallback_chain": ["aws_textract", "tesseract"]
            }
        """
        pool = cls.POOLS.get(capability, [])
        
        for tool in pool:
            if cls.AVAILABILITY.get(tool, False):
                return {
                    "selected_tool": tool,
                    "capability": capability,
                    "reason": f"Selected {tool} - first available in pool",
                    "fallback_chain": [t for t in pool if t != tool]
                }
        
        # No tool available - return mock fallback
        return {
            "selected_tool": f"mock_{capability}",
            "capability": capability,
            "reason": "All tools unavailable, using mock",
            "fallback_chain": []
        }
```

---

## 🔀 Routing Architecture (DETAILED)

### Two-Layer Routing System

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ROUTING LAYERS                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   LAYER 1: MCP Router (Which Server?)                                          │
│   ─────────────────────────────────────                                         │
│   • Decides: COMMON Server vs ATLAS Server                                      │
│   • Based on: Does ability need external data?                                  │
│                                                                                 │
│   LAYER 2: Bigtool Picker (Which Tool?)                                         │
│   ─────────────────────────────────────                                         │
│   • Decides: Which specific tool from the pool                                  │
│   • Based on: Availability, context, cost                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Visual Routing Flow

```
   Invoice arrives at UNDERSTAND stage
                    │
                    ▼
  ┌────────────────────────────────────────┐
  │         MCP ROUTER (Layer 1)           │
  │                                        │
  │  Q: Does OCR need external system?     │
  │  A: YES → Route to ATLAS Server        │
  └────────────────┬───────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────────────┐
   │         ATLAS SERVER                   │
   │                                        │
   │  Receives: execute_ocr(attachments)    │
   └────────────────┬───────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────────────┐
   │      BIGTOOL PICKER (Layer 2)          │
   │                                        │
   │  BigtoolPicker.select("ocr", context)  │
   │  Pool: [google_vision, textract, ...]  │
   │  Selected: google_vision ✓             │
   └────────────────┬───────────────────────┘
                    │
                    ▼
   ┌────────────────────────────────────────┐
   │      MOCK TOOL EXECUTION               │
   │                                        │
   │  mock_google_vision(attachments)       │
   │  Returns: { extracted_text: "..." }    │
   └────────────────────────────────────────┘
```

### Server Routing Rules

```python
class MCPRouter:
    """
    Routes abilities to appropriate MCP server.
    
    COMMON Server: Internal operations, no external API calls
    ATLAS Server: External system integrations
    """
    
    ROUTING_TABLE = {
        # COMMON Server abilities (internal only)
        "validate_schema": "COMMON",
        "persist_invoice": "COMMON",
        "parse_line_items": "COMMON",
        "normalize_vendor": "COMMON",
        "compute_flags": "COMMON",
        "compute_match_score": "COMMON",
        "create_checkpoint": "COMMON",
        "build_accounting_entries": "COMMON",
        "create_audit_log": "COMMON",
        
        # ATLAS Server abilities (external systems)
        "ocr_extract": "ATLAS",
        "enrich_vendor": "ATLAS",
        "fetch_po": "ATLAS",
        "fetch_grn": "ATLAS",
        "fetch_history": "ATLAS",
        "post_to_erp": "ATLAS",
        "schedule_payment": "ATLAS",
        "send_email": "ATLAS",
        "send_slack": "ATLAS",
        "authenticate_user": "ATLAS"
    }
    
    @classmethod
    def route(cls, ability: str) -> str:
        """Returns which server handles this ability."""
        return cls.ROUTING_TABLE.get(ability, "COMMON")
```

### Complete Routing Example (UNDERSTAND Stage)

```
UNDERSTAND Stage Execution:
═══════════════════════════

Step 1: Stage has 2 abilities
        ├── ocr_extract (needs OCR service)
        └── parse_line_items (internal parsing)

Step 2: Route ocr_extract
        │
        ├── MCPRouter.route("ocr_extract") → "ATLAS"
        │
        └── AtlasServer.execute("ocr_extract", attachments)
                │
                ├── BigtoolPicker.select("ocr", context)
                │   └── Returns: google_vision
                │
                └── MockOCR.google_vision(attachments)
                    └── Returns: {"text": "Invoice #123..."}

Step 3: Route parse_line_items
        │
        ├── MCPRouter.route("parse_line_items") → "COMMON"
        │
        └── CommonServer.execute("parse_line_items", ocr_text)
                │
                └── Returns: {"line_items": [...], "po_refs": [...]}

Step 4: Combine results → Update state → Next stage
```

---

## 🖥️ MCP Server Implementation (Live Servers)

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MCP SERVER ARCHITECTURE                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
  │   FastAPI App   │         │  COMMON SERVER  │         │  ATLAS SERVER   │
  │   (Port 8000)   │         │  (Port 8001)    │         │  (Port 8002)    │
  └────────┬────────┘         └────────┬────────┘         └────────┬────────┘
           │                           │                           │
           │      MCP Protocol         │      MCP Protocol         │
           │◄─────────────────────────►│◄─────────────────────────►│
           │                           │                           │
           │                  ┌────────┴────────┐         ┌────────┴────────┐
           │                  │     TOOLS       │         │     TOOLS       │
           │                  ├─────────────────┤         ├─────────────────┤
           │                  │ validate_schema │         │ ocr_extract     │
           │                  │ persist_invoice │         │ enrich_vendor   │
           │                  │ normalize_vendor│         │ fetch_po        │
           │                  │ compute_flags   │         │ fetch_grn       │
           │                  │ compute_match   │         │ post_to_erp     │
           │                  │ build_entries   │         │ send_email      │
           │                  │ create_audit    │         │ send_slack      │
           │                  └─────────────────┘         └─────────────────┘
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         LANGGRAPH WORKFLOW                              │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
  │  │  INTAKE  │─▶│UNDERSTAND│─▶│ PREPARE  │─▶│ RETRIEVE │─▶│  MATCH   │  │
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
  │       │              │             │             │             │        │
  │       ▼              ▼             ▼             ▼             ▼        │
  │   [COMMON]      [ATLAS+COMMON] [ATLAS+COMMON]  [ATLAS]      [COMMON]   │
  └─────────────────────────────────────────────────────────────────────────┘
```

### Startup Sequence

```
1. Start COMMON Server (Port 8001)
   └── Registers tools: validate_schema, persist_invoice, etc.

2. Start ATLAS Server (Port 8002)
   └── Registers tools: ocr_extract, enrich_vendor, etc.

3. Start FastAPI App (Port 8000)
   └── Connects to COMMON & ATLAS as MCP clients
   └── Exposes /invoice/submit, /human-review/* endpoints

4. Agent Workflow Execution
   └── Nodes call MCP Router → Routes to appropriate server
   └── Server executes tool → Returns result
```

---

## 🔧 What We Actually Build

### Option A: Using MCP SDK (Recommended)

We use the official **Model Context Protocol SDK** to create proper MCP servers.

### Option B: Simplified HTTP-based MCP (For Demo)

We create FastAPI-based "MCP-like" servers that expose tools via HTTP endpoints.

**We'll implement Option B** for simplicity while following MCP patterns.

---
