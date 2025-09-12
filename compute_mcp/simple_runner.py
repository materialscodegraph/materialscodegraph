"""Simplified configuration-driven MCP runner

This runner uses intuitive YAML configurations to map natural language
to computational methods without complex regex or nested structures.
"""

import os
import re
import yaml
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from common.schema import Asset, Edge, Run
from common.ids import asset_id, generate_id
from common.io import write_uri


class SimpleRunner:
    """Simple, intuitive configuration-driven runner"""
    
    def __init__(self, config_dir: str = None):
        """Initialize with configuration directory"""
        if config_dir is None:
            config_dir = Path(__file__).parent / "configs"
        self.config_dir = Path(config_dir)
        self.configs = {}
        self.load_configs()
    
    def load_configs(self):
        """Load all YAML configurations"""
        for config_file in self.config_dir.glob("*.yaml"):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                name = config_file.stem
                self.configs[name] = config
                print(f"Loaded {config['name']}")
    
    def understand(self, text: str) -> Dict[str, Any]:
        """Understand what the user wants from natural language"""
        text_lower = text.lower()
        
        # Try each runner config
        for runner_id, config in self.configs.items():
            
            # Check if any understood phrases match
            for phrase, details in config.get('understands', {}).items():
                # Check main phrase
                if phrase in text_lower:
                    return {
                        'runner': runner_id,
                        'method': details.get('method') or details.get('action'),
                        'matched': phrase
                    }
                
                # Check aliases
                for alias in details.get('aliases', []):
                    if alias in text_lower:
                        return {
                            'runner': runner_id,
                            'method': details.get('method') or details.get('action'),
                            'matched': alias
                        }
        
        return None
    
    def extract_params(self, text: str, runner_id: str) -> Dict[str, Any]:
        """Extract parameters from natural language"""
        if runner_id not in self.configs:
            return {}
        
        config = self.configs[runner_id]
        extracts = config.get('extracts', {})
        params = {}
        text_lower = text.lower()
        
        for param_name, param_config in extracts.items():
            value = None
            
            # Check for shortcuts first (like silicon -> mp-149)
            if 'shortcuts' in param_config:
                for shortcut, shortcut_value in param_config['shortcuts'].items():
                    if shortcut in text_lower:
                        value = shortcut_value
                        break
            
            # If no shortcut found, look for keywords
            if value is None:
                for keyword in param_config.get('keywords', []):
                    if keyword in text_lower:
                        # Try to extract value near the keyword
                        value = self._extract_near_keyword(text_lower, keyword, param_config)
                        if value is not None:
                            break
            
            # Use default if nothing found and not required
            if value is None and not param_config.get('required', False):
                if 'default' in param_config:
                    value = param_config['default']
            
            if value is not None:
                params[param_name] = value
        
        return params
    
    def _extract_near_keyword(self, text: str, keyword: str, config: Dict) -> Any:
        """Extract value near a keyword based on examples"""
        
        # Simple patterns based on common formats
        patterns = {
            'number': r'(\d+\.?\d*)',
            'range': r'(\d+)\s*(?:to|-)\s*(\d+)',
            'list': r'(\d+)(?:\s*,\s*(\d+))*',
            'triple': r'(\d+)\s*[x×]\s*(\d+)\s*[x×]\s*(\d+)'
        }
        
        # Look for patterns near the keyword
        search_window = 30  # characters around keyword
        keyword_pos = text.find(keyword)
        if keyword_pos == -1:
            return None
        
        start = max(0, keyword_pos - search_window)
        end = min(len(text), keyword_pos + len(keyword) + search_window)
        text_slice = text[start:end]
        
        # Try to match against example patterns
        if 'examples' in config:
            for example in config['examples']:
                if '->' in example:
                    pattern_str, result = example.split(' -> ')
                    pattern_str = pattern_str.strip().lower()
                    
                    # Convert example to regex
                    if 'to' in pattern_str or '-' in pattern_str:
                        # Range pattern
                        match = re.search(patterns['range'], text_slice)
                        if match:
                            start_val = int(match.group(1))
                            end_val = int(match.group(2))
                            # Generate range with 100 step default
                            return list(range(start_val, end_val + 1, 100))
                    
                    elif 'x' in pattern_str or '×' in pattern_str:
                        # Triple pattern (like 10x10x10)
                        match = re.search(patterns['triple'], text_slice)
                        if match:
                            return [int(match.group(1)), int(match.group(2)), int(match.group(3))]
                    
                    elif ',' in pattern_str:
                        # List pattern
                        matches = re.findall(patterns['number'], text_slice)
                        if matches:
                            return [float(m) if '.' in m else int(m) for m in matches]
                    
                    else:
                        # Single number
                        match = re.search(patterns['number'], text_slice)
                        if match:
                            val = match.group(1)
                            return float(val) if '.' in val else int(val)
        
        # Fallback: just find a number near the keyword
        match = re.search(patterns['number'], text_slice)
        if match:
            val = match.group(1)
            return float(val) if '.' in val else int(val)
        
        return None
    
    def run(self, runner_id: str, run_obj: Run, assets: List[Asset], 
            params: Dict[str, Any], method: str = None) -> Dict[str, Any]:
        """Execute a computation using the specified runner"""
        
        if runner_id not in self.configs:
            raise ValueError(f"Unknown runner: {runner_id}")
        
        config = self.configs[runner_id]
        
        # Update run status
        run_obj.status = "running"
        run_obj.started_at = datetime.utcnow().isoformat()
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                
                # Get the script template
                generates = config.get('generates', {})
                if method and method in generates:
                    template_config = generates[method]
                else:
                    # Use first available
                    method = list(generates.keys())[0] if generates else None
                    template_config = generates.get(method, {})
                
                # Prepare context for template
                context = self._prepare_context(params, assets, template_config)
                
                # Generate script
                script = template_config.get('script', '')
                for key, value in context.items():
                    script = script.replace(f'{{{key}}}', str(value))
                
                # Write script
                script_ext = '.py' if 'python' in script or 'import' in script else '.in'
                script_path = tmppath / f"run{script_ext}"
                with open(script_path, 'w') as f:
                    f.write(script)
                
                # Execute based on config
                result = self._execute(config, script_path, tmppath)
                
                # Parse results
                results = self._parse_output(config, method, tmppath)
                
                # Create result assets
                result_assets = self._create_assets(config, results, run_obj)
                
                # Create edges
                edges = self._create_edges(run_obj, assets, result_assets)
                
                # Update run status
                run_obj.status = "done"
                run_obj.ended_at = datetime.utcnow().isoformat()
                
                return {
                    "run": run_obj.to_dict(),
                    "assets": [a.to_dict() for a in result_assets],
                    "edges": [e.to_dict() for e in edges]
                }
                
        except Exception as e:
            run_obj.status = "error"
            run_obj.ended_at = datetime.utcnow().isoformat()
            run_obj.error_message = str(e)
            raise
    
    def _prepare_context(self, params: Dict, assets: List[Asset], 
                        template_config: Dict) -> Dict[str, Any]:
        """Prepare context for template rendering"""
        context = params.copy()
        
        # Add common calculated values
        if 'temperature' in params and isinstance(params['temperature'], list):
            context['temperature'] = params['temperature'][0]  # Use first for template
        
        if 'equil' in params.get('simulation_time', {}):
            context['equil_steps'] = int(params['simulation_time']['equil'] * 1000)
        if 'prod' in params.get('simulation_time', {}):
            context['prod_steps'] = int(params['simulation_time']['prod'] * 1000)
        
        # Add asset data
        for asset in assets:
            if asset.type == "System":
                context['structure'] = asset.payload
        
        return context
    
    def _execute(self, config: Dict, script_path: Path, work_dir: Path) -> Any:
        """Execute the script"""
        runs_with = config.get('runs_with', {})
        
        # Prefer docker if available
        if 'docker' in runs_with:
            image = runs_with['docker']
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{work_dir}:/work',
                '-w', '/work',
                image
            ]
            
            if script_path.suffix == '.py':
                cmd.extend(['python', script_path.name])
            else:
                cmd.extend(['lmp', '-in', script_path.name])
            
            return subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir)
        
        # Fallback to local
        elif 'local' in runs_with:
            executable = runs_with['local']
            
            if script_path.suffix == '.py':
                cmd = [executable, str(script_path)]
            else:
                cmd = [executable, '-in', str(script_path)]
            
            return subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir)
        
        raise ValueError("No execution method configured")
    
    def _parse_output(self, config: Dict, method: str, output_dir: Path) -> Dict:
        """Parse output files"""
        parses = config.get('parses', {})
        if method not in parses:
            return {}
        
        parse_config = parses[method]
        results = {}
        
        # Read the output file
        output_file = output_dir / parse_config.get('file', 'output.dat')
        if output_file.exists():
            # Simple JSON parsing for now
            if output_file.suffix == '.json':
                with open(output_file, 'r') as f:
                    data = json.load(f)
                
                # Extract specified fields
                for item in parse_config.get('gets', []):
                    if ' -> ' in item:
                        source, target = item.split(' -> ')
                        results[target] = data.get(source)
                    else:
                        results[item] = data.get(item)
        
        return results
    
    def _create_assets(self, config: Dict, results: Dict, run_obj: Run) -> List[Asset]:
        """Create result assets"""
        assets = []
        
        # Create Results asset
        if results:
            results_asset = Asset(
                type="Results",
                id=asset_id("Results", results),
                payload=results
            )
            assets.append(results_asset)
        
        # Create Artifact for raw output
        artifact_uri = f"mcg://artifacts/{run_obj.id}_output.json"
        artifact_hash = write_uri(artifact_uri, results)
        
        artifact_asset = Asset(
            type="Artifact",
            id=generate_id("A"),
            payload={
                "uri": artifact_uri,
                "kind": "output",
                "media_type": "application/json",
                "description": f"Output from {config.get('name', 'unknown')}"
            },
            uri=artifact_uri,
            hash=artifact_hash
        )
        assets.append(artifact_asset)
        
        return assets
    
    def _create_edges(self, run_obj: Run, inputs: List[Asset], 
                     outputs: List[Asset]) -> List[Edge]:
        """Create provenance edges"""
        edges = []
        timestamp = datetime.utcnow().isoformat()
        
        # Input edges
        for asset in inputs:
            edges.append(Edge(
                from_id=run_obj.id,
                to_id=asset.id,
                rel="USES",
                t=timestamp
            ))
        
        # Output edges
        for asset in outputs:
            edges.append(Edge(
                from_id=run_obj.id,
                to_id=asset.id,
                rel="PRODUCES",
                t=timestamp
            ))
        
        return edges


def plan_from_nl(text: str) -> Dict[str, Any]:
    """Simple function to test natural language understanding"""
    runner = SimpleRunner()
    
    # Understand the intent
    intent = runner.understand(text)
    if not intent:
        return {"error": "Could not understand the request"}
    
    # Extract parameters
    params = runner.extract_params(text, intent['runner'])
    
    return {
        "runner": intent['runner'],
        "method": intent['method'],
        "params": params,
        "matched_on": intent['matched']
    }


# Example usage
if __name__ == "__main__":
    # Test natural language understanding
    examples = [
        "Calculate thermal conductivity of silicon using LAMMPS from 300 to 800K",
        "Use kaldo to compute phonon properties with a 20x20x20 mesh",
        "Fetch mp-149 from materials project",
        "Get the band gap of GaN",
        "Run BTE calculation at 300K with gaussian broadening"
    ]
    
    for example in examples:
        print(f"\nInput: {example}")
        result = plan_from_nl(example)
        print(f"Result: {json.dumps(result, indent=2)}")