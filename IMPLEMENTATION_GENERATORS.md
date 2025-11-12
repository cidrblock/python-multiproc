# Implementation Guide: Code Generation Tools

## Overview

This guide covers the **code generation tools** that automate the creation of dataclasses from Ansible docstrings and OpenAPI specifications.

**Audience**: Framework developers setting up code generation infrastructure

**Related Documents**:
- `IMPLEMENTATION_FOUNDATION.md` - Core framework components
- `IMPLEMENTATION_FEATURES.md` - Using these tools to add new features

---

## Table of Contents

1. [Code Generation Strategy](#code-generation-strategy)
2. [Ansible Dataclass Generator](#ansible-dataclass-generator)
3. [API Dataclass Generator](#api-dataclass-generator)
4. [Usage Examples](#usage-examples)
5. [Verification and Review](#verification-and-review)

---

## Code Generation Strategy

### What Gets Generated

| Component | Generated From | Output Location | Frequency |
|-----------|----------------|-----------------|-----------|
| Ansible Dataclass | `DOCUMENTATION` string | `plugins/plugin_utils/ansible_models/` | Once per module |
| API Dataclass (base) | OpenAPI spec | `plugins/plugin_utils/api/v{X}/generated/` | Once per API version |
| Transform Mixin skeleton | Manual template | `plugins/plugin_utils/api/v{X}/` | Once per module+version |

### What Requires Manual Work

- **Field mapping** in transform mixins
- **Custom transformation functions** (e.g., names ↔ IDs)
- **Endpoint operations** configuration
- **Business logic validation**

### Generation Workflow

```
┌─────────────────────┐
│ 1. Write docstring  │
│   (DOCUMENTATION)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Generate Ansible │
│    dataclass        │
│    (automated)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. Generate API     │
│    models from      │
│    OpenAPI          │
│    (automated)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. Create Transform │
│    Mixin (manual)   │
│    - Field mapping  │
│    - Transforms     │
│    - Endpoints      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. Test & Refine    │
└─────────────────────┘
```

---

## Ansible Dataclass Generator

### Tool: `generate_ansible_dataclasses.py`

**Location**: `tools/generators/generate_ansible_dataclasses.py`

**Purpose**: Parse Ansible `DOCUMENTATION` strings and generate typed Python dataclasses.

### Full Implementation

```python
"""Generate Ansible dataclasses from DOCUMENTATION strings.

This script parses Ansible module documentation and generates strongly-typed
Python dataclasses that represent the user-facing data model.
"""

import yaml
import argparse
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class FieldSpec:
    """Specification for a single field."""
    name: str
    python_type: str
    required: bool
    description: str
    default: Optional[str] = None


class AnsibleDataclassGenerator:
    """
    Generator for Ansible dataclasses from DOCUMENTATION strings.
    
    Attributes:
        type_mapping: Maps Ansible types to Python types
    """
    
    # Ansible type -> Python type mapping
    TYPE_MAPPING = {
        'str': 'str',
        'int': 'int',
        'float': 'float',
        'bool': 'bool',
        'list': 'List',
        'dict': 'Dict',
        'path': 'str',
        'raw': 'Any',
        'jsonarg': 'Dict',
    }
    
    def __init__(self):
        """Initialize generator."""
        self.nested_classes: List[str] = []
    
    def parse_documentation(self, doc_string: str) -> Dict[str, Any]:
        """
        Parse DOCUMENTATION YAML string.
        
        Args:
            doc_string: DOCUMENTATION string from module
        
        Returns:
            Parsed documentation dict
        """
        return yaml.safe_load(doc_string)
    
    def generate_from_file(self, doc_file: Path, output_file: Path) -> None:
        """
        Generate dataclass from documentation file.
        
        Args:
            doc_file: Path to file containing DOCUMENTATION
            output_file: Path to output Python file
        """
        # Read documentation file
        content = doc_file.read_text()
        
        # Extract DOCUMENTATION string
        doc_match = re.search(
            r'DOCUMENTATION\s*=\s*["\']+(.*?)["\']',
            content,
            re.DOTALL
        )
        
        if not doc_match:
            raise ValueError(f"No DOCUMENTATION found in {doc_file}")
        
        doc_string = doc_match.group(1)
        
        # Parse and generate
        doc_data = self.parse_documentation(doc_string)
        module_name = doc_data.get('module', doc_file.stem)
        
        generated_code = self.generate_dataclass(module_name, doc_data)
        
        # Write output
        output_file.write_text(generated_code)
        print(f"Generated {output_file}")
    
    def generate_dataclass(
        self,
        module_name: str,
        doc_data: Dict[str, Any]
    ) -> str:
        """
        Generate dataclass code from parsed documentation.
        
        Args:
            module_name: Module name (e.g., 'user')
            doc_data: Parsed documentation dict
        
        Returns:
            Generated Python code as string
        """
        self.nested_classes = []
        
        # Extract options
        options = doc_data.get('options', {})
        
        # Build fields
        fields = self._build_fields(options)
        
        # Generate class name
        class_name = f'Ansible{module_name.title()}'
        
        # Build code
        code_parts = []
        
        # Header
        code_parts.append('"""Generated Ansible dataclass.')
        code_parts.append('')
        code_parts.append(f'Auto-generated from {module_name} module DOCUMENTATION.')
        code_parts.append('DO NOT EDIT MANUALLY - regenerate using tools/generators/')
        code_parts.append('"""')
        code_parts.append('')
        code_parts.append('from dataclasses import dataclass')
        code_parts.append('from typing import Optional, List, Dict, Any')
        code_parts.append('')
        code_parts.append('from ..platform.base_transform import BaseTransformMixin')
        code_parts.append('')
        code_parts.append('')
        
        # Nested classes first
        for nested_code in self.nested_classes:
            code_parts.append(nested_code)
            code_parts.append('')
        
        # Main class
        code_parts.append('@dataclass')
        code_parts.append(f'class {class_name}(BaseTransformMixin):')
        
        # Docstring
        description = doc_data.get('short_description', f'{module_name.title()} resource')
        code_parts.append('    """')
        code_parts.append(f'    {description}')
        code_parts.append('    ')
        code_parts.append('    This dataclass represents the Ansible user-facing data model.')
        code_parts.append('    It is the stable interface that crosses the RPC boundary.')
        code_parts.append('    ')
        code_parts.append('    Attributes:')
        
        for field in fields:
            code_parts.append(f'        {field.name}: {field.description}')
        
        code_parts.append('    """')
        code_parts.append('    ')
        
        # Fields
        for field in fields:
            field_line = f'    {field.name}: '
            
            if not field.required:
                field_line += 'Optional['
            
            field_line += field.python_type
            
            if not field.required:
                field_line += ']'
            
            if field.default or not field.required:
                if field.default:
                    field_line += f' = {field.default}'
                else:
                    field_line += ' = None'
            
            code_parts.append(field_line)
        
        return '\n'.join(code_parts)
    
    def _build_fields(
        self,
        options: Dict[str, Any],
        prefix: str = ''
    ) -> List[FieldSpec]:
        """
        Build field specifications from options.
        
        Args:
            options: Options dict from documentation
            prefix: Prefix for nested fields
        
        Returns:
            List of FieldSpec objects
        """
        fields = []
        
        for field_name, field_spec in options.items():
            # Get field attributes
            field_type = field_spec.get('type', 'str')
            required = field_spec.get('required', False)
            description = field_spec.get('description', '')
            default = field_spec.get('default')
            
            # Handle description (can be string or list)
            if isinstance(description, list):
                description = ' '.join(description)
            
            # Map type
            python_type = self._map_type(field_type, field_spec)
            
            # Handle nested objects (suboptions)
            if 'suboptions' in field_spec:
                nested_class_name = f'{prefix}{field_name.title()}'
                nested_fields = self._build_fields(
                    field_spec['suboptions'],
                    prefix=nested_class_name
                )
                
                # Generate nested class
                nested_code = self._generate_nested_class(
                    nested_class_name,
                    nested_fields
                )
                self.nested_classes.append(nested_code)
                
                # Use nested class as type
                if field_type == 'list':
                    python_type = f'List[{nested_class_name}]'
                else:
                    python_type = nested_class_name
            
            # Create field spec
            field = FieldSpec(
                name=field_name,
                python_type=python_type,
                required=required,
                description=description,
                default=self._format_default(default)
            )
            
            fields.append(field)
        
        return fields
    
    def _map_type(self, ansible_type: str, field_spec: Dict) -> str:
        """
        Map Ansible type to Python type.
        
        Args:
            ansible_type: Ansible type string
            field_spec: Full field specification
        
        Returns:
            Python type string
        """
        base_type = self.TYPE_MAPPING.get(ansible_type, 'Any')
        
        # Handle list with elements type
        if ansible_type == 'list':
            elements = field_spec.get('elements', 'str')
            element_type = self.TYPE_MAPPING.get(elements, 'Any')
            return f'List[{element_type}]'
        
        # Handle dict with specific structure
        if ansible_type == 'dict':
            return 'Dict[str, Any]'
        
        return base_type
    
    def _generate_nested_class(
        self,
        class_name: str,
        fields: List[FieldSpec]
    ) -> str:
        """
        Generate nested dataclass code.
        
        Args:
            class_name: Name of nested class
            fields: List of field specifications
        
        Returns:
            Generated class code
        """
        lines = []
        lines.append('@dataclass')
        lines.append(f'class {class_name}:')
        lines.append('    """Nested dataclass."""')
        lines.append('    ')
        
        for field in fields:
            field_line = f'    {field.name}: '
            
            if not field.required:
                field_line += 'Optional['
            
            field_line += field.python_type
            
            if not field.required:
                field_line += ']'
            
            if field.default or not field.required:
                if field.default:
                    field_line += f' = {field.default}'
                else:
                    field_line += ' = None'
            
            lines.append(field_line)
        
        return '\n'.join(lines)
    
    def _format_default(self, default: Any) -> Optional[str]:
        """
        Format default value for Python code.
        
        Args:
            default: Default value
        
        Returns:
            Formatted string or None
        """
        if default is None:
            return None
        
        if isinstance(default, bool):
            return str(default)
        
        if isinstance(default, (int, float)):
            return str(default)
        
        if isinstance(default, str):
            return f"'{default}'"
        
        return repr(default)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate Ansible dataclasses from DOCUMENTATION'
    )
    parser.add_argument(
        'doc_file',
        type=Path,
        help='Path to file containing DOCUMENTATION'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path (default: infer from module name)'
    )
    
    args = parser.parse_args()
    
    # Infer output path if not provided
    if args.output is None:
        module_name = args.doc_file.stem
        output_dir = Path('plugins/plugin_utils/ansible_models')
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = output_dir / f'{module_name}.py'
    
    # Generate
    generator = AnsibleDataclassGenerator()
    generator.generate_from_file(args.doc_file, args.output)


if __name__ == '__main__':
    main()
```

### Usage

```bash
# Generate from docs file
python tools/generators/generate_ansible_dataclasses.py \
    plugins/plugin_utils/docs/user.py \
    --output plugins/plugin_utils/ansible_models/user.py

# Output: plugins/plugin_utils/ansible_models/user.py
```

---

## API Dataclass Generator

### Tool: `datamodel-code-generator`

**Installation**:
```bash
pip install datamodel-code-generator
```

**Why this tool?**
- Industry standard for OpenAPI → Python
- Handles complex schemas (nested objects, oneOf, allOf, etc.)
- Generates pydantic or dataclass models
- Well-maintained and reliable

### Wrapper Script: `generate_api_models.sh`

**Location**: `tools/generators/generate_api_models.sh`

```bash
#!/bin/bash
# Generate API dataclasses from OpenAPI specs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$SCRIPT_DIR/../openapi_specs"
OUTPUT_BASE="$PROJECT_ROOT/plugins/plugin_utils/api"

echo "Generating API dataclasses from OpenAPI specs..."

# Generate for each version
for spec_file in "$SPECS_DIR"/gateway-v*.json; do
    if [ ! -f "$spec_file" ]; then
        echo "No OpenAPI specs found in $SPECS_DIR"
        exit 1
    fi
    
    # Extract version from filename (gateway-v1.json -> 1)
    filename=$(basename "$spec_file")
    version=$(echo "$filename" | sed -E 's/gateway-v([0-9]+(_[0-9]+)?).json/\1/')
    
    echo "Processing $filename (version $version)..."
    
    # Create output directory
    output_dir="$OUTPUT_BASE/v${version}/generated"
    mkdir -p "$output_dir"
    
    # Generate models
    datamodel-codegen \
        --input "$spec_file" \
        --input-file-type openapi \
        --output "$output_dir/models.py" \
        --output-model-type dataclasses.dataclass \
        --field-constraints \
        --use-standard-collections \
        --use-schema-description \
        --use-title-as-name \
        --target-python-version 3.9 \
        --collapse-root-models \
        --disable-timestamp
    
    # Add header comment
    temp_file=$(mktemp)
    cat > "$temp_file" << 'EOF'
"""Generated API dataclasses from OpenAPI specification.

Auto-generated using datamodel-code-generator.
DO NOT EDIT MANUALLY - regenerate using tools/generators/generate_api_models.sh

These are pure API data models. To add transformation logic, create a
companion file (e.g., user.py) with a TransformMixin that inherits from
BaseTransformMixin.
"""

EOF
    cat "$output_dir/models.py" >> "$temp_file"
    mv "$temp_file" "$output_dir/models.py"
    
    # Create __init__.py
    cat > "$output_dir/__init__.py" << 'EOF'
"""Generated API models."""
from .models import *
EOF
    
    echo "  Generated: $output_dir/models.py"
done

echo ""
echo "API dataclass generation complete!"
echo ""
echo "Next steps:"
echo "  1. Review generated files in plugins/plugin_utils/api/"
echo "  2. Create transform mixins for each resource"
echo "  3. Import generated classes in your transform mixin files"
```

### Usage

```bash
# Place OpenAPI specs in tools/openapi_specs/
# - gateway-v1.json
# - gateway-v2.json

# Generate all API models
cd ansible.platform
bash tools/generators/generate_api_models.sh

# Output structure:
# plugins/plugin_utils/api/
#   v1/
#     generated/
#       __init__.py
#       models.py  # Generated dataclasses
#   v2/
#     generated/
#       __init__.py
#       models.py
```

---

## Usage Examples

### Example 1: Generate User Module Dataclasses

**Step 1**: Create documentation file

```python
# plugins/plugin_utils/docs/user.py
DOCUMENTATION = """
---
module: user
short_description: Manage platform users
options:
  username:
    description: Username for the user
    required: true
    type: str
  email:
    description: Email address
    type: str
  first_name:
    description: First name
    type: str
  last_name:
    description: Last name
    type: str
  is_superuser:
    description: Designates superuser permissions
    type: bool
    default: false
  organizations:
    description: List of organization names
    type: list
    elements: str
  id:
    description: User ID (read-only)
    type: int
"""
```

**Step 2**: Generate Ansible dataclass

```bash
python tools/generators/generate_ansible_dataclasses.py \
    plugins/plugin_utils/docs/user.py
```

**Generated**: `plugins/plugin_utils/ansible_models/user.py`

```python
"""Generated Ansible dataclass.

Auto-generated from user module DOCUMENTATION.
DO NOT EDIT MANUALLY - regenerate using tools/generators/
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from ..platform.base_transform import BaseTransformMixin


@dataclass
class AnsibleUser(BaseTransformMixin):
    """
    Manage platform users
    
    This dataclass represents the Ansible user-facing data model.
    It is the stable interface that crosses the RPC boundary.
    
    Attributes:
        username: Username for the user
        email: Email address
        first_name: First name
        last_name: Last name
        is_superuser: Designates superuser permissions
        organizations: List of organization names
        id: User ID (read-only)
    """
    
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_superuser: Optional[bool] = False
    organizations: Optional[List[str]] = None
    id: Optional[int] = None
```

**Step 3**: Generate API dataclasses

```bash
# Ensure gateway-v1.json is in tools/openapi_specs/
bash tools/generators/generate_api_models.sh
```

**Generated**: `plugins/plugin_utils/api/v1/generated/models.py`

Contains classes like:
- `User` - From `/components/schemas/User`
- `Organization` - From `/components/schemas/Organization`
- etc.

---

### Example 2: Regeneration After Schema Changes

When the OpenAPI spec changes:

```bash
# 1. Update spec file
cp new-gateway-v1.json tools/openapi_specs/gateway-v1.json

# 2. Regenerate API models
bash tools/generators/generate_api_models.sh

# 3. Review changes
git diff plugins/plugin_utils/api/v1/generated/models.py

# 4. Update transform mixins if field names changed
# (Manual step - edit user.py, organization.py, etc.)
```

---

## Verification and Review

### Generated Code Checklist

After generation, verify:

✅ **Imports are correct**
- `from dataclasses import dataclass`
- `from typing import Optional, List, Dict, Any`
- BaseTransformMixin imported correctly

✅ **Field types match expectations**
- Required fields have no `Optional[]`
- Optional fields use `Optional[]` and `= None`
- List types have correct element types

✅ **Nested objects handled correctly**
- Nested dataclasses defined before parent
- Type references are correct

✅ **Docstrings present**
- Module-level docstring
- Class docstring
- Attribute descriptions

### Common Issues and Fixes

**Issue**: Missing imports
```python
# Add at top of generated file
from typing import List, Optional, Dict, Any
```

**Issue**: Wrong default value
```python
# Generated (wrong):
is_active: bool = True

# Fix:
is_active: Optional[bool] = True
```

**Issue**: Nested class order
```python
# Wrong order:
@dataclass
class Parent:
    child: Child  # Error: Child not defined yet

@dataclass
class Child:
    name: str

# Fix: Define Child first
@dataclass
class Child:
    name: str

@dataclass
class Parent:
    child: Child
```

---

## Integration with Features Workflow

The generated dataclasses feed into the feature implementation workflow:

```
GENERATORS (this doc)
  ↓
  Generate AnsibleUser, APIUser_v1 (auto)
  ↓
FEATURES (next doc)
  ↓
  Create UserTransformMixin_v1 (manual)
  - Use generated classes
  - Add field mapping
  - Add transforms
  ↓
  Create UserActionPlugin (manual)
  - Import AnsibleUser
  - Use base action plugin
```

See `IMPLEMENTATION_FEATURES.md` for the next steps.

---

## Summary

### Tools Created

✅ **`generate_ansible_dataclasses.py`** - Parses DOCUMENTATION, generates Ansible dataclasses  
✅ **`generate_api_models.sh`** - Wraps `datamodel-code-generator` for OpenAPI → Python  

### Workflow

1. Write `DOCUMENTATION` string
2. Run Ansible generator → `AnsibleUser`
3. Run API generator → `User` (from OpenAPI)
4. Manually create `UserTransformMixin_v1`
5. Test and iterate

### Key Benefits

- **Consistency**: Generated code follows standards
- **Speed**: Seconds instead of hours
- **Accuracy**: Directly from source of truth (docstring, OpenAPI)
- **Maintainability**: Regenerate when schemas change

---

## Related Documents

- **`IMPLEMENTATION_FOUNDATION.md`** - Core framework (uses generated classes)
- **`IMPLEMENTATION_FEATURES.md`** - Adding features (uses these tools)
- **`REQUIREMENTS.md`** - Requirements driving code generation needs
