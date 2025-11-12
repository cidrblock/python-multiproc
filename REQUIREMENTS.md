# Platform Collection Requirements

## Overview

This document outlines the high-level requirements for the Ansible Platform Collection, which provides action plugins for managing platform resources (users, organizations, teams, etc.) with automatic API version adaptation and code generation capabilities.

## Architecture Goals

1. **User-Facing Stability**: Ansible playbook interface remains stable across API versions
2. **Code Generation**: Minimize manual coding through automated generation from docstrings and OpenAPI specs
3. **Version Flexibility**: Support multiple API versions dynamically without hardcoding
4. **Performance**: Maintain persistent platform connections for faster playbook execution
5. **Type Safety**: Strong typing throughout with validation at multiple layers

## Key Architectural Decisions

### 1. Manager-Side Transformations
**All data transformations happen in the persistent manager process, not the client action plugins.**

- Manager performs forward transform (Ansible → API)
- Manager performs reverse transform (API → Ansible)
- Client never sees API format
- Only Ansible dataclasses cross RPC boundary
- Follows existing multiprocess weather service pattern

### 2. Round-Trip Data Contract
**Output data uses the same format and fields as input data (defined in DOCUMENTATION).**

- No separate RETURN section needed
- Input: `organizations=['Engineering']` (names)
- Output: `organizations=['Engineering']` (names, not IDs)
- API format (`organization_ids=[1]`) is internal to manager
- Consistent, predictable interface for users

### 3. Symmetric Validation
**Single ArgumentSpec (from DOCUMENTATION) used for both input and output validation.**

- Client validates user input before sending to manager
- Client validates manager response before returning to user
- Same spec ensures round-trip compliance
- Catches transformation bugs early
- Manager bugs fail fast with clear errors

### 4. Generic Manager
**Manager is resource-agnostic and works for all modules.**

- No user-specific, organization-specific, or team-specific code
- Single `execute(operation, module, data)` method
- Resource logic lives in dataclass transform mixins
- Manager orchestrates based on mixin instructions
- Easy to add new resources

### 5. Client Responsibilities (Thin)
- Validate input (ArgumentSpec from DOCUMENTATION)
- Create Ansible dataclass
- Send to manager via RPC
- Receive Ansible dataclass back
- Validate output (same ArgumentSpec)
- Format return dict for Ansible

### 6. Manager Responsibilities (Heavy)
- Maintain persistent platform connection
- Detect and cache API version
- Load version-specific classes
- Perform all transformations
- Execute API calls (multi-endpoint support)
- Provide lookup helpers (names ↔ IDs)
- Return Ansible dataclass (not API response)

---

## Personas

### 1. Ansible Playbook Author (End User)
Writes playbooks to automate platform configuration. Expects simple, stable interfaces.

### 2. Collection Developer (Plugin/Module Creator)
Develops and maintains action plugins. Wants to minimize manual coding and leverage generation tools.

### 3. Platform API Developer (API Maintainer)
Maintains the platform API and OpenAPI specifications. Needs changes to propagate to the collection automatically.

### 4. System Administrator (Deployment/Operations)
Deploys and operates playbooks at scale. Needs performance, reliability, and clear error messages.

---

## User Stories

## Persona 1: Ansible Playbook Author

### Story 1.1: Simple Resource Management

**As an** Ansible playbook author  
**I want to** create and manage platform resources (users, organizations, teams) using simple, stable action plugins  
**So that** I can automate platform configuration without worrying about API version differences

**Acceptance Criteria:**
- Single, stable interface regardless of API version
- Clear parameter validation with helpful error messages
- Idempotent operations (detect changes, only update when needed)
- Works with standard Ansible patterns (state: present/absent)
- Return values match the RETURN section of module documentation

**Example Usage:**
```yaml
- name: Create user
  platform.gateway.user:
    gateway_url: "{{ platform_url }}"
    username: jdoe
    email: jdoe@example.com
    first_name: John
    last_name: Doe
    organizations:
      - Engineering
      - DevOps
    state: present

- name: Create organization
  platform.gateway.organization:
    gateway_url: "{{ platform_url }}"
    name: Engineering
    description: Engineering team
    state: present

- name: Remove user
  platform.gateway.user:
    gateway_url: "{{ platform_url }}"
    username: jdoe
    state: absent
```

---

### Story 1.2: Automatic API Version Detection

**As an** Ansible playbook author  
**I want** the action plugin to automatically detect and adapt to the API version  
**So that** my playbooks work across different platform versions without modification

**Acceptance Criteria:**
- Auto-detect API version from platform endpoint
- Automatically use appropriate API endpoints and field mappings
- Warn if using fallback version compatibility
- Allow explicit version override if needed via `api_version` parameter

**Example:**
```yaml
# Auto-detect version (recommended)
- name: Create user with auto-detection
  platform.gateway.user:
    gateway_url: "{{ platform_url }}"
    username: jdoe
    state: present

# Explicit version override (optional)
- name: Create user with specific API version
  platform.gateway.user:
    gateway_url: "{{ platform_url }}"
    api_version: v1
    username: jdoe
    state: present
```

---

### Story 1.3: Relationship Management

**As an** Ansible playbook author  
**I want to** manage resource relationships (users in organizations, users with authenticators)  
**So that** I can configure complete resource setups in a single task

