"""Workflow configuration loader."""
import json
from pathlib import Path
from typing import Any


def load_workflow_config(config_path: str = None) -> dict[str, Any]:
    """
    Load workflow configuration from JSON file.
    
    Args:
        config_path: Path to workflow.json file
        
    Returns:
        dict: Workflow configuration
    """
    if config_path is None:
        # Default path relative to project root
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "workflow.json"
    else:
        config_path = Path(config_path)
    
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    
    # Return default configuration if file doesn't exist
    return get_default_config()


def get_default_config() -> dict[str, Any]:
    """Return default workflow configuration."""
    return {
        "version": "1.0",
        "workflow_name": "InvoiceProcessing_v1",
        "description": "LangGraph invoice processing with HITL checkpoint/resume and Bigtool tool selection.",
        "config": {
            "match_threshold": 0.90,
            "two_way_tolerance_pct": 5,
            "human_review_queue": "human_review_queue",
            "checkpoint_table": "checkpoints",
            "default_db": "sqlite:///./demo.db"
        },
        "stages": [
            {"id": "INTAKE", "mode": "deterministic"},
            {"id": "UNDERSTAND", "mode": "deterministic"},
            {"id": "PREPARE", "mode": "deterministic"},
            {"id": "RETRIEVE", "mode": "deterministic"},
            {"id": "MATCH_TWO_WAY", "mode": "deterministic"},
            {"id": "CHECKPOINT_HITL", "mode": "deterministic"},
            {"id": "HITL_DECISION", "mode": "non-deterministic"},
            {"id": "RECONCILE", "mode": "deterministic"},
            {"id": "APPROVE", "mode": "deterministic"},
            {"id": "POSTING", "mode": "deterministic"},
            {"id": "NOTIFY", "mode": "deterministic"},
            {"id": "COMPLETE", "mode": "deterministic"},
        ]
    }
