# Simplified Configuration System

## Philosophy

The configuration files should be:
- **Intuitive**: Read like documentation, not code
- **Natural**: Use plain English, not regex
- **Simple**: Flat structure, clear mappings
- **Minimal**: Only specify what's different from defaults

## Structure

Each YAML file has these simple sections:

### 1. Basic Info
```yaml
name: Software Name
description: What it does
```

### 2. Understanding Natural Language
```yaml
understands:
  thermal conductivity:
    aliases: [kappa, heat transport]
    method: green_kubo
```
This says: "When user mentions 'thermal conductivity' (or 'kappa' or 'heat transport'), use the green_kubo method"

### 3. Extracting Parameters
```yaml
extracts:
  temperature:
    keywords: [K, kelvin]
    examples:
      - "300K" -> 300
      - "300 to 800K" -> [300, 400, 500, 600, 700, 800]
    default: 300
```
This says: "Look for 'K' or 'kelvin', extract numbers like these examples, default to 300"

### 4. Running the Code
```yaml
runs_with:
  docker: image_name
  local: /path/to/executable
```

### 5. Generating Scripts
```yaml
generates:
  method_name:
    needs: [what_it_needs]
    script: |
      The actual script with {placeholders}
```

### 6. Parsing Output
```yaml
parses:
  method_name:
    file: output.dat
    gets:
      - thermal_conductivity -> kappa
```

## Examples

### Adding a New Software

Create `configs_v2/new_software.yaml`:

```yaml
name: My Software
description: Does something cool

understands:
  my calculation:
    aliases: [calc, compute]
    method: main_method

extracts:
  my_param:
    keywords: [param, value]
    examples:
      - "param 10" -> 10
    default: 5

runs_with:
  local: /usr/bin/mysoftware

generates:
  main_method:
    script: |
      mysoftware --param {my_param}

parses:
  main_method:
    file: output.txt
    gets:
      - result
```

### Using Material Shortcuts

```yaml
extracts:
  material_name:
    shortcuts:
      silicon: mp-149
      graphene: mp-1040425
```

Now users can say "get silicon" instead of "get mp-149"

### Temperature Ranges

```yaml
extracts:
  temperature:
    keywords: [K, kelvin]
    examples:
      - "300K" -> 300
      - "300-800K" -> [300, 400, 500, 600, 700, 800]
      - "300K, 500K, 700K" -> [300, 500, 700]
```

The system learns from examples how to parse different formats.

## Testing

Test natural language understanding:

```python
from compute_mcp.simple_runner import plan_from_nl

# Test your natural language
result = plan_from_nl("calculate thermal conductivity of silicon at 300K")
print(result)
# Output:
# {
#   "runner": "lammps",
#   "method": "green_kubo",
#   "params": {"temperature": 300, "material_id": "mp-149"}
# }
```

## Tips

1. **Start simple**: Add only what you need
2. **Use examples**: Show the system what to expect
3. **Provide defaults**: Most users want standard settings
4. **Test incrementally**: Add one feature at a time
5. **Keep it readable**: Someone should understand it without documentation

## Common Patterns

### Multiple Ways to Say Something
```yaml
understands:
  thermal conductivity:
    aliases: [kappa, k, heat transport, thermal transport]
```

### Common Units
```yaml
extracts:
  time:
    keywords: [ps, picosecond, fs, femtosecond]
    examples:
      - "100 ps" -> 100
      - "0.5 fs" -> 0.5
```

### Grids and Meshes
```yaml
extracts:
  mesh:
    keywords: [mesh, grid, points]
    examples:
      - "20x20x20" -> [20, 20, 20]
      - "mesh 30" -> [30, 30, 30]
```

## Migration from Complex Config

Old (complex):
```yaml
nl_patterns:
  parameters:
    temperature:
      patterns:
        - pattern: '(\d+)\s*(?:-|to|–)\s*(\d+)\s*[kK]'
          type: range
          extract:
            start: $1
            end: $2
```

New (simple):
```yaml
extracts:
  temperature:
    keywords: [K]
    examples:
      - "300-800K" -> [300, 400, 500, 600, 700, 800]
```

The new way is clearer and easier to maintain!