**Acceptance Criteria:**
- Relationships specified as lists of names or IDs
- Automatic ID resolution (names → IDs)
- Multi-step API calls handled transparently
- Atomic operations (rollback on failure)

**Example:**
```yaml
- name: Create user with relationships
  platform.gateway.user:
    gateway_url: "{{ platform_url }}"
    username: jdoe
    organizations:
      - Engineering    # Names automatically resolved to IDs
      - DevOps
    associated_authenticators:
      ldap:
        uid: "jdoe@corp.com"
        email: "jdoe@example.com"
    state: present
```

---

## Persona 2: Collection Developer

### Story 2.1: Generate Action Plugin from Docstring

**As a** collection developer  
**I want to** define a new action plugin by writing an Ansible DOCUMENTATION docstring  
**So that** I can quickly create new plugins with automatic validation and dataclass generation

**Acceptance Criteria:**
- Write DOCUMENTATION string in standard Ansible format
- Run generator script to create:
  - Ansible dataclass with type hints
  - ArgumentSpec for validation
  - Basic action plugin skeleton
- Docstring serves as single source of truth for inputs AND outputs
- Generated code includes nested options (suboptions)
- Supports all Ansible types (str, int, bool, list, dict)
- Handles required/optional fields correctly
- RETURN section defines the contract for action plugin return values
- Return values are validated against RETURN specification

**Workflow:**
```bash
# 1. Write docstring
vim platform/ansible/module_docs/user.py

# 2. Generate Ansible dataclass
python scripts/generate_ansible_dataclasses.py

# 3. Result: platform/ansible/dataclasses/user.py created
# Contains: AnsibleUser dataclass with validation
```

**Generated Output:**
```python
@dataclass
class AnsibleUser(BaseTransformMixin):
    """Configure a gateway user."""
    
    # Required fields
    username: str
    
    # Optional fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    is_superuser: Optional[bool] = None
    organizations: Optional[List[str]] = None
```

---

### Story 2.1b: Round-Trip Data Contract

**As a** collection developer  
**I want** action plugin return values to use the same format and fields as input parameters  
**So that** users get consistent, predictable data flow with a single contract defined in DOCUMENTATION

**Acceptance Criteria:**
- DOCUMENTATION defines field contract for BOTH input and output
- No separate RETURN section needed (output uses same fields as input)
- API responses are reverse-transformed to match input format
- Field names match DOCUMENTATION (not API field names)
- Field types match DOCUMENTATION (list[str] for names, not list[int] for IDs)
- Read-only fields (id, created, modified) included in output but not required in input
- Standard Ansible return fields always included (changed, failed, msg)

**Example DOCUMENTATION (Single Source of Truth):**
```python
DOCUMENTATION = """
options:
    username:
      description: Username for the user
      required: true
      type: str
    email:
      description: Email address
      type: str
    organizations:
      description:
        - List of organization names (NOT IDs)
        - Input: Provide organization names
        - Output: Returns organization names
      type: list
      elements: str
    id:
      description: User ID (read-only, returned after creation)
      type: int
    created:
      description: Creation timestamp (read-only)
      type: str
"""
```

**Round-Trip Example:**
```python
# INPUT (user provides):
{
    'username': 'jdoe',
    'email': 'jdoe@example.com',
    'organizations': ['Engineering', 'DevOps']  # Names
}

# OUTPUT (manager returns - SAME FORMAT):
{
    'changed': True,
    'failed': False,
    'msg': 'User created',
    'username': 'jdoe',
    'email': 'jdoe@example.com',
    'organizations': ['Engineering', 'DevOps'],  # Names (not IDs!)
    'id': 123,  # Read-only field added
    'created': '2025-11-12T10:30:00Z'  # Read-only field added
}
```

**Implementation:**
- Manager performs reverse transformation (API → Ansible format)
- Transform ensures field names/types match DOCUMENTATION
- Client validates output against same ArgumentSpec used for input
- Manager returns Ansible dataclass (not API response)
- Only Ansible dataclasses cross RPC boundary

---

### Story 2.1c: Manager and Client Role Separation

**As a** collection developer  
**I want** clear separation between client (action plugin) and manager (persistent service)  
**So that** the architecture is clean, maintainable, and follows the existing multiprocess pattern

**Acceptance Criteria:**

**Client (Action Plugin) Responsibilities:**
- Validate input using ArgumentSpec (from DOCUMENTATION)
- Create Ansible dataclass from validated input
- Send Ansible dataclass to manager via RPC
- Receive Ansible dataclass back from manager via RPC
- Validate output using same ArgumentSpec
- Format return dict for Ansible (add changed, failed, msg)
- NO API knowledge, NO version resolution, NO transformations

**Manager (Persistent Service) Responsibilities:**
- Maintain persistent platform connection (session reuse)
- Detect and cache API version (once per connection)
- Load version-specific classes dynamically
- Perform forward transformation (Ansible → API format)
- Execute API calls (including multi-endpoint operations)
- Perform reverse transformation (API → Ansible format)
- Return Ansible dataclass (not API response)
- Provide lookup helpers (org names ↔ IDs)
- Generic and resource-agnostic (works for any module)

