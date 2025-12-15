"""Agents module for invoice processing workflow."""
from typing import Type
from .base import BaseAgent
from .ingest_agent import IngestAgent
from .ocr_nlp_agent import OcrNlpAgent
from .normalize_agent import NormalizeAgent
from .erp_fetch_agent import ErpFetchAgent
from .matcher_agent import MatcherAgent
from .checkpoint_agent import CheckpointAgent
from .human_review_agent import HumanReviewAgent
from .reconcile_agent import ReconcileAgent
from .approval_agent import ApprovalAgent
from .posting_agent import PostingAgent
from .notify_agent import NotifyAgent
from .complete_agent import CompleteAgent


class AgentRegistry:
    """
    Registry to get agent instances by stage ID.
    
    Provides factory method to instantiate agents for workflow nodes.
    """
    
    _agents: dict[str, Type[BaseAgent]] = {
        "INTAKE": IngestAgent,
        "UNDERSTAND": OcrNlpAgent,
        "PREPARE": NormalizeAgent,
        "RETRIEVE": ErpFetchAgent,
        "MATCH_TWO_WAY": MatcherAgent,
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
        """
        Get agent instance for stage.
        
        Args:
            stage_id: Stage identifier (e.g., "INTAKE")
            config: Optional configuration for agent
            
        Returns:
            Agent instance for the stage
            
        Raises:
            ValueError: If stage_id is not found
        """
        agent_class = cls._agents.get(stage_id)
        if not agent_class:
            raise ValueError(f"Unknown stage: {stage_id}")
        return agent_class(config=config)
    
    @classmethod
    def list_stages(cls) -> list[str]:
        """Get list of all registered stage IDs."""
        return list(cls._agents.keys())


__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "IngestAgent",
    "OcrNlpAgent",
    "NormalizeAgent",
    "ErpFetchAgent",
    "MatcherAgent",
    "CheckpointAgent",
    "HumanReviewAgent",
    "ReconcileAgent",
    "ApprovalAgent",
    "PostingAgent",
    "NotifyAgent",
    "CompleteAgent",
]
