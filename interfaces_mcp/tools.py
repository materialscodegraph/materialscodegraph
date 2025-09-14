"""Planning and explanation tools for natural language interactions"""
import re
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from dotenv import load_dotenv
import anthropic

load_dotenv()


from common.schema import Asset, Edge
from common.ids import asset_id, generate_id

class InterfacesTools:
    """Tools for planning and explaining computational workflows"""

    def __init__(self, config_dir: str = None):
        """Initialize with configuration directory"""
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "configs"
        self.config_dir = Path(config_dir)
        self.configs = {}
        self.load_configs()

    def load_configs(self):
        """Load all configuration files to understand available runners"""
        # Load JSON config files
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)

                if config:
                    name = config.get('name', config_file.stem)
                    self.configs[name] = config
            except Exception as e:
                # Silently skip files that can't be loaded
                pass


    def plan(self, nl_task: str, context_assets: Optional[List[Asset]] = None) -> Dict[str, Any]:
        """Parse natural language task and create execution plan using configuration-driven approach"""

        # Parse the natural language task
        task_lower = nl_task.lower()

        # Initialize plan components
        runner_kind = None
        assets = []
        params = {}
        workflow = None
        missing = []

        # Build parameter schema from all configurations for AI
        all_parameters = set()
        for config_name, config in self.configs.items():
            all_parameters.update(config.get('required_parameters', []))
            all_parameters.update(config.get('optional_parameters', []))

        # Create parameter mapping for AI (simple mapping - parameter name to itself)
        all_param_mappings = {param: [param] for param in all_parameters}

        # Extract parameters using AI with all available parameters
        self._extract_parameters_from_task(nl_task, params, all_param_mappings, missing)

        # Now find the best matching configuration for execution
        best_match = None
        best_score = 0

        for config_name, config in self.configs.items():
            capabilities = config.get('capabilities', [])
            score = 0
            matched_capabilities = []

            # Check if task matches any of this runner's capabilities
            for capability in capabilities:
                capability_words = capability.lower().replace('_', ' ').split()

                # Check if all capability words appear in task
                if all(word in task_lower for word in capability_words):
                    score += len(capability_words)
                    matched_capabilities.append(capability)

                # Also check for partial matches
                elif any(word in task_lower for word in capability_words):
                    score += 1
                    matched_capabilities.append(capability)

            if score > best_score:
                best_score = score
                best_match = {
                    'config_name': config_name,
                    'config': config,
                    'matched_capabilities': matched_capabilities,
                    'score': score
                }

        if best_match:
            runner_kind = best_match['config_name']
            config = best_match['config']

            # Determine workflow method from config
            matched_capability = best_match['matched_capabilities'][0] if best_match['matched_capabilities'] else None
            if matched_capability:
                workflow = config.get('methods', {}).get(matched_capability, matched_capability)
            else:
                workflow = list(config.get('methods', {}).values())[0] if config.get('methods') else "default"

        # Always check if we need a multi-step workflow, regardless of single runner match
        workflow = self._check_multi_step_workflow(task_lower, runner_kind, params, workflow)

        # Create params asset if we have params
        if params:
            params_asset = Asset(
                type="Params",
                id=asset_id("Params", params),
                payload=params
            )
            assets.append(params_asset)
        
        return {
            "runner_kind": runner_kind,
            "assets": assets,
            "params": params,
            "workflow": workflow,
            "missing": missing
        }
    
    def explain(self, results_assets: List[Asset], ledger_slice: List[Edge]) -> str:
        """Generate human-readable explanation of results"""
        
        explanation = []
        
        # Find results assets
        for asset in results_assets:
            if asset.type == "Results":
                payload = asset.payload
                
                # Check for thermal conductivity results
                if "kappa_W_per_mK" in payload and "T_K" in payload:
                    temps = payload["T_K"]
                    kappas = payload["kappa_W_per_mK"]
                    
                    explanation.append("## Thermal Conductivity Results\n")
                    method = payload.get('method', 'Unknown')
                    explanation.append(f"Method: {method}")
                    
                    if method == "BTE":
                        explanation.append(f"Solver: {payload.get('solver', 'kALDo')}")
                        explanation.append(f"Mesh: {payload.get('mesh', 'Not specified')}")
                        explanation.append(f"Broadening: {payload.get('broadening_shape', 'gauss')} "
                                         f"({payload.get('broadening_width_meV', 1.0)} meV)")
                    else:
                        explanation.append(f"Supercell: {payload.get('supercell', 'Not specified')}")
                    
                    explanation.append("\n### κ(T) values:")
                    
                    for T, k in zip(temps, kappas):
                        explanation.append(f"  - {T} K: {k:.2f} W/(m·K)")
                    
                    # Add tensor components if available (BTE)
                    if "kappa_xx_W_per_mK" in payload:
                        explanation.append("\n### Tensor Components (last T):")
                        explanation.append(f"  - κ_xx: {payload['kappa_xx_W_per_mK'][-1]:.2f} W/(m·K)")
                        explanation.append(f"  - κ_yy: {payload['kappa_yy_W_per_mK'][-1]:.2f} W/(m·K)")
                        explanation.append(f"  - κ_zz: {payload['kappa_zz_W_per_mK'][-1]:.2f} W/(m·K)")
                    
                    # Add trend analysis
                    if len(kappas) > 1:
                        trend = "decreasing" if kappas[-1] < kappas[0] else "increasing"
                        explanation.append(f"\nTrend: Thermal conductivity {trend} with temperature")
                        explanation.append(f"Range: {min(kappas):.2f} - {max(kappas):.2f} W/(m·K)")
                
                # Check for phonon information
                if "phonon_freq_THz" in payload:
                    explanation.append("\n### Phonon Summary")
                    freqs = payload["phonon_freq_THz"]
                    explanation.append(f"Frequency range: {min(freqs):.2f} - {max(freqs):.2f} THz")
                
                if "lifetimes_ps" in payload:
                    lifetimes = payload["lifetimes_ps"]
                    explanation.append(f"Lifetime range: {min(lifetimes):.2f} - {max(lifetimes):.2f} ps")
        
        # Add reproducibility information from ledger
        if ledger_slice:
            explanation.append("\n## Reproducibility")
            
            # Find run IDs
            runs = set()
            for edge in ledger_slice:
                if edge.rel in ["PRODUCES", "USES"] and edge.from_id.startswith("R"):
                    runs.add(edge.from_id)
            
            if runs:
                explanation.append(f"Run IDs: {', '.join(sorted(runs))}")
            
            # Find input assets
            inputs = []
            for edge in ledger_slice:
                if edge.rel == "USES":
                    inputs.append(edge.from_id)
            
            if inputs:
                explanation.append(f"Input assets: {', '.join(inputs)}")
            
            explanation.append("\nTo reproduce:")
            explanation.append("1. Retrieve input assets from Memory MCP")
            explanation.append("2. Execute same runner with identical parameters")
            explanation.append("3. Results should match within numerical tolerance")
        
        return "\n".join(explanation)

    def _extract_parameters_from_task(self, task: str, params: Dict, param_mapping: Dict, missing: List):
        """Extract parameters from task using AI-powered parsing"""

        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

        # Build parameter schema from all available mappings
        param_schema = {}
        for param_key, aliases in param_mapping.items():
            param_schema[param_key] = {
                'aliases': aliases,
                'description': self._get_parameter_description(param_key)
            }

        prompt = f"""Extract simulation parameters from this task description:

"{task}"

Available parameters to extract:
{json.dumps(param_schema, indent=2)}

Return ONLY a JSON object with the extracted parameters. Use the first alias as the key name.
For temperature ranges, return as a list of values (e.g., [300, 400, 500] for 300-500K).
For supercells like "20x20x20", return as [20, 20, 20].
If a parameter is not found, omit it from the response.

Example response format:
{{
  "material_id": "mp-149",
  "temperature": [300, 400, 500],
  "supercell": [20, 20, 20]
}}"""

        try:
            print("🤖 AI Parameter Extraction")
            print(f"📝 Task: {task}")
            print(f"🔍 Available parameters: {list(param_mapping.keys())}")

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()
            print(f"🔮 AI Response: {response_text}")

            extracted_params = json.loads(response_text)
            print(f"✅ Parsed parameters: {extracted_params}")

            # Update params dict with extracted parameters
            for key, value in extracted_params.items():
                params[key] = value
                print(f"  📥 {key}: {value}")

            print(f"🎯 Total extracted: {len(extracted_params)} parameters")

        except Exception as e:
            print(f"AI parameter extraction failed, falling back to basic parsing: {e}")
            # Simple fallback for critical parameters
            task_lower = task.lower()

            # Basic material ID extraction
            if 'material_id' in param_mapping:
                import re
                match = re.search(r'mp-?\d+', task_lower)
                if match:
                    params[param_mapping['material_id'][0]] = match.group()

            # Basic temperature extraction
            if 'temperature' in param_mapping:
                match = re.search(r'(\d+)(?:\s*-\s*(\d+))?\s*k', task_lower)
                if match:
                    if match.group(2):  # Range
                        start, end = int(match.group(1)), int(match.group(2))
                        params[param_mapping['temperature'][0]] = list(range(start, end + 1, 100))
                    else:  # Single value
                        params[param_mapping['temperature'][0]] = [int(match.group(1))]

    def _get_parameter_description(self, param_key: str) -> str:
        """Get human-readable description for parameter"""
        descriptions = {
            'material_id': 'Material identifier (e.g., mp-149, silicon)',
            'temperature': 'Temperature in Kelvin (single value or range)',
            'supercell': 'Supercell dimensions as three integers [x, y, z]',
            'timestep': 'Timestep in femtoseconds',
            'equilibration_time': 'Equilibration time in picoseconds',
            'production_time': 'Production time in picoseconds',
            'formula': 'Chemical formula (e.g., Si, Al2O3)',
            'property': 'Physical property to calculate'
        }
        return descriptions.get(param_key, f'Parameter: {param_key}')

    def _determine_workflow(self, task_lower: str, config: Dict, params: Dict) -> str:
        """Determine workflow using configuration's method resolution"""

        method_resolution = config.get('method_resolution', {})
        understands = config.get('understands', {})

        # Find the best matching method based on keywords/aliases
        best_method = None
        best_score = 0

        for capability, spec in understands.items():
            keywords = spec.get('keywords', [])
            aliases = spec.get('aliases', [])
            all_terms = keywords + aliases + [capability]

            score = sum(1 for term in all_terms if term.lower() in task_lower)
            if score > best_score:
                best_score = score
                best_method = spec.get('method', capability)

        return best_method

    def _check_multi_step_workflow(self, task_lower: str, runner_kind: str, params: Dict, workflow: str) -> str:
        """Check if we need a multi-step workflow based on parameters and context"""

        # Check for material-specific calculations that need fetching
        has_material_id = 'material_id' in params
        has_mp_reference = any(term in task_lower for term in ['mp-']) # Only explicit Materials Project references
        # Use word boundaries to avoid false matches like "si" in "simulation"
        import re
        material_patterns = [r'\bsilicon\b', r'\bsi\b', r'\bgaas\b', r'\bgraphene\b', r'\bgermanium\b', r'\bge\b']
        has_specific_material = any(re.search(pattern, task_lower) for pattern in material_patterns) and 'mp-' not in task_lower

        # Check for calculation types
        has_thermal_calc = any(term in task_lower for term in ['thermal', 'conductivity', 'kappa', 'heat'])
        has_lammps_calc = any(term in task_lower for term in ['lammps', 'molecular dynamics', 'md'])
        has_simulation_params = any(param in params for param in ['temperature', 'supercell', 'timestep'])

        # Only suggest multi-step workflow if we have clear material identification
        needs_material_fetch = has_material_id or has_mp_reference or (has_specific_material and (has_thermal_calc or has_lammps_calc))

        # Determine if we need multi-step workflow
        if needs_material_fetch:
            # Need to fetch material data first, then calculate
            if has_thermal_calc or 'conductivity' in task_lower:
                return "fetch_then_kappa"
            elif 'thermal' in task_lower:
                return "fetch_then_thermal"
            elif has_lammps_calc or has_simulation_params:
                return "fetch_then_lammps"

        # Return original workflow if no multi-step needed
        return workflow