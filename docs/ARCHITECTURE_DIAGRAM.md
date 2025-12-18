# Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              INVOICE PROCESSING SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐     ┌────────────────────────────────────────────────────┐   │
│  │   Frontend   │     │                  LangGraph Engine                   │   │
│  │   (React)    │────▶│  ┌─────────────────────────────────────────────┐   │   │
│  └──────────────┘     │  │              Workflow Graph                  │   │   │
│         │             │  │  INTAKE → UNDERSTAND → PREPARE → RETRIEVE   │   │   │
│         │             │  │     → MATCH → [HITL] → RECONCILE → ...      │   │   │
│         ▼             │  └─────────────────────────────────────────────┘   │   │
│  ┌──────────────┐     │                        │                            │   │
│  │  FastAPI     │     │                        ▼                            │   │
│  │  Backend     │◀───▶│  ┌─────────────────────────────────────────────┐   │   │
│  └──────────────┘     │  │            State Manager                     │   │   │
│         │             │  │  • Persistent state across nodes             │   │   │
│         ▼             │  │  • Checkpoint serialization                  │   │   │
│  ┌──────────────┐     │  └─────────────────────────────────────────────┘   │   │
│  │   Database   │◀────┤                        │                            │   │
│  │   (SQLite)   │     │                        ▼                            │   │
│  └──────────────┘     │  ┌─────────────────────────────────────────────┐   │   │
│                       │  │            MCP Router                        │   │   │
│                       │  │  • Routes to COMMON or ATLAS                 │   │   │
│                       │  └────────────────┬────────────────────────────┘   │   │
│                       └──────────────────┼──────────────────────────────────┘   │
│                                          │                                       │
│                          ┌───────────────┴───────────────┐                      │
│                          │                               │                       │
│                          ▼                               ▼                       │
│                  ┌───────────────┐             ┌───────────────┐                │
│                  │ COMMON Server │             │ ATLAS Server  │                │
│                  └───────────────┘             └───────────────┘                │
│                          │                               │                       │
│                          ▼                               ▼                       │
│                  ┌───────────────┐             ┌───────────────┐                │
│                  │  Bigtool      │             │  External     │                │
│                  │  Picker       │             │  Services     │                │
│                  └───────────────┘             └───────────────┘                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Invoice JSON ──▶ INTAKE ──▶ raw_id, validated
                    │
                    ▼
              UNDERSTAND ──▶ parsed_invoice
                    │
                    ▼
               PREPARE ──▶ vendor_profile, flags
                    │
                    ▼
              RETRIEVE ──▶ matched_pos, matched_grns
                    │
                    ▼
           MATCH_TWO_WAY ──▶ match_score, match_result
                    │
          ┌─────────┴─────────┐
          │                   │
    MATCHED ≥ 0.9       FAILED < 0.9
          │                   │
          │                   ▼
          │          CHECKPOINT_HITL ──▶ checkpoint_id (PAUSED)
          │                   │
          │                   ▼
          │           HITL_DECISION ──▶ human_decision
          │                   │
          │         ┌─────────┴─────────┐
          │         │                   │
          │      ACCEPT              REJECT
          │         │                   │
          └────┬────┘                   ▼
               │                 END (MANUAL_HANDOFF)
               ▼
          RECONCILE ──▶ accounting_entries
               │
               ▼
           APPROVE ──▶ approval_status
               │
               ▼
           POSTING ──▶ erp_txn_id, scheduled_payment_id
               │
               ▼
            NOTIFY ──▶ notify_status
               │
               ▼
          COMPLETE ──▶ final_payload, status=COMPLETED
```
