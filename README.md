# Invoice Processing Workflow

A LangGraph-based workflow for automated invoice processing with Human-in-the-Loop (HITL) checkpoint/resume, Bigtool dynamic tool selection, and MCP server routing.

## 🌟 Features

- **12 Sequential Processing Stages**: INTAKE → UNDERSTAND → PREPARE → RETRIEVE → MATCH → CHECKPOINT → HITL → RECONCILE → APPROVE → POSTING → NOTIFY → COMPLETE
- **Human-in-the-Loop (HITL)**: Automatic checkpoint when matching fails, with API for human review and resume
- **Bigtool Integration**: Dynamic tool selection from capability pools (OCR, enrichment, ERP, DB, email, storage)
- **MCP Server Routing**: Abilities routed to COMMON (internal) or ATLAS (external) servers
- **State Persistence**: LangGraph checkpoint store for workflow pause/resume
- **Structured Audit Logging**: Complete audit trail of all processing actions

## 📁 Project Structure

```
Invoice-Processing-Workflow/
├── backend/
│   ├── src/
│   │   ├── agents/          # 12 Agent classes (one per stage)
│   │   ├── api/             # FastAPI routes
│   │   ├── config/          # Settings and workflow config
│   │   ├── db/              # Database models and checkpoint store
│   │   ├── graph/           # LangGraph workflow definition
│   │   ├── schemas/         # Pydantic models
│   │   ├── tools/           # Bigtool and MCP integration
│   │   ├── utils/           # Logging and utilities
│   │   └── main.py          # FastAPI application
│   ├── tests/               # Pytest test suite
│   ├── demo/                # Demo scripts
│   └── requirements.txt
├── config/
│   ├── workflow.json        # Workflow configuration
│   └── tools.yaml           # Bigtool pool configuration
└── docs/                    # Documentation
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the API Server

```bash
cd backend
uvicorn src.main:app --reload
```

### 3. Access API Documentation

Open http://localhost:8000/docs for Swagger UI.

### 4. Run Demo Script

```bash
cd backend
python -m demo.run_demo
```

## 🔌 API Endpoints

### Invoice Submission

```bash
POST /invoice/submit
```

Submit an invoice for processing:

```json
{
  "invoice_id": "INV-2024-001",
  "vendor_name": "Acme Corp",
  "vendor_tax_id": "TAX-123456",
  "invoice_date": "2024-01-15",
  "due_date": "2024-02-15",
  "amount": 15000.0,
  "currency": "USD",
  "line_items": [
    {"desc": "Software License", "qty": 5, "unit_price": 1000.0, "total": 5000.0}
  ],
  "attachments": ["invoice.pdf"]
}
```

Response includes `thread_id` for tracking.

### Check Status

```bash
GET /invoice/status/{thread_id}
```

### Human Review (HITL)

Get pending reviews:
```bash
GET /human-review/pending
```

Submit decision:
```bash
POST /human-review/decision
{
  "thread_id": "abc123",
  "checkpoint_id": "CHKPT-XYZ",
  "decision": "ACCEPT",
  "notes": "Verified with vendor",
  "reviewer_id": "admin-001"
}
```

### Workflow Status

```bash
GET /workflow/stages         # List all stages
GET /workflow/status/{id}    # Detailed workflow status
GET /workflow/all            # List all workflows
```

## 🔄 Workflow Stages

| Stage | Mode | Description |
|-------|------|-------------|
| INTAKE | Deterministic | Validate and persist invoice |
| UNDERSTAND | Deterministic | OCR and parse line items |
| PREPARE | Deterministic | Normalize vendor, enrich data |
| RETRIEVE | Deterministic | Fetch POs/GRNs from ERP |
| MATCH_TWO_WAY | Deterministic | 2-way match invoice vs PO |
| CHECKPOINT_HITL | Deterministic | Create checkpoint if match fails |
| HITL_DECISION | Non-Deterministic | Wait for human decision |
| RECONCILE | Deterministic | Build accounting entries |
| APPROVE | Deterministic | Apply approval policy |
| POSTING | Deterministic | Post to ERP, schedule payment |
| NOTIFY | Deterministic | Notify vendor and finance team |
| COMPLETE | Deterministic | Finalize and output result |

## 🔧 Bigtool Integration

Dynamic tool selection from capability pools:

| Capability | Tools |
|------------|-------|
| OCR | google_vision, aws_textract, tesseract |
| Enrichment | clearbit, people_data_labs, vendor_db |
| ERP | sap_sandbox, netsuite, mock_erp |
| Database | postgres, sqlite, dynamodb |
| Email | sendgrid, ses, smartlead |
| Storage | s3, gcs, local_fs |

## 🌐 MCP Server Routing

### COMMON Server (Internal)
- validate_schema
- persist_raw
- parse_line_items
- normalize_vendor
- match_engine
- build_accounting_entries

### ATLAS Server (External)
- ocr_extract
- enrich_vendor
- fetch_po/grn
- post_to_erp
- send_email

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

## 📊 Demo Flow

1. **Submit Invoice** → INTAKE validates and persists
2. **OCR Processing** → UNDERSTAND extracts text
3. **Vendor Enrichment** → PREPARE normalizes and enriches
4. **ERP Fetch** → RETRIEVE gets POs and GRNs
5. **Matching** → MATCH_TWO_WAY computes score
   - If score ≥ 0.90 → Continue to RECONCILE
   - If score < 0.90 → CHECKPOINT_HITL → HITL_DECISION
6. **Human Review** (if needed) → ACCEPT/REJECT
7. **Completion** → RECONCILE → APPROVE → POSTING → NOTIFY → COMPLETE

## 📝 Configuration

### Environment Variables

```env
DATABASE_URL=sqlite:///./demo.db
MATCH_THRESHOLD=0.90
TWO_WAY_TOLERANCE_PCT=5.0
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### Workflow Configuration

See `config/workflow.json` for full stage definitions.

## 📚 Documentation

- [Strategy Document](docs/STRATEGY.md)
- [Coding Rules](docs/CODING_RULES.md)
- [Architecture Diagram](docs/ARCHITECTURE_DIAGRAM.md)
- [Implementation Notes](docs/IMPLEMENTATION_NOTES.md)

## 🛠️ Technology Stack

- **LangGraph**: Workflow orchestration with state management
- **FastAPI**: REST API framework
- **SQLAlchemy**: Database ORM
- **Pydantic**: Data validation and schemas
- **SQLite**: Default database (configurable)

## 📄 License

MIT License