**Data Flow:**
```
ACTION PLUGIN (Client)               MANAGER (Server)
-------------------                  ----------------

1. Validate input (ArgumentSpec)
2. Create AnsibleUser dataclass
   organizations=['Engineering']  →  3. Receive AnsibleUser
                                     
                                     4. TRANSFORM: Ansible → API
                                        organizations=['Engineering']
                                        ↓ (lookup names → IDs)
                                        organization_ids=[1]
                                     
                                     5. Call Platform API
                                        POST /api/gateway/v1/users/
                                        body: {organization_ids: [1]}
                                     
                                     6. Receive API response
                                        {id: 123, organization_ids: [1]}
                                     
                                     7. TRANSFORM: API → Ansible
                                        organization_ids=[1]
                                        ↓ (lookup IDs → names)
                                        organizations=['Engineering']
                                     
8. Receive AnsibleUser result     ←  9. Return AnsibleUser dataclass
   organizations=['Engineering']        organizations=['Engineering']
   
9. Validate output (ArgumentSpec)
10. Format for Ansible return
```

**RPC Protocol (Only Ansible Dataclasses Cross Boundary):**
```python
# Client → Manager
{
    'operation': 'create',
    'module': 'user',
    'data': {  # AnsibleUser (serialized)
        'username': 'jdoe',
        'organizations': ['Engineering']  # Names
    }
}

# Manager → Client
{
    'success': True,
    'data': {  # AnsibleUser (serialized)
        'id': 123,
        'username': 'jdoe',
        'organizations': ['Engineering']  # Names (not IDs!)
    }
}

# API format (organization_ids) NEVER crosses RPC boundary
```

**Manager is Generic:**
```python
# Manager has NO user-specific code
# Works for ANY resource (user, organization, team, etc.)

manager.execute('create', 'user', ansible_user_data)
manager.execute('create', 'organization', ansible_org_data)
manager.execute('create', 'team', ansible_team_data)

# Resource-specific logic lives in dataclass transform mixins
# Manager just orchestrates based on mixin instructions
```

**Benefits:**
- Clean separation of concerns
- Client stays thin and simple
- Manager is reusable across all resources
- Transformations have full context (session, cache, version)
- Only user-facing format crosses RPC boundary
- Follows existing weather service multiprocess pattern

---

### Story 2.2: Generate API Models from OpenAPI Spec

**As a** collection developer  
**I want to** generate API dataclasses from OpenAPI specifications  
**So that** I have accurate, type-safe models without manual coding

**Acceptance Criteria:**
- Parse OpenAPI spec JSON file (gateway.json)
- Generate Python dataclasses with:
  - All fields with correct Python types
  - readOnly fields marked (id, created, modified)
  - writeOnly fields marked (password, authenticators)
  - Required vs optional fields
  - Nested object support
  - Field validation constraints (maxLength, pattern, format)
- Auto-detect deprecated fields from descriptions
- Version-specific models (v1, v2, etc.)
- Leverage `datamodel-code-generator` for generation

**Workflow:**
```bash
# 1. Get OpenAPI spec (or use existing)
curl https://platform.example.com/api/gateway/v1/openapi.json > openapi_specs/gateway-v1.json

# 2. Generate API models
./scripts/generate_api_models.sh

# 3. Result: platform/api/v1/generated/models.py created
# Contains: All API dataclasses (User, Organization, Team, etc.)
```

**Generated Output:**
```python
@dataclass
class User:
    """User resource from OpenAPI spec."""
    username: str
    id: Optional[int] = None  # readOnly
    email: Optional[str] = None
    password: Optional[str] = None  # writeOnly
    is_superuser: Optional[bool] = None
    created: Optional[datetime] = None  # readOnly
```

---

### Story 2.3: Define Field Mapping and Transformations

**As a** collection developer  
**I want to** define mappings between Ansible and API dataclasses with transformation logic  
**So that** I can handle field name differences, ID lookups, and complex data transformations

**Acceptance Criteria:**
- Simple 1:1 field mappings (username → username)
- Field name translations (is_superuser → superuser)
- Custom transformations (organization names → IDs)
- Bidirectional mappings (Ansible ↔ API)
- Nested field mappings with dot notation (user.address.city)
- Transformation functions can access manager/context
- Transformations execute at runtime with access to API

**Implementation:**
```python
# platform/api/v1/user.py
class UserTransformMixin_v1(BaseTransformMixin):
    """User transformation logic for API v1."""
    
    _field_mapping = {
        # Direct 1:1 mapping
        'username': 'username',
        'first_name': 'first_name',
        'email': 'email',
        
        # Field rename
        'is_superuser': 'superuser',
        
        # Complex transformation with ID lookup
        'organizations': {
            'api_field': 'organization_ids',
            'forward_transform': 'names_to_ids',  # Ansible → API
            'reverse_transform': 'ids_to_names',  # API → Ansible
            'endpoint': 'organizations_post'      # Separate API call
        },
        
        # Nested object transformation
        'associated_authenticators': {
            'api_field': 'authenticators',
            'forward_transform': 'format_authenticators',
            'endpoint': 'authenticators_post'
        }
    }
    
    _transform_registry = {
        'names_to_ids': lambda names, ctx: ctx['manager'].lookup_org_ids(names),
        'ids_to_names': lambda ids, ctx: ctx['manager'].lookup_org_names(ids),
        'format_authenticators': lambda data, ctx: format_auth(data),
    }
```

---

