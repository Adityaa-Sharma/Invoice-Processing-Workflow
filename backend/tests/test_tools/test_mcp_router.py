"""Tests for MCP Router."""
import pytest
from src.tools.mcp_router import MCPRouter, MCPServer


def test_mcp_router_routing():
    """Test ability routing to correct server."""
    router = MCPRouter()
    
    # COMMON abilities
    assert router.get_server("validate_schema") == MCPServer.COMMON
    assert router.get_server("normalize_vendor") == MCPServer.COMMON
    assert router.get_server("match_engine") == MCPServer.COMMON
    
    # ATLAS abilities
    assert router.get_server("ocr_extract") == MCPServer.ATLAS
    assert router.get_server("enrich_vendor") == MCPServer.ATLAS
    assert router.get_server("post_to_erp") == MCPServer.ATLAS


def test_mcp_router_list_abilities():
    """Test listing abilities by server."""
    router = MCPRouter()
    
    common_abilities = router.list_abilities(MCPServer.COMMON)
    atlas_abilities = router.list_abilities(MCPServer.ATLAS)
    
    assert "validate_schema" in common_abilities
    assert "ocr_extract" in atlas_abilities


@pytest.mark.asyncio
async def test_mcp_router_execute_common():
    """Test executing COMMON server ability."""
    router = MCPRouter()
    
    result = await router.execute("validate_schema", {"invoice": {}})
    
    assert result is not None
    assert result.get("valid") is True


@pytest.mark.asyncio
async def test_mcp_router_execute_atlas():
    """Test executing ATLAS server ability."""
    router = MCPRouter()
    
    result = await router.execute("ocr_extract", {"image": "test.pdf"})
    
    assert result is not None
    assert "text" in result
    assert result.get("tool") == "google_vision"
