#!/usr/bin/env python3
"""
Repository Scanner - Universal tool for scanning simulation code repositories
and generating configuration files for materialcodegraph integration.
Integrated as part of the interfaces_mcp module.
"""

import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import logging
import anthropic

logger = logging.getLogger(__name__)

# Code detection patterns
CODE_SIGNATURES = {
    'kaldo': {
        'imports': ['kaldo', 'from kaldo', 'import kaldo'],
        'files': ['forceconstants.py', 'phonons.py', 'conductivity.py'],
        'extensions': ['.py'],
        'classes': ['Phonons', 'ForceConstants', 'Conductivity'],
        'keywords': ['phonon', 'thermal_conductivity', 'anharmonic', 'force_constants'],
        'capabilities': ['thermal_conductivity', 'phonon_dispersion', 'anharmonic_properties']
    },
    'lammps': {
        'imports': ['lammps', 'from lammps', 'import lammps', 'PyLammps'],
        'files': ['in.', '.lammps', '.data', '.dump'],
        'extensions': ['.lammps', '.in', '.data'],
        'classes': ['LAMMPS', 'PyLammps'],
        'keywords': ['pair_style', 'fix', 'compute', 'thermo', 'timestep', 'atom_style'],
        'capabilities': ['molecular_dynamics', 'thermal_conductivity', 'structure_optimization']
    },
    'quantum_espresso': {
        'imports': ['espresso', 'qe', 'pwscf', 'ase.calculators.espresso'],
        'files': ['.pw', '.in', '.out', 'scf.in', 'bands.in', 'ph.in'],
        'extensions': ['.in', '.out'],
        'classes': ['Espresso', 'PWscf'],
        'keywords': ['&control', '&system', '&electrons', 'ATOMIC_SPECIES', 'K_POINTS'],
        'capabilities': ['dft_calculation', 'band_structure', 'phonon_calculation', 'structure_optimization']
    },
    'vasp': {
        'imports': ['vasp', 'pymatgen', 'ase.calculators.vasp'],
        'files': ['INCAR', 'POSCAR', 'KPOINTS', 'POTCAR', 'OUTCAR', 'CONTCAR'],
        'extensions': [],
        'classes': ['Vasp', 'VaspCalculator'],
        'keywords': ['ENCUT', 'ISMEAR', 'IBRION', 'NSW', 'PREC', 'ALGO'],
        'capabilities': ['dft_calculation', 'structure_optimization', 'band_structure', 'dos_calculation']
    },
    'ase': {
        'imports': ['ase', 'from ase', 'import ase'],
        'files': ['.traj', '.xyz', '.cif'],
        'extensions': ['.traj', '.xyz'],
        'classes': ['Atoms', 'Calculator', 'Trajectory', 'FixAtoms'],
        'keywords': ['atoms', 'calculator', 'get_potential_energy', 'get_forces'],
        'capabilities': ['structure_manipulation', 'calculator_interface', 'molecular_dynamics']
    },
    'materials_project': {
        'imports': ['pymatgen', 'mp_api', 'materialsproject', 'MPRester'],
        'files': ['.json', '.yaml'],
        'extensions': ['.json', '.yaml'],
        'classes': ['MPRester', 'Structure', 'ComputedEntry'],
        'keywords': ['mp-', 'band_gap', 'formation_energy', 'material_id'],
        'capabilities': ['material_search', 'property_retrieval', 'structure_download']
    },
    'cp2k': {
        'imports': ['cp2k', 'ase.calculators.cp2k'],
        'files': ['.inp', '.restart'],
        'extensions': ['.inp'],
        'classes': ['CP2K'],
        'keywords': ['&GLOBAL', '&FORCE_EVAL', '&DFT', '&QS'],
        'capabilities': ['dft_calculation', 'molecular_dynamics', 'monte_carlo']
    },
    'siesta': {
        'imports': ['siesta', 'ase.calculators.siesta'],
        'files': ['.fdf', '.out'],
        'extensions': ['.fdf'],
        'classes': ['Siesta'],
        'keywords': ['SystemName', 'NumberOfAtoms', 'PAO.BasisSize', 'MeshCutoff'],
        'capabilities': ['dft_calculation', 'structure_optimization', 'molecular_dynamics']
    }
}