### Story 2.4: Handle Multi-Endpoint Operations

**As a** collection developer  
**I want to** define multiple API endpoints for a single resource operation  
**So that** I can handle resources that require multiple API calls (main resource + relationships)

**Acceptance Criteria:**
- Define primary endpoint (create user)
- Define relationship endpoints (add to organizations, link authenticators)
- Specify execution order and dependencies
- Automatic orchestration of multiple calls
- Rollback on failure (delete created resources)
- Path parameter substitution ({id})

**Implementation:**
```python
@classmethod
def get_endpoint_operations(cls) -> Dict[str, EndpointOperation]:
    """Define all API endpoints for User."""
    return {
        'create': EndpointOperation(
            path='/api/gateway/v1/users/',
            method='POST',
            fields=['username', 'email', 'first_name', 'password'],
            order=1
        ),
        'update': EndpointOperation(
            path='/api/gateway/v1/users/{id}/',
            method='PATCH',
            fields=['username', 'email', 'first_name'],
            path_params=['id'],
            order=1,
            required_for='update'
        ),
        'organizations_post': EndpointOperation(
            path='/api/gateway/v1/users/{id}/organizations/',
            method='POST',
            fields=['organizations'],
            path_params=['id'],
            depends_on='create',  # Must run after create
            order=2
        ),
        'authenticators_post': EndpointOperation(
            path='/api/gateway/v1/users/{id}/authenticators/',
            method='POST',
            fields=['associated_authenticators'],
            path_params=['id'],
            depends_on='create',
            order=3
        ),
    }
```

**Execution Flow:**
```
User creates user with organizations:
1. POST /api/gateway/v1/users/ → returns {id: 123}
2. POST /api/gateway/v1/users/123/organizations/ → associate orgs
3. Return combined result to user
```

---

### Story 2.5: Support Multiple API Versions

**As a** collection developer  
**I want** version-specific implementations that inherit from previous versions  
**So that** I can support multiple API versions with minimal code duplication

**Acceptance Criteria:**
- Organize by API version (api/v1/, api/v2/)
- Later versions inherit from earlier versions (v2 extends v1)
- Override only what changed between versions
- Automatic version discovery (scan filesystem)
- Fallback to closest compatible version if exact match not found
- Version-specific field mappings and endpoints

**Directory Structure:**
```
platform/api/
├── v1/
│   ├── generated/
│   │   └── models.py         # Generated from gateway-v1.json
│   ├── user.py               # UserTransformMixin_v1
│   └── organization.py       # OrgTransformMixin_v1
│
└── v2/
    ├── generated/
    │   └── models.py         # Generated from gateway-v2.json
    ├── user.py               # UserTransformMixin_v2 extends v1
    └── organization.py
```

**Inheritance Example:**
```python
# api/v1/user.py
class UserTransformMixin_v1(BaseTransformMixin):
    _field_mapping = {
        'username': 'username',
        'is_superuser': 'is_superuser',  # v1 uses full name
    }

# api/v2/user.py
class UserTransformMixin_v2(UserTransformMixin_v1):
    _field_mapping = {
        **UserTransformMixin_v1._field_mapping,
        'is_superuser': 'superuser',  # v2 shortened name
        # Only override what changed
    }
```

---

### Story 2.6: Dynamic Version Discovery

**As a** collection developer  
**I want** the system to automatically discover available API versions  
**So that** I can add new versions without updating configuration files

**Acceptance Criteria:**
- Scan filesystem for version directories on startup
- Build registry of available versions and modules
- Support version fallback (if v2.8 not found, try v2.7)
- Provide version compatibility matrix
- No hardcoded version lists

**Implementation:**
```python
# Automatic discovery
registry = APIVersionRegistry('platform/api')

# Available versions discovered from filesystem
print(registry.get_supported_versions())
# Output: ['v1', 'v2', 'v2.1']

# Check module support
print(registry.get_api_versions_for_module('user'))
# Output: ['v1', 'v2']

# Find best version match
best = registry.find_best_api_version('v2.0', 'user')
# Output: 'v2' (closest match)
```

---

## Persona 3: Platform API Developer

### Story 3.1: Update OpenAPI Spec Triggers Regeneration

**As a** platform API developer  
**I want** changes to OpenAPI spec to automatically trigger model regeneration  
**So that** API changes are immediately reflected in the collection

**Acceptance Criteria:**
- OpenAPI spec changes detected in CI/CD pipeline
- Models automatically regenerated
- Tests run against new models
- Pull request created if changes detected
- Clear diff showing what changed in generated code
- Manual review required for transform mixin updates

**CI/CD Workflow:**
```yaml
# .github/workflows/generate-models.yml
name: Generate API Models

on:
  push:
    paths:
      - 'openapi_specs/*.json'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - name: Install generator
        run: pip install datamodel-code-generator
      
      - name: Generate models
        run: ./scripts/generate_api_models.sh
      
      - name: Check for changes
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            echo "Models changed - review needed"
            git diff
          fi
      
      - name: Run tests
        run: pytest tests/
      
      - name: Create PR if changes
        if: steps.check.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v4
        with:
          title: "Update API models from OpenAPI spec"
```

---

### Story 3.2: Version Compatibility Matrix

**As a** platform API developer  
**I want to** see which collection version supports which API versions  
**So that** I can plan deprecations and communicate compatibility to users

