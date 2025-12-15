# Coding Rules & Best Practices

## 📋 Table of Contents

1. [Project Structure](#project-structure)
2. [TypedDict & State Management](#typeddict--state-management)
3. [Agent Class Design](#agent-class-design)
4. [LangGraph Best Practices](#langgraph-best-practices)
5. [Checkpoint & Persistence](#checkpoint--persistence)
6. [Error Handling & Retry](#error-handling--retry)
7. [MCP & Bigtool Integration](#mcp--bigtool-integration)
8. [API Design](#api-design)
9. [Frontend Guidelines](#frontend-guidelines)
10. [Testing Strategy](#testing-strategy)
11. [Logging & Observability](#logging--observability)
12. [Code Style & Conventions](#code-style--conventions)

---

## 1. Project Structure

```
Invoice-Processing-Workflow/
│
├── backend/                          # Python Backend
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py           # Pydantic Settings
│   │   │   └── workflow_config.py    # Load workflow.json
│   │   │
│   │   ├── agents/                   # Agent Classes
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # BaseAgent abstract class
│   │   │   ├── ingest_agent.py       # INTAKE
│   │   │   ├── ocr_nlp_agent.py      # UNDERSTAND
│   │   │   ├── normalize_agent.py    # PREPARE
│   │   │   ├── erp_fetch_agent.py    # RETRIEVE
│   │   │   ├── matcher_agent.py      # MATCH_TWO_WAY
│   │   │   ├── checkpoint_agent.py   # CHECKPOINT_HITL
│   │   │   ├── human_review_agent.py # HITL_DECISION
│   │   │   ├── reconcile_agent.py    # RECONCILE
│   │   │   ├── approval_agent.py     # APPROVE
│   │   │   ├── posting_agent.py      # POSTING
│   │   │   ├── notify_agent.py       # NOTIFY
│   │   │   └── complete_agent.py     # COMPLETE
│   │   │
│   │   ├── graph/                    # LangGraph Workflow
│   │   │   ├── __init__.py
│   │   │   ├── state.py              # TypedDict State Schema
│   │   │   ├── workflow.py           # Graph Definition
│   │   │   ├── nodes.py              # Node Functions
│   │   │   └── edges.py              # Conditional Edge Logic
│   │   │
│   │   ├── tools/                    # Bigtool & MCP
│   │   │   ├── __init__.py
│   │   │   ├── bigtool_picker.py     # Tool Selection Logic
│   │   │   ├── mcp_router.py         # MCP Server Router
│   │   │   ├── pools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ocr_pool.py
│   │   │   │   ├── enrichment_pool.py
│   │   │   │   ├── erp_pool.py
│   │   │   │   ├── db_pool.py
│   │   │   │   └── email_pool.py
│   │   │   └── mcp_servers/
│   │   │       ├── __init__.py
│   │   │       ├── common_server.py
│   │   │       └── atlas_server.py
│   │   │
│   │   ├── db/                       # Database Layer
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # SQLAlchemy Models
│   │   │   ├── session.py            # DB Session Management
│   │   │   └── checkpoint_store.py   # LangGraph SqliteSaver
│   │   │
│   │   ├── api/                      # FastAPI Routes
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── invoice.py        # Invoice submission
│   │   │   │   ├── human_review.py   # HITL endpoints
│   │   │   │   ├── workflow.py       # Workflow status
│   │   │   │   └── health.py         # Health checks
│   │   │   └── dependencies.py       # FastAPI Dependencies
│   │   │
│   │   ├── schemas/                  # Pydantic Schemas
│   │   │   ├── __init__.py
│   │   │   ├── invoice.py
│   │   │   ├── review.py
│   │   │   └── response.py
│   │   │
│   │   └── utils/                    # Utilities
│   │       ├── __init__.py
│   │       ├── logger.py             # Structured Logging
│   │       ├── retry.py              # Retry Decorators
│   │       └── validators.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Pytest Fixtures
│   │   ├── test_agents/
│   │   ├── test_graph/
│   │   ├── test_tools/
│   │   └── test_api/
│   │
│   ├── alembic/                      # DB Migrations
│   │   └── versions/
│   │
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/                         # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── InvoiceForm.tsx
│   │   │   ├── ReviewQueue.tsx
│   │   │   ├── ReviewDetail.tsx
│   │   │   ├── WorkflowStatus.tsx
│   │   │   └── AuditLog.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── SubmitInvoice.tsx
│   │   │   └── HumanReview.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── config/
│   ├── workflow.json                 # Workflow Definition
│   └── tools.yaml                    # Tool Pool Config
│
├── docs/
│   ├── STRATEGY.md
│   ├── CODING_RULES.md               # This file
│   └── API.md
│
├── docker-compose.yml
├── README.md
└── .env.example
```

---

## 2. TypedDict & State Management

### Rule 2.1: Use TypedDict for All State Definitions

```python
# ✅ CORRECT: Use TypedDict with proper annotations
from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages

class InvoiceWorkflowState(TypedDict):
    """
    Immutable state schema for the invoice processing workflow.
    All fields must be explicitly typed.
    """
    # Input
    invoice_payload: dict
    
    # Stage outputs - use Optional for fields set later
    raw_id: Optional[str]
    ingest_ts: Optional[str]
    validated: Optional[bool]
    
    # Use Annotated for reducer functions (message accumulation)
    messages: Annotated[list, add_messages]
    audit_log: Annotated[list, lambda x, y: x + y]  # Append-only
    
    # Workflow metadata
    current_stage: str
    status: str  # "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED"
    error: Optional[str]

# ❌ WRONG: Using plain dict
state = {"invoice": data}  # No type safety
```

### Rule 2.2: Define Nested TypedDicts for Complex Structures

```python
# ✅ CORRECT: Nested TypedDict for structured data
class ParsedInvoice(TypedDict):
    invoice_text: str
    parsed_line_items: list[dict]
    detected_pos: list[str]
    currency: str
    parsed_dates: dict

class VendorProfile(TypedDict):
    normalized_name: str
    tax_id: str
    enrichment_meta: dict
    risk_score: float

class InvoiceWorkflowState(TypedDict):
    # ...existing code...
    parsed_invoice: Optional[ParsedInvoice]
    vendor_profile: Optional[VendorProfile]
```

### Rule 2.3: Use Annotated Reducers for Accumulating Data

```python
from typing import Annotated
from operator import add

class InvoiceWorkflowState(TypedDict):
    # Append new entries to existing list
    audit_log: Annotated[list[dict], add]
    
    # Custom reducer for bigtool selections
    bigtool_selections: Annotated[dict, lambda old, new: {**old, **new}]
```

---

## 3. Agent Class Design

### Rule 3.1: All Agents Must Inherit from BaseAgent

```python
# backend/src/agents/base.py
from abc import ABC, abstractmethod
from typing import Any
from ..graph.state import InvoiceWorkflowState
from ..utils.logger import get_logger

class BaseAgent(ABC):
    """
    Abstract base class for all workflow agents.
    Provides common functionality and enforces interface.
    """
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"agent.{name}")
    
    @abstractmethod
    async def execute(self, state: InvoiceWorkflowState) -> dict:
        """
        Execute the agent's logic.
        
        Args:
            state: Current workflow state
            
        Returns:
            dict: State updates to merge
        """
        pass
    
    def validate_input(self, state: InvoiceWorkflowState) -> bool:
        """Validate required input fields exist."""
        return True
    
    def log_execution(self, stage: str, result: dict):
        """Standard logging for agent execution."""
        self.logger.info(
            f"Agent executed",
            extra={
                "agent": self.name,
                "stage": stage,
                "result_keys": list(result.keys())
            }
        )
```

### Rule 3.2: Each Stage Has Its Own Agent Class

```python
# backend/src/agents/ingest_agent.py
from .base import BaseAgent
from ..graph.state import InvoiceWorkflowState
from ..tools.bigtool_picker import BigtoolPicker
from ..tools.mcp_router import MCPRouter

class IngestAgent(BaseAgent):
    """
    INTAKE Stage Agent.
    Validates payload schema, persists raw invoice.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="IngestAgent", config=config)
        self.bigtool = BigtoolPicker()
        self.mcp = MCPRouter()
    
    async def execute(self, state: InvoiceWorkflowState) -> dict:
        """
        Execute INTAKE stage.
        
        Returns:
            dict with raw_id, ingest_ts, validated
        """
        self.logger.info("Starting INTAKE stage")
        
        # 1. Validate schema
        invoice = state["invoice_payload"]
        is_valid = self._validate_schema(invoice)
        
        # 2. Select storage tool via Bigtool
        storage_tool = self.bigtool.select(
            capability="storage",
            context={"size": len(str(invoice))}
        )
        self.logger.info(f"Bigtool selected: {storage_tool['selected_tool']}")
        
        # 3. Persist via MCP COMMON server
        result = await self.mcp.execute(
            server="COMMON",
            ability="persist_invoice",
            payload=invoice,
            tool=storage_tool["selected_tool"]
        )
        
        return {
            "raw_id": result["raw_id"],
            "ingest_ts": result["timestamp"],
            "validated": is_valid,
            "current_stage": "INTAKE",
            "bigtool_selections": {"INTAKE": storage_tool},
            "audit_log": [{
                "stage": "INTAKE",
                "action": "persist_invoice",
                "tool": storage_tool["selected_tool"],
                "timestamp": result["timestamp"]
            }]
        }
    
    def _validate_schema(self, invoice: dict) -> bool:
        """Validate invoice payload schema."""
        required = ["invoice_id", "vendor_name", "amount", "line_items"]
        return all(k in invoice for k in required)
```

### Rule 3.3: Agent Registry Pattern

```python
# backend/src/agents/__init__.py
from typing import Type
from .base import BaseAgent
from .ingest_agent import IngestAgent
from .ocr_nlp_agent import OcrNlpAgent
# ... import all agents

class AgentRegistry:
    """Registry to get agent by stage ID."""
    
    _agents: dict[str, Type[BaseAgent]] = {
        "INTAKE": IngestAgent,
        "UNDERSTAND": OcrNlpAgent,
        "PREPARE": NormalizeEnrichAgent,
        "RETRIEVE": ErpFetchAgent,
        "MATCH_TWO_WAY": TwoWayMatcherAgent,
        "CHECKPOINT_HITL": CheckpointAgent,
        "HITL_DECISION": HumanReviewAgent,
        "RECONCILE": ReconcileAgent,
        "APPROVE": ApprovalAgent,
        "POSTING": PostingAgent,
        "NOTIFY": NotifyAgent,
        "COMPLETE": CompleteAgent,
    }
    
    @classmethod
    def get(cls, stage_id: str, config: dict = None) -> BaseAgent:
        """Get agent instance for stage."""
        agent_class = cls._agents.get(stage_id)
        if not agent_class:
            raise ValueError(f"Unknown stage: {stage_id}")
        return agent_class(config=config)
```

---

## 4. LangGraph Best Practices

### Rule 4.1: Use StateGraph with Proper Type Annotations

```python
# backend/src/graph/workflow.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from .state import InvoiceWorkflowState
from .nodes import (
    intake_node, understand_node, prepare_node,
    retrieve_node, match_node, checkpoint_node,
    hitl_decision_node, reconcile_node, approve_node,
    posting_node, notify_node, complete_node
)
from .edges import should_checkpoint, after_hitl_decision

def create_invoice_workflow(checkpointer: SqliteSaver = None) -> StateGraph:
    """
    Create the invoice processing workflow graph.
    
    Args:
        checkpointer: LangGraph checkpoint saver for persistence
        
    Returns:
        Compiled StateGraph
    """
    # Initialize graph with typed state
    workflow = StateGraph(InvoiceWorkflowState)
    
    # Add all nodes
    workflow.add_node("INTAKE", intake_node)
    workflow.add_node("UNDERSTAND", understand_node)
    workflow.add_node("PREPARE", prepare_node)
    workflow.add_node("RETRIEVE", retrieve_node)
    workflow.add_node("MATCH_TWO_WAY", match_node)
    workflow.add_node("CHECKPOINT_HITL", checkpoint_node)
    workflow.add_node("HITL_DECISION", hitl_decision_node)
    workflow.add_node("RECONCILE", reconcile_node)
    workflow.add_node("APPROVE", approve_node)
    workflow.add_node("POSTING", posting_node)
    workflow.add_node("NOTIFY", notify_node)
    workflow.add_node("COMPLETE", complete_node)
    
    # Define edges
    workflow.add_edge(START, "INTAKE")
    workflow.add_edge("INTAKE", "UNDERSTAND")
    workflow.add_edge("UNDERSTAND", "PREPARE")
    workflow.add_edge("PREPARE", "RETRIEVE")
    workflow.add_edge("RETRIEVE", "MATCH_TWO_WAY")
    
    # Conditional edge: Match result determines next step
    workflow.add_conditional_edges(
        "MATCH_TWO_WAY",
        should_checkpoint,
        {
            "checkpoint": "CHECKPOINT_HITL",
            "continue": "RECONCILE"
        }
    )
    
    # HITL flow
    workflow.add_edge("CHECKPOINT_HITL", "HITL_DECISION")
    
    # Conditional edge: Human decision
    workflow.add_conditional_edges(
        "HITL_DECISION",
        after_hitl_decision,
        {
            "accept": "RECONCILE",
            "reject": "COMPLETE"  # With MANUAL_HANDOFF status
        }
    )
    
    # Continue to completion
    workflow.add_edge("RECONCILE", "APPROVE")
    workflow.add_edge("APPROVE", "POSTING")
    workflow.add_edge("POSTING", "NOTIFY")
    workflow.add_edge("NOTIFY", "COMPLETE")
    workflow.add_edge("COMPLETE", END)
    
    # Compile with checkpointer
    return workflow.compile(checkpointer=checkpointer)
```

### Rule 4.2: Node Functions Must Return State Updates

```python
# backend/src/graph/nodes.py
from ..agents import AgentRegistry
from .state import InvoiceWorkflowState

async def intake_node(state: InvoiceWorkflowState) -> dict:
    """
    INTAKE node - validates and persists invoice.
    
    Node functions receive state and return updates to merge.
    """
    agent = AgentRegistry.get("INTAKE")
    return await agent.execute(state)

async def understand_node(state: InvoiceWorkflowState) -> dict:
    """UNDERSTAND node - OCR and parsing."""
    agent = AgentRegistry.get("UNDERSTAND")
    return await agent.execute(state)

# ... pattern repeats for all nodes
```

### Rule 4.3: Conditional Edges Must Return String Keys

```python
# backend/src/graph/edges.py
from .state import InvoiceWorkflowState

def should_checkpoint(state: InvoiceWorkflowState) -> str:
    """
    Determine if HITL checkpoint is needed.
    
    Returns:
        "checkpoint" if match failed, "continue" otherwise
    """
    match_result = state.get("match_result", "")
    match_score = state.get("match_score", 0)
    threshold = 0.90  # From config
    
    if match_result == "FAILED" or match_score < threshold:
        return "checkpoint"
    return "continue"

def after_hitl_decision(state: InvoiceWorkflowState) -> str:
    """
    Route based on human decision.
    
    Returns:
        "accept" to continue, "reject" to end with manual handoff
    """
    decision = state.get("human_decision", "")
    
    if decision == "ACCEPT":
        return "accept"
    return "reject"
```

### Rule 4.4: Use LangGraph's Interrupt for HITL

```python
# backend/src/graph/nodes.py
from langgraph.types import interrupt

async def hitl_decision_node(state: InvoiceWorkflowState) -> dict:
    """
    HITL Decision node - waits for human input.
    
    Uses LangGraph's interrupt() for clean pause/resume.
    """
    # Check if we already have a decision (resuming)
    if state.get("human_decision"):
        return {
            "current_stage": "HITL_DECISION",
            "status": "RUNNING"
        }
    
    # Interrupt and wait for human input
    # This will be resumed via the API with Command(resume=...)
    human_input = interrupt({
        "type": "human_review",
        "checkpoint_id": state.get("checkpoint_id"),
        "invoice_id": state.get("invoice_payload", {}).get("invoice_id"),
        "reason": state.get("paused_reason")
    })
    
    return {
        "human_decision": human_input.get("decision"),
        "reviewer_id": human_input.get("reviewer_id"),
        "resume_token": human_input.get("resume_token"),
        "current_stage": "HITL_DECISION",
        "status": "RUNNING" if human_input.get("decision") == "ACCEPT" else "MANUAL_HANDOFF"
    }
```

---

## 5. Checkpoint & Persistence

### Rule 5.1: Use LangGraph's Built-in SqliteSaver

```python
# backend/src/db/checkpoint_store.py
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver
import sqlite3

def get_checkpointer(db_url: str = "sqlite:///./demo.db"):
    """
    Get appropriate checkpointer based on DB URL.
    
    Uses LangGraph's built-in checkpoint savers.
    """
    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return SqliteSaver(conn)
    elif db_url.startswith("postgresql"):
        return PostgresSaver.from_conn_string(db_url)
    else:
        raise ValueError(f"Unsupported DB: {db_url}")

# Usage in main.py
from .db.checkpoint_store import get_checkpointer
from .graph.workflow import create_invoice_workflow

checkpointer = get_checkpointer("sqlite:///./demo.db")
workflow = create_invoice_workflow(checkpointer=checkpointer)
```

### Rule 5.2: Use Thread IDs for Workflow Instances

```python
# backend/src/api/routes/invoice.py
from fastapi import APIRouter
from uuid import uuid4
from ...graph.workflow import create_invoice_workflow
from ...db.checkpoint_store import get_checkpointer

router = APIRouter()

@router.post("/invoice/submit")
async def submit_invoice(invoice: InvoicePayload):
    """Submit invoice and start workflow."""
    
    # Generate unique thread ID for this workflow instance
    thread_id = str(uuid4())
    
    # Create workflow with checkpointer
    checkpointer = get_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    # Initial state
    initial_state = {
        "invoice_payload": invoice.dict(),
        "current_stage": "START",
        "status": "RUNNING",
        "audit_log": [],
        "bigtool_selections": {}
    }
    
    # Config with thread_id for checkpoint tracking
    config = {"configurable": {"thread_id": thread_id}}
    
    # Run workflow (will pause at HITL if needed)
    result = await workflow.ainvoke(initial_state, config)
    
    return {
        "thread_id": thread_id,
        "status": result.get("status"),
        "current_stage": result.get("current_stage")
    }
```

### Rule 5.3: Resume from Checkpoint with Command

```python
# backend/src/api/routes/human_review.py
from fastapi import APIRouter
from langgraph.types import Command
from ...graph.workflow import create_invoice_workflow
from ...db.checkpoint_store import get_checkpointer

router = APIRouter()

@router.post("/human-review/decision")
async def submit_decision(decision: ReviewDecision):
    """Submit human review decision and resume workflow."""
    
    checkpointer = get_checkpointer()
    workflow = create_invoice_workflow(checkpointer)
    
    # Config to resume specific thread
    config = {"configurable": {"thread_id": decision.thread_id}}
    
    # Resume with human input using Command
    result = await workflow.ainvoke(
        Command(resume={
            "decision": decision.decision,
            "reviewer_id": decision.reviewer_id,
            "notes": decision.notes,
            "resume_token": str(uuid4())
        }),
        config
    )
    
    return {
        "status": result.get("status"),
        "next_stage": result.get("current_stage")
    }
```

---

## 6. Error Handling & Retry

### Rule 6.1: Use LangGraph's Built-in Retry

```python
# backend/src/graph/workflow.py
from langgraph.graph import StateGraph
from langgraph.pregel import RetryPolicy

def create_invoice_workflow(checkpointer=None):
    workflow = StateGraph(InvoiceWorkflowState)
    
    # Define retry policy
    retry_policy = RetryPolicy(
        max_attempts=3,
        initial_interval=1.0,  # seconds
        backoff_factor=2.0,
        max_interval=10.0,
        retry_on=(ConnectionError, TimeoutError)
    )
    
    # Add nodes with retry policy
    workflow.add_node(
        "UNDERSTAND",
        understand_node,
        retry=retry_policy  # Retry OCR failures
    )
    
    workflow.add_node(
        "RETRIEVE",
        retrieve_node,
        retry=retry_policy  # Retry ERP connection failures
    )
    
    # ... rest of graph
```

### Rule 6.2: Custom Retry Decorator for Tools

```python
# backend/src/utils/retry.py
import asyncio
from functools import wraps
from typing import Type
from ..utils.logger import get_logger

logger = get_logger("retry")

def with_retry(
    max_attempts: int = 3,
    backoff_seconds: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry decorator with exponential backoff.
    
    Usage:
        @with_retry(max_attempts=3, backoff_seconds=2)
        async def call_external_api():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = backoff_seconds * (2 ** (attempt - 1))
                        logger.warning(
                            f"Attempt {attempt} failed, retrying in {wait_time}s",
                            extra={"function": func.__name__, "error": str(e)}
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed",
                            extra={"function": func.__name__, "error": str(e)}
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
```

### Rule 6.3: Error State Handling in Nodes

```python
# backend/src/graph/nodes.py
from ..utils.logger import get_logger

logger = get_logger("nodes")

async def understand_node(state: InvoiceWorkflowState) -> dict:
    """UNDERSTAND node with error handling."""
    try:
        agent = AgentRegistry.get("UNDERSTAND")
        result = await agent.execute(state)
        return result
        
    except Exception as e:
        logger.error(f"UNDERSTAND stage failed: {e}")
        
        # Return error state - workflow can decide to retry or fail
        return {
            "current_stage": "UNDERSTAND",
            "status": "ERROR",
            "error": str(e),
            "audit_log": [{
                "stage": "UNDERSTAND",
                "action": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
```

---

## 7. MCP & Bigtool Integration

### Rule 7.1: BigtoolPicker as Singleton Service

```python
# backend/src/tools/bigtool_picker.py
from typing import Optional
from ..utils.logger import get_logger

class BigtoolPicker:
    """
    Singleton service for selecting tools from pools.
    Thread-safe and configurable.
    """
    
    _instance: Optional["BigtoolPicker"] = None
    
    POOLS = {
        "ocr": ["google_vision", "aws_textract", "tesseract"],
        "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
        "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
        "db": ["postgres", "sqlite", "dynamodb"],
        "email": ["sendgrid", "ses", "smartlead"],
        "storage": ["s3", "gcs", "local_fs"]
    }
    
    # Simulated availability (real: health checks)
    AVAILABILITY = {
        "google_vision": True,
        "aws_textract": True,
        "tesseract": True,
        "clearbit": True,
        "people_data_labs": False,
        "vendor_db": True,
        "sap_sandbox": False,
        "netsuite": True,
        "mock_erp": True,  # Always available for demo
        "postgres": True,
        "sqlite": True,
        "dynamodb": False,
        "sendgrid": True,
        "ses": True,
        "smartlead": False,
        "s3": True,
        "gcs": True,
        "local_fs": True
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logger = get_logger("bigtool")
        return cls._instance
    
    def select(self, capability: str, context: dict = None) -> dict:
        """
        Select best available tool for capability.
        
        Args:
            capability: Tool capability (ocr, enrichment, etc.)
            context: Optional context for selection (file_type, size, etc.)
            
        Returns:
            {
                "selected_tool": str,
                "capability": str,
                "reason": str,
                "fallback_chain": list
            }
        """
        pool = self.POOLS.get(capability, [])
        context = context or {}
        
        for tool in pool:
            if self._is_available(tool):
                result = {
                    "selected_tool": tool,
                    "capability": capability,
                    "reason": f"Selected {tool} - first available in pool",
                    "fallback_chain": [t for t in pool if t != tool and self._is_available(t)]
                }
                self.logger.info(f"Tool selected: {tool} for {capability}")
                return result
        
        # Fallback to mock
        mock_tool = f"mock_{capability}"
        self.logger.warning(f"No tools available, using {mock_tool}")
        return {
            "selected_tool": mock_tool,
            "capability": capability,
            "reason": "All tools unavailable, using mock",
            "fallback_chain": []
        }
    
    def _is_available(self, tool: str) -> bool:
        """Check tool availability."""
        return self.AVAILABILITY.get(tool, False)
```

### Rule 7.2: MCPRouter with Server Abstraction

```python
# backend/src/tools/mcp_router.py
from enum import Enum
from typing import Any
from .mcp_servers.common_server import CommonServer
from .mcp_servers.atlas_server import AtlasServer
from ..utils.logger import get_logger

class MCPServer(Enum):
    COMMON = "COMMON"
    ATLAS = "ATLAS"

class MCPRouter:
    """
    Routes abilities to appropriate MCP server.
    """
    
    ROUTING_TABLE = {
        # COMMON Server abilities
        "validate_schema": MCPServer.COMMON,
        "persist_invoice": MCPServer.COMMON,
        "parse_line_items": MCPServer.COMMON,
        "normalize_vendor": MCPServer.COMMON,
        "compute_flags": MCPServer.COMMON,
        "compute_match_score": MCPServer.COMMON,
        "create_checkpoint": MCPServer.COMMON,
        "build_accounting_entries": MCPServer.COMMON,
        "create_audit_log": MCPServer.COMMON,
        
        # ATLAS Server abilities
        "ocr_extract": MCPServer.ATLAS,
        "enrich_vendor": MCPServer.ATLAS,
        "fetch_po": MCPServer.ATLAS,
        "fetch_grn": MCPServer.ATLAS,
        "fetch_history": MCPServer.ATLAS,
        "post_to_erp": MCPServer.ATLAS,
        "schedule_payment": MCPServer.ATLAS,
        "send_email": MCPServer.ATLAS,
        "send_slack": MCPServer.ATLAS,
    }
    
    def __init__(self):
        self.logger = get_logger("mcp_router")
        self.common_server = CommonServer()
        self.atlas_server = AtlasServer()
    
    async def execute(
        self,
        ability: str,
        payload: dict,
        tool: str = None,
        **kwargs
    ) -> Any:
        """
        Execute ability on appropriate server.
        
        Args:
            ability: Ability name to execute
            payload: Input payload
            tool: Selected tool (from Bigtool)
            
        Returns:
            Result from server execution
        """
        server = self.ROUTING_TABLE.get(ability, MCPServer.COMMON)
        
        self.logger.info(
            f"Routing {ability} to {server.value}",
            extra={"tool": tool}
        )
        
        if server == MCPServer.COMMON:
            return await self.common_server.execute(ability, payload, **kwargs)
        else:
            return await self.atlas_server.execute(ability, payload, tool=tool, **kwargs)
```

---

## 8. API Design

### Rule 8.1: Use Pydantic Models for Request/Response

```python
# backend/src/schemas/invoice.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class LineItem(BaseModel):
  desc: str
  qty: float
  unit_price: float
  total: float

class InvoicePayload(BaseModel):
  invoice_id: str
  vendor_name: str
  vendor_tax_id: Optional[str] = None
  invoice_date: str
  due_date: str
  amount: float
  currency: str = "USD"
  line_items: list[LineItem]
  attachments: list[str] = []

class InvoiceSubmitResponse(BaseModel):
  thread_id: str
  status: str
  current_stage: str
  message: str

# backend/src/schemas/review.py
class ReviewDecision(BaseModel):
  thread_id: str
  checkpoint_id: str
  decision: str = Field(..., pattern="^(ACCEPT|REJECT)$")
  notes: Optional[str] = None
  reviewer_id: str

class PendingReviewItem(BaseModel):
  checkpoint_id: str
  thread_id: str
  invoice_id: str
  vendor_name: str
  amount: float
  created_at: datetime
  reason_for_hold: str
  review_url: str
```

### Rule 8.2: Dependency Injection for Services

```python
# backend/src/api/dependencies.py
from functools import lru_cache
from ..db.checkpoint_store import get_checkpointer
from ..graph.workflow import create_invoice_workflow
from ..tools.bigtool_picker import BigtoolPicker

@lru_cache()
def get_workflow():
    """Get compiled workflow (cached)."""
    checkpointer = get_checkpointer()
    return create_invoice_workflow(checkpointer)

@lru_cache()
def get_bigtool():
    """Get BigtoolPicker instance (cached singleton)."""
    return BigtoolPicker()

# Usage in routes
from fastapi import Depends

@router.post("/invoice/submit")
async def submit_invoice(
    invoice: InvoicePayload,
    workflow = Depends(get_workflow)
):
    ...
```

---

## 9. Frontend Guidelines

### Rule 9.1: TypeScript Types Mirror Backend Schemas

```typescript
// frontend/src/types/index.ts

export interface LineItem {
  desc: string;
  qty: number;
  unit_price: number;
  total: number;
}

export interface InvoicePayload {
  invoice_id: string;
  vendor_name: string;
  vendor_tax_id?: string;
  invoice_date: string;
  due_date: string;
  amount: number;
  currency: string;
  line_items: LineItem[];
  attachments: string[];
}

export interface PendingReview {
  checkpoint_id: string;
  thread_id: string;
  invoice_id: string;
  vendor_name: string;
  amount: number;
  created_at: string;
  reason_for_hold: string;
  review_url: string;
}

export interface WorkflowStatus {
  thread_id: string;
  status: 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED';
  current_stage: string;
  audit_log: AuditEntry[];
}
```

### Rule 9.2: API Service Layer

```typescript
// frontend/src/services/api.ts
import axios from 'axios';
import { InvoicePayload, PendingReview, ReviewDecision } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
});

export const invoiceApi = {
  submit: (invoice: InvoicePayload) => 
    api.post('/invoice/submit', invoice),
    
  getStatus: (threadId: string) =>
    api.get(`/workflow/status/${threadId}`),
};

export const reviewApi = {
  getPending: () =>
    api.get<{ items: PendingReview[] }>('/human-review/pending'),
    
  submitDecision: (decision: ReviewDecision) =>
    api.post('/human-review/decision', decision),
};
```

---

## 10. Testing Strategy

### Rule 10.1: Use Pytest Fixtures for Common Setup

```python
# backend/tests/conftest.py
import pytest
from src.graph.state import InvoiceWorkflowState
from src.graph.workflow import create_invoice_workflow
from src.tools.bigtool_picker import BigtoolPicker

@pytest.fixture
def sample_invoice() -> dict:
    """Sample invoice payload for testing."""
    return {
        "invoice_id": "INV-TEST-001",
        "vendor_name": "Test Vendor Inc",
        "vendor_tax_id": "TAX123",
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-15",
        "amount": 15000.00,
        "currency": "USD",
        "line_items": [
            {"desc": "Widget A", "qty": 100, "unit_price": 100, "total": 10000},
            {"desc": "Widget B", "qty": 50, "unit_price": 100, "total": 5000}
        ],
        "attachments": ["invoice.pdf"]
    }

@pytest.fixture
def initial_state(sample_invoice) -> InvoiceWorkflowState:
    """Initial workflow state."""
    return {
        "invoice_payload": sample_invoice,
        "current_stage": "START",
        "status": "RUNNING",
        "audit_log": [],
        "bigtool_selections": {}
    }

@pytest.fixture
def workflow():
    """Workflow without persistence (for unit tests)."""
    return create_invoice_workflow(checkpointer=None)

@pytest.fixture
def bigtool():
    """BigtoolPicker instance."""
    return BigtoolPicker()
```

### Rule 10.2: Test Agents in Isolation

```python
# backend/tests/test_agents/test_ingest_agent.py
import pytest
from src.agents.ingest_agent import IngestAgent

@pytest.mark.asyncio
async def test_ingest_agent_validates_payload(initial_state):
    """Test INTAKE stage validates invoice."""
    agent = IngestAgent()
    result = await agent.execute(initial_state)
    
    assert result["validated"] is True
    assert "raw_id" in result
    assert "ingest_ts" in result
    assert result["current_stage"] == "INTAKE"

@pytest.mark.asyncio
async def test_ingest_agent_rejects_invalid(initial_state):
    """Test INTAKE rejects invalid payload."""
    initial_state["invoice_payload"] = {"invalid": "data"}
    agent = IngestAgent()
    result = await agent.execute(initial_state)
    
    assert result["validated"] is False
```

---

## 11. Logging & Observability

### Rule 11.1: Structured Logging with Context

```python
# backend/src/utils/logger.py
import logging
import json
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ["name", "msg", "args", "created", "filename",
                              "funcName", "levelname", "levelno", "lineno",
                              "module", "msecs", "pathname", "process",
                              "processName", "relativeCreated", "stack_info",
                              "exc_info", "exc_text", "thread", "threadName"]:
                    log_entry[key] = value
        
        return json.dumps(log_entry)

def get_logger(name: str) -> logging.Logger:
    """Get configured logger."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger

# Usage
logger = get_logger("agent.intake")
logger.info(
    "Invoice processed",
    extra={
        "invoice_id": "INV-001",
        "stage": "INTAKE",
        "tool": "local_fs"
    }
)
# Output: {"timestamp": "...", "level": "INFO", "logger": "agent.intake", 
#          "message": "Invoice processed", "invoice_id": "INV-001", ...}
```

### Rule 11.2: Audit Log in State

```python
# Every node must append to audit_log
def create_audit_entry(
    stage: str,
    action: str,
    details: dict = None
) -> dict:
    """Create standardized audit log entry."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "action": action,
        "details": details or {}
    }

# In node
return {
    "audit_log": [create_audit_entry(
        stage="UNDERSTAND",
        action="ocr_complete",
        details={"tool": "google_vision", "confidence": 0.95}
    )]
}
```

---

## 12. Code Style & Conventions

### Rule 12.1: Naming Conventions

```python
# Classes: PascalCase
class IngestAgent:
class BigtoolPicker:

# Functions/Methods: snake_case
def process_invoice():
async def execute():

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_THRESHOLD = 0.90

# Variables: snake_case
invoice_payload = {}
match_score = 0.85

# Type aliases: PascalCase
InvoiceState = TypedDict(...)
```

### Rule 12.2: Docstrings (Google Style)

```python
async def execute(self, state: InvoiceWorkflowState) -> dict:
    """
    Execute the INTAKE stage.
    
    Validates invoice payload and persists raw data.
    
    Args:
        state: Current workflow state containing invoice_payload
        
    Returns:
        dict: State updates with raw_id, ingest_ts, validated
        
    Raises:
        ValidationError: If payload schema is invalid
        PersistenceError: If storage fails
        
    Example:
        >>> agent = IngestAgent()
        >>> result = await agent.execute(state)
        >>> print(result["validated"])
        True
    """
```

### Rule 12.3: Import Order

```python
# 1. Standard library
import asyncio
from typing import Optional
from datetime import datetime

# 2. Third-party packages
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from langgraph.graph import StateGraph

# 3. Local imports
from ..graph.state import InvoiceWorkflowState
from ..tools.bigtool_picker import BigtoolPicker
from ..utils.logger import get_logger
```

### Rule 12.4: File Length Limits

- Maximum 300 lines per file
- Split large files by responsibility
- One class per file for agents

---

## 📋 Quick Reference Checklist

```
□ All state uses TypedDict
□ All agents inherit from BaseAgent
□ Checkpoints use SqliteSaver/PostgresSaver
□ HITL uses LangGraph interrupt()
□ Retry policy on external calls
□ Structured logging in all components
□ Pydantic schemas for API
□ Tests for each agent
□ Audit log updated in every node
□ Bigtool selection logged
□ MCP routing logged
```