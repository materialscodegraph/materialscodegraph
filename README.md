# MaterialsCodeGraph

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

> An AI-powered computational materials science platform using natural language to orchestrate LAMMPS, MaterialsProject, and other simulation tools with full provenance tracking.

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

MaterialsCodeGraph (MCG) enables **AI-powered computational workflows** for materials science. Simply describe what you want to calculate in plain English, and MCG's AI system intelligently parses parameters, selects appropriate simulation tools, and executes complex workflows.

```bash
# Example: AI-powered thermal conductivity calculation
python -m cli.mcg plan "Calculate thermal conductivity for mp-149 silicon at 300-500K using LAMMPS with 20x20x20 supercell" --save
python -m cli.mcg start --plan plan.json
```

### Why MaterialsCodeGraph?

- **🤖 AI-Powered Parsing**: Claude AI intelligently extracts simulation parameters from natural language
- **🗣️ Natural Language Interface**: No need to learn complex APIs or simulation inputs
- **🔄 Multiple Skills**: Compare LAMMPS MD with MaterialsProject data in unified workflows
- **📊 Full Provenance**: Every calculation step is tracked with immutable lineage
- **⚡ Smart Configuration**: Zero hardcoding - everything driven by JSON configuration files

## Features

- **🤖 AI-Powered Parameter Extraction** - Claude AI intelligently parses complex natural language descriptions
- **📋 Smart Planning with Logging** - Full transparency into AI decision-making process
- **🔧 Multi-Method Support** - LAMMPS Green-Kubo simulations and MaterialsProject data integration
- **📊 Materials Project Integration** - Automatic structure fetching and property lookup
- **🔗 Complete Lineage Tracking** - Immutable provenance with content-based hashing
- **⚙️ Configuration-Driven** - Zero hardcoded tool knowledge, everything in JSON configs
- **🚀 Extensible Architecture** - Easy to add new simulation tools via configuration

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Materials Project API key ([get one free](https://materialsproject.org/api)) - optional for MaterialsProject workflows

### Installation

```bash
# Clone the repository
git clone https://github.com/materialscodegraph/materialscodegraph.git
cd materialscodegraph

# Install dependencies (includes AI packages)
pip install anthropic python-dotenv

# Set up API keys in .env file
echo "ANTHROPIC_API_KEY=your_anthropic_key_here" > .env
echo "MP_API_KEY=your_materials_project_key_here" >> .env
```

### Your First Calculation

Calculate thermal conductivity of silicon with AI-powered parsing:

```bash
# 1. Plan the calculation using natural language (AI parses everything!)
python -m cli.mcg plan "Calculate thermal conductivity for mp-149 silicon at 300-500K using LAMMPS with 20x20x20 supercell" --save

# 2. Execute the workflow
python -m cli.mcg start --plan plan.json

# 3. View results
python -m cli.mcg results R12345678
```

**See the AI in action:**
```
🤖 AI Parameter Extraction
📝 Task: calculate thermal conductivity for mp-149 silicon at 300-500k using lammps with 20x20x20 supercell
🔍 Available parameters: ['material_id', 'formula', 'property', 'temperature', 'supercell', ...]
🔮 AI Response: {
  "material_id": "mp-149",
  "formula": "silicon",
  "property": "thermal conductivity",
  "temperature": [300, 400, 500],
  "supercell": [20, 20, 20]
}
✅ Parsed parameters: 5 parameters extracted
🎯 Total extracted: 5 parameters
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

MCG uses an AI-powered command-line interface with five main commands:

| Command | Description | Example |
|---------|-------------|---------|
| `plan` | AI-powered workflow creation | `python -m cli.mcg plan "Calculate κ for silicon" --save` |
| `start` | Execute a workflow plan | `python -m cli.mcg start --plan plan.json` |
| `status` | Check calculation progress | `python -m cli.mcg status R12345678` |
| `results` | Retrieve calculation results | `python -m cli.mcg results R12345678` |
| `explain` | Get human-readable explanation | `python -m cli.mcg explain R12345678` |

### Plan Command Options

| Flag | Description | Example |
|------|-------------|---------|
| `--save` | Save to plan.json | `python -m cli.mcg plan "task" --save` |
| `-o FILE` | Save to custom file | `python -m cli.mcg plan "task" -o my_plan.json` |
| *(none)* | Show output only | `python -m cli.mcg plan "task"` |

### Natural Language Examples

MCG's AI system understands various ways to describe calculations:

```bash
# Basic thermal conductivity (AI infers reasonable defaults)
python -m cli.mcg plan "Calculate thermal conductivity for silicon" --save

# Specify temperature range (AI parses "300K to 800K")
python -m cli.mcg plan "Get κ for mp-149 from 300K to 800K" --save

# Complex specifications (AI extracts all parameters)
python -m cli.mcg plan "Study heat transport in aluminum oxide at room temperature and 800K with medium simulation cell" --save

# Materials Project integration (AI detects mp- prefix)
python -m cli.mcg plan "Pull mp-2534 data and calculate thermal conductivity from 273K to 373K" --save

# Natural conversational language
python -m cli.mcg plan "I want to simulate thermal conductivity of mp-149 silicon using LAMMPS at 300-500K with 20x20x20 supercell" --save
```

**AI Understanding Examples:**
- **"room temperature"** → `temperature: [300]`
- **"300K to 800K"** → `temperature: [300, 400, 500, 600, 700, 800]`
- **"aluminum oxide"** → `material_id: "aluminum oxide", formula: "Al2O3"`
- **"20x20x20 supercell"** → `supercell: [20, 20, 20]`
- **"medium sized simulation"** → `supercell: [15, 15, 15]` (reasonable default)

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

## Configuration

MCG uses **JSON configuration files** in the `configs/` directory to define all computational tools and their skills. This enables perfect encapsulation - the core system has zero knowledge of specific simulation codes.

### Configuration Architecture

Each computational tool is defined by a `.json` file in `configs/`:
- `configs/lammps.json` - LAMMPS molecular dynamics
- `configs/materialsproject.json` - Materials Project data fetching

### Configuration Structure

Example `configs/lammps.json`:
```json
{
  "name": "LAMMPS",
  "description": "Molecular dynamics simulator",
  "understands": {
    "thermal conductivity": {
      "aliases": ["kappa", "heat transport"],
      "method": "green_kubo",
      "keywords": ["thermal", "conductivity", "kappa"]
    }
  },
  "parameter_mapping": {
    "temperature": ["temperature", "T_K", "temp"],
    "supercell": ["supercell", "cell", "size"]
  },
  "execution": {
    "local": {
      "executable": "/usr/local/bin/lmp_serial",
      "command_template": "{executable} -in {input_file}"
    }
  },
  "templates": {
    "green_kubo": {
      "needs": ["temperature", "supercell"],
      "files": {
        "input_script": {
          "name": "in.kappa_gk",
          "content": "# LAMMPS Green-Kubo input template..."
        }
      }
    }
  }
}
```

### Execution Modes

- **docker**: Runs LAMMPS in a Docker container
- **local**: Uses locally installed LAMMPS executable  
- **hpc**: Submits jobs to HPC scheduler (SLURM)

### Environment Variables

Required and optional environment variables:

**Required:**
- `ANTHROPIC_API_KEY`: Your Anthropic Claude API key for AI parsing

**Optional:**
- `MP_API_KEY`: Materials Project API key (only needed for MP workflows)
- `MCG_STORAGE_PATH`: Base path for data storage
- `MCG_LOG_LEVEL`: Logging level (INFO, DEBUG)

### Quick Setup Examples

#### For Local LAMMPS Installation
```json
{
  "codes": {
    "lammps": {
      "execution": {
        "mode": "local",
        "local": {
          "executable": "/usr/bin/lmp",
          "mpi_command": "mpirun -np 8"
        }
      }
    }
  }
}
```

#### For Docker Execution
```json
{
  "codes": {
    "lammps": {
      "execution": {
        "mode": "docker",
        "docker": {
          "image": "lammps/lammps:stable",
          "gpu": {
            "enabled": true,
            "runtime": "nvidia"
          }
        }
      }
    }
  }
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

### Project Structure

```
materialscodegraph/
├── interfaces_mcp/               # Natural language processing
├── compute_mcp/                  # Simulation runners
├── memory_mcp/                   # Asset and lineage storage
├── common/                       # Shared utilities
├── cli/                          # Command-line interface
├── examples/                     # Example workflows
├── tests/                        # Test suite
├── lammps/                       # LAMMPS reference code
├── kaldo/                        # kALDo reference code
├── README.md                     # This file
├── LICENSE                       # MIT license
├── requirements.txt              # Python dependencies
└── docker-compose.yml            # Docker orchestration
```

### Adding New Skills

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
| `ANTHROPIC_API_KEY` | Claude AI API key for parameter parsing | **Yes** |
| `MP_API_KEY` | Materials Project API key | Only for MP workflows |
| `MCG_STORAGE_PATH` | Data storage directory | No |
| `MCG_LOG_LEVEL` | Logging level (INFO, DEBUG) | No |

### Configuration File

Create `.env` file for persistent configuration:

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
MP_API_KEY=your_materials_project_api_key
MCG_STORAGE_PATH=/opt/mcg/data
MCG_LOG_LEVEL=INFO
```

## Troubleshooting

### Common Issues

**Issue: "Interfaces MCP tools not available"**
```bash
pip install anthropic python-dotenv
```

**Issue: "ANTHROPIC_API_KEY not set"**
```bash
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

**Issue: "AI parameter extraction failed"**
- Check your internet connection
- Verify API key is valid
- System will fallback to basic regex parsing

**Issue: "MP_API_KEY not set"**
```bash
echo "MP_API_KEY=your_key_here" >> .env
```

**Issue: "Run not found"**
- Ensure the run ID is correct
- Check if calculation completed: `python -m cli.mcg status RUN_ID`

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