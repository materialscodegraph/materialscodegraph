# MCP Runner Configuration Guide

This directory contains MCG (MaterialsCodeGraph) configuration files that define how to map natural language to computational methods. Each software tool (LAMMPS, kALDo, Materials Project, etc.) has its own `config_[software].mcg` file.

## Philosophy

Configuration files should be:
- **Intuitive**: Read like documentation, not code
- **Natural**: Use plain English, not regex patterns
- **Simple**: Flat structure with clear mappings
- **Minimal**: Only specify what's different from defaults

## Configuration Structure

Each MCG file contains these sections (using YAML format):

### 1. Basic Information
```yaml
name: Software Name
description: What this software does
```

### 2. Natural Language Understanding
```yaml
understands:
  thermal conductivity:
    aliases: [kappa, heat transport]
    method: green_kubo
```
This maps user phrases to specific methods. When someone says "thermal conductivity", "kappa", or "heat transport", the system knows to use the `green_kubo` method.

### 3. Parameter Extraction
```yaml
extracts:
  temperature:
    keywords: [K, kelvin]
    examples:
      - "300K -> 300"
      - "300-800K -> [300, 400, 500, 600, 700, 800]"
    default: 300
```
This tells the system how to find and extract parameters from natural language. The examples show the system what input patterns to expect and how to convert them.

### 4. Execution Configuration
```yaml
runs_with:
  docker: software/image:latest
  local: /path/to/executable
```
Simple execution modes - no complex nested configuration.

### 5. Script Generation
```yaml
generates:
  method_name:
    needs: [structure, temperature]
    script: |
      # Simple template with {placeholders}
      run_software --temp {temperature}
```
Templates for generating input scripts with placeholder substitution.

### 6. Output Parsing
```yaml
parses:
  method_name:
    file: output.dat
    gets:
      - thermal_conductivity -> kappa
      - convergence -> converged
```
How to extract results from output files.

## Available Software

Current configurations:
- **config_lammps.mcg** - Molecular dynamics simulations
- **config_kaldo.mcg** - Phonon transport via Boltzmann equation
- **config_materials_project.mcg** - Crystal structure database
- **config_vasp.mcg** - First-principles electronic structure

## Adding New Software

Create a new MCG file in this directory (e.g., `config_mysoftware.mcg`):

```yaml
name: My Software
description: What it calculates

understands:
  my calculation:
    aliases: [calc, compute]
    method: main_method

extracts:
  my_parameter:
    keywords: [param, value]
    examples:
      - "param 10 -> 10"
    default: 5

runs_with:
  local: /usr/bin/mysoftware

generates:
  main_method:
    script: |
      mysoftware --param {my_parameter}

parses:
  main_method:
    file: output.txt
    gets:
      - result
```

## Testing Your Configuration

Test natural language understanding:

```python
from compute_mcp.simple_runner import plan_from_nl

# Test your configuration
result = plan_from_nl("calculate thermal conductivity of silicon at 300K")
print(result)
```

Expected output:
```python
{
  "runner": "lammps",
  "method": "green_kubo", 
  "params": {"temperature": 300, "material_name": "mp-149"},
  "matched_on": "thermal conductivity"
}
```

## Common Patterns

### Material Shortcuts
Allow users to say "silicon" instead of "mp-149":

```yaml
extracts:
  material_name:
    shortcuts:
      silicon: mp-149
      graphene: mp-1040425
      diamond: mp-66
```

### Multiple Aliases
Support different ways to say the same thing:

```yaml
understands:
  thermal conductivity:
    aliases: [kappa, k, heat transport, thermal transport]
```

### Temperature Ranges
Handle different temperature input formats:

```yaml
extracts:
  temperature:
    keywords: [K, kelvin]
    examples:
      - "300K -> 300"
      - "300-800K -> [300, 400, 500, 600, 700, 800]" 
      - "300K, 500K, 700K -> [300, 500, 700]"
```

### Grid Specifications
Extract mesh/grid parameters:

```yaml
extracts:
  mesh:
    keywords: [mesh, grid, k-points]
    examples:
      - "20x20x20 mesh -> [20, 20, 20]"
      - "mesh 30 -> [30, 30, 30]"
```

## Best Practices

1. **Start simple** - Add only essential features first
2. **Use examples** - Show the system concrete input/output pairs
3. **Provide defaults** - Most users want standard settings
4. **Test incrementally** - Verify each addition works
5. **Keep it readable** - Others should understand without explanation

## Parameter Types

The system handles various parameter types automatically:
- **Numbers**: `"300K -> 300"` 
- **Arrays**: `"10x10x10 -> [10, 10, 10]"`
- **Ranges**: `"300-800K -> [300, 400, 500, 600, 700, 800]"`
- **Objects**: `"gaussian broadening -> {shape: gauss}"`
- **Booleans**: `"with isotopes -> true"`

## Validation

Simple validation rules:
```yaml
validates:
  temperature: 1 to 10000  # Kelvin
  mesh: 5 to 100          # grid points
```

The configuration system learns from your examples and applies that knowledge to new inputs automatically.