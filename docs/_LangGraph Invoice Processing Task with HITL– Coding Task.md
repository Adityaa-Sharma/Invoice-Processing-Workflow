# **Lang Graph Agent – Coding Task (Invoice Processing Workflow)**

## **Task Overview**

Use **vibe coding** — leverage AI coding assistants (Cursor, Claude, GitHub Copilot, etc.) to write most of the code. You must **review, test, and validate** AI-generated code so it works end-to-end. We highly encourage AI-assisted development.

You are required to design and implement a **Lang Graph Agent** that models an **Invoice Processing workflow** as a graph of sequential stages.

Each stage represents a clearly defined step in the workflow, and the agent must **persist and pass state variables across stages**, including storing data at **checkpoint states** and resuming execution after **Human-In-The-Loop (HITL)** decisions.

The agent must support:

* **Deterministic stages** (executed one after another)

* **Non-deterministic stages** (dynamic logic based on context)

* **HITL Checkpoints** (pause workflow → human review → resume)

* **Integration with MCP Clients** (to access ATLAS or COMMON servers for ability execution)

* **Bigtool** (to dynamically select tools from a tool pool for OCR, Enrichment, ERP access, etc.)

The goal is to implement a full **invoice-processing workflow** using Lang Graph, mapping multiple stages with abilities, and demonstrating:  
 ➡️ reasoning,  
 ➡️ state management,  
 ➡️ checkpoint & resume,  
 ➡️ HITL routing,  
 ➡️ Bigtool-based tool selection,  
 ➡️ MCP client orchestration.

---

# 

# **Agent Capabilities**

## **🧩 Graph Orchestration Agent (Lang Graph)**

Your agent must:

* Represent each workflow stage as a **node** with persistent state

* Execute **deterministic nodes sequentially**

* Execute **non-deterministic nodes** by choosing abilities at runtime

* Route abilities through MCP clients to:

  * **COMMON Server** → abilities requiring no external data

  * **ATLAS Server** → abilities requiring external system interaction (ERP, enrichment services)

* Support **checkpoint-based execution** using LangGraph’s native `checkpoints` feature

* Store checkpoint state in DB so it appears under the **Human Review tab** in the app

* Resume workflow execution from the checkpoint after human action

  ---

  # **🧩 Invoice Processing Agent Flow (New Workflow)**

Implement the following stages as LangGraph nodes:

---

### **1\. INTAKE 📥 – accept\_invoice\_payload (Deterministic)**

* Accept invoice payload (raw data \+ attachments)

* Validate schema

* Persist raw invoice

**Servers:** COMMON

---

### **2\. UNDERSTAND 🧠 – ocr\_extract, parse\_line\_items (Deterministic)**

* Run OCR on invoice attachments

* Parse line items, amounts, PO references

**Servers:**

* OCR via ATLAS (external)

* Parsing via COMMON

Bigtool must select OCR provider (Google Vision / Tesseract / AWS Textract).

---

### **3\. PREPARE 🛠️ – normalize\_vendor, enrich\_vendor, compute\_flags (Deterministic)**

* Normalize vendor name

* Enrich vendor data (PAN/GST/TaxID), credit score, risk score

* Compute validation flags

**Servers:**

* COMMON: normalize\_vendor, compute\_flags

* ATLAS: enrich\_vendor

Bigtool chooses the enrichment tool (Clearbit / PDL / Vendor DB).

---

### **4\. RETRIEVE 📚 – fetch\_po, fetch\_grn, fetch\_history (Deterministic)**

* Fetch Purchase Orders

* Fetch Goods Received Notes

* Fetch historical invoices

**Servers:** ATLAS (ERP connector)

Bigtool chooses ERP connector tool.

---

### **5\. MATCH\_TWO\_WAY ⚖️ – compute\_match\_score (Deterministic)**

* Perform **2-way matching**: Invoice vs PO

* Compute match\_score (0–1)

* If **match\_score \< threshold** → mark for **HITL CHECKPOINT**

**Servers:** COMMON

---

### **6\. CHECKPOINT\_HITL ⏸️ – save\_state\_for\_human\_review (Deterministic)**

Triggered **ONLY IF** matching fails.

This stage must:

* Create a **LangGraph Checkpoint**

* Persist full workflow state to DB

* Add entry into **Human Review queue**

* Generate a `review_url` for the reviewer

* Pause execution (`PAUSED` state)

**Servers:** COMMON  
 Bigtool selects DB tool (Postgres / SQLite / Dynamo etc.)

---

### **7\. HITL\_DECISION 👨‍💼 – accept\_or\_reject\_invoice (Non-Deterministic)**

Executed when a human acts on the review UI.

Your job:

* Read stored checkpoint state

* Get reviewer decision (`ACCEPT` / `REJECT`)

