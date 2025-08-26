# Code Restoration Instructions

## What Happened
The Python source code was accidentally removed during documentation reorganization. The repository now has the correct structure with all documentation at the root level, but the Python modules need to be restored.

## What to Restore
You need to restore these directories and their Python files at the **root level** (not in an app/ subdirectory):

```
├── interfaces_mcp/               # Natural language processing MCP
│   ├── __init__.py
│   ├── server.py
│   └── tools.py
├── compute_mcp/                  # Simulation execution MCP  
│   ├── __init__.py
│   ├── server.py
│   └── runners/
│       ├── __init__.py
│       ├── materials_project.py
│       ├── lammps_kappa_gk.py
│       └── kaldo_bte.py
├── memory_mcp/                   # Asset and lineage storage MCP
│   ├── __init__.py
│   ├── server.py
│   └── store.py
├── common/                       # Shared utilities
│   ├── __init__.py
│   ├── schema.py
│   ├── ids.py
│   ├── units.py
│   └── io.py
├── cli/                          # Command-line interface
│   ├── __init__.py
│   └── mcg.py
├── examples/                     # Example workflows
│   ├── __init__.py
│   ├── scripted_flow.py
│   └── kaldo_bte_example.py
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_schema.py
│   ├── test_memory.py
│   ├── test_ids.py
│   └── test_integration.py
└── run_tests.py                  # Test runner
```

## After Restoring

Once you restore the code to the root level, these commands should work:

```bash
# Test everything works
python run_tests.py

# Run examples
python examples/scripted_flow.py
python examples/kaldo_bte_example.py

# Use CLI
python -m cli.mcg plan "Calculate thermal conductivity for silicon"
```

## What's Already Updated

✅ **README.md** - Updated for root-level structure  
✅ **All documentation** - Already at root level with correct paths  
✅ **Docker files** - Ready for root-level deployment  
✅ **Package configuration** - setup.py and pyproject.toml updated  

## Key Change Made

The repository structure changed from:
```
materialscodegraph/
├── app/
│   ├── interfaces_mcp/
│   ├── compute_mcp/
│   └── ...
```

To:
```  
materialscodegraph/
├── interfaces_mcp/
├── compute_mcp/
└── ...
```

All documentation and examples have been updated to reflect this flattened structure.

---

**After restoration, delete this file and you're ready for open source release!** 🚀