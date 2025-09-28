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

        # Initialize plan components
        assets = []
        params = {}
        missing = []

        # Build parameter schema from all configurations for AI
        all_parameters = set()
        for config_name, config in self.configs.items():
            for method_name, method_config in config.get('skills', {}).items():
                all_parameters.update(method_config.get('required_parameters', []))
                all_parameters.update(method_config.get('optional_parameters', []))

        # Create parameter mapping for AI (simple mapping - parameter name to itself)
        all_param_mappings = {param: [param] for param in all_parameters}

        # Extract parameters using AI with all available parameters
        self._extract_parameters_from_task(nl_task, params, all_param_mappings, missing)

        # Use LLM to create a general workflow plan
        workflow_steps = self._create_workflow_plan(nl_task, params)

        # Create params asset if we have params
        if params:
            params_asset = Asset(
                type="Params",
                id=asset_id("Params", params),
                payload=params
            )
            assets.append(params_asset)

        # Create the plan with workflow steps
        plan = {
            "assets": assets,
            "params": params,
            "workflow": "multi_step_workflow",
            "missing": missing,
            "workflow_steps": workflow_steps
        }

        return plan

    def _create_workflow_plan(self, task: str, params: Dict) -> List[Dict]:
        """Use LLM to create a general workflow plan with any number of steps"""

        # Get available tools and their capabilities
        available_tools = self._get_available_tools()

        # Create prompt for LLM workflow planning
        workflow_prompt = f"""
Task: {task}
Parameters extracted: {params}

Available computational tools and their capabilities:
"""

        for tool_name, tool_info in available_tools.items():
            workflow_prompt += f"\n{tool_name}:\n"
            for method_name, method_info in tool_info['skills'].items():
                workflow_prompt += f"  - {method_name}: {method_info['description']}\n"
                workflow_prompt += f"    Requires: {', '.join(method_info.get('required_parameters', []))}\n"
                if method_info.get('outputs'):
                    outputs = [out.get('name', out) if isinstance(out, dict) else out for out in method_info['outputs']]
                    workflow_prompt += f"    Produces: {', '.join(outputs)}\n"

        workflow_prompt += f"""

Please analyze this task and break it down into a sequence of computational steps.

Respond with a JSON array of steps, where each step has:
- "step": step number (1, 2, 3, ...)
- "description": what this step does
- "runner": which tool to use (exact name from available tools)
- "method": which method within that tool
- "depends_on": array of step numbers this step depends on (empty array if no dependencies)

Example response for "Calculate thermal conductivity for mp-149 silicon":
[
  {{
    "step": 1,
    "description": "Fetch material structure and properties for mp-149 silicon",
    "runner": "MaterialsProject",
    "method": "fetch_material",
    "depends_on": []
  }},
  {{
    "step": 2,
    "description": "Calculate thermal conductivity using molecular dynamics simulation",
    "runner": "LAMMPS",
    "method": "green_kubo",
    "depends_on": [1]
  }}
]

For single-step tasks like "Run LAMMPS with temperature 400K", respond with:
[
  {{
    "step": 1,
    "description": "Run LAMMPS molecular dynamics simulation",
    "runner": "LAMMPS",
    "method": "green_kubo",
    "depends_on": []
  }}
]

Workflow plan for the given task:"""

        try:
            # Use AI to create workflow plan
            from anthropic import Anthropic
            import os
            import json

            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": workflow_prompt
                }]
            )

            workflow_response = response.content[0].text.strip()

            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', workflow_response, re.DOTALL)
            if json_match:
                workflow_json = json_match.group(0)
                workflow_steps = json.loads(workflow_json)

                # Validate and clean the steps
                validated_steps = []
                for step in workflow_steps:
                    if all(key in step for key in ['step', 'runner', 'method']):
                        validated_steps.append(step)

                return validated_steps
            else:
                print("Could not parse workflow JSON from LLM response")
                return []

        except Exception as e:
            print(f"LLM workflow planning failed: {e}")
            # Fallback: create a simple single-step plan
            return [{
                "step": 1,
                "description": f"Execute task: {task}",
                "runner": "LAMMPS",  # Default fallback
                "method": "green_kubo",
                "depends_on": []
            }]

    def _get_available_tools(self) -> Dict:
        """Get available tools and their capabilities from configs"""
        tools = {}

        for config_name, config in self.configs.items():
            tool_name = config.get('name', config_name)
            tools[tool_name] = {
                'description': config.get('description', ''),
                'skills': {}
            }

            for method_name, method_config in config.get('skills', {}).items():
                tools[tool_name]['skills'][method_name] = {
                    'description': method_config.get('description', f'{method_name} method'),
                    'required_parameters': method_config.get('required_parameters', []),
                    'optional_parameters': method_config.get('optional_parameters', []),
                    'outputs': method_config.get('outputs', [])
                }

        return tools
    
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

