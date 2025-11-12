# Implementation Guide: Foundation Components

## Overview

This guide is for developers building the **foundational framework** of the Ansible Platform Collection. This includes the core infrastructure that all feature modules will use:

- Base transformation system
- Platform manager (persistent service)
- RPC communication layer
- Version registry and class loaders
- Code generation tools

**Audience**: Framework/infrastructure developers

**Related Document**: See `IMPLEMENTATION_FEATURES.md` for adding new resource modules (users, organizations, etc.)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Core Components](#core-components)
4. [Manager Service](#manager-service)
5. [Manager Startup Strategy](#manager-startup-strategy)
6. [Testing the Foundation](#testing-the-foundation)

---

## Architecture Overview

### High-Level Flow

```
PLAYBOOK TASK 1
    ↓
1. Action Plugin spawns Manager (if not running)
    ↓
2. Manager detects API version, loads registry
    ↓
3. Action Plugin validates input (ArgumentSpec)
    ↓
4. Creates Ansible dataclass, sends to Manager
    ↓
5. Manager transforms (Ansible → API)
    ↓
6. Manager calls Platform API
    ↓
7. Manager transforms (API → Ansible)
    ↓
8. Action Plugin validates output, returns

PLAYBOOK TASK 2+ reuse same Manager (persistent connection)
```

### Component Responsibilities

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `BaseTransformMixin` | `plugins/plugin_utils/platform/` | Universal transformation logic |
| `PlatformManager` | `plugins/plugin_utils/manager/` | Persistent service, API calls, transformations |
| `RPC Client` | `plugins/plugin_utils/manager/` | Client-side manager communication |
| `Version Registry` | `plugins/plugin_utils/platform/` | Dynamic version/module discovery |
| `Class Loader` | `plugins/plugin_utils/platform/` | Load version-specific classes |
| `Base Action Plugin` | `plugins/action/base_action.py` | Manager spawning, validation, common logic |
| `Generators` | `tools/generators/` | Code generation scripts |

---

## Directory Structure

```
ansible.platform/
├── galaxy.yml                          # Collection metadata
├── meta/
│   └── runtime.yml                     # Python/Ansible version requirements
│
├── plugins/
│   ├── action/                         # Action plugins (client-side)
│   │   ├── __init__.py
│   │   ├── base_action.py              # ⭐ Base action plugin class (FOUNDATION)
│   │   └── user.py                     # User action plugin (example - inherits from base)
│   │
│   ├── plugin_utils/                   # Shared utilities (importable)
│   │   ├── __init__.py
│   │   │
│   │   ├── platform/                   # Core platform components
│   │   │   ├── __init__.py
│   │   │   ├── base_transform.py       # BaseTransformMixin
│   │   │   ├── types.py                # Shared types (EndpointOperation, etc.)
│   │   │   ├── registry.py             # APIVersionRegistry
│   │   │   └── loader.py               # DynamicClassLoader
│   │   │
│   │   ├── manager/                    # Manager service components
│   │   │   ├── __init__.py
│   │   │   ├── platform_manager.py     # PlatformManager (server)
│   │   │   └── rpc_client.py           # ManagerRPCClient (client)
│   │   │
│   │   ├── ansible_models/             # Ansible dataclasses (stable)
│   │   │   ├── __init__.py
│   │   │   └── user.py                 # AnsibleUser (from docstring)
│   │   │
│   │   ├── api/                        # API dataclasses (versioned)
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── generated/          # Auto-generated from OpenAPI
│   │   │   │   │   └── models.py
│   │   │   │   └── user.py             # UserTransformMixin_v1, APIUser_v1
│   │   │   │
│   │   │   └── v2/                     # Future version
│   │   │       ├── __init__.py
│   │   │       └── ...
│   │   │
│   │   └── docs/                       # Module documentation
│   │       ├── __init__.py
│   │       └── user.py                 # DOCUMENTATION string
│   │
│   └── module_utils/                   # (Standard Ansible, can remain empty)
│       └── __init__.py
│
├── tools/                              # Development tools (not shipped)
│   ├── generators/
│   │   ├── generate_ansible_dataclasses.py
│   │   └── generate_api_models.sh
│   │
│   └── openapi_specs/
│       ├── gateway-v1.json             # OpenAPI specs
│       └── gateway-v2.json
│
└── requirements.txt                    # Python dependencies
```

### Key Organizational Principles

1. **`plugins/plugin_utils/`** - All common code (framework)
2. **`plugins/action/`** - Action plugins only
3. **`tools/`** - Development only, not shipped with collection
4. **Version hierarchy in `api/`** - v1/, v2/, etc.
5. **Stable models in `ansible_models/`** - No versions

---

## Core Components

### 1. Base Transform Mixin

**File**: `plugins/plugin_utils/platform/base_transform.py`

**Purpose**: Universal transformation logic inherited by all dataclasses.

```python
"""Base transformation mixin for bidirectional data transformation.

This module provides the core transformation logic used by all Ansible
and API dataclasses.
"""

from abc import ABC
from dataclasses import asdict
from typing import TypeVar, Type, Optional, Dict, Any

T = TypeVar('T')


class BaseTransformMixin(ABC):
    """
    Base transformation mixin providing bidirectional data transformation.
    
    All Ansible dataclasses and API dataclasses inherit from this mixin.
    It provides generic transformation logic that works with the specific
    field mappings and transform functions defined in subclasses.
    
    Attributes:
        _field_mapping: Dict defining field mappings (set by subclasses)
        _transform_registry: Dict of transformation functions (set by subclasses)
    """
    
    # Subclasses must define these class variables
    _field_mapping: Optional[Dict] = None
    _transform_registry: Optional[Dict] = None
    
    def to_api(self, context: Optional[Dict] = None) -> Any:
        """
        Transform from Ansible format to API format.
        
        Args:
            context: Optional context dict containing:
                - manager: PlatformManager instance for lookups
                - session: HTTP session
                - cache: Lookup cache
                - api_version: Current API version
        
        Returns:
            API dataclass instance
        """
        return self._transform(
            target_class=self._get_api_class(),
            direction='forward',
            context=context or {}
        )
    
    def to_ansible(self, context: Optional[Dict] = None) -> Any:
        """
        Transform from API format to Ansible format.
        
        Args:
            context: Optional context dict (same as to_api)
        
        Returns:
            Ansible dataclass instance
        """
        return self._transform(
            target_class=self._get_ansible_class(),
            direction='reverse',
            context=context or {}
        )
    
    def _transform(
        self,
        target_class: Type[T],
        direction: str,
        context: Dict
    ) -> T:
        """
        Generic bidirectional transformation logic.
        
        Args:
            target_class: Target dataclass type to instantiate
            direction: 'forward' (Ansible→API) or 'reverse' (API→Ansible)
            context: Context dict for transformation functions
        
        Returns:
            Instance of target_class with transformed data
        """
        # Convert self to dict
        source_data = asdict(self)
        transformed_data = {}
        
        # Get field mapping from subclass
        mapping = self._field_mapping or {}
        
        # Apply mapping based on direction
        if direction == 'forward':
            transformed_data = self._apply_forward_mapping(
                source_data, mapping, context
            )
        elif direction == 'reverse':
            transformed_data = self._apply_reverse_mapping(
                source_data, mapping, context
            )
        else:
            raise ValueError(f"Invalid direction: {direction}")
        
        # Allow subclass post-processing hook
        transformed_data = self._post_transform_hook(
            transformed_data, direction, context
        )
        
        # Create and return target class instance
        return target_class(**transformed_data)
    
    def _apply_forward_mapping(
        self,
        source_data: dict,
        mapping: dict,
        context: dict
    ) -> dict:
        """
        Apply forward mapping (Ansible → API).
        
        Args:
            source_data: Source data as dict
            mapping: Field mapping configuration
            context: Transform context
        
        Returns:
            Transformed data dict
        """
        result = {}
        
        for ansible_field, spec in mapping.items():
            # Get value from source
            value = self._get_nested(source_data, ansible_field)
            
            if value is None:
                continue
            
            # Apply forward transformation if specified
            if isinstance(spec, dict) and 'forward_transform' in spec:
                transform_name = spec['forward_transform']
                value = self._apply_transform(value, transform_name, context)
            
            # Get target field name
            if isinstance(spec, str):
                target_field = spec
            elif isinstance(spec, dict):
                target_field = spec.get('api_field', ansible_field)
            else:
                target_field = ansible_field
            
            # Set in result
            self._set_nested(result, target_field, value)
        
        return result
    
    def _apply_reverse_mapping(
        self,
        source_data: dict,
        mapping: dict,
        context: dict
    ) -> dict:
        """
        Apply reverse mapping (API → Ansible).
        
        Args:
            source_data: Source data as dict
            mapping: Field mapping configuration
            context: Transform context
        
        Returns:
            Transformed data dict
        """
        result = {}
        
        for ansible_field, spec in mapping.items():
            # Determine source field name
            if isinstance(spec, str):
                source_field = spec
            elif isinstance(spec, dict):
                source_field = spec.get('api_field', ansible_field)
            else:
                source_field = ansible_field
            
            # Get value from source
            value = self._get_nested(source_data, source_field)
            
            if value is None:
                continue
            
            # Apply reverse transformation if specified
            if isinstance(spec, dict) and 'reverse_transform' in spec:
                transform_name = spec['reverse_transform']
                value = self._apply_transform(value, transform_name, context)
            
            # Set in result
            self._set_nested(result, ansible_field, value)
        
        return result
    
    def _apply_transform(
        self,
        value: Any,
        transform_name: str,
        context: Dict
    ) -> Any:
        """
        Apply a named transformation function.
        
        Args:
            value: Value to transform
            transform_name: Name of transform function in registry
            context: Transform context
        
        Returns:
            Transformed value
        """
        if self._transform_registry and transform_name in self._transform_registry:
            transform_func = self._transform_registry[transform_name]
            return transform_func(value, context)
        return value
    
    def _get_nested(self, data: dict, path: str) -> Any:
        """
        Get value from nested dict using dot-delimited path.
        
        Args:
            data: Source dict
            path: Dot-delimited path (e.g., 'user.address.city')
        
        Returns:
            Value at path, or None if not found
        """
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None
        
        return current
    
    def _set_nested(self, data: dict, path: str, value: Any) -> None:
        """
        Set value in nested dict using dot-delimited path.
        
        Args:
            data: Target dict
            path: Dot-delimited path
            value: Value to set
        """
        keys = path.split('.')
        current = data
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set final value
        current[keys[-1]] = value
    
    def _post_transform_hook(
        self,
        data: dict,
        direction: str,
        context: dict
    ) -> dict:
        """
        Hook for module-specific post-processing after transformation.
        
        Subclasses can override this to add custom logic.
        
        Args:
            data: Transformed data
            direction: Transform direction
            context: Transform context
        
        Returns:
            Possibly modified data
        """
        return data
    
    @classmethod
    def _get_api_class(cls) -> Type:
        """
        Get the API dataclass type for this resource.
        
        Must be overridden by module-specific mixins.
        
        Returns:
            API dataclass type
        
        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement _get_api_class()"
        )
    
    @classmethod
    def _get_ansible_class(cls) -> Type:
        """
        Get the Ansible dataclass type for this resource.
        
        Must be overridden by module-specific mixins.
        
        Returns:
            Ansible dataclass type
        
        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement _get_ansible_class()"
        )
    
    def validate(self) -> bool:
        """
        Hook for module-specific validation.
        
        Subclasses can override to add custom validation logic.
        
        Returns:
            True if valid, False otherwise
        """
        return True
```

**Key Features**:
- Generic transformation logic (no resource-specific code)
- Supports dot-notation for nested fields
- Pluggable transformation functions via registry
- Bidirectional (forward and reverse) transforms
- Post-transform hooks for custom logic

---

### 2. Shared Types

**File**: `plugins/plugin_utils/platform/types.py`

**Purpose**: Type definitions used across the framework.

```python
"""Shared type definitions for the platform collection.

This module contains dataclasses and type definitions used throughout
the framework.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EndpointOperation:
    """
    Configuration for a single API endpoint operation.
    
    Defines how to call a specific API endpoint, what data to send,
    and how it relates to other operations.
    
    Attributes:
        path: API endpoint path (e.g., '/api/gateway/v1/users/')
        method: HTTP method ('GET', 'POST', 'PATCH', 'DELETE')
        fields: List of dataclass field names to include in request
        path_params: Optional list of path parameter names (e.g., ['id'])
        required_for: Optional operation type this is required for
            ('create', 'update', 'delete', or None for always)
        depends_on: Optional name of operation this depends on
        order: Execution order (lower runs first)
    
    Examples:
        >>> # Main create operation
        >>> EndpointOperation(
        ...     path='/api/gateway/v1/users/',
        ...     method='POST',
        ...     fields=['username', 'email'],
        ...     order=1
        ... )
        
        >>> # Dependent operation (runs after create)
        >>> EndpointOperation(
        ...     path='/api/gateway/v1/users/{id}/organizations/',
        ...     method='POST',
        ...     fields=['organizations'],
        ...     path_params=['id'],
        ...     depends_on='create',
        ...     order=2
        ... )
    """
    
    path: str
    method: str
    fields: List[str]
    path_params: Optional[List[str]] = None
    required_for: Optional[str] = None
    depends_on: Optional[str] = None
    order: int = 0
```

**Usage**: Imported by transform mixins to define API endpoint operations.

---

### 3. API Version Registry

**File**: `plugins/plugin_utils/platform/registry.py`

**Purpose**: Discover available API versions and modules by scanning filesystem.

```python
"""API version registry for dynamic version discovery.

This module provides filesystem-based discovery of available API versions
and module implementations without hardcoded version lists.
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging
from packaging import version

logger = logging.getLogger(__name__)


class APIVersionRegistry:
    """
    Registry that discovers and manages API version information.
    
    Scans the api/ directory to find available versions and tracks
    which modules are implemented for each version.
    
    Attributes:
        api_base_path: Path to api/ directory containing versioned modules
        ansible_models_path: Path to ansible_models/ with stable interfaces
        versions: Dict mapping version string to available modules
        module_versions: Dict mapping module name to available versions
    """
    
    def __init__(
        self,
        api_base_path: Optional[str] = None,
        ansible_models_path: Optional[str] = None
    ):
        """
        Initialize registry and discover versions.
        
        Args:
            api_base_path: Path to api/ directory (auto-detected if None)
            ansible_models_path: Path to ansible_models/ (auto-detected if None)
        """
        # Auto-detect paths if not provided
        if api_base_path is None:
            # Assume we're in plugin_utils/platform/
            current_file = Path(__file__)
            plugin_utils = current_file.parent.parent
            api_base_path = str(plugin_utils / 'api')
        
        if ansible_models_path is None:
            current_file = Path(__file__)
            plugin_utils = current_file.parent.parent
            ansible_models_path = str(plugin_utils / 'ansible_models')
        
        self.api_base_path = Path(api_base_path)
        self.ansible_models_path = Path(ansible_models_path)
        
        # Storage for discovered information
        self.versions: Dict[str, List[str]] = {}  # version -> [modules]
        self.module_versions: Dict[str, List[str]] = {}  # module -> [versions]
        
        # Discover on init
        self._discover_versions()
    
    def _discover_versions(self) -> None:
        """Scan filesystem to discover API versions and modules."""
        if not self.api_base_path.exists():
            logger.warning(f"API base path not found: {self.api_base_path}")
            return
        
        # Scan api/ directory for version directories (v1/, v2/, etc.)
        for version_dir in self.api_base_path.iterdir():
            if not version_dir.is_dir():
                continue
            
            # Must start with 'v' and contain digits
            if not version_dir.name.startswith('v'):
                continue
            
            # Extract version string: v1 -> 1, v2_1 -> 2.1
            version_str = version_dir.name[1:].replace('_', '.')
            
            # Find module implementations in this version
            module_files = [
                f for f in version_dir.glob('*.py')
                if not f.name.startswith('_') and f.name != 'generated'
            ]
            
            module_names = [f.stem for f in module_files]
            
            # Store version info
            self.versions[version_str] = module_names
            
            # Update module -> versions mapping
            for module_name in module_names:
                if module_name not in self.module_versions:
                    self.module_versions[module_name] = []
                self.module_versions[module_name].append(version_str)
        
        # Sort version lists
        for module_name in self.module_versions:
            self.module_versions[module_name].sort(key=version.parse)
        
        logger.info(
            f"Discovered {len(self.versions)} API versions: "
            f"{sorted(self.versions.keys(), key=version.parse)}"
        )
    
    def get_supported_versions(self) -> List[str]:
        """
        Get all discovered API versions, sorted.
        
        Returns:
            List of version strings (e.g., ['1', '2', '2.1'])
        """
        return sorted(self.versions.keys(), key=version.parse)
    
    def get_latest_version(self) -> Optional[str]:
        """
        Get the latest available API version.
        
        Returns:
            Latest version string, or None if no versions found
        """
        versions = self.get_supported_versions()
        return versions[-1] if versions else None
    
    def get_modules_for_version(self, api_version: str) -> List[str]:
        """
        Get list of modules available for a specific API version.
        
        Args:
            api_version: Version string (e.g., '1', '2.1')
        
        Returns:
            List of module names
        """
        return self.versions.get(api_version, [])
    
    def get_versions_for_module(self, module_name: str) -> List[str]:
        """
        Get list of API versions that implement a module.
        
        Args:
            module_name: Module name (e.g., 'user', 'organization')
        
        Returns:
            List of version strings
        """
        return self.module_versions.get(module_name, [])
    
    def find_best_version(
        self,
        requested_version: str,
        module_name: str
    ) -> Optional[str]:
        """
        Find the best available version for a module.
        
        Strategy:
        1. Try exact match
        2. Try closest lower version (backward compatible)
        3. Try closest higher version (forward compatible, with warning)
        
        Args:
            requested_version: Desired API version
            module_name: Module name
        
        Returns:
            Best matching version string, or None if not found
        """
        available = self.get_versions_for_module(module_name)
        
        if not available:
            logger.error(
                f"Module '{module_name}' not found in any API version"
            )
            return None
        
        requested = version.parse(requested_version)
        available_parsed = [(v, version.parse(v)) for v in available]
        
        # Exact match
        if requested_version in available:
            logger.debug(
                f"Found exact version match for {module_name}: {requested_version}"
            )
            return requested_version
        
        # Find closest lower version (prefer backward compatibility)
        lower_versions = [
            (v, vp) for v, vp in available_parsed if vp <= requested
        ]
        
        if lower_versions:
            best = max(lower_versions, key=lambda x: x[1])[0]
            logger.warning(
                f"Using version {best} for {module_name} "
                f"(requested {requested_version}, closest lower version)"
            )
            return best
        
        # Fallback: closest higher version
        higher_versions = [
            (v, vp) for v, vp in available_parsed if vp > requested
        ]
        
        if higher_versions:
            best = min(higher_versions, key=lambda x: x[1])[0]
            logger.warning(
                f"Using version {best} for {module_name} "
                f"(requested {requested_version}, closest higher version - "
                f"may have compatibility issues)"
            )
            return best
        
        return None
    
    def module_supports_version(
        self,
        module_name: str,
        api_version: str
    ) -> bool:
        """
        Check if a module has an implementation for an API version.
        
        Args:
            module_name: Module name
            api_version: Version string
        
        Returns:
            True if module exists for version
        """
        return api_version in self.get_versions_for_module(module_name)
```

**Key Features**:
- No hardcoded version lists
- Filesystem-based discovery
- Version fallback logic
- Tracks module × version matrix

---

### 4. Dynamic Class Loader

**File**: `plugins/plugin_utils/platform/loader.py`

**Purpose**: Load version-appropriate classes at runtime.

```python
"""Dynamic class loader for version-specific implementations.

This module loads Ansible and API dataclasses based on the detected
API version without hardcoded imports.
"""

import importlib
import inspect
from typing import Type, Tuple, Optional, Dict
from pathlib import Path
import logging

from .base_transform import BaseTransformMixin
from .registry import APIVersionRegistry

logger = logging.getLogger(__name__)


class DynamicClassLoader:
    """
    Dynamically load version-specific classes at runtime.
    
    Loads the appropriate Ansible dataclass and API dataclass/mixin
    based on the module name and API version.
    
    Attributes:
        registry: APIVersionRegistry for version discovery
        class_cache: Cache of loaded classes to avoid repeated imports
    """
    
    def __init__(self, registry: APIVersionRegistry):
        """
        Initialize loader with a version registry.
        
        Args:
            registry: Version registry for discovering available versions
        """
        self.registry = registry
        self._class_cache: Dict[str, Tuple[Type, Type, Type]] = {}
    
    def load_classes_for_module(
        self,
        module_name: str,
        api_version: str
    ) -> Tuple[Type, Type, Type]:
        """
        Load classes for a module and API version.
        
        Args:
            module_name: Module name (e.g., 'user', 'organization')
            api_version: API version (e.g., '1', '2.1')
        
        Returns:
            Tuple of (AnsibleClass, APIClass, MixinClass)
        
        Raises:
            ValueError: If classes cannot be loaded
        """
        # Find best matching version
        best_version = self.registry.find_best_version(api_version, module_name)
        
        if not best_version:
            raise ValueError(
                f"No compatible API version found for module '{module_name}' "
                f"with requested version '{api_version}'"
            )
        
        # Check cache
        cache_key = f"{module_name}_{best_version.replace('.', '_')}"
        if cache_key in self._class_cache:
            logger.debug(f"Using cached classes for {cache_key}")
            return self._class_cache[cache_key]
        
        # Load classes
        logger.info(
            f"Loading classes for {module_name} (API version {best_version})"
        )
        
        ansible_class = self._load_ansible_class(module_name)
        api_class, mixin_class = self._load_api_classes(module_name, best_version)
        
        # Cache and return
        result = (ansible_class, api_class, mixin_class)
        self._class_cache[cache_key] = result
        
        return result
    
    def _load_ansible_class(self, module_name: str) -> Type:
        """
        Load stable Ansible dataclass.
        
        Args:
            module_name: Module name
        
        Returns:
            Ansible dataclass type
        
        Raises:
            ImportError: If module cannot be imported
            ValueError: If class cannot be found
        """
        # Import from ansible_models/<module_name>.py
        module_path = f'ansible.platform.plugins.plugin_utils.ansible_models.{module_name}'
        
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(
                f"Failed to import Ansible module {module_path}: {e}"
            ) from e
        
        # Find Ansible dataclass (e.g., AnsibleUser)
        class_name = f'Ansible{module_name.title()}'
        
        if hasattr(module, class_name):
            return getattr(module, class_name)
        
        # Fallback: find any class starting with 'Ansible'
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.startswith('Ansible'):
                logger.warning(
                    f"Using {name} instead of expected {class_name}"
                )
                return obj
        
        raise ValueError(
            f"No Ansible dataclass found in {module_path} "
            f"(expected {class_name})"
        )
    
    def _load_api_classes(
        self,
        module_name: str,
        api_version: str
    ) -> Tuple[Type, Type]:
        """
        Load API dataclass and transform mixin for a version.
        
        Args:
            module_name: Module name
            api_version: API version
        
        Returns:
            Tuple of (APIClass, MixinClass)
        
        Raises:
            ImportError: If module cannot be imported
            ValueError: If classes cannot be found
        """
        # Import from api/v<version>/<module_name>.py
        version_normalized = api_version.replace('.', '_')
        module_path = (
            f'ansible.platform.plugins.plugin_utils.api.'
            f'v{version_normalized}.{module_name}'
        )
        
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(
                f"Failed to import API module {module_path}: {e}"
            ) from e
        
        # Find API dataclass (e.g., APIUser_v1)
        api_class_name = f'API{module_name.title()}_v{version_normalized}'
        api_class = self._find_class_in_module(
            module,
            [api_class_name, f'API{module_name.title()}', 'API*'],
            f"API dataclass for {module_name}"
        )
        
        # Find transform mixin (e.g., UserTransformMixin_v1)
        mixin_class_name = f'{module_name.title()}TransformMixin_v{version_normalized}'
        mixin_class = self._find_class_in_module(
            module,
            [mixin_class_name, f'{module_name.title()}TransformMixin', '*TransformMixin'],
            f"Transform mixin for {module_name}",
            base_class=BaseTransformMixin
        )
        
        return api_class, mixin_class
    
    def _find_class_in_module(
        self,
        module,
        patterns: list,
        description: str,
        base_class: Optional[Type] = None
    ) -> Type:
        """
        Find a class in a module matching patterns.
        
        Args:
            module: Imported module
            patterns: List of patterns to try (wildcards supported)
            description: Description for error messages
            base_class: Optional base class to filter by
        
        Returns:
            Matched class type
        
        Raises:
            ValueError: If no matching class found
        """
        # Get all classes from module
        classes = inspect.getmembers(module, inspect.isclass)
        
        # Filter by base class if specified
        if base_class:
            classes = [
                (name, cls) for name, cls in classes
                if issubclass(cls, base_class) and cls != base_class
            ]
        
        # Try each pattern
        for pattern in patterns:
            if '*' in pattern:
                # Wildcard pattern
                prefix = pattern.replace('*', '')
                for name, cls in classes:
                    if name.startswith(prefix):
                        logger.debug(
                            f"Found {description}: {name} (pattern: {pattern})"
                        )
                        return cls
            else:
                # Exact match
                for name, cls in classes:
                    if name == pattern:
                        logger.debug(f"Found {description}: {name}")
                        return cls
        
        # Not found
        raise ValueError(
            f"No {description} found in {module.__name__}. "
            f"Tried patterns: {patterns}"
        )
```

**Key Features**:
- Dynamic imports (no hardcoded class names)
- Pattern matching for class discovery
- Caching for performance
- Fallback logic

---

## Manager Service

The Platform Manager is the persistent service that maintains the connection to the platform API and handles all transformations.

### 5. Platform Manager (Server)

**File**: `plugins/plugin_utils/manager/platform_manager.py`

**Purpose**: Persistent service that handles API communication and transformations.

**Note**: This is a large file. See the weather service `server.py` in the workspace root as reference for multiprocess manager patterns.

**Key Components**:

```python
"""Platform Manager - Persistent service for API communication.

This module provides the server-side manager that maintains persistent
connections to the platform API and handles all data transformations.
"""

from multiprocessing.managers import BaseManager
from socketserver import ThreadingMixIn
import requests
import logging
import threading
from typing import Any, Dict, Optional
from dataclasses import asdict, is_dataclass

from ..platform.registry import APIVersionRegistry
from ..platform.loader import DynamicClassLoader

logger = logging.getLogger(__name__)


class PlatformService:
    """
    Generic platform service - resource agnostic.
    
    This service is analogous to WeatherService in the workspace example.
    It maintains a persistent connection and handles all resource operations
    generically.
    
    Attributes:
        base_url: Platform base URL
        session: Persistent HTTP session
        api_version: Detected/cached API version
        registry: Version registry
        loader: Class loader
        cache: Lookup cache (org names ↔ IDs, etc.)
    """
    
    def __init__(self, base_url: str):
        """
        Initialize platform service.
        
        Args:
            base_url: Platform base URL (e.g., https://platform.example.com)
        """
        self.base_url = base_url
        
        # Initialize persistent session (thread-safe)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ansible Platform Collection',
            'Accept': 'application/json'
        })
        
        # Detect API version (cached for lifetime)
        self.api_version = self._detect_version()
        logger.info(f"PlatformService initialized with API v{self.api_version}")
        
        # Initialize registry and loader
        self.registry = APIVersionRegistry()
        self.loader = DynamicClassLoader(self.registry)
        
        # Cache for lookups
        self.cache: Dict[str, Any] = {}
    
    def _detect_version(self) -> str:
        """
        Detect platform API version.
        
        Returns:
            Version string (e.g., '1', '2.1')
        """
        try:
            # Try to get version from API
            response = self.session.get(f'{self.base_url}/api/v2/ping/')
            response.raise_for_status()
            version_str = response.json().get('version', '1')
            
            # Normalize version string
            if version_str.startswith('v'):
                version_str = version_str[1:]
            
            logger.info(f"Detected platform API version: {version_str}")
            return version_str
            
        except Exception as e:
            logger.warning(f"Failed to detect API version: {e}, using default '1'")
            return '1'
    
    def execute(
        self,
        operation: str,
        module_name: str,
        ansible_data_dict: dict
    ) -> dict:
        """
        Execute a generic operation on any resource.
        
        This is the main entry point called by action plugins via RPC.
        
        Args:
            operation: Operation type ('create', 'update', 'delete', 'find')
            module_name: Module name (e.g., 'user', 'organization')
            ansible_data_dict: Ansible dataclass as dict
        
        Returns:
            Result as dict (Ansible format)
        
        Raises:
            ValueError: If operation is unknown or execution fails
        """
        thread_id = threading.get_ident()
        logger.info(
            f"Executing {operation} on {module_name} [Thread: {thread_id}]"
        )
        
        # Load version-appropriate classes
        AnsibleClass, APIClass, MixinClass = self.loader.load_classes_for_module(
            module_name,
            self.api_version
        )
        
        # Reconstruct Ansible dataclass
        ansible_instance = AnsibleClass(**ansible_data_dict)
        
        # Build transformation context
        context = {
            'manager': self,
            'session': self.session,
            'cache': self.cache,
            'api_version': self.api_version
        }
        
        # Execute operation
        try:
            if operation == 'create':
                result = self._create_resource(
                    ansible_instance, MixinClass, context
                )
            elif operation == 'update':
                result = self._update_resource(
                    ansible_instance, MixinClass, context
                )
            elif operation == 'delete':
                result = self._delete_resource(
                    ansible_instance, MixinClass, context
                )
            elif operation == 'find':
                result = self._find_resource(
                    ansible_instance, MixinClass, context
                )
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            logger.info(
                f"Operation {operation} on {module_name} completed "
                f"[Thread: {thread_id}]"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Operation {operation} on {module_name} failed: {e}",
                exc_info=True
            )
            raise
    
    def _create_resource(
        self,
        ansible_data: Any,
        mixin_class: type,
        context: dict
    ) -> dict:
        """
        Create resource with transformation.
        
        Args:
            ansible_data: Ansible dataclass instance
            mixin_class: Transform mixin class
            context: Transformation context
        
        Returns:
            Created resource as dict (Ansible format)
        """
        # FORWARD TRANSFORM: Ansible → API
        api_data = ansible_data.to_api(context)
        
        # Get endpoint operations from mixin
        operations = mixin_class.get_endpoint_operations()
        
        # Execute operations (potentially multi-endpoint)
        api_result = self._execute_operations(
            operations, api_data, context, required_for='create'
        )
        
        # REVERSE TRANSFORM: API → Ansible
        if api_result:
            api_result_instance = type(api_data)(**api_result)
            ansible_result = api_result_instance.to_ansible(context)
            return asdict(ansible_result)
        
        return {}
    
    def _execute_operations(
        self,
        operations: Dict,
        api_data: Any,
        context: dict,
        required_for: str = None
    ) -> dict:
        """
        Execute potentially multiple API endpoint operations.
        
        Args:
            operations: Dict of EndpointOperations
            api_data: API dataclass instance
            context: Context
            required_for: Filter operations by required_for field
        
        Returns:
            Combined API response dict
        """
        # Filter operations
        relevant_ops = {
            name: op for name, op in operations.items()
            if op.required_for is None or op.required_for == required_for
        }
        
        # Sort by dependencies and order
        sorted_ops = self._sort_operations(relevant_ops)
        
        # Execute in order
        results = {}
        api_data_dict = asdict(api_data)
        
        for op_name in sorted_ops:
            endpoint_op = relevant_ops[op_name]
            
            # Extract fields for this endpoint
            request_data = {}
            for field in endpoint_op.fields:
                if field in api_data_dict and api_data_dict[field] is not None:
                    request_data[field] = api_data_dict[field]
            
            if not request_data:
                logger.debug(f"Skipping {op_name} - no data")
                continue
            
            # Build URL with path parameters
            path = endpoint_op.path
            if endpoint_op.path_params:
                for param in endpoint_op.path_params:
                    if param in results:
                        path = path.replace(f'{{{param}}}', str(results[param]))
            
            url = f"{self.base_url}{path}"
            
            # Make API call
            logger.debug(f"Calling {endpoint_op.method} {url}")
            response = self.session.request(
                endpoint_op.method,
                url,
                json=request_data
            )
            response.raise_for_status()
            
            # Store result
            result_data = response.json()
            results[op_name] = result_data
            
            # Store ID for dependent operations
            if 'id' in result_data and 'id' not in results:
                results['id'] = result_data['id']
        
        # Return main result
        return results.get('create') or results.get('main') or {}
    
    def _sort_operations(self, operations: Dict) -> list:
        """
        Sort operations by dependencies and order.
        
        Args:
            operations: Dict of EndpointOperations
        
        Returns:
            List of operation names in execution order
        """
        sorted_ops = []
        remaining = dict(operations)
        
        # Topological sort based on depends_on
        while remaining:
            # Find operations with no unmet dependencies
            ready = [
                name for name, op in remaining.items()
                if op.depends_on is None or op.depends_on in sorted_ops
            ]
            
            if not ready:
                raise ValueError(
                    f"Circular dependency in operations: "
                    f"{list(remaining.keys())}"
                )
            
            # Sort ready operations by order field
            ready.sort(key=lambda name: remaining[name].order)
            
            # Add first ready operation
            sorted_ops.append(ready[0])
            remaining.pop(ready[0])
        
        return sorted_ops
    
    # Helper methods for transformations (called via context)
    
    def lookup_org_ids(self, org_names: list) -> list:
        """
        Convert organization names to IDs.
        
        Args:
            org_names: List of organization names
        
        Returns:
            List of organization IDs
        """
        ids = []
        for name in org_names:
            # Check cache
            cache_key = f'org_name:{name}'
            if cache_key in self.cache:
                ids.append(self.cache[cache_key])
                continue
            
            # API lookup
            response = self.session.get(
                f'{self.base_url}/api/gateway/v{self.api_version}/organizations/',
                params={'name': name}
            )
            response.raise_for_status()
            results = response.json().get('results', [])
            
            if results:
                org_id = results[0]['id']
                self.cache[cache_key] = org_id
                ids.append(org_id)
            else:
                raise ValueError(f"Organization '{name}' not found")
        
        return ids
    
    def lookup_org_names(self, org_ids: list) -> list:
        """
        Convert organization IDs to names.
        
        Args:
            org_ids: List of organization IDs
        
        Returns:
            List of organization names
        """
        names = []
        for org_id in org_ids:
            # Check reverse cache
            cache_key = f'org_id:{org_id}'
            if cache_key in self.cache:
                names.append(self.cache[cache_key])
                continue
            
            # API lookup
            response = self.session.get(
                f'{self.base_url}/api/gateway/v{self.api_version}'
                f'/organizations/{org_id}/'
            )
            response.raise_for_status()
            org = response.json()
            
            name = org['name']
            self.cache[cache_key] = name
            self.cache[f'org_name:{name}'] = org_id  # Store both directions
            names.append(name)
        
        return names


class PlatformManager(ThreadingMixIn, BaseManager):
    """
    Custom Manager for sharing PlatformService across processes.
    
    Uses ThreadingMixIn to handle concurrent client connections.
    Analogous to WeatherManager in the workspace.
    
    Attributes:
        daemon_threads: Threads exit when main process exits
    """
    daemon_threads = True
```

**Key Responsibilities**:
- Maintain persistent connection (session)
- Detect and cache API version
- Load version-specific classes
- Perform all transformations (forward and reverse)
- Execute multi-endpoint operations
- Provide lookup helpers

---

### 6. RPC Client

**File**: `plugins/plugin_utils/manager/rpc_client.py`

**Purpose**: Client-side connection to manager service.

```python
"""RPC Client for communicating with Platform Manager.

Provides the client-side interface for action plugins to communicate
with the persistent Platform Manager service.
"""

from multiprocessing.managers import BaseManager
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ManagerRPCClient:
    """
    Client for communicating with Platform Manager.
    
    Handles connection to the manager service and provides a simple
    interface for action plugins to execute operations.
    
    Attributes:
        base_url: Platform base URL
        socket_path: Path to Unix socket
        authkey: Authentication key
        manager: Manager instance
        service_proxy: Proxy to PlatformService
    """
    
    def __init__(self, base_url: str, socket_path: str, authkey: bytes):
        """
        Initialize RPC client.
        
        Args:
            base_url: Platform base URL
            socket_path: Path to Unix socket
            authkey: Authentication key
        """
        self.base_url = base_url
        self.socket_path = socket_path
        self.authkey = authkey
        
        # Import manager class
        from .platform_manager import PlatformManager
        
        # Register remote service
        PlatformManager.register('get_platform_service')
        
        # Connect to manager
        logger.debug(f"Connecting to manager at {socket_path}")
        self.manager = PlatformManager(
            address=socket_path,
            authkey=authkey
        )
        self.manager.connect()
        
        # Get service proxy
        self.service_proxy = self.manager.get_platform_service()
        logger.info("Connected to Platform Manager")
    
    def execute(
        self,
        operation: str,
        module_name: str,
        ansible_data: Any
    ) -> Any:
        """
        Execute operation via manager.
        
        Args:
            operation: Operation type
            module_name: Module name
            ansible_data: Ansible dataclass instance
        
        Returns:
            Result dataclass instance
        """
        from dataclasses import asdict, is_dataclass
        
        # Convert to dict for RPC
        if is_dataclass(ansible_data):
            data_dict = asdict(ansible_data)
        else:
            data_dict = ansible_data
        
        # Execute via proxy
        result_dict = self.service_proxy.execute(
            operation,
            module_name,
            data_dict
        )
        
        return result_dict
```

---

### 7. Base Action Plugin

**File**: `plugins/action/base_action.py`

**Purpose**: Common functionality for all resource action plugins.

This is the base class that all resource-specific action plugins inherit from. It provides:
- Manager spawning/connection logic
- Input/output validation
- ArgumentSpec generation from DOCUMENTATION

```python
"""Base action plugin for platform resources.

Provides common functionality inherited by all resource action plugins.
"""

from ansible.plugins.action import ActionBase
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator
from ansible.errors import AnsibleError
from pathlib import Path
import yaml
import logging
import tempfile
import secrets
import base64
from multiprocessing import Process
import time

logger = logging.getLogger(__name__)


class BaseResourceActionPlugin(ActionBase):
    """
    Base action plugin for all platform resources.
    
    Provides common functionality:
    - Manager spawning/connection (_get_or_spawn_manager)
    - Input/output validation (_validate_data)
    - ArgumentSpec generation (_build_argspec_from_docs)
    
    Subclasses must define:
    - MODULE_NAME: Name of the resource (e.g., 'user', 'organization')
    - DOCUMENTATION: Module documentation string
    - ANSIBLE_DATACLASS: The Ansible dataclass type
    
    Example subclass:
        class ActionModule(BaseResourceActionPlugin):
            MODULE_NAME = 'user'
            
            def run(self, tmp=None, task_vars=None):
                # Use inherited methods
                manager = self._get_or_spawn_manager(task_vars)
                # ... implement resource-specific logic
    """
    
    MODULE_NAME = None  # Subclass must override
    
    def _get_or_spawn_manager(self, task_vars: dict):
        """
        Get existing manager or spawn new one.
        
        Checks if a manager is already running (stored in hostvars).
        If found, connects to it. If not, spawns a new manager process.
        
        Args:
            task_vars: Task variables from Ansible
        
        Returns:
            ManagerRPCClient instance
        
        Raises:
            RuntimeError: If manager fails to start
        """
        # Import here to avoid circular imports
        from ansible.plugins.plugin_utils.manager.rpc_client import ManagerRPCClient
        
        # Check if manager info in hostvars
        hostvars = task_vars.get('hostvars', {})
        inventory_hostname = task_vars.get('inventory_hostname', 'localhost')
        host_vars = hostvars.get(inventory_hostname, {})
        
        socket_path = host_vars.get('platform_manager_socket')
        authkey_b64 = host_vars.get('platform_manager_authkey')
        gateway_url = host_vars.get('gateway_url')
        
        if not gateway_url:
            raise AnsibleError(
                "gateway_url must be defined in inventory or host_vars"
            )
        
        # If manager already running, try to connect
        if socket_path and authkey_b64 and Path(socket_path).exists():
            try:
                authkey = base64.b64decode(authkey_b64)
                client = ManagerRPCClient(gateway_url, socket_path, authkey)
                logger.info("Connected to existing manager")
                return client
            except Exception as e:
                logger.warning(
                    f"Failed to connect to existing manager: {e}. "
                    f"Spawning new one..."
                )
                # Fall through to spawn new one
        
        # Spawn new manager
        logger.info("Spawning new Platform Manager")
        
        # Generate socket path and authkey
        socket_dir = Path(tempfile.gettempdir()) / 'ansible_platform'
        socket_dir.mkdir(exist_ok=True)
        socket_path = str(socket_dir / f'manager_{inventory_hostname}.sock')
        authkey = secrets.token_bytes(32)
        
        # Clean up old socket if exists
        if Path(socket_path).exists():
            try:
                Path(socket_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to remove old socket: {e}")
        
        # Start manager process
        def start_manager():
            """Manager process entry point."""
            from ansible.plugins.plugin_utils.manager.platform_manager import (
                PlatformManager,
                PlatformService
            )
            
            # Create service
            service = PlatformService(gateway_url)
            
            # Register with manager
            PlatformManager.register(
                'get_platform_service',
                callable=lambda: service
            )
            
            # Start manager server
            manager = PlatformManager(address=socket_path, authkey=authkey)
            manager.start()
            
            # Keep running
            import signal
            signal.pause()
        
        # Spawn process
        process = Process(target=start_manager, daemon=True)
        process.start()
        
        # Wait for socket to be created
        max_wait = 50  # 5 seconds
        for _ in range(max_wait):
            if Path(socket_path).exists():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(
                f"Manager failed to start within {max_wait * 0.1} seconds"
            )
        
        # Store info in facts for future tasks
        authkey_b64 = base64.b64encode(authkey).decode('utf-8')
        
        # Set facts so subsequent tasks can reuse this manager
        try:
            self._execute_module(
                module_name='ansible.builtin.set_fact',
                module_args={
                    'platform_manager_socket': socket_path,
                    'platform_manager_authkey': authkey_b64,
                    'cacheable': True  # Persist across plays
                },
                task_vars=task_vars
            )
        except Exception as e:
            logger.warning(f"Failed to set facts: {e}")
        
        # Connect to newly spawned manager
        client = ManagerRPCClient(gateway_url, socket_path, authkey)
        logger.info(f"Spawned and connected to new manager at {socket_path}")
        
        return client
    
    def _build_argspec_from_docs(self, documentation: str) -> dict:
        """
        Build argument spec from DOCUMENTATION string.
        
        Parses the YAML documentation and converts it to Ansible's
        ArgumentSpec format for validation.
        
        Args:
            documentation: DOCUMENTATION string from module
        
        Returns:
            ArgumentSpec dict suitable for ArgumentSpecValidator
        
        Raises:
            ValueError: If documentation cannot be parsed
        """
        try:
            doc_data = yaml.safe_load(documentation)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse DOCUMENTATION: {e}") from e
        
        options = doc_data.get('options', {})
        
        # Build argspec in Ansible format
        argspec = {
            'options': options,
            'mutually_exclusive': doc_data.get('mutually_exclusive', []),
            'required_together': doc_data.get('required_together', []),
            'required_one_of': doc_data.get('required_one_of', []),
            'required_if': doc_data.get('required_if', []),
        }
        
        return argspec
    
    def _validate_data(
        self,
        data: dict,
        argspec: dict,
        direction: str
    ) -> dict:
        """
        Validate data against argument spec.
        
        Uses Ansible's built-in ArgumentSpecValidator to validate
        both input (from playbook) and output (from manager).
        
        Args:
            data: Data dict to validate
            argspec: Argument specification
            direction: 'input' or 'output' (for error messages)
        
        Returns:
            Validated and normalized data dict
        
        Raises:
            AnsibleError: If validation fails
        """
        # Create validator
        validator = ArgumentSpecValidator(argspec)
        
        # Validate
        result = validator.validate(data)
        
        # Check for errors
        if result.error_messages:
            error_msg = (
                f"{direction.title()} validation failed: " +
                ", ".join(result.error_messages)
            )
            raise AnsibleError(error_msg)
        
        return result.validated_parameters
    
    def _detect_operation(self, args: dict) -> str:
        """
        Detect operation type from arguments.
        
        Args:
            args: Module arguments
        
        Returns:
            Operation name ('create', 'update', 'delete', 'find')
        """
        state = args.get('state', 'present')
        
        if state == 'absent':
            return 'delete'
        elif state == 'present':
            # Check if ID is provided (update) or not (create)
            if args.get('id'):
                return 'update'
            else:
                return 'create'
        elif state == 'find':
            return 'find'
        else:
            raise AnsibleError(f"Unknown state: {state}")


# Example usage in resource-specific action plugin:
#
# from .base_action import BaseResourceActionPlugin
# from ansible.plugins.plugin_utils.docs.user import DOCUMENTATION
# from ansible.plugins.plugin_utils.ansible_models.user import AnsibleUser
#
# class ActionModule(BaseResourceActionPlugin):
#     MODULE_NAME = 'user'
#     
#     def run(self, tmp=None, task_vars=None):
#         super(ActionModule, self).run(tmp, task_vars)
#         
#         if task_vars is None:
#             task_vars = {}
#         
#         args = self._task.args.copy()
#         
#         try:
#             # 1. Validate input
#             argspec = self._build_argspec_from_docs(DOCUMENTATION)
#             validated_args = self._validate_data(args, argspec, 'input')
#             
#             # 2. Get manager
#             manager = self._get_or_spawn_manager(task_vars)
#             
#             # 3. Create dataclass
#             user_data = AnsibleUser(**validated_args)
#             
#             # 4. Execute
#             operation = self._detect_operation(args)
#             result_dict = manager.execute(operation, self.MODULE_NAME, user_data)
#             
#             # 5. Validate output
#             validated_result = self._validate_data(result_dict, argspec, 'output')
#             
#             # 6. Return
#             return {
#                 'failed': False,
#                 'changed': True,
#                 self.MODULE_NAME: validated_result
#             }
#         except Exception as e:
#             return {'failed': True, 'msg': str(e)}
```

**Key Features**:
- Manager lifecycle management (spawn once, reuse)
- Bidirectional validation (input and output)
- Fact caching for manager connection info
- Error handling and logging
- Template for resource-specific action plugins

**Usage by Resource Action Plugins**:

Resource-specific action plugins only need to:
1. Inherit from `BaseResourceActionPlugin`
2. Set `MODULE_NAME`
3. Import their DOCUMENTATION and dataclass
4. Implement a thin `run()` method that uses inherited helpers

See `IMPLEMENTATION_FEATURES.md` for complete examples.

---

## Manager Startup Strategy

### 8. Manager Lifecycle

**Concept**: The first playbook task spawns the manager if not already running. Subsequent tasks reuse the same manager.

**Flow**:
1. First task calls `_get_or_spawn_manager()` (from `BaseResourceActionPlugin`)
2. No manager exists → spawns new manager process
3. Sets facts (`platform_manager_socket`, `platform_manager_authkey`)
4. Returns `ManagerRPCClient` connected to new manager
5. Subsequent tasks call `_get_or_spawn_manager()` → finds existing manager in facts → reuses it

See **Section 7: Base Action Plugin** above for complete `_get_or_spawn_manager()` implementation.

**Inventory Setup**:

```yaml
# inventory/hosts.yml
all:
  hosts:
    localhost:
      ansible_connection: local
      gateway_url: https://platform.example.com
      # platform_manager_socket and platform_manager_authkey set by first task
```

---

## Testing the Foundation

### Manual Test: Spawn Manager

Create a simple test script to verify the manager can be spawned:

**File**: `tools/test_manager.py`

```python
"""Test script for Platform Manager."""

import sys
from pathlib import Path

# Add plugins to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'plugins'))

from plugin_utils.manager.platform_manager import PlatformManager, PlatformService

def main():
    base_url = 'https://platform.example.com'
    socket_path = '/tmp/test_manager.sock'
    authkey = b'test_secret'
    
    # Clean up old socket
    if Path(socket_path).exists():
        Path(socket_path).unlink()
    
    # Create service
    service = PlatformService(base_url)
    
    # Register with manager
    PlatformManager.register('get_platform_service', callable=lambda: service)
    
    # Start manager
    print(f"Starting manager at {socket_path}")
    manager = PlatformManager(address=socket_path, authkey=authkey)
    manager.start()
    
    print("Manager started successfully")
    print(f"API Version: {service.api_version}")
    print(f"Supported versions: {service.registry.get_supported_versions()}")
    
    # Keep running
    import signal
    signal.pause()

if __name__ == '__main__':
    main()
```

Run:
```bash
cd ansible.platform
python tools/test_manager.py
```

---

## Next Steps

With the foundation complete, you can now:

1. **Add modules/resources** - See `IMPLEMENTATION_FEATURES.md`
2. **Set up code generation** - See `IMPLEMENTATION_GENERATORS.md`
3. **Test with real playbooks** - Create test playbooks in `tests/integration/`

---

## Summary

The foundation provides:

✅ **BaseTransformMixin** - Universal transformation logic  
✅ **Shared Types** - EndpointOperation and others  
✅ **APIVersionRegistry** - Dynamic version discovery  
✅ **DynamicClassLoader** - Load version-specific classes  
✅ **PlatformManager** - Persistent service (generic, resource-agnostic)  
✅ **ManagerRPCClient** - Client-side communication  
✅ **BaseResourceActionPlugin** - Common action plugin functionality  
✅ **Manager Lifecycle** - First task spawns, others reuse  

**All components are generic and work for ANY resource module.**

---

## Related Documents

- **`IMPLEMENTATION_GENERATORS.md`** - Code generation tools (docstring → dataclass, OpenAPI → dataclass)
- **`IMPLEMENTATION_FEATURES.md`** - Adding new resource modules (user, organization, team)
- **`REQUIREMENTS.md`** - High-level requirements and architecture decisions
