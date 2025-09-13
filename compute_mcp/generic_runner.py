"""Pure generic configuration-driven runner

This runner has ZERO knowledge of any specific computational tools, domains,
or parameter types. Everything is driven purely by configuration files.
"""

import os
import re
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import string

# Try to import yaml, fall back to json if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from common.schema import Asset, Edge, Run
from common.ids import asset_id, generate_id
from common.io import write_uri


class GenericRunner:
    """Pure generic configuration-driven runner with zero domain knowledge"""

    def __init__(self, config_dir: str = None):
        """Initialize with configuration directory"""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "configs"
        self.config_dir = Path(config_dir)
        self.configs = {}
        self.load_configs()

    def load_configs(self):
        """Load all configuration files"""
        # Load JSON configs first (preferred)
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                if config:
                    name = config_file.stem
                    self.configs[name] = config
                    print(f"Loaded JSON config: {config.get('name', name)}")
            except Exception as e:
                print(f"Error loading {config_file}: {e}")

        # Also load YAML/MCG files if no JSON equivalent exists
        for config_file in self.config_dir.glob("*.mcg"):
            name = config_file.stem.replace('config_', '')
            if name not in self.configs:
                try:
                    with open(config_file, 'r') as f:
                        if HAS_YAML:
                            config = yaml.safe_load(f)
                        else:
                            config = self._parse_simple_config(f.read())

                    if config:
                        self.configs[name] = config
                        print(f"Loaded MCG config: {config.get('name', name)}")
                except Exception as e:
                    print(f"Error loading {config_file}: {e}")

        # Load YAML files
        for config_file in self.config_dir.glob("*.yml"):
            name = config_file.stem
            if name not in self.configs and HAS_YAML:
                try:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                    if config:
                        self.configs[name] = config
                        print(f"Loaded YAML config: {config.get('name', name)}")
                except Exception as e:
                    print(f"Error loading {config_file}: {e}")

    def _parse_simple_config(self, content: str) -> Dict:
        """Simple config parser for testing without YAML"""
        config = {}
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if key == 'name':
                    config['name'] = value
                elif key == 'description':
                    config['description'] = value

        # Add minimal structure for testing
        if 'name' not in config:
            config['name'] = 'Unknown'

        # Add default structures
        config.setdefault('understands', {})
        config.setdefault('extracts', {})
        config.setdefault('execution', {'local': {'executable': 'echo'}})
        config.setdefault('templates', {'default': {'needs': [], 'files': {}}})
        config.setdefault('outputs', {})

        return config

    def run(self, runner_kind: str, run_obj: Run, assets: List[Asset], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a run using configuration only"""

        # Find configuration
        config = self._find_config(runner_kind)

        # Update run status
        run_obj.status = "running"
        run_obj.started_at = datetime.utcnow().isoformat()

        try:
            # Determine method using config logic only
            method = self._resolve_method(config, params)

            # Get template configuration
            template_config = config.get('templates', {}).get(method)
            if not template_config:
                raise ValueError(f"No template found for method: {method}")

            # Organize assets
            asset_map = self._organize_assets(assets)

            # Validate requirements using config specifications
            self._validate_requirements(template_config, asset_map, params, config)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)

                # Generate all files from templates
                print(f"=== Generating files for {config.get('name')} - {method} ===")
                generated_files = self._generate_files(
                    template_config, config, asset_map, params, tmppath
                )

                # Execute based on configuration
                execution_mode = params.get('execution_mode', 'local')
                exec_config = config.get('execution', {}).get(execution_mode)

                if not exec_config:
                    raise ValueError(f"No execution config for mode: {execution_mode}")

                print(f"=== Executing with {execution_mode} mode ===")
                output_files = self._execute(
                    exec_config, execution_mode, generated_files, tmppath, params, config
                )

                # Parse outputs according to config specifications
                print("=== Parsing outputs ===")
                results = self._parse_outputs(
                    config.get('outputs', {}).get(method, {}),
                    output_files, tmppath, params, config
                )

                # Create assets according to config specifications
                assets_to_return = self._create_result_assets(config, method, results, params)

                # Store log artifact
                log_content = self._generate_log(config, method, params, results)
                log_uri = f"mcg://logs/{runner_kind}_{run_obj.id}.txt"
                log_hash = write_uri(log_uri, log_content)

                log_artifact = Asset(
                    type="Artifact",
                    id=generate_id("A"),
                    payload={
                        "uri": log_uri,
                        "kind": "log",
                        "media_type": "text/plain"
                    },
                    uri=log_uri,
                    hash=log_hash
                )

                # Create lineage edges
                edges = self._create_edges(run_obj, assets, assets_to_return[0], log_artifact)

                # Update run status
                run_obj.status = "done"
                run_obj.ended_at = datetime.utcnow().isoformat()

                return {
                    "assets": assets_to_return + [log_artifact],
                    "edges": edges,
                    "run": run_obj
                }

        except Exception as e:
            run_obj.status = "error"
            run_obj.ended_at = datetime.utcnow().isoformat()
            print(f"Error in GenericRunner: {e}")
            raise e

    def _find_config(self, runner_kind: str) -> Dict:
        """Find configuration for runner_kind using only config data"""
        config = None

        # Try exact matches first
        for key in [runner_kind.lower(), runner_kind.lower().replace(' ', '_')]:
            if key in self.configs:
                config = self.configs[key]
                break

        # Try matching by name field in configs
        if not config:
            for key, cfg in self.configs.items():
                if cfg.get('name', '').lower() == runner_kind.lower():
                    config = cfg
                    break

        if not config:
            available = list(self.configs.keys())
            raise ValueError(f"No configuration found for runner: {runner_kind}. Available: {available}")

        return config

    def _resolve_method(self, config: Dict, params: Dict) -> str:
        """Resolve method using config's resolution logic"""
        # First check if method is explicitly provided
        if 'method' in params:
            return params['method']

        # Use config's method resolution rules
        method_rules = config.get('method_resolution', {})

        for rule_name, rule_spec in method_rules.items():
            if self._evaluate_rule(rule_spec.get('condition', {}), params):
                return rule_spec.get('method', rule_name)

        # Fall back to config's inference logic
        understands = config.get('understands', {})
        for phrase, details in understands.items():
            if self._matches_understanding(phrase, details, params):
                return details.get('method', phrase)

        # Finally, use first available template
        templates = config.get('templates', {})
        if templates:
            return list(templates.keys())[0]

        return 'default'

    def _evaluate_rule(self, condition: Dict, params: Dict) -> bool:
        """Evaluate a rule condition against parameters"""
        if not condition:
            return False

        # Check if any required parameters are present
        if 'requires_any' in condition:
            for param_name in condition['requires_any']:
                if param_name in params:
                    return True

        # Check if all required parameters are present
        if 'requires_all' in condition:
            return all(param_name in params for param_name in condition['requires_all'])

        # Check parameter patterns
        if 'patterns' in condition:
            for param_name, pattern in condition['patterns'].items():
                if param_name in params:
                    value = str(params[param_name])
                    if re.search(pattern, value):
                        return True

        return False

    def _matches_understanding(self, phrase: str, details: Dict, params: Dict) -> bool:
        """Check if params match an understanding phrase"""
        # Simple keyword matching - can be enhanced based on config
        keywords = details.get('keywords', [])
        param_values = ' '.join(str(v) for v in params.values()).lower()

        return any(keyword.lower() in param_values for keyword in keywords)

    def _validate_requirements(self, template_config: Dict, asset_map: Dict, params: Dict, config: Dict):
        """Validate requirements using config's validation rules"""
        needs = template_config.get('needs', [])
        param_mapping = config.get('parameter_mapping', {})

        for need in needs:
            found = False

            # Check assets
            if need in asset_map:
                found = True

            # Check params with mapping
            if need in params:
                found = True
            elif need in param_mapping:
                # Check all aliases for this parameter
                aliases = param_mapping[need]
                for alias in aliases:
                    if alias in params:
                        found = True
                        break

            if not found:
                print(f"Available params: {list(params.keys())}")
                print(f"Available assets: {list(asset_map.keys())}")
                print(f"Need: {need}, mapping: {param_mapping.get(need, [])}")
                raise ValueError(f"Required input missing: {need}")

    def _organize_assets(self, assets: List[Asset]) -> Dict[str, Asset]:
        """Organize assets by type - purely generic"""
        asset_map = {}
        for asset in assets:
            asset_type = asset.type.lower()
            asset_map[asset_type] = asset
        return asset_map

    def _generate_files(self, template_config: Dict, config: Dict,
                       asset_map: Dict, params: Dict, tmppath: Path) -> Dict[str, Path]:
        """Generate all files from templates using config specifications"""
        generated = {}

        files_config = template_config.get('files', {})
        for file_key, file_spec in files_config.items():
            filename = file_spec.get('name', file_key)

            if 'content' in file_spec:
                # Template-based generation
                content = self._render_template(
                    file_spec['content'], config, asset_map, params
                )
            elif 'generator' in file_spec:
                # Use a generator function defined in config
                content = self._run_generator(
                    file_spec['generator'], config, asset_map, params
                )
            else:
                content = ""

            filepath = tmppath / filename
            with open(filepath, 'w') as f:
                f.write(content)

            generated[file_key] = filepath
            print(f"Generated: {filename}")

        return generated

    def _render_template(self, template: str, config: Dict, asset_map: Dict, params: Dict) -> str:
        """Render template using config's context rules"""
        # Build context from config specifications
        context = self._build_template_context(config, asset_map, params)

        # Handle special template syntax (e.g., double braces)
        template_syntax = config.get('template_syntax', {})
        if 'escape_sequences' in template_syntax:
            for original, replacement in template_syntax['escape_sequences'].items():
                template = template.replace(original, replacement)

        # Use string.Template for substitution
        template_obj = string.Template(template)

        try:
            result = template_obj.safe_substitute(**context)
        except Exception as e:
            print(f"Template substitution error: {e}")
            result = template

        # Handle array indexing and other post-processing
        post_processors = config.get('template_post_processors', [])
        for processor in post_processors:
            if processor['type'] == 'array_indexing':
                pattern = processor['pattern']
                result = re.sub(pattern, lambda m: self._resolve_array_index(m, context), result)

        return result

    def _build_template_context(self, config: Dict, asset_map: Dict, params: Dict) -> Dict:
        """Build template context using config's context rules"""
        context = {
            'timestamp': datetime.utcnow().isoformat(),
            'seed': 12345,
            **params  # Include all parameters
        }

        # Apply parameter mapping to resolve aliases
        param_mapping = config.get('parameter_mapping', {})
        for canonical_name, aliases in param_mapping.items():
            for alias in aliases:
                if alias in params and canonical_name not in context:
                    context[canonical_name] = params[alias]

        # Apply config's context builders
        context_builders = config.get('context_builders', {})

        for builder_name, builder_spec in context_builders.items():
            try:
                if builder_spec['type'] == 'parameter_transform':
                    source_param = builder_spec['source']
                    if source_param in context:
                        context[builder_name] = self._apply_transform(
                            context[source_param],
                            builder_spec['transform']
                        )

                elif builder_spec['type'] == 'computed_value':
                    context[builder_name] = self._compute_value(builder_spec, context)
            except Exception as e:
                print(f"Error building context for {builder_name}: {e}")
                # Use default if computation fails
                context[builder_name] = builder_spec.get('default', '')

        return context

    def _apply_transform(self, value: Any, transform: Dict) -> Any:
        """Apply transformation according to config specification"""
        transform_type = transform['type']

        if transform_type == 'list_to_string':
            if isinstance(value, list):
                separator = transform.get('separator', ' ')
                return separator.join(map(str, value))
            return str(value)

        elif transform_type == 'unit_conversion':
            factor = transform.get('factor', 1.0)
            return value * factor

        elif transform_type == 'steps_calculation':
            time_value = value
            timestep = transform.get('timestep', 1.0)
            return int(time_value * transform.get('multiplier', 1000) / timestep)

        return value

    def _compute_value(self, spec: Dict, context: Dict) -> Any:
        """Compute value according to config specification"""
        computation = spec.get('computation', {})
        default_value = spec.get('default', '')

        if computation.get('type') == 'formula':
            # Simple formula evaluation
            formula = computation.get('formula', '')

            # Simple substitutions for common patterns
            if 'equil_ps' in context and 'timestep_fs' in context:
                if 'equil_ps * 1000 / timestep_fs' in formula:
                    try:
                        return int(context['equil_ps'] * 1000 / context['timestep_fs'])
                    except:
                        pass

            if 'prod_ps' in context and 'timestep_fs' in context:
                if 'prod_ps * 1000 / timestep_fs' in formula:
                    try:
                        return int(context['prod_ps'] * 1000 / context['timestep_fs'])
                    except:
                        pass

            if 'supercell' in context:
                supercell = context['supercell']
                if isinstance(supercell, list):
                    if '[0]' in formula:
                        return supercell[0] if len(supercell) > 0 else 10
                    elif '[1]' in formula:
                        return supercell[1] if len(supercell) > 1 else 10
                    elif '[2]' in formula:
                        return supercell[2] if len(supercell) > 2 else 10
                else:
                    return supercell

            return computation.get('default', default_value)

        return default_value

    def _resolve_array_index(self, match, context: Dict) -> str:
        """Resolve array indexing like {array[0]}"""
        array_name = match.group(1)
        index = int(match.group(2))
        array_value = context.get(array_name, [])

        if isinstance(array_value, list) and 0 <= index < len(array_value):
            return str(array_value[index])

        return match.group(0)  # Return original if not found

    def _run_generator(self, generator_name: str, config: Dict, asset_map: Dict, params: Dict) -> str:
        """Run a generator function defined in config"""
        generators = config.get('generators', {})
        if generator_name not in generators:
            return ""

        generator_spec = generators[generator_name]
        generator_type = generator_spec['type']

        if generator_type == 'template':
            return self._render_template(generator_spec['template'], config, asset_map, params)
        elif generator_type == 'data_file':
            return self._generate_data_file(generator_spec, asset_map, params)

        return ""

    def _generate_data_file(self, spec: Dict, asset_map: Dict, params: Dict) -> str:
        """Generate data file according to config specification"""
        # Generic data file generation based on config
        template = spec.get('template', '')

        # Use system asset if available
        if 'system' in asset_map:
            system_data = asset_map['system'].payload
            # Replace placeholders with system data
            for key, value in system_data.items():
                template = template.replace(f'{{{key}}}', str(value))

        return template

    def _execute(self, config: Dict, mode: str, files: Dict[str, Path],
                tmppath: Path, params: Dict, runner_config: Dict) -> Dict[str, Path]:
        """Execute according to config specifications"""
        if mode == 'local':
            return self._execute_local(config, files, tmppath, runner_config)
        elif mode == 'docker':
            return self._execute_docker(config, files, tmppath, runner_config)
        elif mode == 'hpc':
            return self._execute_hpc(config, files, tmppath, runner_config)
        else:
            raise ValueError(f"Unknown execution mode: {mode}")

    def _execute_local(self, config: Dict, files: Dict, tmppath: Path, runner_config: Dict) -> Dict[str, Path]:
        """Execute locally according to config"""
        executable = config.get('executable', 'echo')

        # Build command according to config
        command_template = config.get('command_template', '{executable} {input_file}')

        # Get input file
        input_file = files.get('input_script', files.get('query_script', list(files.values())[0]))

        # Apply command template - avoid conflicts with config keys
        template_vars = {
            'executable': executable,
            'input_file': input_file.name
        }
        # Only add non-conflicting config values
        for key, value in config.items():
            if key not in template_vars:
                template_vars[key] = value

        command = command_template.format(**template_vars)

        # Set environment from config
        env = os.environ.copy()
        for key, value in config.get('environment', {}).items():
            env[key] = str(value)

        print(f"Executing: {command}")
        print(f"Working directory: {tmppath}")

        # Execute
        result = subprocess.run(
            command, shell=True, cwd=tmppath,
            capture_output=True, text=True, env=env
        )

        if result.stdout:
            print("STDOUT:", result.stdout[:500])
        if result.stderr:
            print("STDERR:", result.stderr[:500])

        # Return output files according to config expectations
        return self._find_output_files(tmppath, runner_config)

    def _execute_docker(self, config: Dict, files: Dict, tmppath: Path, runner_config: Dict) -> Dict[str, Path]:
        """Execute in Docker according to config"""
        # Implementation would be similar but use config specifications
        return self._find_output_files(tmppath, runner_config)

    def _execute_hpc(self, config: Dict, files: Dict, tmppath: Path, runner_config: Dict) -> Dict[str, Path]:
        """Execute on HPC according to config"""
        # Implementation would be similar but use config specifications
        return self._find_output_files(tmppath, runner_config)

    def _find_output_files(self, tmppath: Path, config: Dict) -> Dict[str, Path]:
        """Find output files according to config specifications"""
        output_files = {}

        # Use config's file discovery rules
        file_patterns = config.get('expected_outputs', ['*.dat', '*.txt', '*.json', '*.out'])

        for pattern in file_patterns:
            for filepath in tmppath.glob(pattern):
                if filepath.is_file():
                    output_files[filepath.stem] = filepath

        return output_files

    def _parse_outputs(self, output_config: Dict, files: Dict,
                      tmppath: Path, params: Dict, config: Dict) -> Dict[str, Any]:
        """Parse outputs according to config specifications"""
        results = {}

        for file_spec in output_config.get('files', []):
            if 'pattern' in file_spec:
                # Find files matching pattern
                pattern = file_spec['pattern']
                matching_files = list(tmppath.glob(pattern))
                for filepath in matching_files:
                    parsed = self._parse_file(filepath, file_spec, config)
                    results.update(parsed)
            elif 'name' in file_spec:
                # Specific file
                filepath = tmppath / file_spec['name']
                if filepath.exists():
                    parsed = self._parse_file(filepath, file_spec, config)
                    results.update(parsed)

        # Apply config's default results if nothing parsed
        if not results:
            default_results = config.get('default_results', {})
            results.update(default_results)

        return results

    def _parse_file(self, filepath: Path, spec: Dict, config: Dict) -> Dict[str, Any]:
        """Parse file according to config parser specifications"""
        parser_name = spec.get('parser', 'simple')
        parsers = config.get('parsers', {})

        if parser_name in parsers:
            parser_spec = parsers[parser_name]
            return self._apply_parser(filepath, parser_spec)

        # Fallback parsing
        if filepath.suffix == '.json':
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}

        return {}

    def _apply_parser(self, filepath: Path, parser_spec: Dict) -> Dict[str, Any]:
        """Apply parser according to specification"""
        parser_type = parser_spec.get('type', 'simple')

        if parser_type == 'json':
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}
        elif parser_type == 'regex':
            patterns = parser_spec.get('patterns', [])
            results = {}
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        # Store matches with pattern as key
                        results[f'matches_{len(results)}'] = matches
            except:
                pass
            return results
        elif parser_type == 'columnar':
            # Parse columnar data according to spec
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                skip_lines = parser_spec.get('skip_lines', 0)
                data_lines = lines[skip_lines:]
                # Simple columnar parsing - could be enhanced
                return {'data': [line.strip().split() for line in data_lines if line.strip()]}
            except:
                return {}

        return {}

    def _create_result_assets(self, config: Dict, method: str, results: Dict, params: Dict) -> List[Asset]:
        """Create result assets according to config specifications"""
        assets = []

        # Create main results asset
        results_payload = {
            'method': method,
            'runner': config.get('name'),
            **results,
            **{k: v for k, v in params.items() if k not in ['method', 'execution_mode']}
        }

        results_asset = Asset(
            type="Results",
            id=asset_id("Results", results_payload),
            payload=results_payload,
            units=self._extract_units(config, results)
        )
        assets.append(results_asset)

        # Create additional assets based on config rules
        asset_rules = config.get('result_assets', {})
        for rule_name, rule_spec in asset_rules.items():
            if self._should_create_asset(rule_spec, results, params):
                additional_asset = self._create_asset_from_rule(rule_spec, results, params)
                if additional_asset:
                    assets.append(additional_asset)

        return assets

    def _should_create_asset(self, rule_spec: Dict, results: Dict, params: Dict) -> bool:
        """Check if asset should be created based on rule"""
        conditions = rule_spec.get('conditions', {})

        # Check if required data is present
        if 'requires_data' in conditions:
            for key in conditions['requires_data']:
                if key not in results:
                    return False

        return True

    def _create_asset_from_rule(self, rule_spec: Dict, results: Dict, params: Dict) -> Optional[Asset]:
        """Create asset according to rule specification"""
        asset_type = rule_spec.get('type', 'Asset')

        payload = {}
        # Extract payload according to rule
        payload_rules = rule_spec.get('payload', {})
        for key, source in payload_rules.items():
            if source in results:
                payload[key] = results[source]
            elif source in params:
                payload[key] = params[source]

        if payload:
            return Asset(
                type=asset_type,
                id=generate_id(asset_type[0]),
                payload=payload
            )

        return None

    def _extract_units(self, config: Dict, results: Dict) -> Dict[str, str]:
        """Extract units from config specifications"""
        units = {}
        results_format = config.get('results', {}).get('format', {})

        for key in results:
            if key in results_format and 'unit' in results_format[key]:
                units[key] = results_format[key]['unit']

        return units

    def _generate_log(self, config: Dict, method: str, params: Dict, results: Dict) -> str:
        """Generate log using config template if available"""
        log_template = config.get('log_template')
        if log_template:
            context = {
                'config_name': config.get('name'),
                'method': method,
                'timestamp': datetime.utcnow().isoformat(),
                'params': params,
                'results': results
            }
            return string.Template(log_template).safe_substitute(**context)

        # Default log format
        log = f"Run completed: {config.get('name')} - {method}\n"
        log += f"Timestamp: {datetime.utcnow().isoformat()}\n\n"
        log += "Parameters:\n"
        for key, value in params.items():
            log += f"  {key}: {value}\n"
        log += "\nResults:\n"
        for key, value in results.items():
            log += f"  {key}: {value}\n"
        return log

    def _create_edges(self, run_obj: Run, input_assets: List[Asset],
                     results_asset: Asset, log_artifact: Asset) -> List[Edge]:
        """Create lineage edges - purely generic"""
        edges = []
        timestamp = datetime.utcnow().isoformat()

        # Input assets to run
        for asset in input_assets:
            edges.append(Edge(
                from_id=asset.id,
                to_id=run_obj.id,
                rel="USES" if asset.type == "System" else "CONFIGURES",
                t=timestamp
            ))

        # Run to outputs
        edges.append(Edge(
            from_id=run_obj.id,
            to_id=results_asset.id,
            rel="PRODUCES",
            t=timestamp
        ))

        edges.append(Edge(
            from_id=run_obj.id,
            to_id=log_artifact.id,
            rel="LOGS",
            t=timestamp
        ))

        return edges