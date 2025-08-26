# Contributing to MaterialsCodeGraph-lite

Thank you for considering contributing to MCG-lite! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/your-username/materialscodegraph.git`
3. **Create** a virtual environment: `python -m venv mcg-dev`
4. **Install** in development mode: `pip install -e .`
5. **Run tests** to ensure everything works: `python run_tests.py`

## 🎯 Types of Contributions

### 🔬 New Computational Methods
- Add runners for VASP, Quantum ESPRESSO, CASTEP, etc.
- Implement new property calculators (electronic, mechanical, optical)
- Create method-specific result parsers

### 🧮 Enhanced Physics
- Improve thermal conductivity models
- Add uncertainty quantification
- Implement advanced phonon analysis

### 🏗️ Infrastructure Improvements
- Database backends (PostgreSQL, MongoDB)
- HPC integration (SLURM, PBS)
- Container orchestration (Kubernetes)
- Authentication and authorization

### 📚 Documentation & Examples
- Tutorial notebooks
- Method comparison studies
- Best practice guides
- API documentation

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8 for Python code style
- Use type hints where appropriate
- Keep functions focused and well-documented
- Prefer composition over inheritance

### Testing Requirements
- All new features must include tests
- Aim for >90% test coverage
- Test both success and failure cases
- Use descriptive test names

```python
def test_kaldo_runner_handles_missing_force_constants():
    """Test that KALDoRunner gracefully handles missing force constants"""
    # Test implementation here
```

### Documentation Standards
- Update docstrings for all public functions
- Include usage examples in docstrings
- Update README.md for new features
- Add type annotations

### Lineage Tracking
**Critical**: All new runners must maintain full provenance:

```python
def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]):
    # ... computation logic ...
    
    # Always create lineage edges
    edges = [
        Edge(input_asset.id, run_obj.id, "USES", timestamp),
        Edge(run_obj.id, result_asset.id, "PRODUCES", timestamp),
        # ... more edges as needed
    ]
    
    return {"assets": [result_asset], "edges": edges, "run": run_obj}
```

## 📝 Adding New Computational Methods

### Step-by-Step Guide

1. **Create Runner Class**
```python
# compute_mcp/runners/your_method.py
class YourMethodRunner:
    def __init__(self):
        self.runner_version = "1.0.0"
    
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]):
        # Implementation here
        pass
```

2. **Register in Compute MCP**
```python
# compute_mcp/server.py
elif runner_kind == "YourMethod":
    runner = YourMethodRunner()
    results = runner.run(run, assets, params)
```

3. **Update Natural Language Planning**
```python
# interfaces_mcp/tools.py
if 'your_keyword' in task_lower or 'your_method' in task_lower:
    runner_kind = "YourMethod"
    workflow = "your_calculation"
    # Add parameter parsing logic
```

4. **Add Result Explanation**
```python
# interfaces_mcp/tools.py - in explain() method
if "your_property" in payload:
    explanation.append("## Your Property Results")
    # Add method-specific explanation logic
```

5. **Create Tests**
```python
# tests/test_your_method.py
def test_your_method_runner():
    runner = YourMethodRunner()
    # Test runner functionality
```

### Example: Adding VASP DFT Calculator

```python
class VASPRunner:
    def run(self, run_obj: Run, assets: List[Asset], params: Dict[str, Any]):
        # Get structure
        structure = extract_structure(assets)
        
        # Generate VASP input files
        self._write_poscar(structure)
        self._write_incar(params)
        self._write_kpoints(params)
        
        # Execute VASP (containerized)
        result = self._run_vasp_container()
        
        # Parse outputs and create result assets
        results_asset = Asset(
            type="Results",
            payload={
                "total_energy_eV": result["energy"],
                "forces_eV_per_A": result["forces"],
                "method": "DFT-PBE"
            }
        )
        
        # Create lineage
        edges = [...]
        
        return {"assets": [results_asset], "edges": edges, "run": run_obj}
```

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── test_schema.py           # Schema validation
├── test_memory.py           # Storage and lineage  
├── test_interfaces.py       # Natural language processing
├── test_compute_runners.py  # Individual runner tests
├── test_integration.py      # End-to-end workflows
└── test_your_method.py      # Your new method tests
```

### Running Tests
```bash
# Run all tests
python run_tests.py

# Run specific test module
python tests/test_your_method.py

# Run with coverage (if pytest available)
pytest tests/ --cov=. --cov-report=html
```

### Test Data
- Use minimal test structures (2-8 atoms)
- Mock expensive computations
- Test both happy path and edge cases
- Include realistic but small datasets

## 📋 Pull Request Process

1. **Create Feature Branch**
```bash
git checkout -b feature/your-amazing-feature
```

2. **Make Changes**
- Implement your feature
- Add comprehensive tests
- Update documentation

3. **Test Thoroughly**
```bash
python run_tests.py
# All tests must pass
```

4. **Commit with Clear Messages**
```bash
git commit -m "feat: add VASP DFT runner with full lineage tracking

- Implement VASPRunner with POSCAR/INCAR generation
- Add natural language parsing for 'DFT' and 'VASP' keywords  
- Include comprehensive tests for structure handling
- Update CLI to support DFT workflows

Closes #123"
```

5. **Submit Pull Request**
- Use descriptive title and detailed description
- Reference related issues
- Include test results
- Request review from maintainers

### PR Review Checklist
- [ ] Tests pass and cover new functionality
- [ ] Documentation updated (README, docstrings)
- [ ] Lineage tracking implemented correctly
- [ ] Code follows project style guidelines
- [ ] No breaking changes (or clearly documented)
- [ ] Performance impact considered

## 🏷️ Release Process

### Version Numbering
We follow semantic versioning (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `__init__.py`
- [ ] Tag created: `git tag v1.2.0`
- [ ] Release notes prepared

## 💬 Communication

### Getting Help
- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Slack**: Real-time chat with the community

### Code of Conduct
- Be respectful and inclusive
- Provide constructive feedback
- Focus on the technical merit of contributions
- Help others learn and grow

## 🎖️ Recognition

Contributors are recognized in:
- README.md acknowledgments
- CONTRIBUTORS.md file
- Release notes
- Conference presentations

## 📚 Resources

### Understanding MCG Architecture
- Read the [MCG-lite Schema](common/schema.py)
- Study existing runners as templates
- Understand the MCP protocol

### Materials Science Background
- [Materials Project Documentation](https://docs.materialsproject.org/)
- [LAMMPS Manual](https://lammps.sandia.gov/doc/Manual.html)
- [kALDo Documentation](https://kaldo.readthedocs.io/)

### Python Development
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [asyncio Programming](https://docs.python.org/3/library/asyncio.html)
- [Testing Best Practices](https://realpython.com/python-testing/)

---

**Thank you for contributing to the future of computational materials science!** 🚀

If you have questions, don't hesitate to reach out via GitHub Discussions or Issues.