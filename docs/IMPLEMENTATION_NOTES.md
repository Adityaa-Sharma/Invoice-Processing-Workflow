# Implementation Notes - Bigtool & Routing

## Key Clarifications

### 1. Bigtool is a MOCK Layer

The task does NOT require real integrations. We implement:

```
✅ BigtoolPicker class with selection logic
✅ Pool configuration (which tools exist)
✅ Availability simulation
✅ Selection logging
✅ Fallback chain logic

❌ Real Google Vision API calls
❌ Real Clearbit API calls
❌ Real SAP connections
```

### 2. Two-Layer Routing Summary

```
Layer 1: MCP Router
─────────────────────
Question: "Does this need external data?"
Answer: COMMON (no) or ATLAS (yes)

Layer 2: Bigtool Picker  
─────────────────────
Question: "Which tool in the pool should handle this?"
Answer: First available based on priority + context
```

### 3. What "Mock" Means

```python
# Instead of this (real API):
def google_vision_ocr(image):
    client = vision.ImageAnnotatorClient()
    response = client.text_detection(image=image)
    return response.text_annotations

# We implement this (mock):
def google_vision_ocr(image):
    return {
        "tool": "google_vision",
        "text": "INVOICE #123\nVendor: Acme\nAmount: $15,000",
        "confidence": 0.95
    }
```

### 4. Demo Flow Shows Real Logic, Fake Data

The demo will show:
- ✅ Real routing decisions (logged)
- ✅ Real tool selection logic (logged)
- ✅ Real state management (persisted)
- ✅ Real checkpoint/resume (working)
- ✅ Fake tool outputs (hardcoded responses)

### 5. Why This Approach?

The task tests your ability to:
1. Design a proper orchestration system
2. Implement LangGraph correctly
3. Handle HITL checkpoint/resume
4. Structure code for real integrations

NOT your ability to:
1. Get API keys for 15 services
2. Set up cloud infrastructure
3. Handle real OCR edge cases