@dataclass
class CodePattern:
    """Represents a code pattern found in examples"""
    file_path: str
    skill_name: str
    parameters: Dict[str, Any]
    imports: List[str]
    description: str = ""
    capability: str = ""
    code_snippet: str = ""
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)


@dataclass
class MethodConfig:
    """Configuration for a computational method"""
    description: str
    capability: str
    required_parameters: List[str] = field(default_factory=list)  # Must be provided by user
    optional_parameters: List[str] = field(default_factory=list)   # Can be omitted by user
    parameter_types: Dict[str, str] = field(default_factory=dict)
    default_parameters: Dict[str, Any] = field(default_factory=dict)    # Defaults for any parameter
    input_template: List[str] = field(default_factory=list)
    script_template: str = ""
    outputs: List[Dict[str, str]] = field(default_factory=list)
    execution: Dict[str, Any] = field(default_factory=dict)


class RepoScanner:
    """Universal scanner class for analyzing simulation code repositories"""

    def __init__(self, repo_path: str, code_name: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.patterns: List[CodePattern] = []
        self.skills: Dict[str, MethodConfig] = {}
        self.input_examples: Dict[str, List[str]] = defaultdict(list)
        self.documentation: Dict[str, str] = {}

        # Auto-detect code if not specified
        if code_name and code_name != 'auto':
            self.code_name = code_name.lower()
        else:
            self.code_name = self.detect_code_type()
            logger.info(f"Auto-detected code type: {self.code_name}")

        # Initialize Anthropic client
        self.client = anthropic.Anthropic()

    def detect_code_type(self) -> str:
        """Auto-detect the type of simulation code in the repository"""
        detected_scores = defaultdict(int)

        # Check for characteristic files and patterns
        for code, signatures in CODE_SIGNATURES.items():
            # Check for characteristic files
            for file_pattern in signatures['files']:
                matches = list(self.repo_path.rglob(f"*{file_pattern}*"))
                detected_scores[code] += len(matches) * 3

            # Check extensions
            for ext in signatures['extensions']:
                matches = list(self.repo_path.rglob(f"*{ext}"))
                detected_scores[code] += len(matches) * 2

            # Check Python files for imports and classes (limit search for performance)
            py_files = list(self.repo_path.rglob("*.py"))[:100]
            for py_file in py_files:
                try:
                    content = py_file.read_text()
                    # Check imports
                    for imp in signatures['imports']:
                        if imp in content:
                            detected_scores[code] += 5
                    # Check classes
                    for cls in signatures['classes']:
                        if re.search(rf'\b{cls}\b', content):
                            detected_scores[code] += 3
                    # Check keywords
                    for keyword in signatures['keywords']:
                        if keyword.lower() in content.lower():
                            detected_scores[code] += 1
                except Exception:
                    continue

        # Return the code with highest score
        if detected_scores:
            detected_code = max(detected_scores, key=detected_scores.get)
            logger.info(f"Detection scores: {dict(detected_scores)}")
            return detected_code

        # Default fallback
        logger.warning("Could not auto-detect code type, using 'generic'")
        return 'generic'

    def scan(self) -> Dict[str, Any]:
        """Main scanning method"""
        logger.info(f"Scanning {self.code_name} repository: {self.repo_path}")

        # Step 1: Find relevant files based on code type
        example_files = self.find_example_files()
        input_files = self.find_input_files()
        doc_files = self.find_documentation()

        logger.info(f"Found {len(example_files)} example files, {len(input_files)} input files, {len(doc_files)} docs")

        # Step 2: Extract patterns from examples
        for file_path in example_files[:100]:  # Limit to prevent excessive processing
            patterns = self.extract_patterns(file_path)
            self.patterns.extend(patterns)

        # Step 3: Parse input files
        for input_file in input_files[:50]:
            self.parse_input_file(input_file)

        logger.info(f"Extracted {len(self.patterns)} code patterns")

        # Step 4: Analyze patterns with LLM
        if self.patterns:
            self.analyze_with_llm()

        # Step 5: Consolidate into skills
        self.consolidate_skills()

        # Step 6: Generate config
        config = self.generate_config()

        return config

    def find_example_files(self) -> List[Path]:
        """Find example files based on code type"""
        example_files = []

        # Common example directory names
        example_dirs = ['examples', 'example', 'test', 'tests', 'demo', 'demos',
                       'tutorial', 'tutorials', 'benchmarks', 'samples']

        # Get code-specific extensions
        extensions = CODE_SIGNATURES.get(self.code_name, {}).get('extensions', ['.py'])

        # Find files in example directories
        for dir_name in example_dirs:
            for example_dir in self.repo_path.rglob(dir_name):
                if example_dir.is_dir():
                    # Add code-specific files
                    if self.code_name == 'lammps':
                        example_files.extend(example_dir.rglob('in.*'))
                        example_files.extend(example_dir.rglob('*.lammps'))
                    elif self.code_name == 'quantum_espresso':
                        example_files.extend(example_dir.rglob('*.in'))
                        example_files.extend(example_dir.rglob('*.pw'))
                    elif self.code_name == 'vasp':
                        example_files.extend(example_dir.rglob('INCAR*'))
                        example_files.extend(example_dir.rglob('POSCAR*'))
                    else:
                        # Default to Python files and known extensions
                        for ext in extensions:
                            example_files.extend(example_dir.rglob(f'*{ext}'))

        # Also look for files with example patterns
        for pattern in ['*example*', '*demo*', '*tutorial*', '*test*']:
            for ext in extensions:
                example_files.extend(self.repo_path.rglob(f'{pattern}{ext}'))

        # Remove duplicates and filter
        example_files = list(set(f for f in example_files
                               if f.is_file() and f.stat().st_size < 500_000))

        return example_files

    def find_input_files(self) -> List[Path]:
        """Find input template files based on code type"""
        input_files = []

        if self.code_name == 'lammps':
            input_files.extend(self.repo_path.rglob('*.lammps'))
            input_files.extend(self.repo_path.rglob('in.*'))
        elif self.code_name == 'quantum_espresso':
            input_files.extend(self.repo_path.rglob('*.pw.in'))
            input_files.extend(self.repo_path.rglob('*.ph.in'))
            input_files.extend(self.repo_path.rglob('*.pp.in'))
        elif self.code_name == 'vasp':
            input_files.extend(self.repo_path.rglob('INCAR'))
            input_files.extend(self.repo_path.rglob('KPOINTS'))
        elif self.code_name == 'cp2k':
            input_files.extend(self.repo_path.rglob('*.inp'))
        elif self.code_name == 'siesta':
            input_files.extend(self.repo_path.rglob('*.fdf'))

        return list(set(f for f in input_files
                       if f.is_file() and f.stat().st_size < 100_000))

    def find_documentation(self) -> List[Path]:
        """Find documentation files"""
        doc_files = []
        doc_patterns = ['README*', 'readme*', '*.md', '*.rst', '*.txt', 'doc*', 'Doc*']

        for pattern in doc_patterns:
            doc_files.extend(self.repo_path.rglob(pattern))

        return list(set(f for f in doc_files
                       if f.is_file() and f.stat().st_size < 500_000))

    def parse_input_file(self, file_path: Path):
        """Parse input files based on code type"""
        try:
            content = file_path.read_text()

            if self.code_name == 'lammps':
                self._parse_lammps_input(content, file_path)
            elif self.code_name == 'quantum_espresso':
                self._parse_qe_input(content, file_path)
            elif self.code_name == 'vasp':
                self._parse_vasp_input(content, file_path)
            elif self.code_name == 'cp2k':
                self._parse_cp2k_input(content, file_path)

        except Exception as e:
            logger.debug(f"Could not parse input file {file_path}: {e}")

    def _parse_lammps_input(self, content: str, file_path: Path):
        """Parse LAMMPS input script"""
        commands = defaultdict(list)
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split()
                if parts:
                    commands[parts[0]].append(line)

        # Extract pattern
        pattern = CodePattern(
            file_path=str(file_path),
            skill_name='lammps_simulation',
            parameters={'commands': dict(commands)},
            imports=[],
            description=f"LAMMPS input from {file_path.name}",
            capability='molecular_dynamics'
        )
        self.patterns.append(pattern)

    def _parse_qe_input(self, content: str, file_path: Path):
        """Parse Quantum ESPRESSO input file"""
        sections = {}
        current_section = None

        for line in content.splitlines():
            if line.strip().startswith('&'):
                current_section = line.strip()
                sections[current_section] = []
            elif current_section and line.strip() and not line.strip().startswith('/'):
                sections[current_section].append(line.strip())

        # Determine calculation type
        capability = 'dft_calculation'
        if '&phonon' in sections:
            capability = 'phonon_calculation'
        elif 'calculation' in str(sections):
            if 'bands' in str(sections).lower():
                capability = 'band_structure'

        pattern = CodePattern(
            file_path=str(file_path),
            skill_name='qe_calculation',
            parameters={'sections': sections},
            imports=[],
            description=f"QE input from {file_path.name}",
            capability=capability
        )
        self.patterns.append(pattern)

    def _parse_vasp_input(self, content: str, file_path: Path):
        """Parse VASP input files"""
        parameters = {}

        if 'INCAR' in file_path.name:
            for line in content.splitlines():
                if '=' in line and not line.strip().startswith('#'):
                    parts = line.split('=')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        parameters[key] = value

            # Determine calculation type
            capability = 'dft_calculation'
            if 'IBRION' in parameters:
                if parameters['IBRION'] in ['1', '2', '3']:
                    capability = 'structure_optimization'

            pattern = CodePattern(
                file_path=str(file_path),
                skill_name='vasp_calculation',
                parameters=parameters,
                imports=[],
                description=f"VASP INCAR from {file_path.name}",
                capability=capability
            )
            self.patterns.append(pattern)

    def _parse_cp2k_input(self, content: str, file_path: Path):
        """Parse CP2K input file"""
        # Simple parsing for CP2K
        sections = defaultdict(list)
        current_section = []

        for line in content.splitlines():
            if line.strip().startswith('&'):
                section = line.strip()
                current_section.append(section)
                sections[section] = []
            elif line.strip().startswith('&END'):
                if current_section:
                    current_section.pop()
            elif current_section:
                sections[current_section[-1]].append(line.strip())

        pattern = CodePattern(
            file_path=str(file_path),
            skill_name='cp2k_calculation',
            parameters={'sections': dict(sections)},
            imports=[],
            description=f"CP2K input from {file_path.name}",
            capability='dft_calculation'
        )
        self.patterns.append(pattern)

    def extract_patterns(self, file_path: Path) -> List[CodePattern]:
        """Extract code patterns from files based on code type"""
        patterns = []

        # Handle different file types
        if file_path.suffix == '.py':
            patterns = self.extract_python_patterns(file_path)
        elif self.code_name == 'lammps' and (file_path.suffix in ['.lammps', '.in'] or 'in.' in file_path.name):
            self.parse_input_file(file_path)
        elif self.code_name == 'quantum_espresso' and file_path.suffix == '.in':
            self.parse_input_file(file_path)
        elif self.code_name == 'vasp' and ('INCAR' in file_path.name or 'KPOINTS' in file_path.name):
            self.parse_input_file(file_path)
        elif self.code_name == 'cp2k' and file_path.suffix == '.inp':
            self.parse_input_file(file_path)

        return patterns

    def extract_python_patterns(self, file_path: Path) -> List[CodePattern]:
        """Extract patterns from Python files"""
        patterns = []

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")

            # Extract method calls and configurations
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    pattern = self._extract_call_pattern(node, file_path, imports, content)
                    if pattern:
                        patterns.append(pattern)
                elif isinstance(node, ast.Dict):
                    pattern = self._extract_config_pattern(node, file_path, imports, content)
                    if pattern:
                        patterns.append(pattern)

        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")

        return patterns

    def _extract_call_pattern(self, node: ast.Call, file_path: Path, imports: List[str], content: str) -> Optional[CodePattern]:
        """Extract pattern from a function call"""
        try:
            # Get function name
            if isinstance(node.func, ast.Name):
                skill_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                skill_name = node.func.attr
            else:
                return None

            # Skip common non-relevant functions
            skip_functions = ['print', 'len', 'range', 'open', 'str', 'int', 'float',
                            'list', 'dict', 'set', 'tuple', 'isinstance', 'hasattr']
            if skill_name in skip_functions:
                return None

            # Check if this is a relevant method for the detected code
            relevant = False
            if self.code_name in CODE_SIGNATURES:
                for cls in CODE_SIGNATURES[self.code_name]['classes']:
                    if cls.lower() in skill_name.lower():
                        relevant = True
                        break
                for keyword in CODE_SIGNATURES[self.code_name]['keywords']:
                    if keyword.lower() in skill_name.lower():
                        relevant = True
                        break

            if not relevant and self.code_name != 'generic':
                return None

            # Extract parameters
            parameters = {}
            for keyword in node.keywords:
                if keyword.arg:
                    try:
                        parameters[keyword.arg] = ast.literal_eval(keyword.value)
                    except:
                        parameters[keyword.arg] = str(ast.unparse(keyword.value))

            # Determine capability
            capability = self._infer_capability(skill_name, parameters)

            # Get code snippet
            try:
                snippet = ast.unparse(node)
            except:
                snippet = ""

            return CodePattern(
                file_path=str(file_path),
                skill_name=skill_name,
                parameters=parameters,
                imports=imports,
                description="",
                capability=capability,
                code_snippet=snippet
            )

        except Exception:
            return None

    def _extract_config_pattern(self, node: ast.Dict, file_path: Path, imports: List[str], content: str) -> Optional[CodePattern]:
        """Extract pattern from configuration dictionary"""
        try:
            # Look for configuration-like dictionaries
            config_keywords = ['config', 'params', 'parameters', 'settings', 'options', 'args']

            # Try to find variable name
            parent = None
            for line in content.split('\n'):
                if '=' in line and '{' in line:
                    for keyword in config_keywords:
                        if keyword in line.lower():
                            parent = line.split('=')[0].strip()
                            break

            if not parent:
                return None

            # Extract the configuration
            parameters = {}
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant):
                    key_str = key.value
                    try:
                        parameters[key_str] = ast.literal_eval(value)
                    except:
                        try:
                            parameters[key_str] = str(ast.unparse(value))
                        except:
                            parameters[key_str] = str(value)

            # Determine capability
            capability = self._infer_capability(parent, parameters)

            return CodePattern(
                file_path=str(file_path),
                skill_name=f"config_{parent}",
                parameters=parameters,
                imports=imports,
                description="",
                capability=capability,
                code_snippet=str(parameters)
            )

        except Exception:
            return None

    def _infer_capability(self, skill_name: str, parameters: Dict) -> str:
        """Infer capability from method name and parameters"""
        skill_lower = skill_name.lower()
        param_str = str(parameters).lower()

        # Check for specific capabilities
        capability_mappings = {
            'thermal_conductivity': ['thermal', 'conductivity', 'kappa', 'heat'],
            'phonon_dispersion': ['phonon', 'dispersion', 'frequency', 'bands'],
            'band_structure': ['band', 'bands', 'electronic'],
            'dos_calculation': ['dos', 'density_of_states'],
            'structure_optimization': ['optimize', 'relax', 'minimize'],
            'molecular_dynamics': ['md', 'dynamics', 'nvt', 'npt', 'nve'],
            'dft_calculation': ['scf', 'dft', 'electronic', 'energy'],
            'force_constants': ['force', 'constant', 'hessian', 'dynamical'],
            'anharmonic_properties': ['anharmonic', 'lifetime', 'linewidth']
        }

        for capability, keywords in capability_mappings.items():
            for keyword in keywords:
                if keyword in skill_lower or keyword in param_str:
                    return capability

        # Default based on code type
        if self.code_name in CODE_SIGNATURES:
            caps = CODE_SIGNATURES[self.code_name].get('capabilities', [])
            if caps:
                return caps[0]

        return 'calculation'

    def analyze_with_llm(self):
        """Use LLM to understand the code patterns"""
        logger.info("Analyzing patterns with LLM...")

        # Group patterns by capability
        capability_groups = defaultdict(list)
        for pattern in self.patterns:
            capability_groups[pattern.capability].append(pattern)

        # Analyze each capability group
        for capability, patterns in capability_groups.items():
            if len(patterns) > 100:  # Limit to prevent excessive API calls
                patterns = patterns[:100]

            # Prepare context for LLM
            context = self._prepare_llm_context(capability, patterns[:10])

            # Get LLM analysis
            analysis = self._get_llm_analysis(context)

            # Update patterns with analysis
            if analysis:
                for pattern in patterns:
                    if not pattern.description:
                        pattern.description = analysis.get('description', '')

    def _prepare_llm_context(self, capability: str, patterns: List[CodePattern]) -> str:
        """Prepare context for LLM analysis"""
        context = f"""
Analyze these {self.code_name} code patterns for the capability: {capability}

Examples found:
"""
        for i, pattern in enumerate(patterns[:5], 1):
            context += f"""
Example {i}:
File: {Path(pattern.file_path).name}
Skill: {pattern.skill_name}
Parameters: {json.dumps(pattern.parameters, indent=2)[:500]}
"""

        context += f"""

Based on these examples for {self.code_name}, determine:
1. What is the purpose and description of this capability?
2. What are the typical required and optional parameters?
3. Generate a brief input template

Respond in JSON format:
{{
    "description": "Brief description",
    "required_parameters": ["param1", "param2"],
    "optional_parameters": ["param3", "param4"],
    "template_snippet": "Brief template example"
}}
"""
        return context

    def _get_llm_analysis(self, context: str) -> Optional[Dict]:
        """Get analysis from LLM"""
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,
                messages=[{"role": "user", "content": context}]
            )

            # Extract JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.debug(f"LLM analysis failed: {e}")

        return None

    def consolidate_skills(self):
        """Consolidate patterns into skills with proper parameter classification"""
        # Group patterns by capability
        capability_groups = defaultdict(list)
        for pattern in self.patterns:
            if pattern.capability:
                capability_groups[pattern.capability].append(pattern)

        # Create method configs for each capability
        for capability, patterns in capability_groups.items():
            if not patterns:
                continue

            # Analyze parameter usage across patterns
            param_analysis = self._analyze_parameters(patterns)

            # Generate method name
            skill_name = capability.replace('_', ' ').title().replace(' ', '_').lower()

            # Create method config
            description = patterns[0].description if patterns and patterns[0].description else f"{capability} calculation"

            skill_config = MethodConfig(
                description=description,
                capability=capability,
                required_parameters=param_analysis['mandatory'][:10],
                optional_parameters=param_analysis['optional'][:15],
                parameter_types=param_analysis['types'],
                default_parameters=param_analysis['defaults'],
                input_template=self._generate_template(capability, param_analysis['mandatory'], param_analysis['optional']),
                script_template=self._generate_script_template(),
                outputs=self._generate_outputs(capability),
                execution={'command': self._get_execution_command(), 'timeout': 3600}
            )

            self.skills[skill_name] = skill_config

    def _analyze_parameters(self, patterns: List[CodePattern]) -> Dict[str, Any]:
        """Analyze parameters to classify them properly"""
        param_counts = defaultdict(int)
        param_examples = defaultdict(list)

        # Collect parameter usage statistics
        for pattern in patterns:
            for param, value in pattern.parameters.items():
                param_counts[param] += 1
                if len(param_examples[param]) < 5:
                    param_examples[param].append(value)

        total_patterns = len(patterns)
        mandatory = []
        optional = []
        param_types = {}
        defaults = {}

        # Classify parameters based on usage frequency and domain knowledge
        for param, count in param_counts.items():
            usage_frequency = count / total_patterns

            # Determine parameter type
            if param_examples[param]:
                param_types[param] = self._infer_type(param_examples[param][0])

                # Always store most common value as potential default
                defaults[param] = param_examples[param][0]

            # Classify as mandatory or optional based on:
            # 1. Usage frequency (>80% = likely mandatory)
            # 2. Domain knowledge (certain params are always mandatory)
            # 3. Parameter name patterns

            if self._is_required_parameter(param, usage_frequency):
                mandatory.append(param)
            else:
                optional.append(param)

        return {
            'mandatory': mandatory,
            'optional': optional,
            'types': param_types,
            'defaults': defaults
        }

    def _is_required_parameter(self, param: str, usage_frequency: float) -> bool:
        """Determine if a parameter should be required based on domain knowledge"""
        param_lower = param.lower()

        # Always required parameters (domain knowledge)
        always_required = {
            'material_id', 'structure', 'atoms', 'forceconstants', 'phonons',
            'method', 'calculation', 'input_file', 'system'
        }

        # Check direct matches
        if param_lower in always_required:
            return True

        # Check partial matches for required concepts
        required_patterns = ['material', 'structure', 'method', 'calculation']
        for pattern in required_patterns:
            if pattern in param_lower and usage_frequency > 0.5:
                return True

        # High usage frequency suggests required
        if usage_frequency > 0.8:
            return True

        # Config/setup parameters with high usage are often required
        config_patterns = ['config', 'setup', 'init']
        for pattern in config_patterns:
            if pattern in param_lower and usage_frequency > 0.6:
                return True

        return False

    def _infer_type(self, value: Any) -> str:
        """Infer parameter type from value"""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            if value:
                if all(isinstance(v, int) for v in value):
                    return "list[int]"
                elif all(isinstance(v, float) for v in value):
                    return "list[float]"
            return "list"
        elif isinstance(value, dict):
            return "object"
        else:
            return "any"

    def _generate_template(self, capability: str, mandatory: List[str], optional: List[str]) -> List[str]:
        """Generate input template based on code type"""
        template = []

        if self.code_name == 'kaldo':
            template = [
                f"# {capability} calculation for {{material_id}}",
                "from kaldo.forceconstants import ForceConstants",
                "from kaldo.phonons import Phonons",
                "",
                "# Load force constants",
                "forceconstants = ForceConstants.from_folder('{forceconstants_source}')",
                "",
                "# Configure calculation",
                "config = {",
            ]
            for param in mandatory[:5]:
                template.append(f"    '{param}': {{{param}}},")
            template.append("}")

        elif self.code_name == 'lammps':
            template = [
                "# LAMMPS input for {material_id}",
                "# {capability}",
                "",
                "units metal",
                "atom_style atomic",
                "boundary p p p",
                "",
                "read_data {structure_file}",
                "",
                "pair_style {pair_style}",
                "pair_coeff * * {pair_coeff}",
                "",
                "compute {compute_command}",
                "fix {fix_command}",
                "",
                "run {steps}"
            ]

        elif self.code_name == 'quantum_espresso':
            template = [
                "&control",
                "    calculation = '{calculation_type}'",
                "    prefix = '{material_id}'",
                "/",
                "&system",
                "    ibrav = {ibrav}",
                "    nat = {nat}",
                "    ntyp = {ntyp}",
                "/",
                "&electrons",
                "    mixing_beta = 0.7",
                "/",
                "ATOMIC_SPECIES",
                "{atomic_species}",
                "ATOMIC_POSITIONS {atomic_units}",
                "{atomic_positions}",
                "K_POINTS {k_points_type}",
                "{k_points}"
            ]

        elif self.code_name == 'vasp':
            template = [
                "# VASP INCAR for {material_id}",
                "SYSTEM = {material_id}",
                "PREC = Accurate",
                "ENCUT = {encut}",
                "ISMEAR = {ismear}",
                "SIGMA = 0.05",
                "IBRION = {ibrion}",
                "NSW = {nsw}",
                "ISIF = {isif}"
            ]
        else:
            # Generic template
            template = [
                f"# {self.code_name} {capability} calculation",
                "# Material: {material_id}",
                "# Auto-generated template",
                ""
            ]
            for param in mandatory[:5]:
                template.append(f"{param} = {{{param}}}")

        return template

    def _generate_script_template(self) -> str:
        """Generate execution script template"""
        if self.code_name == 'kaldo':
            return "python {script_name}.py"
        elif self.code_name == 'lammps':
            return "lmp -in {input_file}"
        elif self.code_name == 'quantum_espresso':
            return "pw.x < {input_file} > {output_file}"
        elif self.code_name == 'vasp':
            return "vasp_std"
        else:
            return "python run.py"

    def _generate_outputs(self, capability: str) -> List[Dict[str, str]]:
        """Generate output specifications"""
        outputs = []

        if 'thermal_conductivity' in capability:
            outputs.append({
                "name": "thermal_conductivity",
                "file": "thermal_conductivity.dat",
                "type": "data"
            })

        if 'phonon' in capability:
            outputs.append({
                "name": "phonon_frequencies",
                "file": "frequencies.dat",
                "type": "data"
            })
            outputs.append({
                "name": "phonon_dos",
                "file": "dos.dat",
                "type": "data"
            })

        if 'band' in capability:
            outputs.append({
                "name": "band_structure",
                "file": "bands.dat",
                "type": "data"
            })

        if 'structure' in capability:
            outputs.append({
                "name": "optimized_structure",
                "file": "structure.out",
                "type": "structure"
            })

        # Default output
        if not outputs:
            outputs.append({
                "name": "output",
                "file": "output.log",
                "type": "log"
            })

        return outputs

    def _get_execution_command(self) -> str:
        """Get execution command based on code type"""
        commands = {
            'kaldo': 'python',
            'lammps': 'lmp',
            'quantum_espresso': 'mpirun',
            'vasp': 'mpirun',
            'ase': 'python',
            'materials_project': 'python',
            'cp2k': 'cp2k',
            'siesta': 'siesta'
        }
        return commands.get(self.code_name, 'bash')

    def generate_config(self) -> Dict[str, Any]:
        """Generate configuration file"""
        # Get code description
        description = f"{self.code_name.upper()} - "
        descriptions = {
            'kaldo': 'Anharmonic Lattice Dynamics package for thermal transport',
            'lammps': 'Large-scale Atomic/Molecular Massively Parallel Simulator',
            'quantum_espresso': 'Integrated suite for electronic-structure calculations',
            'vasp': 'Vienna Ab initio Simulation Package',
            'ase': 'Atomic Simulation Environment',
            'materials_project': 'Materials data and analysis platform',
            'cp2k': 'Quantum chemistry and solid state physics software',
            'siesta': 'Spanish Initiative for Electronic Simulations with Thousands of Atoms'
        }
        description += descriptions.get(self.code_name, 'Computational simulation package')

        config = {
            "name": self.code_name,
            "description": description,
            "skills": {}
        }

        # Add skills
        for skill_name, skill_config in self.skills.items():
            config["skills"][skill_name] = {
                "description": skill_config.description,
                "capability": skill_config.capability,
                "required_parameters": skill_config.required_parameters,
                "optional_parameters": skill_config.optional_parameters,
                "parameter_types": skill_config.parameter_types,
                "default_parameters": skill_config.default_parameters,
                "input_template": skill_config.input_template,
                "script_template": skill_config.script_template,
                "outputs": skill_config.outputs,
                "execution": skill_config.execution
            }

        # Add code-specific information
        if self.code_name in CODE_SIGNATURES:
            config["supported_capabilities"] = CODE_SIGNATURES[self.code_name].get('capabilities', [])

        return config

    def save_config(self, output_path: str):
        """Save configuration to file"""
        config = self.generate_config()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Configuration saved to {output_path}")


def scan_repository(repo_path: str, code_name: Optional[str] = None, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Scan a repository and generate configuration file.

    Args:
        repo_path: Path to repository to scan
        code_name: Optional code type (auto-detect if not specified)
        output_path: Optional output file path (use "auto" for automatic naming)

    Returns:
        Generated configuration dictionary
    """
    scanner = RepoScanner(repo_path, code_name)
    config = scanner.scan()

    if output_path:
        if output_path == "auto":
            # Auto-generate path based on detected code
            code_name = config.get('name', 'unknown')
            output_path = f"configs/{code_name}.json"
        scanner.save_config(output_path)

    return config