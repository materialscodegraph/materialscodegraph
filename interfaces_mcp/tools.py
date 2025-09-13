"""Planning and explanation tools for natural language interactions"""
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


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

        # First, extract ALL possible parameters from ALL configurations
        # This ensures we capture material_id, temperature, etc. regardless of which runner matches first
        all_param_mappings = {}
        for config_name, config in self.configs.items():
            param_mapping = config.get('parameter_mapping', {})
            for param_key, param_aliases in param_mapping.items():
                if param_key not in all_param_mappings:
                    all_param_mappings[param_key] = param_aliases

        # Extract parameters using combined mapping from all configurations
        self._extract_parameters_from_task(task_lower, params, all_param_mappings, missing)

        # Now find the best matching configuration for execution
        best_match = None
        best_score = 0

        for config_name, config in self.configs.items():
            understands = config.get('understands', {})
            score = 0
            matched_keywords = []

            # Check each capability this config understands
            for capability, spec in understands.items():
                keywords = spec.get('keywords', [])
                aliases = spec.get('aliases', [])

                # Check if task matches any keywords or aliases
                all_terms = keywords + aliases + [capability]
                for term in all_terms:
                    if term.lower() in task_lower:
                        score += 1
                        matched_keywords.append(term)

            if score > best_score:
                best_score = score
                best_match = {
                    'config_name': config_name,
                    'config': config,
                    'matched_keywords': matched_keywords,
                    'score': score
                }

        if best_match:
            runner_kind = best_match['config_name']
            config = best_match['config']

            # Determine workflow based on configuration's method resolution
            workflow = self._determine_workflow(task_lower, config, params)

            # Check if we need multiple runners for a workflow based on extracted parameters
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

    def _extract_parameters_from_task(self, task_lower: str, params: Dict, param_mapping: Dict, missing: List):
        """Extract parameters from task using configuration's parameter mapping"""

        # Material ID extraction (generic pattern)
        material_patterns = [
            r'mp-?\d+',  # Materials Project IDs
            r'\b[A-Z][a-z]?\d*\b',  # Chemical formulas like Si, Al2O3
        ]

        for pattern in material_patterns:
            match = re.search(pattern, task_lower, re.IGNORECASE)
            if match:
                material_id = match.group()
                if 'material_id' in param_mapping:
                    params[param_mapping['material_id'][0]] = material_id
                    break

        # Temperature extraction
        temp_patterns = [
            (r'(\d+)\s*(?:-|to|–)\s*(\d+)\s*k', 'range'),  # Range like "300-800K"
            (r'(\d+)\s*k(?:elvin)?', 'single'),  # Single temp like "300K"
        ]

        for pattern, pattern_type in temp_patterns:
            if 'temperature' in param_mapping:
                temp_aliases = param_mapping['temperature']
                matches = re.findall(pattern, task_lower)
                if matches:
                    if pattern_type == 'range' and len(matches[0]) == 2:
                        T_start, T_end = int(matches[0][0]), int(matches[0][1])
                        temp_values = list(range(T_start, T_end + 1, 100))
                    else:
                        temp_values = [int(m) if isinstance(m, str) else int(m[0]) for m in matches]

                    params[temp_aliases[0]] = temp_values
                    break
        else:
            if 'temperature' in param_mapping:
                missing.append('temperature')

        # Supercell extraction
        supercell_patterns = [
            r'(\d+)x(\d+)x(\d+)',  # Format like "20x20x20"
            r'[\(\[]?\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)\s*[\)\]]?'  # Format like "[20, 20, 20]"
        ]

        if 'supercell' in param_mapping:
            supercell_aliases = param_mapping['supercell']
            for pattern in supercell_patterns:
                match = re.search(pattern, task_lower)
                if match:
                    params[supercell_aliases[0]] = [int(match.group(1)), int(match.group(2)), int(match.group(3))]
                    break
            else:
                missing.append('supercell')

        # Generic numeric parameter extraction for timestep, etc.
        numeric_patterns = {
            'timestep': r'timestep[:\s]*(\d+\.?\d*)\s*fs',
            'equilibration': r'equil[^\d]*(\d+)\s*ps',
            'production': r'prod[^\d]*(\d+)\s*ps',
        }

        for param_key, pattern in numeric_patterns.items():
            if param_key in param_mapping:
                match = re.search(pattern, task_lower)
                if match:
                    param_aliases = param_mapping[param_key]
                    params[param_aliases[0]] = float(match.group(1))

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

        # If we have both material_id and thermal properties, suggest fetch-then-calculate workflow
        has_material_fetch = 'material_id' in params
        has_thermal_calc = any(term in task_lower for term in ['thermal', 'conductivity', 'kappa'])

        if has_material_fetch and has_thermal_calc:
            return "fetch_then_kappa"

        return workflow