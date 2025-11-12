# Implementation Guide: Adding Resource Features

## Overview

This guide is for developers **adding new resource modules** (users, organizations, teams, etc.) to the Ansible Platform Collection.

**Audience**: Feature developers adding user-facing capabilities

**Prerequisites**: Foundation and generators already set up (see related docs)

---

## Table of Contents

1. [Feature Implementation Workflow](#feature-implementation-workflow)
2. [Step-by-Step: Adding a Resource](#step-by-step-adding-a-resource)
3. [Complete Example: User Resource](#complete-example-user-resource)
4. [Complete Example: Organization Resource](#complete-example-organization-resource)
5. [Testing Your Feature](#testing-your-feature)
6. [Common Patterns](#common-patterns)

---

## Feature Implementation Workflow

### High-Level Steps

```
1. Write DOCUMENTATION (user-facing)
   ↓
2. Generate Ansible dataclass (automated)
   ↓
3. Generate API models from OpenAPI (automated)
   ↓
4. Create Transform Mixin (manual - this is where you add value)
   - Field mapping
   - Custom transformations
   - Endpoint operations
   ↓
5. Create API dataclass (combines generated + mixin)
   ↓
6. Create Action Plugin (thin wrapper)
   ↓
7. Test with playbook
```

### Time Estimates

| Task | Complexity | Time |
|------|------------|------|
| Write DOCUMENTATION | Simple | 15-30 min |
| Run generators | N/A | < 1 min |
| Create transform mixin | Simple | 30-60 min |
| | With transforms | 1-2 hours |
| | Multi-endpoint | 2-3 hours |
| Create action plugin | Simple | 10 min |
| Write test playbook | Simple | 15-30 min |

---

## Step-by-Step: Adding a Resource

### Step 1: Write Documentation

**File**: `plugins/plugin_utils/docs/{resource}.py`

Define the user-facing interface:

```python
# plugins/plugin_utils/docs/user.py

DOCUMENTATION = """
---
module: user
short_description: Manage platform users
description:
  - Create, update, or delete platform users
  - Manage user attributes and associations
options:
  username:
    description:
      - Username for the user
      - Required for creation
    required: true
    type: str
  
  email:
    description: Email address
    type: str
  
  first_name:
    description: First name of the user
    type: str
  
  last_name:
    description: Last name of the user
    type: str
  
  is_superuser:
    description: Grant superuser permissions
    type: bool
    default: false
  
  password:
    description: 
      - User password
      - Write-only field
    type: str
  
  organizations:
    description:
      - List of organization names (NOT IDs)
      - On input: Organization names to associate
      - On output: Returns organization names
    type: list
    elements: str
  
  id:
    description:
      - User ID
      - Read-only, returned after creation
    type: int
  
  created:
    description:
      - Creation timestamp
      - Read-only
    type: str
"""
```

**Key Principles**:
- User-facing (names, not IDs)
- Clear descriptions
- Mark read-only fields
- Specify required fields

---

### Step 2: Generate Ansible Dataclass

```bash
python tools/generators/generate_ansible_dataclasses.py \
    plugins/plugin_utils/docs/user.py
```

**Output**: `plugins/plugin_utils/ansible_models/user.py`

```python
@dataclass
class AnsibleUser(BaseTransformMixin):
    """Manage platform users."""
    
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_superuser: Optional[bool] = False
    password: Optional[str] = None
    organizations: Optional[List[str]] = None
    id: Optional[int] = None
    created: Optional[str] = None
```

**Review**: Verify types and defaults match intent.

---

### Step 3: Generate API Models

Ensure OpenAPI spec is in `tools/openapi_specs/gateway-v1.json`, then:

```bash
bash tools/generators/generate_api_models.sh
```

**Output**: `plugins/plugin_utils/api/v1/generated/models.py`

Contains all API schemas, including:
```python
@dataclass
class User:
    id: Optional[int] = None
    username: str = ''
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_superuser: Optional[bool] = False
    password: Optional[str] = None  # writeOnly in OpenAPI
    created: Optional[str] = None  # readOnly in OpenAPI
    # ... other fields from API
```

---

### Step 4: Create Transform Mixin (MANUAL)

**File**: `plugins/plugin_utils/api/v1/user.py`

This is where you add value - defining how Ansible and API formats relate.

```python
"""Transform mixin for User resource (API v1).

This module bridges the Ansible user model and the platform API user model.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from ..platform.base_transform import BaseTransformMixin
from ..platform.types import EndpointOperation
from .generated.models import User as GeneratedAPIUser


class UserTransformMixin_v1(BaseTransformMixin):
    """
    Transform mixin for User resource (API v1).
    
    Defines field mappings, custom transformations, and endpoint operations
    specific to the User resource in API version 1.
    """
    
    # --- FIELD MAPPING ---
    _field_mapping = {
        # Simple 1:1 mappings (field name same in both)
        'username': 'username',
        'email': 'email',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'is_superuser': 'is_superuser',
        'password': 'password',
        'id': 'id',
        'created': 'created',
        
        # Complex mapping (requires transformation)
        'organizations': {
            'api_field': 'organization_ids',  # API uses IDs
            'forward_transform': 'names_to_ids',  # Ansible → API
            'reverse_transform': 'ids_to_names',  # API → Ansible
            'endpoint': 'organizations_post',  # Separate endpoint
        },
    }
    
    # --- TRANSFORMATION FUNCTIONS ---
    _transform_registry = {
        'names_to_ids': lambda value, context: context['manager'].lookup_org_ids(value),
        'ids_to_names': lambda value, context: context['manager'].lookup_org_names(value),
    }
    
    # --- ENDPOINT OPERATIONS ---
    @classmethod
    def get_endpoint_operations(cls) -> Dict[str, EndpointOperation]:
        """
        Define API endpoint operations for User resource.
        
        Returns:
            Dict mapping operation names to EndpointOperation objects
        """
        return {
            # Main create/update endpoint
            'create': EndpointOperation(
                path='/api/gateway/v1/users/',
                method='POST',
                fields=['username', 'email', 'first_name', 'last_name', 
                        'is_superuser', 'password'],
                order=1
            ),
            
            'update': EndpointOperation(
                path='/api/gateway/v1/users/{id}/',
                method='PATCH',
                fields=['email', 'first_name', 'last_name', 'is_superuser', 
                        'password'],
                path_params=['id'],
                order=1
            ),
            
            # Sub-resource: Associate organizations
            'organizations_post': EndpointOperation(
                path='/api/gateway/v1/users/{id}/organizations/',
                method='POST',
                fields=['organization_ids'],
                path_params=['id'],
                depends_on='create',  # Must create user first
                required_for='create',  # Only on create
                order=2
            ),
        }
    
    # --- CLASS REFERENCES ---
    @classmethod
    def _get_api_class(cls):
        """Return API dataclass type."""
        return APIUser_v1
    
    @classmethod
    def _get_ansible_class(cls):
        """Return Ansible dataclass type."""
        from ...ansible_models.user import AnsibleUser
        return AnsibleUser


@dataclass
class APIUser_v1(UserTransformMixin_v1, GeneratedAPIUser):
    """
    API User dataclass (v1) with transformation capabilities.
    
    Combines:
    - Generated API structure (from OpenAPI)
    - Transformation logic (from mixin)
    """
    pass
```

**Key Sections**:

1. **`_field_mapping`**: How fields map between Ansible ↔ API
2. **`_transform_registry`**: Custom transformation functions
3. **`get_endpoint_operations()`**: API endpoint configuration
4. **`_get_api_class()` / `_get_ansible_class()`**: Class references

---

### Step 5: Create Action Plugin

**File**: `plugins/action/user.py`

```python
"""Action plugin for user resource."""

from ansible.plugins.action import ActionBase
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator
from ansible.errors import AnsibleError
import yaml
import logging

# Import from plugin_utils
from ansible.plugins.plugin_utils.manager.rpc_client import ManagerRPCClient
from ansible.plugins.plugin_utils.docs.user import DOCUMENTATION
from ansible.plugins.plugin_utils.ansible_models.user import AnsibleUser

logger = logging.getLogger(__name__)


class ActionModule(ActionBase):
    """
    Action plugin for managing platform users.
    
    This is a thin client that:
    1. Validates input
    2. Calls manager
    3. Validates output
    4. Returns result
    """
    
    MODULE_NAME = 'user'
    
    def run(self, tmp=None, task_vars=None):
        """
        Execute action plugin.
        
        Args:
            tmp: Temporary directory (unused)
            task_vars: Task variables from Ansible
        
        Returns:
            Dict with 'failed', 'changed', and result data
        """
        super(ActionModule, self).run(tmp, task_vars)
        
        if task_vars is None:
            task_vars = {}
        
        # Get task arguments
        args = self._task.args.copy()
        
        try:
            # 1. INPUT VALIDATION
            argspec = self._build_argspec_from_docs()
            validated_args = self._validate_data(args, argspec, 'input')
            
            # 2. GET/SPAWN MANAGER
            manager_client = self._get_or_spawn_manager(task_vars)
            
            # 3. CREATE ANSIBLE DATACLASS
            ansible_user = AnsibleUser(**validated_args)
            
            # 4. EXECUTE VIA MANAGER
            operation = args.get('state', 'present')
            if operation == 'present':
                operation = 'create'  # TODO: Detect update vs create
            elif operation == 'absent':
                operation = 'delete'
            
            result_dict = manager_client.execute(
                operation=operation,
                module_name=self.MODULE_NAME,
                ansible_data=ansible_user
            )
            
            # 5. OUTPUT VALIDATION
            validated_result = self._validate_data(result_dict, argspec, 'output')
            
            # 6. RETURN
            return {
                'failed': False,
                'changed': True,  # TODO: Detect actual changes
                self.MODULE_NAME: validated_result
            }
            
        except Exception as e:
            logger.error(f"Action plugin failed: {e}", exc_info=True)
            return {
                'failed': True,
                'msg': str(e)
            }
    
    def _build_argspec_from_docs(self) -> dict:
        """
        Build argument spec from DOCUMENTATION string.
        
        Returns:
            ArgumentSpec dict
        """
        doc_data = yaml.safe_load(DOCUMENTATION)
        options = doc_data.get('options', {})
        
        # Convert to argspec format
        argspec = {
            'options': options,
            'mutually_exclusive': [],
            'required_together': [],
        }
        
        return argspec
    
    def _validate_data(
        self,
        data: dict,
        argspec: dict,
        direction: str
    ) -> dict:
        """
        Validate data against argspec.
        
        Args:
            data: Data to validate
            argspec: Argument specification
            direction: 'input' or 'output'
        
        Returns:
            Validated data
        
        Raises:
            AnsibleError: If validation fails
        """
        validator = ArgumentSpecValidator(argspec)
        result = validator.validate(data)
        
        if result.error_messages:
            error_msg = f"{direction.title()} validation failed: " + \
                       ", ".join(result.error_messages)
            raise AnsibleError(error_msg)
        
        return result.validated_parameters
    
    def _get_or_spawn_manager(
        self,
        task_vars: dict
    ) -> ManagerRPCClient:
        """
        Get existing manager or spawn new one.
        
        Args:
            task_vars: Task variables
        
        Returns:
            ManagerRPCClient instance
        """
        # ... (implementation from foundation doc)
        # See IMPLEMENTATION_FOUNDATION.md section 7
        pass
```

---

### Step 6: Test with Playbook

**File**: `tests/integration/test_user.yml`

```yaml
---
- name: Test User Management
  hosts: localhost
  gather_facts: false
  
  vars:
    gateway_url: https://platform.example.com
  
  tasks:
    - name: Create user (this will spawn manager)
      ansible.platform.user:
        username: john_doe
        email: john@example.com
        first_name: John
        last_name: Doe
        organizations:
          - Engineering
          - Platform Team
      register: user_result
    
    - name: Verify user was created
      assert:
        that:
          - user_result is not failed
          - user_result.changed
          - user_result.user.username == 'john_doe'
          - user_result.user.id is defined
          - user_result.user.organizations | length == 2
    
    - name: Update user (reuses existing manager)
      ansible.platform.user:
        username: john_doe
        email: john.doe@example.com
        first_name: John
        last_name: Doe-Smith
        organizations:
          - Engineering
      register: update_result
    
    - name: Verify update
      assert:
        that:
          - update_result is not failed
          - update_result.user.email == 'john.doe@example.com'
          - update_result.user.last_name == 'Doe-Smith'
```

Run:
```bash
ansible-playbook tests/integration/test_user.yml
```

---

## Complete Example: User Resource

See Step 4 above for full `UserTransformMixin_v1` implementation.

### Key Features

✅ **Simple field mappings** (username, email, etc.)  
✅ **Complex transformation** (org names ↔ IDs)  
✅ **Multi-endpoint** (create user, then associate orgs)  
✅ **Read-only fields** (id, created)  
✅ **Write-only fields** (password)  

---

## Complete Example: Organization Resource

A simpler resource with no custom transformations.

### File: `plugins/plugin_utils/docs/organization.py`

```python
DOCUMENTATION = """
---
module: organization
short_description: Manage platform organizations
options:
  name:
    description: Organization name
    required: true
    type: str
  
  description:
    description: Organization description
    type: str
  
  max_hosts:
    description: Maximum number of hosts
    type: int
  
  id:
    description: Organization ID (read-only)
    type: int
"""
```

### Generate

```bash
python tools/generators/generate_ansible_dataclasses.py \
    plugins/plugin_utils/docs/organization.py
```

### File: `plugins/plugin_utils/api/v1/organization.py`

```python
"""Transform mixin for Organization resource (API v1)."""

from dataclasses import dataclass
from typing import Dict

from ..platform.base_transform import BaseTransformMixin
from ..platform.types import EndpointOperation
from .generated.models import Organization as GeneratedAPIOrganization


class OrganizationTransformMixin_v1(BaseTransformMixin):
    """Transform mixin for Organization (v1)."""
    
    # Simple 1:1 mapping (no transformations needed)
    _field_mapping = {
        'name': 'name',
        'description': 'description',
        'max_hosts': 'max_hosts',
        'id': 'id',
    }
    
    # No custom transforms needed
    _transform_registry = {}
    
    @classmethod
    def get_endpoint_operations(cls) -> Dict[str, EndpointOperation]:
        """Define endpoint operations."""
        return {
            'create': EndpointOperation(
                path='/api/gateway/v1/organizations/',
                method='POST',
                fields=['name', 'description', 'max_hosts'],
                order=1
            ),
            'update': EndpointOperation(
                path='/api/gateway/v1/organizations/{id}/',
                method='PATCH',
                fields=['description', 'max_hosts'],
                path_params=['id'],
                order=1
            ),
        }
    
    @classmethod
    def _get_api_class(cls):
        return APIOrganization_v1
    
    @classmethod
    def _get_ansible_class(cls):
        from ...ansible_models.organization import AnsibleOrganization
        return AnsibleOrganization


@dataclass
class APIOrganization_v1(OrganizationTransformMixin_v1, GeneratedAPIOrganization):
    """API Organization dataclass (v1)."""
    pass
```

### File: `plugins/action/organization.py`

```python
"""Action plugin for organization resource."""

from ansible.plugins.plugin_utils.docs.organization import DOCUMENTATION
from ansible.plugins.plugin_utils.ansible_models.organization import AnsibleOrganization

# ... (same structure as user action plugin, just change module name and class)

class ActionModule(ActionBase):
    MODULE_NAME = 'organization'
    # ... rest is identical pattern
```

---

## Testing Your Feature

### Unit Tests

Test transformation logic in isolation:

```python
# tests/unit/test_user_transform.py

from plugins.plugin_utils.ansible_models.user import AnsibleUser
from plugins.plugin_utils.api.v1.user import APIUser_v1

def test_forward_transform():
    """Test Ansible → API transformation."""
    # Create Ansible user
    ansible_user = AnsibleUser(
        username='test_user',
        email='test@example.com',
        organizations=['Org1', 'Org2']
    )
    
    # Mock context
    context = {
        'manager': MockManager(),
        'cache': {}
    }
    
    # Transform
    api_user = ansible_user.to_api(context)
    
    # Verify
    assert api_user.username == 'test_user'
    assert api_user.organization_ids == [1, 2]  # Mocked lookup

def test_reverse_transform():
    """Test API → Ansible transformation."""
    # Create API user
    api_user = APIUser_v1(
        username='test_user',
        email='test@example.com',
        organization_ids=[1, 2]
    )
    
    # Mock context
    context = {
        'manager': MockManager(),
        'cache': {}
    }
    
    # Transform
    ansible_user = api_user.to_ansible(context)
    
    # Verify
    assert ansible_user.username == 'test_user'
    assert ansible_user.organizations == ['Org1', 'Org2']  # Mocked reverse lookup
```

### Integration Tests

Test via playbooks (see Step 6 above).

---

## Common Patterns

### Pattern 1: Name ↔ ID Transformation

**Use Case**: User provides names, API requires IDs.

```python
_field_mapping = {
    'team_names': {
        'api_field': 'team_ids',
        'forward_transform': 'team_names_to_ids',
        'reverse_transform': 'team_ids_to_names',
    }
}

_transform_registry = {
    'team_names_to_ids': lambda names, ctx: ctx['manager'].lookup_team_ids(names),
    'team_ids_to_names': lambda ids, ctx: ctx['manager'].lookup_team_names(ids),
}

# Implement in PlatformService:
def lookup_team_ids(self, names: List[str]) -> List[int]:
    # ... API call with caching
```

### Pattern 2: Nested Object Flattening

**Use Case**: API has nested structure, Ansible uses flat.

```python
# Ansible: address_city, address_state
# API: address.city, address.state

_field_mapping = {
    'address_city': 'address.city',
    'address_state': 'address.state',
}
```

BaseTransformMixin handles dot-notation automatically.

### Pattern 3: Conditional Fields

**Use Case**: Field only relevant for certain operations.

```python
@classmethod
def get_endpoint_operations(cls) -> Dict[str, EndpointOperation]:
    return {
        'create': EndpointOperation(
            path='/api/v1/resources/',
            method='POST',
            fields=['name', 'initial_config'],  # Only on create
            order=1
        ),
        'update': EndpointOperation(
            path='/api/v1/resources/{id}/',
            method='PATCH',
            fields=['name'],  # No initial_config on update
            path_params=['id'],
            order=1
        ),
    }
```

### Pattern 4: Multi-Step Create

**Use Case**: Create resource, then configure sub-resources.

```python
@classmethod
def get_endpoint_operations(cls) -> Dict[str, EndpointOperation]:
    return {
        # Step 1: Create team
        'create': EndpointOperation(
            path='/api/v1/teams/',
            method='POST',
            fields=['name', 'description'],
            order=1
        ),
        
        # Step 2: Add members (depends on create)
        'add_members': EndpointOperation(
            path='/api/v1/teams/{id}/members/',
            method='POST',
            fields=['member_ids'],
            path_params=['id'],
            depends_on='create',
            required_for='create',
            order=2
        ),
        
        # Step 3: Set permissions (depends on create)
        'set_permissions': EndpointOperation(
            path='/api/v1/teams/{id}/permissions/',
            method='POST',
            fields=['permission_ids'],
            path_params=['id'],
            depends_on='create',
            required_for='create',
            order=3
        ),
    }
```

Manager will execute in dependency order: create → add_members → set_permissions.

### Pattern 5: Version-Specific Overrides

**Use Case**: API v2 changes a field name.

```python
# v1: organization_ids
# v2: org_ids

# plugins/plugin_utils/api/v2/user.py

class UserTransformMixin_v2(UserTransformMixin_v1):
    """V2 overrides v1."""
    
    # Override field mapping
    _field_mapping = {
        **UserTransformMixin_v1._field_mapping,  # Inherit v1
        'organizations': {
            'api_field': 'org_ids',  # Changed in v2
            'forward_transform': 'names_to_ids',
            'reverse_transform': 'ids_to_names',
        }
    }
```

---

## Summary

### What You Built

✅ **Documentation** (`docs/user.py`) - User-facing contract  
✅ **Ansible Dataclass** (`ansible_models/user.py`) - Generated  
✅ **API Models** (`api/v1/generated/models.py`) - Generated  
✅ **Transform Mixin** (`api/v1/user.py`) - **Your value-add**  
✅ **Action Plugin** (`action/user.py`) - Thin wrapper  
✅ **Tests** (`tests/integration/test_user.yml`) - Verification  

### Time Investment

- **Setup** (one-time): Foundation + generators = 4-8 hours
- **Per resource** (simple): 1-2 hours
- **Per resource** (complex): 3-4 hours

### Reusability

- **Foundation**: 100% reusable across all resources
- **Generators**: 100% reusable
- **Action plugin pattern**: 95% reusable (change module name only)
- **Transform mixin**: Resource-specific, but patterns repeat

---

## Related Documents

- **`IMPLEMENTATION_FOUNDATION.md`** - Core framework you're building on
- **`IMPLEMENTATION_GENERATORS.md`** - How to run the generators
- **`REQUIREMENTS.md`** - Why we're doing it this way
