"""Tests for BigtoolPicker."""
import pytest
from src.tools.bigtool_picker import BigtoolPicker


def test_bigtool_singleton():
    """Test BigtoolPicker is a singleton."""
    picker1 = BigtoolPicker()
    picker2 = BigtoolPicker()
    
    assert picker1 is picker2


def test_bigtool_select_ocr(bigtool):
    """Test OCR tool selection."""
    result = bigtool.select("ocr")
    
    assert result["success"] is True
    assert result["capability"] == "ocr"
    assert result["selected_tool"] == "google_vision"
    assert "pool" in result


def test_bigtool_select_enrichment(bigtool):
    """Test enrichment tool selection."""
    result = bigtool.select("enrichment")
    
    assert result["success"] is True
    assert result["selected_tool"] == "clearbit"


def test_bigtool_select_erp(bigtool):
    """Test ERP connector selection (fallback to mock)."""
    result = bigtool.select("erp_connector")
    
    assert result["success"] is True
    # sap_sandbox and netsuite are unavailable, should fall back to mock_erp
    assert result["selected_tool"] == "mock_erp"


def test_bigtool_select_with_hint(bigtool):
    """Test selection with pool hint."""
    result = bigtool.select("ocr", pool_hint=["tesseract"])
    
    assert result["success"] is True
    assert result["selected_tool"] == "tesseract"


def test_bigtool_select_unknown_capability(bigtool):
    """Test selection with unknown capability."""
    result = bigtool.select("unknown_capability")
    
    assert result["success"] is False
    assert result["selected_tool"] is None


def test_bigtool_list_capabilities(bigtool):
    """Test listing all capabilities."""
    capabilities = bigtool.list_capabilities()
    
    expected = ["ocr", "enrichment", "erp_connector", "db", "email", "storage"]
    assert set(capabilities) == set(expected)