* If **ACCEPT** → resume workflow at the next node (RECONCILE)

* If **REJECT** → finalize workflow with status `REQUIRES_MANUAL_HANDLING`

**Servers:** ATLAS

---

### **8\. RECONCILE 📘 – build\_accounting\_entries (Deterministic)**

* Reconstruct accounting entries

* Build payable/receivable ledger entries

**Servers:** COMMON

---

### **9\. APPROVE 🔄 – apply\_invoice\_approval\_policy (Deterministic)**

* Auto-approve or escalate based on invoice amount \+ rules

**Servers:** ATLAS (if integration needed)

---

### **10\. POSTING 🏃 – post\_to\_erp, schedule\_payment (Deterministic)**

* Post entries to ERP/AP

* Schedule payment

**Servers:** ATLAS

---

### **11\. NOTIFY ✉️ – notify\_vendor, notify\_finance\_team (Deterministic)**

* Notify vendor and internal team

**Servers:** ATLAS

---

### **12\. COMPLETE ✅ – output\_final\_payload (Deterministic)**

* Produce final structured payload

* Output logs

* Mark workflow complete

**Servers:** COMMON

---

# **🧠 Prompt Template (Agent Personality)**

You are **Langie – the Invoice Processing LangGraph Agent**.

You think in structured stages.  
 Each node is a well-defined processing phase.  
 You always carry forward **state variables** between nodes.  
 You know when to execute deterministic steps and when to choose dynamically.  
 You orchestrate MCP clients to call **COMMON** or **ATLAS** abilities as required.  
 You use **Bigtool** whenever a tool must be selected from a pool.  
 You log every decision, every tool choice, and every state update.  
 You always produce clean structured output.

---

# **✅ Expected Deliverables**

### **1\. LangGraph Agent Config (JSON)**

Must include:

* Input workflow.json schema: Check sample in APPENDIX-1.

* Stages definition with mode: deterministic / non-deterministic

* Ability → MCP server mapping (COMMON or ATLAS)

* Bigtool configuration for choosing OCR/Enrichment/ERP tools

* HITL logic: checkpoint creation, pause, resume

  ---

  ### **2\. Working LangGraph Implementation**

Your implementation must:

* Build lang graph based on the workflow.json input.  
* Execute all stages in order

* Persist and pass state across nodes

* Create & store checkpoints on matching failure

* Expose an API for human review (accept/reject)

* Resume workflow after HITL decision

* Show Bigtool tool selections per stage

* Integrate with MCP Clients for ability execution

  ---

  ### **3\. Demo Run**

Provide:

* **Input:** Sample invoice JSON

* **Output:** Final structured payload after all stages

* **Logs:**

  * Stage-by-stage execution

  * Ability calls

  * Bigtool selections

  * Checkpoint creation

  * Human resume event

  ---

  # **🛠️ Recommended Steps**

* **Stage Modeling:** Define all 12 stages in LangGraph

* **State Management:** Persist state across stages \+ DB checkpoints

* **Checkpointing:** Integrate LangGraph checkpoint store \+ DB

* **HITL Flow:** Pause workflow → store for human review → resume

* **MCP Integration:** Route abilities to COMMON/ATLAS servers

* **Bigtool Integration:** Implement tool selection

* **Validation:** Run full workflow and show logs

# **📦 Method of Submission**

### **Submission Checklist**

* GitHub repo with full LangGraph implementation \+ config

* Latest resume attached

* Must have **Demo video** link on onedrive or google drive etc:

  * Self introduction \-1 min

  * Demo of working solution from frontend UI app, execution logs etc (**must speak and explain in English**). \-4 min

### **📧 Send to:**

**santosh.thota@analytos.ai**

**Cc:**  
 shashwat.shlok@analytos.ai  
gaurav.gupta@analytos.ai

**Subject:**  
 **LangGraph Invoice Processing Task with HITL – \<Your Name\>**

---

# **🔥 ALL THE BEST\!**

We’re excited to see how you leverage **LangGraph \+ MCP \+ HITL \+ Bigtool** to build a truly autonomous, resilient, human-guided invoice processing agent.

---

# **📎 Appendix-1**

