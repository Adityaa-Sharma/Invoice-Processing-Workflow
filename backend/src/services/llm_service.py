"""LLM Service - Gemini Integration for Invoice Processing Agent.

Provides LLM capabilities for intelligent decision making in the workflow.
Uses Google's Gemini model via LangChain.
"""
from typing import Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger("llm_service")

# Agent personality prompt
AGENT_PERSONALITY = """You are **Langie – the Invoice Processing LangGraph Agent**.

You think in structured stages.
Each node is a well-defined processing phase.
You always carry forward state variables between nodes.
You know when to execute deterministic steps and when to choose dynamically.
You orchestrate MCP clients to call COMMON or ATLAS abilities as required.
You use Bigtool whenever a tool must be selected from a pool.
You log every decision, every tool choice, and every state update.
You always produce clean structured output.

Current Stage: {stage}
Task: {task}
"""

# Singleton LLM instance
_llm_instance: Optional[ChatGoogleGenerativeAI] = None


def get_llm() -> ChatGoogleGenerativeAI:
    """Get or create the LLM instance (singleton)."""
    global _llm_instance
    
    if _llm_instance is not None:
        return _llm_instance
    
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, LLM features disabled")
        return None
    
    logger.info(f"Initializing Gemini LLM: {settings.LLM_MODEL}")
    
    _llm_instance = ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=None,
        timeout=30,
        max_retries=settings.LLM_MAX_RETRIES,
    )
    
    return _llm_instance


async def invoke_agent(
    stage: str,
    task: str,
    context: dict[str, Any],
    output_format: str = None
) -> dict[str, Any]:
    """
    Invoke the LLM agent for a specific stage task.
    
    Args:
        stage: Current workflow stage (e.g., "UNDERSTAND", "PREPARE")
        task: Task description
        context: Context data for the task
        output_format: Expected output format description
        
    Returns:
        dict with LLM response and metadata
    """
    llm = get_llm()
    
    if llm is None:
        logger.warning(f"LLM not available for stage {stage}, using fallback")
        return {
            "success": False,
            "stage": stage,
            "error": "LLM not configured",
            "fallback": True
        }
    
    try:
        # Build the prompt
        system_prompt = AGENT_PERSONALITY.format(stage=stage, task=task)
        
        context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
        
        user_prompt = f"""Process this invoice data:

Context:
{context_str}

Task: {task}

{f"Expected output format: {output_format}" if output_format else ""}

Analyze the data and provide your structured response."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.info(f"Invoking LLM for stage: {stage}")
        response = await llm.ainvoke(messages)
        
        return {
            "success": True,
            "stage": stage,
            "response": response.content,
            "usage": getattr(response, "usage_metadata", None)
        }
        
    except Exception as e:
        logger.error(f"LLM invocation failed for stage {stage}: {e}")
        return {
            "success": False,
            "stage": stage,
            "error": str(e),
            "fallback": True
        }


async def select_tool_with_reasoning(
    capability: str,
    pool: list[str],
    context: dict[str, Any]
) -> dict[str, Any]:
    """
    Use LLM to intelligently select a tool from a pool.
    
    Args:
        capability: Required capability (e.g., "ocr", "enrichment")
        pool: Available tools in the pool
        context: Context for selection (file type, size, etc.)
        
    Returns:
        dict with selected tool and reasoning
    """
    llm = get_llm()
    
    if llm is None:
        # Fallback: return first available tool
        return {
            "selected_tool": pool[0] if pool else None,
            "reason": "LLM not available, using first tool",
            "fallback": True
        }
    
    try:
        context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
        
        prompt = f"""You are selecting a tool for the "{capability}" capability.

Available tools: {', '.join(pool)}

Context:
{context_str}

Select the best tool and explain why in 1 sentence.

Respond in this exact format:
SELECTED: <tool_name>
REASON: <one sentence explanation>"""

        messages = [HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)
        
        # Parse response
        lines = response.content.strip().split('\n')
        selected = None
        reason = "No reason provided"
        
        for line in lines:
            if line.startswith("SELECTED:"):
                selected = line.replace("SELECTED:", "").strip().lower()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
        
        # Validate selection is in pool
        if selected not in [t.lower() for t in pool]:
            selected = pool[0]
            reason = f"LLM selected invalid tool, falling back to {selected}"
        
        return {
            "selected_tool": selected,
            "reason": reason,
            "llm_response": response.content
        }
        
    except Exception as e:
        logger.error(f"Tool selection LLM call failed: {e}")
        return {
            "selected_tool": pool[0] if pool else None,
            "reason": f"LLM error, using fallback: {str(e)}",
            "fallback": True
        }


async def analyze_match_result(
    invoice_data: dict,
    po_data: dict,
    match_score: float,
    threshold: float
) -> dict[str, Any]:
    """
    Use LLM to analyze match results and provide insights.
    
    Args:
        invoice_data: Invoice details
        po_data: Purchase order details
        match_score: Computed match score
        threshold: Match threshold
        
    Returns:
        dict with analysis and recommendations
    """
    llm = get_llm()
    
    if llm is None:
        return {
            "analysis": "LLM not available",
            "fallback": True
        }
    
    try:
        prompt = f"""Analyze this invoice-to-PO matching result:

Invoice:
- Amount: {invoice_data.get('amount')}
- Vendor: {invoice_data.get('vendor_name')}
- Date: {invoice_data.get('invoice_date')}

PO:
- Amount: {po_data.get('amount')}
- Vendor: {po_data.get('vendor_name')}

Match Score: {match_score:.2f}
Threshold: {threshold:.2f}
Result: {"MATCHED" if match_score >= threshold else "FAILED"}

Provide a brief analysis (2-3 sentences) of why this match succeeded or failed,
and any recommendations for the reviewer if it failed."""

        messages = [HumanMessage(content=prompt)]
        response = await llm.ainvoke(messages)
        
        return {
            "analysis": response.content,
            "match_score": match_score,
            "passed": match_score >= threshold
        }
        
    except Exception as e:
        logger.error(f"Match analysis LLM call failed: {e}")
        return {
            "analysis": f"Analysis unavailable: {str(e)}",
            "fallback": True
        }