**Acceptance Criteria:**
- Automatic discovery of supported versions
- Matrix showing module × API version support
- Documentation generation for compatibility
- Warning when using deprecated endpoints or fields
- Clear migration path documentation

**Example Matrix:**
```
Module         | API v1 | API v2 | API v2.1
---------------|--------|--------|----------
user           |   ✓    |   ✓    |    ✓
organization   |   ✓    |   ✓    |    ✓
team           |   ✗    |   ✓    |    ✓
credential     |   ✗    |   ✗    |    ✓
```

---

## Persona 4: System Administrator

### Story 4.1: Persistent Platform Connection

**As a** system administrator  
**I want** the collection to maintain a persistent connection to the platform  
**So that** playbooks run faster without repeated authentication overhead

**Acceptance Criteria:**
- Manager process maintains connection pool
- Action plugins communicate with manager via multiprocess
- Connection reused across multiple tasks in playbook
- Authentication happens once per playbook run
- Graceful connection handling (retry, timeout, reconnect)
- Connection cleanup on playbook completion

**Architecture:**
```
Playbook Task 1 → Action Plugin → \
Playbook Task 2 → Action Plugin → → Platform Manager (persistent) → Platform API
Playbook Task 3 → Action Plugin → /
```

**Performance Impact:**
- Without persistent connection: ~1-2s per task (auth + request)
- With persistent connection: ~0.2-0.5s per task (request only)
- **50-75% faster playbook execution**

---

### Story 4.2: Clear Error Messages

**As a** system administrator  
**I want** clear, actionable error messages when operations fail  
**So that** I can quickly diagnose and fix issues without deep debugging

**Acceptance Criteria:**
- Validation errors show which field failed and why
- API errors include HTTP status and response body
- Version compatibility warnings are clear
- Suggestions for resolution when possible
- Context about what operation was being performed

**Example Error Messages:**
```
# Validation error
FAILED! => {
    "msg": "Argument validation failed: 
            - Field 'username' is required
            - Field 'email' must be a valid email address
            - Field 'organizations' contains unknown org 'Sales' (available: Engineering, DevOps)"
}

# API error
FAILED! => {
    "msg": "Failed to create user: HTTP 400 Bad Request
            API Response: Username 'jdoe' already exists
            Suggestion: Use state=present to update existing user"
}

# Version compatibility warning
WARNING: API version v2.0 not found for module 'user', falling back to v1
```

---

### Story 4.3: Idempotent Operations

**As a** system administrator  
**I want** all operations to be idempotent  
**So that** I can safely re-run playbooks without creating duplicates or errors

**Acceptance Criteria:**
- Detect if resource already exists
- Compare desired vs existing state
- Only make changes if needed (changed=true only when modified)
- Report unchanged resources (changed=false)
- Handle partial failures gracefully

**Example:**
```yaml
- name: Create user (first run)
  platform.gateway.user:
    username: jdoe
    email: jdoe@example.com
    state: present
  # Result: changed=true, msg="User created"

- name: Create user (second run - no changes)
  platform.gateway.user:
    username: jdoe
    email: jdoe@example.com
    state: present
  # Result: changed=false, msg="User already exists"

- name: Create user (third run - email changed)
  platform.gateway.user:
    username: jdoe
    email: john.doe@example.com
    state: present
  # Result: changed=true, msg="User updated"
```

---

## Cross-Cutting Requirements

### Requirement 1: Code Generation Workflow

**Goal:** Minimize manual coding for new resources

**Process:**
1. **Input 1:** Write Ansible DOCUMENTATION docstring
   - Defines user-facing interface
   - Includes validation rules
   - Single source of truth for Ansible side

2. **Input 2:** Obtain OpenAPI specification
   - Defines API data structures
   - Includes field types, constraints
   - Single source of truth for API side

3. **Generation:** Run automated scripts
   - Generate Ansible dataclass from docstring
   - Generate API dataclasses from OpenAPI spec
   - Generate action plugin skeleton