{

  "version": "1.0",

  "workflow\_name": "InvoiceProcessing\_v1",

  "description": "LangGraph invoice processing with HITL checkpoint/resume and Bigtool tool selection.",

  "config": {

    "match\_threshold": 0.90,

    "two\_way\_tolerance\_pct": 5,

    "human\_review\_queue": "human\_review\_queue",

    "checkpoint\_table": "checkpoints",

    "default\_db": "sqlite:///./demo.db"

  },

  "inputs": {

    "invoice\_payload": {

      "invoice\_id": "string",

      "vendor\_name": "string",

      "vendor\_tax\_id": "string",

      "invoice\_date": "string",

      "due\_date": "string",

      "amount": "number",

      "currency": "string",

      "line\_items": \[

        { "desc": "string", "qty": "number", "unit\_price": "number", "total": "number" }

      \],

      "attachments": \["string"\]

    }

  },

  "stages": \[

    {

      "id": "INTAKE",

      "mode": "deterministic",

      "agent": "IngestNode",

      "instructions": "Validate payload schema, persist raw invoice payload and attachments metadata. Return raw\_id and ingest timestamp.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "storage", "action": "select", "pool\_hint": \["s3","gcs","local\_fs"\] },

        { "name": "DB", "config\_ref": "{{DB\_CONN}}" }

      \],

      "output\_schema": {

        "raw\_id": "string",

        "ingest\_ts": "string",

        "validated": "boolean"

      }

    },

    {

      "id": "UNDERSTAND",

      "mode": "deterministic",

      "agent": "OcrNlpNode",

      "instructions": "Run OCR on attachments, extract text and parse line items, normalize dates/currency, return parsed\_invoice.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "ocr", "action": "select", "pool\_hint": \["google\_vision","tesseract","aws\_textract"\] },

        { "name": "NLPParser", "config\_ref": "{{NLP\_KEY}}" }

      \],

      "output\_schema": {

        "parsed\_invoice": {

          "invoice\_text": "string",

          "parsed\_line\_items": "array",

          "detected\_pos": "array",

          "currency": "string",

          "parsed\_dates": { "invoice\_date": "string", "due\_date": "string" }

        }

      }

    },

    {

      "id": "PREPARE",

      "mode": "deterministic",

      "agent": "NormalizeEnrichNode",

      "instructions": "Normalize vendor name, enrich vendor profile and compute flags (risk, missing\_info). Use Bigtool to pick enrichment provider.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "enrichment", "action": "select", "pool\_hint": \["clearbit","people\_data\_labs","vendor\_db"\] },

        { "name": "COMMON\_utils", "config\_ref": "{{COMMON\_KEY}}" }

      \],

      "output\_schema": {

        "vendor\_profile": { "normalized\_name": "string", "tax\_id": "string", "enrichment\_meta": "object" },

        "normalized\_invoice": { "amount": "number", "currency": "string", "line\_items": "array" },

        "flags": { "missing\_info": "array", "risk\_score": "number" }

      }

    },

    {

      "id": "RETRIEVE",

      "mode": "deterministic",

      "agent": "ErpFetchNode",

      "instructions": "Fetch POs, GRNs and historical invoices from ERP/Procurement systems to find candidate matches.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "erp\_connector", "action": "select", "pool\_hint": \["sap\_sandbox","netsuite","mock\_erp"\] },

        { "name": "ATLAS\_client", "config\_ref": "{{ATLAS\_ERP\_KEY}}" }

      \],

      "output\_schema": {

        "matched\_pos": "array",

        "matched\_grns": "array",

        "history": "array"

      }

    },

    {

      "id": "MATCH\_TWO\_WAY",

      "mode": "deterministic",

      "agent": "TwoWayMatcherNode",

      "instructions": "Compute 2-way match score between invoice and PO. If match\_score \>= config.match\_threshold set match\_result='MATCHED' else 'FAILED'. Include tolerance analysis.",

      "tools": \[

        { "name": "MatchEngine", "config\_ref": "{{MATCH\_KEY}}" },

        { "name": "COMMON\_utils", "config\_ref": "{{COMMON\_KEY}}" }

      \],

      "output\_schema": {

        "match\_score": "number",

        "match\_result": "string",

        "tolerance\_pct": "number",

        "match\_evidence": "object"

      }

    },

    {

      "id": "CHECKPOINT\_HITL",

      "mode": "deterministic",

      "agent": "CheckpointNode",

      "instructions": "If match\_result \== 'FAILED' persist full state as a checkpoint (state\_blob) in DB, create review ticket and push to human review queue. Return checkpoint\_id and review\_url. Pause workflow.",

      "trigger\_condition": "input\_state.match\_result \== 'FAILED'",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "db", "action": "select", "pool\_hint": \["postgres","sqlite","dynamodb"\] },

        { "name": "QueueService", "config\_ref": "{{QUEUE\_KEY}}" }

      \],

      "output\_schema": {

        "checkpoint\_id": "string",

        "review\_url": "string",

        "paused\_reason": "string"

      }

    },

    {

      "id": "HITL\_DECISION",

      "mode": "non-deterministic",

      "agent": "HumanReviewNode",

      "instructions": "Await human decision via human-review API. Accept or Reject. On ACCEPT return resume\_token and next\_stage='RECONCILE'. On REJECT finalize with status 'MANUAL\_HANDOFF'.",

      "tools": \[

        { "name": "HumanUI", "config\_ref": "{{APP\_URL}}" },

        { "name": "Auth", "config\_ref": "{{AUTH\_KEY}}" }

      \],

      "output\_schema": {

        "human\_decision": "string",

        "reviewer\_id": "string",

        "resume\_token": "string",

        "next\_stage": "string"

      }

    },

    {

      "id": "RECONCILE",

      "mode": "deterministic",

      "agent": "ReconciliationNode",

      "instructions": "If human accepted or invoice matched, create accounting entries (debits/credits) and reconciliation report.",

      "tools": \[

        { "name": "AccountingEngine", "config\_ref": "{{ACCT\_KEY}}" },

        { "name": "COMMON\_utils", "config\_ref": "{{COMMON\_KEY}}" }

      \],

      "output\_schema": {

        "accounting\_entries": "array",

        "reconciliation\_report": "object"

      }

    },

    {

      "id": "APPROVE",

      "mode": "deterministic",

      "agent": "ApprovalNode",

      "instructions": "Apply approval policies (auto-approve under threshold, escalate above). Return approval\_status and approver\_id if escalated.",

      "tools": \[

        { "name": "WorkflowEngine", "config\_ref": "{{WF\_KEY}}" }

      \],

      "output\_schema": {

        "approval\_status": "string",

        "approver\_id": "string"

      }

    },

    {

      "id": "POSTING",

      "mode": "deterministic",

      "agent": "PostingNode",

      "instructions": "Post journal entries to ERP and schedule payment. Return posted flag and txn ids.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "erp\_connector", "action": "select", "pool\_hint": \["sap\_sandbox","netsuite","mock\_erp"\] },

        { "name": "Payments", "config\_ref": "{{PAY\_KEY}}" }

      \],

      "output\_schema": {

        "posted": "boolean",

        "erp\_txn\_id": "string",

        "scheduled\_payment\_id": "string"

      }

    },

    {

      "id": "NOTIFY",

      "mode": "deterministic",

      "agent": "NotifyNode",

      "instructions": "Send notifications to vendor and internal finance team (email/slack). Log notification statuses.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "email", "action": "select", "pool\_hint": \["sendgrid","smartlead","ses"\] },

        { "name": "Messaging", "config\_ref": "{{SLACK\_KEY}}" }

      \],

      "output\_schema": {

        "notify\_status": "object",

        "notified\_parties": "array"

      }

    },

    {

      "id": "COMPLETE",

      "mode": "deterministic",

      "agent": "CompleteNode",

      "instructions": "Produce final payload and audit log entries. Mark workflow completed and persist audit to DB.",

      "tools": \[

        { "name": "BigtoolPicker", "capability": "db", "action": "select", "pool\_hint": \["postgres","sqlite","dynamodb"\] }

      \],

      "output\_schema": {

        "final\_payload": "object",

        "audit\_log": "array",

        "status": "string"

      }

    }

  \],

  "error\_handling": {

    "retry\_policy": { "max\_retries": 3, "backoff\_seconds": 2 },

    "on\_unrecoverable\_error": { "action": "persist\_and\_fail", "notify": \["ops\_team"\] }

  },

  "human\_review\_api\_contract": {

    "list\_pending\_endpoint": {

      "path": "/human-review/pending",

      "method": "GET",

      "response\_schema": {

        "items": \[

          {

            "checkpoint\_id": "string",

            "invoice\_id": "string",

            "vendor\_name": "string",

            "amount": "number",

            "created\_at": "string",

            "reason\_for\_hold": "string",

            "review\_url": "string"

          }

        \]

      }

    },

    "decision\_endpoint": {

      "path": "/human-review/decision",

      "method": "POST",

      "request\_schema": {

        "checkpoint\_id": "string",

        "decision": "string",

        "notes": "string",

        "reviewer\_id": "string"

      },

      "response\_schema": {

        "resume\_token": "string",

        "next\_stage": "string"

      }

    }

  },

  "tools\_hint": {

    "bigtool\_picker": "Use BigtoolPicker.select(capability, context) to choose tool implementation. Pool configured via tools.yaml or env.",

    "example\_pools": {

      "ocr": \["google\_vision", "tesseract", "aws\_textract"\],

      "enrichment": \["clearbit", "people\_data\_labs", "vendor\_db"\],

      "erp\_connector": \["sap\_sandbox", "netsuite", "mock\_erp"\],

      "db": \["postgres", "sqlite", "dynamodb"\],

      "email": \["sendgrid", "smartlead", "ses"\]

    }

  },

  "notes": "Adjust config refs ({{...}}) to actual env var names. CheckpointNode will set \`paused\_reason\` and produce \`review\_url\`. HumanReviewNode must return a \`resume\_token\` that LangGraph uses to resume execution."

}

