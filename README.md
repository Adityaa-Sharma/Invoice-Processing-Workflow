# Invoice Processing Workflow

LangGraph-based invoice processing with **HITL checkpoint/resume**, **MCP server routing**, and **Bigtool dynamic tool selection**.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│ MCP Servers  │
│   (React)    │ SSE │  (FastAPI)   │     │ COMMON/ATLAS │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                     ┌──────┴──────┐
                     │  LangGraph  │
                     │  Workflow   │
                     └─────────────┘
```

## Quick Start

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
uvicorn src.main:app --port 8000 --reload

# 2. MCP Servers (separate terminals)
uvicorn src.mcp.common_server:app --port 8001
uvicorn src.mcp.atlas_server:app --port 8002

# 3. Frontend
cd frontend
npm install && npm run dev
```

**Access:** http://localhost:5173 (Frontend) | http://localhost:8000/docs (API)

## Workflow Stages

| # | Stage | Server | Description |
|---|-------|--------|-------------|
| 1 | INTAKE | COMMON | Validate schema, persist invoice |
| 2 | UNDERSTAND | ATLAS | OCR extraction, parse line items |
| 3 | PREPARE | ATLAS | Normalize & enrich vendor |
| 4 | RETRIEVE | ATLAS | Fetch PO/GRN from ERP |
| 5 | MATCH_TWO_WAY | COMMON | 2-way match (Invoice ↔ PO) |
| 6 | CHECKPOINT_HITL | COMMON | Create checkpoint if match < threshold |
| 7 | HITL_DECISION | — | Human ACCEPT/REJECT (interrupt) |
| 8 | RECONCILE | COMMON | Build accounting entries |
| 9 | APPROVE | COMMON | Apply approval policy |
| 10 | POSTING | ATLAS | Post to ERP, schedule payment |
| 11 | NOTIFY | ATLAS | Notify vendor & finance |
| 12 | COMPLETE | COMMON | Finalize workflow |

## Key Features

### HITL Checkpoint/Resume
- Uses LangGraph's `interrupt()` for clean pause
- Checkpoint stored in DB + Human Review queue
- Resume via API with ACCEPT/REJECT decision

### MCP Server Routing
- **COMMON** (port 8001): Internal ops (validation, matching, accounting)
- **ATLAS** (port 8002): External ops (OCR, ERP, notifications)

### Bigtool Dynamic Selection
LLM-based tool selection from capability pools:

| Capability | Tools |
|------------|-------|
| OCR | google_vision, aws_textract, tesseract |
| Enrichment | clearbit, pdl, vendor_db |
| ERP | sap, netsuite, mock_erp |

## API Endpoints

```bash
# Submit invoice
POST /invoice/submit

# Check status
GET /invoice/status/{thread_id}

# Human review
GET /human-review/pending
POST /human-review/decision

# SSE events
GET /events/workflow/{thread_id}
```

## Project Structure

```
backend/
├── src/
│   ├── agents/          # 12 stage agents
│   ├── graph/           # LangGraph workflow
│   ├── mcp/             # COMMON & ATLAS servers
│   ├── tools/           # Bigtool picker
│   └── api/             # FastAPI routes
├── config/
│   └── workflow.json    # Workflow configuration
└── demo/                # Demo scripts

frontend/
└── src/
    ├── components/      # React components
    └── hooks/           # useWorkflow SSE hook
```

## Configuration

Key settings in `backend/src/config/settings.py`:

```python
MATCH_THRESHOLD = 0.90      # Below this → HITL
TWO_WAY_TOLERANCE_PCT = 5.0 # Amount tolerance
LLM_PROVIDER = "groq"       # LLM for Bigtool
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## Tech Stack

- **LangGraph** - Workflow orchestration with checkpoints ([config](./config/workflow.json))
- **FastAPI** - REST API + SSE
- **React + TypeScript** - Frontend UI
- **Groq (Llama 3.1)** - LLM for Bigtool selection
- **SQLite** - Checkpoint storage

## Deliverables

✅ LangGraph workflow with 12 stages  
✅ HITL checkpoint/resume with `interrupt()`  
✅ MCP server integration (COMMON + ATLAS)  
✅ Bigtool dynamic tool selection  
✅ Real-time SSE event streaming  
✅ React frontend with workflow visualization  
✅ Human review UI  

## License

MIT