4. **Manual:** Write custom logic (only what's necessary)
   - Field mapping between Ansible ↔ API
   - Custom transformations (ID lookups, format conversions)
   - Business logic hooks

**Automation Target:**
- ~80% automated (data structures, validation, boilerplate)
- ~20% manual (business logic, transformations)

**Time Savings:**
- Traditional approach: 2-3 days per module
- With generation: 2-4 hours per module
- **90% time reduction**

---

### Requirement 2: Bidirectional Data Transformation (Manager-Side)

**Goal:** Seamlessly transform data between Ansible and API formats while maintaining round-trip contract compliance

**Architecture:** All transformations happen in the **Manager** (not client). Only Ansible dataclasses cross RPC boundary.

**Features:**

1. **Forward Transformation** (Ansible → API) - **Manager Side**
   - Manager receives Ansible-formatted data from client
   - Transforms to version-appropriate API format
   - Handles field renames (organizations → organization_ids)
   - Performs ID lookups (names → IDs)
   - Splits data across multiple endpoints if needed
   - Uses version-specific transform mixin rules

2. **Reverse Transformation** (API → Ansible) - **Manager Side**
   - Manager receives API response
   - Transforms back to Ansible format (round-trip contract)
   - Field names match DOCUMENTATION (not API field names)
   - Field types match DOCUMENTATION (list[str] not list[int])
   - Converts IDs back to names (reverse lookups)
   - Returns Ansible dataclass to client
   - **Output format matches input format**

3. **Round-Trip Contract Enforcement**
   - DOCUMENTATION defines contract for both input AND output
   - Output uses same field names/types as input
   - Manager ensures: input format → (API internal) → output format
   - API format details never exposed to client
   - Consistent across all API versions

4. **Context-Aware Transformations** (Manager Has Full Context)
   - Transformations access PlatformManager instance
   - Can perform API lookups during transform (names ↔ IDs)
   - Cache results for performance
   - Access to persistent session
   - Knowledge of API version

5. **Nested Object Support**
   - Dot notation for nested fields (user.address.city)
   - Recursive transformation of complex structures
   - Handle arrays of objects
   - Suboptions transformed recursively

**Transform Location:**
```
CLIENT (Action Plugin)                MANAGER (Persistent Service)
----------------------                ----------------------------
- Validate input                      - Forward transform ✓
- Create Ansible dataclass            - API calls
- Send via RPC →                      - Reverse transform ✓
- Validate output                     - Return Ansible dataclass
- Format return                       

TRANSFORM HAPPENS IN MANAGER          CLIENT NEVER SEES API FORMAT
```

**Example Flow:**
```python
# CLIENT: Create and send
ansible_user = AnsibleUser(
    username='jdoe',
    organizations=['Engineering', 'DevOps']  # Names
)
manager.execute('create', 'user', ansible_user)

# MANAGER: Transform forward
context = {'manager': self, 'session': self.session, 'cache': self.cache}
api_user = ansible_user.to_api(context)
# api_user.organization_ids = [1, 2]  # IDs looked up internally

# MANAGER: Call API
response = self.session.post('/api/gateway/v1/users/', json=asdict(api_user))

# MANAGER: Transform reverse
api_result = APIUser(**response.json())
ansible_result = api_result.to_ansible(context)
# ansible_result.organizations = ['Engineering', 'DevOps']  # Names restored

# CLIENT: Receive (same format as input)
# ansible_result.organizations = ['Engineering', 'DevOps']  ✓
```

**Why Manager-Side Transforms:**
- Manager has API connection for lookups
- Manager knows API version
- Manager has persistent cache
- Client stays thin and version-agnostic
- Clean RPC protocol (only Ansible format)
- Follows existing multiprocess weather service pattern

---

### Requirement 3: Dynamic Version Management

**Goal:** Support multiple API versions without hardcoding version lists

**Features:**

1. **Filesystem-Based Discovery**
   - Scan `platform/api/` directory on startup
   - Discover version directories (v1/, v2/, v2.1/)
   - Build registry of available versions and modules
   - No configuration files needed

2. **Version Detection**
   - Query platform for current API version
   - Auto-select appropriate implementation
   - Warn if exact version not found
   - Fall back to closest compatible version

3. **Version Fallback Strategy**
   - Try exact match first (v2.5 requested → v2.5)
   - Try closest lower version (v2.5 requested → v2.4 if v2.5 missing)
   - Try closest higher version (v2.5 requested → v2.6 if no lower found)
   - Clear warning to user about fallback

4. **Per-Module Version Support**
   - Each module can support different versions
   - `user` might exist in v1, v2, v2.1
   - `team` might only exist in v2, v2.1
   - Registry tracks module × version matrix

5. **Easy Version Addition**
   - Create new directory: `platform/api/v3/`
   - Add module files: `v3/user.py`
   - System automatically discovers on next run
   - No code changes required

**API:**
```python
# Registry usage
registry = APIVersionRegistry('platform/api')

# What versions exist?
registry.get_supported_versions()
# → ['v1', 'v2', 'v2.1']

# What modules exist in v2?
registry.get_modules_for_api_version('v2')
# → ['user', 'organization', 'team']

# What versions support user module?
registry.get_api_versions_for_module('user')
# → ['v1', 'v2', 'v2.1']

# Find best match
registry.find_best_api_version('v2.3', 'user')
# → 'v2.1' (closest lower version)
```

---

### Requirement 4: Architecture Separation

**Goal:** Clean separation of concerns with clear boundaries

**Layers:**

```
┌─────────────────────────────────────────┐
│   Ansible Playbook (User Interface)    │
│   - Stable YAML interface               │
│   - Version-agnostic                    │
└──────────────────┬──────────────────────┘
                   │
╔══════════════════▼══════════════════════╗
║   CLIENT (Action Plugin - Thin)        ║
║─────────────────────────────────────────║
║ 1. Validate input (ArgumentSpec)       ║
║ 2. Create Ansible dataclass            ║
║ 3. Send to manager (RPC) ───────────┐  ║
║ 4. Receive Ansible dataclass  ◄─────│──║
║ 5. Validate output (ArgumentSpec)   │  ║
║ 6. Format return dict               │  ║
║                                     │  ║
║ NO transformations                  │  ║
║ NO API knowledge                    │  ║
║ NO version resolution               │  ║
╚═════════════════════════════════════╪══╝
                                      │
                     RPC Boundary     │
                (Ansible dataclass)   │
                                      │
╔═════════════════════════════════════▼══╗
║   MANAGER (Persistent Service - Heavy) ║
║─────────────────────────────────────────║
║ 1. Receive Ansible dataclass           ║
║ 2. Detect/cache API version             ║
║ 3. Load version-specific classes        ║
║ 4. FORWARD TRANSFORM ───────────┐       ║
║    Ansible → API                │       ║
║    (names → IDs, field renames) │       ║
║ 5. Execute API calls            │       ║
║    (multi-endpoint support)     │       ║
║ 6. REVERSE TRANSFORM ◄──────────┘       ║
║    API → Ansible                        ║
║    (IDs → names, field renames)         ║
║ 7. Return Ansible dataclass ────────┘   ║
║                                         ║
║ Has: Session, Cache, Version, Context   ║
║ Generic: Works for ALL resources        ║
╚═════════════════════════════════════════╝
                   │
┌──────────────────▼──────────────────────┐
│   Platform API (External System)        │
│   - REST API endpoints                  │
│   - Version-specific schemas            │
│   - Authentication                      │
└─────────────────────────────────────────┘

KEY:
━━━ = Client-side processing
─── = Manager-side processing
RPC = Only Ansible dataclasses cross this boundary
```

**Key Principles:**
- Each layer has a single responsibility
- Clear interfaces between layers
- Client (action plugin) is thin and stateless
- Manager (persistent service) is heavy and stateful
- Only Ansible dataclasses cross RPC boundary
- Manager handles ALL transformations
- Follows proven multiprocess weather service pattern
- Each layer can be tested independently

---

### Requirement 5: Round-Trip Validation Strategy

**Goal:** Multi-layer validation with symmetric input/output checking using single ArgumentSpec

**Key Principle:** Use same ArgumentSpec (from DOCUMENTATION) for both input and output validation

**Validation Layers:**

**1. Client-Side Input Validation** (Action Plugin)
   - Generate ArgumentSpec from DOCUMENTATION string
   - Validate user arguments against spec
   - Check types, required fields, choices, constraints
   - Happens before sending to manager
   - Fast fail with clear error messages

**2. Dataclass Construction** (Client)
   - Create Ansible dataclass from validated input
   - Type hints provide additional compile-time checking
   - IDE support for development

**3. Manager-Side Transformation** (Manager)
   - Forward transform applies business logic
   - Can query API for validation (org exists, etc.)
   - Has full context for validation
   - Not strictly validation but enforces constraints

**4. API Validation** (Platform)
   - Final validation by API itself
   - Authoritative for API-specific rules
   - Catches edge cases

**5. Manager-Side Reverse Transform** (Manager)
   - Transforms API response back to Ansible format
   - Ensures output matches input contract
   - Performs reverse lookups (IDs → names)

**6. Client-Side Output Validation** (Action Plugin) - **Safety Check**
   - **Reuse same ArgumentSpec from DOCUMENTATION**
   - Validate manager response matches expected format
   - Check field names, types match DOCUMENTATION
   - Catches bugs in manager transforms
   - Ensures contract compliance

**Symmetric Validation:**
```python
# SINGLE ARGSPEC (from DOCUMENTATION)
argspec = build_argspec(DOCUMENTATION)

# Used for INPUT validation
validated_input = validate_data(user_args, argspec, direction='input')

# Used for OUTPUT validation (same spec!)
validated_output = validate_data(manager_response, argspec, direction='output')
```

**Validation Flow:**
```
┌──────────────────────────────────────────────┐
│  DOCUMENTATION (Single Source)               │
│  - Defines field contract                    │
│  - Used for input AND output                 │
└────────────┬─────────────────────────────────┘
             │
             ├─→ Generate ArgumentSpec
             │
    ┌────────┴────────┐
    ↓                 ↓
┌─────────┐       ┌─────────┐
│ INPUT   │       │ OUTPUT  │
│Validate │       │Validate │
└────┬────┘       └────┬────┘
     │                 ↑
     ↓                 │
  Client           Manager
  Creates    →→→   Transforms  →→→  Returns
  Ansible          (API hidden)     Ansible
  Dataclass                         Dataclass
```

**Example Implementation:**
```python
class ActionModule(BaseResourceActionPlugin):
    def run(self, tmp=None, task_vars=None):
        # Get single argspec from DOCUMENTATION
        argspec = self._build_argspec_from_docs()
        
        # 1. INPUT VALIDATION
        validated_input = self._validate_data(
            self._task.args,
            argspec,
            direction='input'
        )
        
        # 2. Create Ansible dataclass and call manager
        ansible_data = AnsibleUser(**validated_input)
        result = manager.execute('create', 'user', ansible_data)
        
        # 3. OUTPUT VALIDATION (same argspec!)
        validated_output = self._validate_data(
            asdict(result),
            argspec,
            direction='output'
        )
        
        # 4. Return to user
        return {
            'changed': True,
            'failed': False,
            'msg': 'User created',
            **validated_output
        }
```

**Benefits:**
- Single source of truth (DOCUMENTATION)
- Symmetric contract (input format = output format)
- Catches manager bugs early
- Type safety at runtime
- Clear error messages at both ends
- No separate RETURN section needed

---

## Success Metrics

### For Ansible Playbook Authors:
- ✅ Write once, works across API versions (no playbook changes needed)
- ✅ Clear validation errors at task execution (fail fast with actionable messages)
- ✅ 50-75% faster playbook execution (persistent connections)
- ✅ Idempotent operations (safe to re-run)
- ✅ Simple, stable interface (no API details exposed)
- ✅ Round-trip data contract (output matches input format - predictable and reliable)

### For Collection Developers:
- ✅ New resource in <2 hours (vs 2-3 days manual coding)
- ✅ 80% code generation, 20% custom logic
- ✅ API version update in <1 hour (regenerate + test)
- ✅ Clear patterns and conventions
- ✅ Easy to test and maintain
- ✅ Single DOCUMENTATION defines input AND output contract
- ✅ Manager is generic - no resource-specific code needed
- ✅ Transform logic isolated in dataclass mixins

### For Platform Team:
- ✅ OpenAPI spec is single source of truth
- ✅ Automated compatibility testing
- ✅ Clear deprecation path for old endpoints
- ✅ Version compatibility matrix auto-generated
- ✅ Changes propagate automatically to collection

### For System Administrators:
- ✅ Reliable, predictable behavior
- ✅ Clear error messages with resolution steps
- ✅ Fast execution (persistent connections)
- ✅ Works across platform versions
- ✅ Production-ready error handling

---

## Technical Stack

### Core Technologies:
- **Python 3.10+** - Type hints, dataclasses
- **Ansible 2.14+** - Action plugins, ArgumentSpecValidator
- **OpenAPI 3.0+** - API specifications
- **datamodel-code-generator** - OpenAPI → Python dataclasses
- **PyYAML** - Docstring parsing
- **multiprocessing** - Persistent manager connections

### Generated Code:
- **Ansible Dataclasses** - From DOCUMENTATION strings
- **API Dataclasses** - From OpenAPI specs
- **Action Plugin Skeletons** - Basic structure
- **ArgumentSpec** - From DOCUMENTATION strings

### Manual Code:
- **Transform Mixins** - Field mappings, business logic
- **BaseTransformMixin** - Universal transformation logic
- **PlatformManager** - Connection management
- **Action Plugin Logic** - State management, idempotency

---

## Future Enhancements

### Phase 2: Enhanced Features
- **Check Mode Support** - Dry run without making changes
- **Diff Mode** - Show what would change before applying
- **Bulk Operations** - Create multiple resources in one task
- **Change Tracking** - Track which fields changed
- **Performance Metrics** - Timing for each operation

### Phase 3: Advanced Capabilities
- **Inventory Plugin** - Discover resources as inventory
- **Caching Layer** - Cache lookups for performance
- **Webhook Support** - Listen for platform events
- **Import/Export** - Bulk resource management
- **Resource Dependencies** - Automatic ordering

### Phase 4: Developer Experience
- **CLI Tool** - Generate new modules from command line
- **VS Code Extension** - Syntax highlighting, validation
- **Testing Framework** - Mock platform for testing
- **Documentation Generator** - Auto-generate user docs
- **Migration Tool** - Help migrate between versions

---

## Appendix: Example Directory Structure

```
platform/
├── common/
│   ├── __init__.py
│   ├── base_transform.py          # BaseTransformMixin
│   ├── types.py                   # Shared types (EndpointOperation)
│   ├── registry.py                # Version/OpenAPI registry
│   └── loader.py                  # Dynamic class loader
│
├── ansible/
│   ├── action_plugins/
│   │   ├── __init__.py
│   │   ├── base_action.py         # Base action plugin
│   │   ├── user.py                # User action plugin
│   │   ├── organization.py        # Organization action plugin
│   │   └── team.py                # Team action plugin
│   │
│   ├── dataclasses/
│   │   ├── __init__.py
│   │   ├── user.py                # AnsibleUser (generated)
│   │   ├── organization.py        # AnsibleOrganization (generated)
│   │   └── team.py                # AnsibleTeam (generated)
│   │
│   └── module_docs/
│       ├── user.py                # DOCUMENTATION string
│       ├── organization.py        # DOCUMENTATION string
│       └── team.py                # DOCUMENTATION string
│
├── api/
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── generated/
│   │   │   └── models.py          # Generated from OpenAPI
│   │   ├── user.py                # UserTransformMixin_v1 + APIUser_v1
│   │   ├── organization.py        # OrgTransformMixin_v1 + APIOrg_v1
│   │   └── team.py                # TeamTransformMixin_v1 + APITeam_v1
│   │
│   └── v2/
│       ├── __init__.py
│       ├── generated/
│       │   └── models.py          # Generated from OpenAPI
│       ├── user.py                # UserTransformMixin_v2 + APIUser_v2
│       └── organization.py        # OrgTransformMixin_v2 + APIOrg_v2
│
├── manager/
│   ├── __init__.py
│   ├── platform_manager.py        # PlatformManager (persistent connection)
│   └── connection_pool.py         # Connection pooling
│
├── openapi_specs/
│   ├── gateway-v1.json            # OpenAPI spec for v1
│   └── gateway-v2.json            # OpenAPI spec for v2
│
├── scripts/
│   ├── generate_ansible_dataclasses.py
│   └── generate_api_models.sh
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── REQUIREMENTS.md                # This document
├── DESIGN.md                      # Technical design details
├── README.md                      # User documentation
└── requirements.txt               # Python dependencies
```

---

## Document Metadata

- **Version:** 1.0
- **Last Updated:** 2025-11-12
- **Status:** Draft
- **Maintainer:** Platform Team

