# MaterialsCodeGraph

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

> A minimal, production-ready implementation of MaterialsCodeGraph using Model Context Protocols (MCPs) for computational materials science workflows with full lineage tracking.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [User Guide](#user-guide)
- [API Documentation](#api-documentation)
- [Examples](#examples)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## Overview

MaterialsCodeGraph (MCG) enables **natural language driven computational workflows** for materials science. Simply describe what you want to calculate in plain English, and MCG handles the rest - from fetching crystal structures to running simulations to explaining results.

```bash
# Example: One command to get thermal conductivity
mcg plan "Calculate thermal conductivity for silicon using LAMMPS at 300-800K"
```

### Why MaterialsCodeGraph?

- **🗣️ Natural Language Interface**: No need to learn complex APIs or simulation inputs
- **🔄 Multiple Methods**: Compare LAMMPS MD with kALDo BTE in the same framework
- **📊 Full Provenance**: Every calculation step is tracked for reproducibility
- **🚀 Production Ready**: Docker support, comprehensive testing, extensible architecture

## Features

- **Natural Language Planning** - Parse tasks like "Calculate κ for mp-149 silicon"
- **Multi-Method Support** - LAMMPS Green-Kubo and kALDo BTE calculations
- **Materials Project Integration** - Automatic structure fetching by material ID
- **Complete Lineage Tracking** - Immutable provenance with content-based hashing
- **Rich Analysis** - Thermal conductivity tensors, phonon properties, trend analysis
- **Extensible Architecture** - Easy to add VASP, Quantum ESPRESSO, or other codes

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Materials Project API key ([get one free](https://materialsproject.org/api))

### Installation

```bash
# Clone the repository
git clone https://github.com/materialscodegraph/materialscodegraph.git
cd materialscodegraph

# Install dependencies
pip install -r requirements.txt

# Set your Materials Project API key
export MP_API_KEY="your_api_key_here"
```

### Your First Calculation

Calculate thermal conductivity of silicon in 3 steps:

```bash
# 1. Plan the calculation using natural language
mcg plan "Calculate thermal conductivity for mp-149 silicon at 300-800K using LAMMPS"

# 2. Execute the workflow
mcg start --plan plan.json

# 3. View results
mcg results R12345678
```

Output:
```
Thermal Conductivity κ(T):
Temperature [K]  |  κ [W/(m·K)]
--------------------------------
     300        |   148.50
     400        |    95.20
     500        |    68.10
     600        |    51.30
     700        |    40.20
     800        |    32.50
```

## Installation

### Option 1: Standard Installation

```bash
git clone https://github.com/materialscodegraph/materialscodegraph.git
cd materialscodegraph
pip install -e .
```

### Option 2: Docker Installation

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t mcg:latest .
docker run -e MP_API_KEY=$MP_API_KEY mcg:latest
```

### Option 3: Development Installation

```bash
# Clone and create virtual environment
git clone https://github.com/materialscodegraph/materialscodegraph.git
cd materialscodegraph
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with extras
pip install -e ".[dev]"

# Run tests to verify installation
python run_tests.py
```

## User Guide

### Basic Usage

MCG uses a simple command-line interface with five main commands:

| Command | Description | Example |
|---------|-------------|---------|
| `plan` | Create workflow from natural language | `mcg plan "Calculate κ for silicon"` |
| `start` | Execute a workflow plan | `mcg start --plan plan.json` |
| `status` | Check calculation progress | `mcg status R12345678` |
| `results` | Retrieve calculation results | `mcg results R12345678` |
| `explain` | Get human-readable explanation | `mcg explain R12345678` |

### Natural Language Examples

MCG understands various ways to describe calculations:

```bash
# Basic thermal conductivity
mcg plan "Calculate thermal conductivity for silicon"

# Specify temperature range
mcg plan "Get κ for mp-149 from 300K to 800K"

# Choose specific method
mcg plan "Use LAMMPS Green-Kubo for silicon thermal conductivity at 300-800K"

# Use Boltzmann Transport Equation
mcg plan "Calculate κ using kALDo BTE for silicon with 25x25x25 mesh"

# Compare methods
mcg plan "Compare LAMMPS and kALDo thermal conductivity for silicon"
```

### Understanding Results

Results include detailed thermal transport properties:

```python
# LAMMPS Green-Kubo Results
{
  "T_K": [300, 400, 500, 600, 700, 800],
  "kappa_W_per_mK": [148.5, 95.2, 68.1, 51.3, 40.2, 32.5],
  "method": "Green-Kubo",
  "supercell": [20, 20, 20]
}

# kALDo BTE Results (includes tensor & phonons)
{
  "T_K": [300, 400, 500],
  "kappa_W_per_mK": [200.0, 137.6, 102.9],
  "kappa_xx_W_per_mK": [204.0, 140.3, 105.0],
  "kappa_yy_W_per_mK": [196.0, 134.8, 100.8],
  "kappa_zz_W_per_mK": [200.0, 137.6, 102.9],
  "phonon_freq_THz": [2.1, 4.5, 7.8, 12.3, 14.6],
  "lifetimes_ps": [47.6, 22.2, 12.8, 8.1, 6.8],
  "method": "BTE",
  "solver": "kALDo"
}
```

## API Documentation

### Python API

```python
from interfaces_mcp.tools import InterfacesTools
from compute_mcp.runners.lammps_kappa_gk import LAMMPSKappaGKRunner
from memory_mcp.store import MemoryStore

# Initialize components
interfaces = InterfacesTools()
memory = MemoryStore()

# Plan a calculation
task = "Calculate thermal conductivity for silicon at 300K"
plan = interfaces.plan(task)

# Run simulation
runner = LAMMPSKappaGKRunner()
results = runner.run(run_obj, assets, params)

# Store with lineage
memory.put_asset(results_asset)
memory.append_edge(lineage_edge)
```

### MCP Tool Interfaces

#### Interfaces MCP
- `plan(nl_task: str)` - Convert natural language to execution plan
- `explain(results: List[Asset], ledger: List[Edge])` - Generate human explanation

#### Compute MCP
- `start(runner_kind: str, assets: List, params: Dict)` - Start calculation
- `status(run_id: str)` - Check calculation status
- `results(run_id: str)` - Retrieve results and lineage

#### Memory MCP
- `put_assets(assets: List[Asset])` - Store computational assets
- `get_assets(ids: List[str])` - Retrieve assets by ID
- `link(edges: List[Edge])` - Record lineage relationships
- `ledger(select: Dict)` - Query provenance graph

## Examples

### Example 1: Silicon Thermal Conductivity (LAMMPS)

```python
#!/usr/bin/env python3
"""Calculate silicon thermal conductivity using LAMMPS Green-Kubo"""

from cli.mcg import MCGClient

client = MCGClient()

# Plan the calculation
plan = client.plan("Calculate thermal conductivity for mp-149 silicon at 300-800K using LAMMPS")

# Execute
run_id = client.start(plan)
print(f"Started calculation: {run_id}")

# Get results
results = client.results(run_id)
for T, k in zip(results["T_K"], results["kappa_W_per_mK"]):
    print(f"{T}K: {k:.2f} W/(m·K)")
```

### Example 2: Phonon Analysis with kALDo

```python
#!/usr/bin/env python3
"""Analyze phonon transport using kALDo BTE"""

from cli.mcg import MCGClient

client = MCGClient()

# Use BTE for detailed phonon analysis
plan = client.plan("Calculate thermal conductivity using kALDo BTE for silicon with 30x30x30 mesh")
run_id = client.start(plan)

results = client.results(run_id)
print(f"Average κ at 300K: {results['kappa_W_per_mK'][0]:.1f} W/(m·K)")
print(f"Phonon frequency range: {min(results['phonon_freq_THz']):.1f}-{max(results['phonon_freq_THz']):.1f} THz")
print(f"Average lifetime: {sum(results['lifetimes_ps'])/len(results['lifetimes_ps']):.1f} ps")
```

### Example 3: Method Comparison

See `examples/scripted_flow.py` and `examples/kaldo_bte_example.py` for complete workflows.

## Architecture

MCG uses a three-MCP architecture for clean separation of concerns:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Interfaces MCP │────▶│   Compute MCP   │────▶│   Memory MCP    │
│                 │     │                 │     │                 │
│ • NL Planning   │     │ • MP Fetcher    │     │ • Asset Store   │
│ • Explanation   │     │ • LAMMPS Runner │     │ • Lineage Graph │
│                 │     │ • kALDo Runner  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Adding New Methods

To add support for a new computational method (e.g., VASP):

1. **Create Runner** (`compute_mcp/runners/vasp.py`):
```python
class VASPRunner:
    def run(self, run_obj, assets, params):
        # Your implementation
        return {"assets": results, "edges": lineage}
```

2. **Register Runner** (`compute_mcp/server.py`):
```python
elif runner_kind == "VASP":
    runner = VASPRunner()
```

3. **Update NL Parser** (`interfaces_mcp/tools.py`):
```python
if 'vasp' in task_lower or 'dft' in task_lower:
    runner_kind = "VASP"
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.

## Testing

```bash
# Run all tests
python run_tests.py

# Run specific test module
python tests/test_schema.py

# With pytest (if installed)
pytest tests/ -v --cov=.
```

## Deployment

### Local Development
```bash
python -m cli.mcg plan "your task"
```

### Docker Deployment
```bash
docker-compose up -d
```

### Production Deployment
See `docker-compose.yml` for production configuration with PostgreSQL and Redis.

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `MP_API_KEY` | Materials Project API key | Yes |
| `MCG_STORAGE_PATH` | Data storage directory | No |
| `MCG_LOG_LEVEL` | Logging level (INFO, DEBUG) | No |
| `LAMMPS_IMAGE` | Docker image for LAMMPS | No |
| `KALDO_IMAGE` | Docker image for kALDo | No |

### Configuration File

Create `.env` file for persistent configuration:

```bash
MP_API_KEY=your_materials_project_api_key
MCG_STORAGE_PATH=/opt/mcg/data
MCG_LOG_LEVEL=INFO
```

## Troubleshooting

### Common Issues

**Issue: "No module named 'numpy'"**
```bash
pip install numpy
```

**Issue: "MP_API_KEY not set"**
```bash
export MP_API_KEY="your_api_key_here"
```

**Issue: "Run not found"**
- Ensure the run ID is correct
- Check if calculation completed: `mcg status RUN_ID`

### Getting Help

- 📖 [Documentation](https://github.com/materialscodegraph/materialscodegraph/wiki)
- 💬 [Discussions](https://github.com/materialscodegraph/materialscodegraph/discussions)
- 🐛 [Issue Tracker](https://github.com/materialscodegraph/materialscodegraph/issues)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Steps

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Run tests (`python run_tests.py`)
5. Submit pull request

## Citation

If you use MaterialsCodeGraph in your research, please cite:

```bibtex
@software{materialscodegraph2024,
  title = {MaterialsCodeGraph: MCP-based Materials Science Workflows},
  author = {MaterialsCodeGraph Contributors},
  year = {2024},
  url = {https://github.com/materialscodegraph/materialscodegraph},
  version = {1.0.0}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Materials Project for structure data and API
- LAMMPS and kALDo communities for simulation tools
- MCP specification contributors
- All contributors to this project

---

**Built with ❤️ for the computational materials science community**