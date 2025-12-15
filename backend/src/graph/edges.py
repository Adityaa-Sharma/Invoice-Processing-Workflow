"""Conditional edge functions for LangGraph workflow."""
from .state import InvoiceWorkflowState
from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger("edges")


def should_checkpoint(state: InvoiceWorkflowState) -> str:
    """
    Determine if HITL checkpoint is needed after matching.
    
    This conditional edge routes to CHECKPOINT_HITL if match failed,
    or directly to RECONCILE if match passed.
    
    Args:
        state: Current workflow state
        
    Returns:
        "checkpoint" if match failed and HITL needed
        "continue" if match passed and can proceed
    """
    match_result = state.get("match_result", "")
    match_score = state.get("match_score", 0)
    threshold = settings.MATCH_THRESHOLD
    
    logger.info(
        f"Evaluating match result: score={match_score}, result={match_result}, threshold={threshold}"
    )
    
    if match_result == "FAILED" or match_score < threshold:
        logger.info("Routing to CHECKPOINT_HITL - match failed")
        return "checkpoint"
    
    logger.info("Routing to RECONCILE - match passed")
    return "continue"


def after_hitl_decision(state: InvoiceWorkflowState) -> str:
    """
    Route based on human decision after HITL review.
    
    Args:
        state: Current workflow state
        
    Returns:
        "accept" to continue to RECONCILE
        "reject" to end with MANUAL_HANDOFF
    """
    decision = state.get("human_decision", "")
    
    logger.info(f"Routing after HITL decision: {decision}")
    
    if decision == "ACCEPT":
        logger.info("HITL decision ACCEPT - routing to RECONCILE")
        return "accept"
    
    logger.info("HITL decision REJECT - routing to MANUAL_HANDOFF")
    return "reject"
