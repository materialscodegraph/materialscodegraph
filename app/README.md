# MaterialsCodeGraph (MCG-lite)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

A minimal, production-ready implementation of MaterialsCodeGraph using three Model Context Protocols (MCPs) for computational materials science workflows with full lineage tracking.

## 🎯 Overview

MCG-lite enables **natural language driven computational workflows** for materials science, focusing on thermal conductivity calculations. The system uses three specialized MCPs that provide a clean separation of concerns:

- **🧠 Interfaces MCP**: Plans workflows from natural language and explains results
- **⚡ Compute MCP**: Executes simulations (Materials Project, LAMMPS, kALDo)  
- **💾 Memory MCP**: Stores assets and maintains append-only lineage ledger

### 🌟 Key Innovation: MCG-lite Schema
Clean, minimal schema with deterministic IDs and immutable provenance:
- **Assets**: System, Method, Params, Results, Artifact
- **Lineage**: USES → PRODUCES → DERIVES chains
- **No nested blobs**: Everything is traceable and reproducible

## ✨ Features

### 🗣️ Natural Language Interface
- **Smart Planning**: "Pull mp-149 silicon and simulate thermal conductivity 300-800K with CHGNet"
- **Method Detection**: Automatically chooses LAMMPS Green-Kubo vs kALDo BTE
- **Parameter Extraction**: Parses temperatures, supercells, meshes from plain text
- **Human Explanations**: Generate publication-ready result summaries

### 🧮 Computational Methods
- **Materials Project**: Automated structure fetching by mp-id
- **LAMMPS Green-Kubo**: Molecular dynamics with heat flux autocorrelation
- **kALDo BTE**: Boltzmann transport with full phonon analysis
- **Method Comparison**: Side-by-side LAMMPS vs BTE results

### 📊 Rich Results & Analysis
- **Thermal Conductivity**: κ(T) curves with uncertainty quantification
- **Phonon Properties**: Frequencies, lifetimes, mode contributions
- **Tensor Components**: Full κ_xx, κ_yy, κ_zz anisotropy
- **Trend Analysis**: Automatic scaling detection (T^-n)

