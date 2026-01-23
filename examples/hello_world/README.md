# OSQAr Hello World Example

This example demonstrates the core capabilities of OSQAr through a simple, domain-agnostic temperature monitoring component.

## Overview

**Component**: Thermal Sensor Interface Module  
**Purpose**: Monitor temperature and report safe/unsafe states  
**Domain**: Generic (applicable to medical devices, industrial machinery, automotive, robotics, etc.)

## What This Example Shows

1. **Requirements Traceability**: Safety requirements linked to functional and design specifications
2. **ISO 26262 Compliance**: Structured requirement IDs, traceability matrices, and verification mapping
3. **Architecture Documentation**: System diagrams with PlantUML
4. **Test Mapping**: Requirements traced to test cases for verification

## Files

- `index.rst` - Documentation entry point
- `01_requirements.rst` - Safety and functional requirements
- `02_architecture.rst` - System design and data flow
- `03_verification.rst` - Test and verification methods
- `diagrams/` - PlantUML architecture diagrams

## Building the Example

```bash
cd examples/hello_world
poetry install  # If not already done from root
sphinx-build -b html . _build/html
# Open _build/html/index.html in your browser
```

## Key Takeaways

- Requirements use structured IDs: `REQ_SAFETY_*`, `REQ_FUNC_*`, `ARCH_*`, `TEST_*`
- Each requirement links upstream/downstream for traceability
- Architecture diagrams show component boundaries and data flow
- Test cases are mapped to requirements for compliance verification
