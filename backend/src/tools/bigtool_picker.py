"""Bigtool Picker for dynamic tool selection from pools."""
from typing import Optional, Any
from ..utils.logger import get_logger


class BigtoolPicker:
    """
    Singleton service for selecting tools from pools.
    
    Bigtool dynamically selects the appropriate tool from a pool
    based on capability requirements, availability, and context.
    """
    
    _instance: Optional["BigtoolPicker"] = None
    
    # Tool pools organized by capability
    POOLS = {
        "ocr": ["google_vision", "aws_textract", "tesseract"],
        "enrichment": ["clearbit", "people_data_labs", "vendor_db"],
        "erp_connector": ["sap_sandbox", "netsuite", "mock_erp"],
        "db": ["postgres", "sqlite", "dynamodb"],
        "email": ["sendgrid", "ses", "smartlead"],
        "storage": ["s3", "gcs", "local_fs"],
    }
    
    # Simulated tool availability (in production: real health checks)
    AVAILABILITY = {
        # OCR tools
        "google_vision": True,
        "aws_textract": True,
        "tesseract": True,
        
        # Enrichment tools
        "clearbit": True,
        "people_data_labs": True,
        "vendor_db": True,
        
        # ERP connectors
        "sap_sandbox": False,  # Simulating unavailable
        "netsuite": False,     # Simulating unavailable
        "mock_erp": True,
        
        # Databases
        "postgres": True,
        "sqlite": True,
        "dynamodb": False,
        
        # Email providers
        "sendgrid": True,
        "ses": True,
        "smartlead": False,
        
        # Storage
        "s3": True,
        "gcs": True,
        "local_fs": True,
    }
    
    # Tool priorities (lower is better)
    PRIORITIES = {
        # OCR - ordered by accuracy
        "google_vision": 1,
        "aws_textract": 2,
        "tesseract": 3,
        
        # Enrichment - ordered by data quality
        "clearbit": 1,
        "people_data_labs": 2,
        "vendor_db": 3,
        
        # ERP - ordered by preference
        "sap_sandbox": 1,
        "netsuite": 2,
        "mock_erp": 3,
        
        # DB - ordered by preference
        "postgres": 1,
        "sqlite": 2,
        "dynamodb": 3,
        
        # Email - ordered by reliability
        "sendgrid": 1,
        "ses": 2,
        "smartlead": 3,
        
        # Storage - ordered by preference
        "s3": 1,
        "gcs": 2,
        "local_fs": 3,
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.logger = get_logger("bigtool")
        self._initialized = True
    
    def select(
        self,
        capability: str,
        context: dict = None,
        pool_hint: list[str] = None
    ) -> dict[str, Any]:
        """
        Select the best available tool for a capability.
        
        Args:
            capability: Required capability (e.g., "ocr", "enrichment")
            context: Optional context for selection (file type, size, etc.)
            pool_hint: Optional list of preferred tools
            
        Returns:
            dict with selected tool info and selection metadata
        """
        context = context or {}
        
        # Get pool for capability
        pool = self.POOLS.get(capability, [])
        if not pool:
            self.logger.warning(f"No pool found for capability: {capability}")
            return self._create_selection_result(
                capability=capability,
                selected=None,
                reason="no_pool_found",
                pool=[]
            )
        
        # Filter by pool_hint if provided
        if pool_hint:
            pool = [t for t in pool if t in pool_hint]
        
        # Get available tools sorted by priority
        available_tools = [
            t for t in pool
            if self._is_available(t)
        ]
        
        if not available_tools:
            self.logger.warning(f"No available tools for capability: {capability}")
            return self._create_selection_result(
                capability=capability,
                selected=None,
                reason="no_available_tools",
                pool=pool
            )
        
        # Sort by priority
        available_tools.sort(key=lambda t: self.PRIORITIES.get(t, 999))
        
        # Select best available tool
        selected = available_tools[0]
        
        self.logger.info(
            f"Selected tool: {selected} for capability: {capability}",
            extra={"extra": {
                "capability": capability,
                "selected": selected,
                "pool": pool,
                "available": available_tools
            }}
        )
        
        return self._create_selection_result(
            capability=capability,
            selected=selected,
            reason=f"best_available_by_priority",
            pool=pool,
            available=available_tools
        )
    
    def _is_available(self, tool: str) -> bool:
        """Check if a tool is available."""
        return self.AVAILABILITY.get(tool, False)
    
    def _create_selection_result(
        self,
        capability: str,
        selected: Optional[str],
        reason: str,
        pool: list[str],
        available: list[str] = None
    ) -> dict[str, Any]:
        """Create standardized selection result."""
        return {
            "capability": capability,
            "selected_tool": selected,
            "pool": pool,
            "available": available or [],
            "reason": reason,
            "success": selected is not None
        }
    
    def get_pool(self, capability: str) -> list[str]:
        """Get all tools in a capability pool."""
        return self.POOLS.get(capability, [])
    
    def check_availability(self, tool: str) -> bool:
        """Check if a specific tool is available."""
        return self._is_available(tool)
    
    def set_availability(self, tool: str, available: bool) -> None:
        """Set tool availability (for testing/simulation)."""
        self.AVAILABILITY[tool] = available
    
    def list_capabilities(self) -> list[str]:
        """List all available capabilities."""
        return list(self.POOLS.keys())