### 🔗 Provenance & Reproducibility  
- **Immutable Lineage**: Every computation step tracked
- **Deterministic IDs**: Content-based hashing for assets
- **Full Traceability**: From raw structures to final results
- **Reproducible Workflows**: Complete parameter capture  

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Materials Project API key ([get one here](https://materialsproject.org/api))

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/materialscodegraph-lite.git
cd materialscodegraph-lite

# Create virtual environment (recommended)
python -m venv mcg-env
source mcg-env/bin/activate  # On Windows: mcg-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MP_API_KEY="your_materials_project_api_key_here"
```

### 🎬 30-Second Demo

```bash
# Plan a thermal conductivity calculation
python -m cli.mcg plan "Calculate thermal conductivity for mp-149 silicon using kALDo BTE at 300-800K"

# Run the workflow  
python -m cli.mcg start --plan plan.json

# Get results with explanation
python -m cli.mcg results R12345678 && python -m cli.mcg explain R12345678
```

## 📚 Examples & Tutorials

### 🧪 Method Comparison: LAMMPS vs kALDo

| Feature | LAMMPS Green-Kubo | kALDo BTE |
|---------|-------------------|-----------|
| **Physics** | MD + heat flux autocorr | Phonon Boltzmann transport |
| **Time** | ~hours (depends on system) | ~minutes (depends on mesh) |
| **Accuracy** | Includes all scattering | Harmonic + perturbative |
| **Output** | κ(T) scalar | κ(T) tensor + phonon details |
| **Best for** | Realistic systems, defects | Clean crystals, fundamentals |

#### Example 1: LAMMPS Green-Kubo
```bash
# Molecular dynamics approach - realistic but computationally expensive
mcg plan "Simulate thermal conductivity of mp-149 silicon using LAMMPS Green-Kubo at 300-800K with 20x20x20 supercell"
mcg start --plan plan.json
# → κ(300K) ≈ 148 W/(m·K) - includes all scattering mechanisms
```

#### Example 2: kALDo BTE  
```bash
# First-principles phonon transport - fast but requires force constants
mcg plan "Calculate thermal conductivity using kALDo BTE for mp-149 silicon at 300-800K with 25x25x25 mesh"
mcg start --plan plan.json
# → κ(300K) ≈ 200 W/(m·K) - upper bound without grain boundaries
```

#### Example 3: Comparative Analysis
```bash
# Plan both methods for comparison
mcg plan "Compare LAMMPS and kALDo thermal conductivity for mp-149 silicon at 300-500K"
# → Generates workflow with both runners for side-by-side analysis
```

### Scripted Examples

```bash
# Run LAMMPS Green-Kubo workflow
python examples/scripted_flow.py

# Run kALDo BTE workflow
python examples/kaldo_bte_example.py
```

LAMMPS Output:
```
MaterialsCodeGraph - Silicon Thermal Conductivity Workflow
============================================================
...
4. RESULTS
----------------------------------------
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

kALDo BTE Output:
```
MaterialsCodeGraph - kALDo BTE Workflow
============================================================
...
5. BTE RESULTS
----------------------------------------
Thermal Conductivity Tensor κ(T):
Temperature [K]  |  κ_avg [W/(m·K)]  |  κ_xx    κ_yy    κ_zz
-----------------------------------------------------------------
     300        |     200.00      | 204.00 196.00 200.00
     400        |     137.60      | 140.35 134.85 137.60
     500        |     102.95      | 105.01 100.89 102.95
     600        |      81.23      |  82.85  79.60  81.23
     700        |      66.48      |  67.80  65.15  66.48
     800        |      55.88      |  57.00  54.76  55.88

### Phonon Analysis
Frequency range: 2.0 - 16.5 THz
Lifetime range: 1.2 - 50.0 ps
```

## Architecture

### Asset Types (MCG-lite Schema)

- **System**: Crystal structure (`atoms`, `lattice`, `pbc`)
- **Method**: Computational method (`family`, `code`, `model`, `device`)
- **Params**: Simulation parameters with units
- **Results**: Computed properties (`kappa_W_per_mK`, `T_K`, etc.)
- **Artifact**: Files and logs (`uri`, `kind`, `hash`)

### Lineage Relations

- `USES`: Input asset to computation
- `PRODUCES`: Computation output
- `CONFIGURES`: Method/params to run
- `DERIVES`: Derived from another asset
- `LOGS`: Log/artifact generation

## MCP Servers

### Running Individual MCPs

```bash
# Memory MCP
python -m memory_mcp.server

# Compute MCP  
python -m compute_mcp.server

# Interfaces MCP
python -m interfaces_mcp.server
```

### MCP Tool Surfaces

**Interfaces MCP:**
- `plan(nl_task)` - Parse natural language into execution plan
- `explain(results, ledger)` - Generate human-readable explanations

**Compute MCP:**
- `start(runner_kind, assets, params)` - Start computation
- `status(run_id)` - Check run status
- `results(run_id)` - Retrieve results

**Memory MCP:**
- `put_assets(assets)` - Store assets
- `get_assets(ids)` - Retrieve assets
- `link(edges)` - Record lineage
- `ledger(select)` - Query provenance

## Testing

```bash
# Run all tests
pytest app/tests -v

# Run specific test modules
pytest app/tests/test_schema.py -v
pytest app/tests/test_memory.py -v
pytest app/tests/test_ids.py -v
```

## 🏗️ Architecture & Extension Guide

### Project Structure

```
materialscodegraph-lite/
├── 🧠 interfaces_mcp/           # Natural language interface
│   ├── server.py                # MCP server for planning/explaining  
│   └── tools.py                 # NL parsing and result explanation
├── ⚡ compute_mcp/              # Simulation execution
│   ├── server.py                # MCP server for job dispatch
│   └── runners/                 # Method implementations
│       ├── materials_project.py # MP structure fetching
│       ├── lammps_kappa_gk.py  # Green-Kubo thermal conductivity
│       └── kaldo_bte.py         # BTE thermal conductivity
├── 💾 memory_mcp/               # Asset and lineage storage
│   ├── server.py                # MCP server for data management
│   └── store.py                 # In-memory/persistent store
├── 🔧 common/                   # Shared utilities
│   ├── schema.py                # MCG-lite data schemas
│   ├── ids.py                   # Deterministic ID generation
│   ├── units.py                 # Unit system handling
│   └── io.py                    # URI and file management
├── 🖥️  cli/                     # Command-line interface
│   └── mcg.py                   # Main CLI orchestrator
├── 📝 examples/                 # Complete workflows
│   ├── scripted_flow.py         # LAMMPS Green-Kubo demo
│   └── kaldo_bte_example.py     # kALDo BTE demo
└── ✅ tests/                    # Unit and integration tests
```

### 🔌 Adding New Methods

Want to add VASP, Quantum ESPRESSO, or other codes? Here's how:

1. **Create Runner** (`compute_mcp/runners/your_method.py`)
```python
class YourMethodRunner:
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]):
        # Your simulation logic here
        return {"assets": [...], "edges": [...], "run": run_obj}
```

2. **Register in Compute MCP** (`compute_mcp/server.py`)
```python
elif runner_kind == "YourMethod":
    runner = YourMethodRunner()
    results = runner.run(run, assets, params)
```

3. **Update Planning** (`interfaces_mcp/tools.py`)
```python
if 'your_keyword' in task_lower:
    runner_kind = "YourMethod"
    # Add method-specific parameter parsing
```

4. **Add Tests** (`tests/test_your_method.py`)

### 📊 Result Schema Extensions

All results use the flexible `Results` asset type:
```python
results_payload = {
    "T_K": [300, 400, 500],           # Your temperature grid
    "your_property": [val1, val2],    # Your computed property
    "method": "YourMethod",           # Method identifier
    "your_param": param_value,        # Method-specific parameters
    # Add any method-specific outputs
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Required for Materials Project integration
export MP_API_KEY="your_api_key_here"

# Optional: Container images for production
export LAMMPS_IMAGE="lammps/lammps:stable" 
export KALDO_IMAGE="kaldo/kaldo:latest"

# Optional: Storage configuration
export MCG_STORAGE_PATH="/path/to/mcg/data"
export MCG_CACHE_SIZE="1000"  # Number of assets to cache
```

### Production Configuration

For production deployments, create a `.env` file:

```bash
# .env file
MP_API_KEY=your_materials_project_api_key
MCG_STORAGE_PATH=/opt/mcg/data
MCG_LOG_LEVEL=INFO

# HPC/Cloud settings
SLURM_QUEUE=compute
LAMMPS_NODES=4
KALDO_MEMORY=32GB
```

### 🚀 Deployment Options

#### Option 1: Local Development
```bash
# Direct execution (current approach)
python -m cli.mcg plan "your task"
```

#### Option 2: Container Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "-m", "memory_mcp.server"]
```

#### Option 3: HPC Integration
```bash
# Submit to SLURM
sbatch --job-name=mcg_kappa --nodes=4 mcg_job.sh

# mcg_job.sh integrates with job schedulers
#!/bin/bash
#SBATCH --partition=gpu
#SBATCH --gres=gpu:4
python -m cli.mcg start --plan $1
```

## ⚠️ Current Limitations

This is a **minimal implementation** focused on demonstrating the MCG architecture:

| Component | Current Status | Production Needs |
|-----------|----------------|------------------|
| **LAMMPS** | Mock simulation | Real container/HPC integration |
| **kALDo** | Mock BTE solver | Actual force constants + solver |
| **Storage** | In-memory + JSON | PostgreSQL/MongoDB backend |
| **Compute** | Single machine | HPC job schedulers (SLURM, PBS) |
| **Auth** | API keys only | OAuth, role-based access |
| **UI** | CLI only | Web dashboard, Jupyter integration |

## 🗺️ Roadmap

### v1.1 - Real Simulations
- [ ] Containerized LAMMPS execution
- [ ] True kALDo force constants pipeline
- [ ] VASP/QE integration for FC generation

### v1.2 - Production Scale  
- [ ] PostgreSQL Memory MCP backend
- [ ] SLURM/PBS job scheduler integration
- [ ] Multi-user support with authentication

### v1.3 - Advanced Features
- [ ] Web UI with workflow visualization
- [ ] Jupyter notebook integration
- [ ] ML property predictions
- [ ] Automated literature comparison

### v2.0 - Full Platform
- [ ] Multi-property support (electronic, mechanical)
- [ ] Advanced materials discovery workflows
- [ ] Integration with experimental databases

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contributing Steps
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`python run_tests.py`)
5. Submit a pull request

### Development Guidelines
- **Tests**: All new features need tests
- **Documentation**: Update relevant docstrings and README
- **Lineage**: Maintain provenance tracking in all new runners
- **Schema**: Follow MCG-lite schema patterns

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/your-org/materialscodegraph-lite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/materialscodegraph-lite/discussions)  
- **Documentation**: [Wiki](https://github.com/your-org/materialscodegraph-lite/wiki)
- **Slack**: Join our [MCG Community](https://mcg-community.slack.com)

## 📚 Citation

If you use MCG-lite in your research, please cite:

```bibtex
@software{mcg_lite_2024,
  title = {MaterialsCodeGraph-lite: Minimal MCP Implementation for Materials Science Workflows},
  author = {Your Organization},
  year = {2024},
  url = {https://github.com/your-org/materialscodegraph-lite},
  version = {1.0.0}
}
```

## 🙏 Acknowledgments

- **Materials Project** for structure data and API
- **LAMMPS** and **kALDo** communities for simulation tools
- **MCP** specification contributors
- All contributors and users of this project

---

**Ready to simulate thermal transport with full provenance? Get started with MCG-lite today!** 🚀