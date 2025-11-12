# Agent Instructions for Ansible Platform Collection

## Purpose

This document guides AI agents working with developers on this project. It helps determine the developer's role and provides tailored Q&A walkthroughs for completing their work.

---

## Quick Start for AI Agents

When a developer starts working with you:

1. **Determine their role** using the Role Identification section below
2. **Load the appropriate implementation guide(s)** into context
3. **Follow the persona-specific walkthrough** for their role
4. **Apply coding standards** consistently throughout

---

## Role Identification

Ask the developer these questions to determine their persona:

### Question 1: What are you working on?

**A)** Building the core framework (BaseTransformMixin, Manager, Registry, Loader, etc.)
→ **PERSONA: Foundation Builder** (see section below)

**B)** Adding a new resource module (user, organization, team, etc.)
→ **PERSONA: Feature Developer** (see section below)

**C)** Something else (debugging, refactoring, docs)
→ Ask clarifying questions to understand the task

### Question 2: Does the foundation exist yet?

Check for these key files:
- `plugins/plugin_utils/platform/base_transform.py`
- `plugins/plugin_utils/manager/platform_manager.py`
- `tools/generators/generate_ansible_dataclasses.py`

**If NO**: Foundation Builder persona is needed first
**If YES**: Feature Developer persona can proceed

---

## PERSONA 1: Foundation Builder

### When to Use This Persona

- Developer is building the framework from scratch
- Core components don't exist yet
- Setting up code generation tools

### Required Context

Load these documents into your context before starting:

1. **REQUIREMENTS.md** - Understand architecture decisions
2. **IMPLEMENTATION_FOUNDATION.md** - Complete implementation guide
3. **IMPLEMENTATION_GENERATORS.md** - Code generation tools

### Q&A Walkthrough: Foundation Builder

#### Phase 1: Understanding the Architecture

**Agent Question 1**: "Have you reviewed the REQUIREMENTS.md document? Let me summarize the key architectural decisions for you."

*Wait for response, then provide summary from REQUIREMENTS.md*

**Agent Question 2**: "The foundation consists of several core components:
- BaseTransformMixin (universal transformation logic)
- APIVersionRegistry (dynamic version discovery)
- DynamicClassLoader (runtime class loading)
- PlatformManager (persistent service)
- RPC Client (client communication)

Which component would you like to start with, or should we build them in the recommended order?"

**Recommended order**:
1. Shared types (EndpointOperation)
2. BaseTransformMixin
3. APIVersionRegistry
4. DynamicClassLoader
5. PlatformManager
6. RPC Client
7. Base Action Plugin pattern

---

#### Phase 2: Building Core Components

**For Each Component**:

**Agent Question**: "I'm going to implement [COMPONENT_NAME] based on the specification in IMPLEMENTATION_FOUNDATION.md. This component will:
- [Brief description of purpose]
- [Key features]
- [Location: file path]

Should I proceed with the full implementation?"

*Wait for confirmation*

**Agent Action**:
1. Read the relevant section from IMPLEMENTATION_FOUNDATION.md
2. Create the file with complete implementation
3. Include:
   - Google-style docstrings
   - Type hints on all functions/methods
   - Comprehensive inline comments
   - Error handling

**Agent Question**: "I've implemented [COMPONENT_NAME]. Let me show you the key parts:"

*Display critical code sections*

"Would you like me to:
a) Proceed to the next component?
b) Add tests for this component?
c) Refine this implementation?"

---

#### Phase 3: Setting Up Code Generators

**Agent Question**: "Now let's set up the code generation tools. These will automate creating dataclasses from:
1. Ansible DOCUMENTATION strings → Ansible dataclasses
2. OpenAPI specifications → API dataclasses

Should I implement both generators?"

*Wait for response*

**Agent Action**:
1. Read IMPLEMENTATION_GENERATORS.md
2. Create `tools/generators/generate_ansible_dataclasses.py`
3. Create `tools/generators/generate_api_models.sh`
4. Create directory structure: `tools/openapi_specs/`

**Agent Question**: "The generators are implemented. Would you like me to:
a) Test them with a sample resource (like 'user')?
b) Move on to testing the foundation?
c) Create additional helper scripts?"

---

#### Phase 4: Foundation Testing

**Agent Question**: "Let's verify the foundation works. I'll create a test script that:
1. Spawns the PlatformManager
2. Verifies version detection
3. Tests the registry and loader

Should I create this test script?"

*If yes, create `tools/test_manager.py` from IMPLEMENTATION_FOUNDATION.md*

**Agent Question**: "To run the test, you'll need to:
```bash
cd ansible.platform
python tools/test_manager.py
```

Would you like me to:
a) Add more comprehensive tests?
b) Create a simple test resource to verify end-to-end flow?
c) Move on to documentation?"

---

#### Phase 5: Foundation Complete

**Agent Statement**: "🎉 The foundation is complete! You've built:
✅ BaseTransformMixin - Universal transformation logic
✅ APIVersionRegistry - Dynamic version discovery
✅ DynamicClassLoader - Runtime class loading
✅ PlatformManager - Persistent service
✅ RPC Client - Client communication
✅ Code Generators - Automated dataclass creation

Next steps:
1. Test with a real resource (User, Organization)
2. Add resources as a Feature Developer (see PERSONA 2)
3. Review IMPLEMENTATION_FEATURES.md for adding resources

Would you like to add your first resource now?"

*If yes, switch to Feature Developer persona*

---

## PERSONA 2: Feature Developer

### When to Use This Persona

- Foundation already exists
- Adding a new resource module (user, organization, team, etc.)
- Extending existing resources

### Prerequisites Check

**Agent Action**: Verify these files exist:
- `plugins/plugin_utils/platform/base_transform.py`
- `plugins/plugin_utils/manager/platform_manager.py`
- `tools/generators/generate_ansible_dataclasses.py`
- `tools/generators/generate_api_models.sh`

**If missing**: "The foundation doesn't exist yet. We need to build it first using the Foundation Builder persona. Should we do that now?"

### Required Context

Load these documents:

1. **IMPLEMENTATION_FEATURES.md** - Step-by-step resource guide
2. **IMPLEMENTATION_FOUNDATION.md** - (Reference only, for understanding)
3. **REQUIREMENTS.md** - (Reference only, for architecture understanding)

### Q&A Walkthrough: Feature Developer

#### Phase 1: Resource Planning

**Agent Question 1**: "What resource are you adding? (e.g., user, organization, team, role)"

*Store response as RESOURCE_NAME*

**Agent Question 2**: "Let me ask a few questions about this resource:

a) **Complexity**: Does this resource require:
   - Simple 1:1 field mappings only? (like 'organization')
   - Name ↔ ID transformations? (like converting org names to IDs)
   - Multiple API endpoints? (like create user, then add to orgs)
   - All of the above?

b) **API Version**: Which API version are you targeting? (e.g., v1, v2)

c) **OpenAPI Spec**: Do you have the OpenAPI spec file? What's its location?"

*Store responses*

**Agent Analysis**: Based on your answers:
- Complexity: [Simple/Medium/Complex]
- Estimated time: [1-2 hours / 2-3 hours / 3-4 hours]
- Similar example: [Point to Organization or User example in IMPLEMENTATION_FEATURES.md]

---

#### Phase 2: Documentation

**Agent Question**: "Let's start by defining the user-facing interface. I'll help you create the DOCUMENTATION string.

Key principles:
- Use user-friendly field names (e.g., 'organization_names' not 'org_ids')
- Mark read-only fields clearly (e.g., 'id', 'created')
- Mark write-only fields (e.g., 'password')
- Provide clear descriptions

Should I create a DOCUMENTATION template for the '{RESOURCE_NAME}' resource?"

*Wait for confirmation*

**Agent Action**:
1. Create `plugins/plugin_utils/docs/{RESOURCE_NAME}.py`
2. Generate DOCUMENTATION template with common fields
3. Ask for resource-specific fields

**Agent Question**: "Here's the DOCUMENTATION template I created:

[Show template]

What additional fields does the {RESOURCE_NAME} resource need?"

*Iterate on fields until complete*

---

#### Phase 3: Generate Dataclasses

**Agent Question**: "Now I'll generate the dataclasses. This is automated:

1. Ansible dataclass from DOCUMENTATION
2. API dataclass from OpenAPI spec

Should I run the generators now?"

*If yes:*

**Agent Action**:
```bash
# Generate Ansible dataclass
python tools/generators/generate_ansible_dataclasses.py \
    plugins/plugin_utils/docs/{RESOURCE_NAME}.py

# Generate API models (if needed)
bash tools/generators/generate_api_models.sh
```

**Agent Question**: "Generated:
✅ `plugins/plugin_utils/ansible_models/{RESOURCE_NAME}.py`
✅ `plugins/plugin_utils/api/v{VERSION}/generated/models.py`

I'll show you the generated Ansible dataclass:

[Display generated class]

Does this look correct? Should I proceed?"

---

#### Phase 4: Transform Mixin (The Core Work)

**Agent Question**: "Now for the important part - the Transform Mixin. This is where we define:
1. **Field Mapping**: How Ansible fields map to API fields
2. **Transformations**: Custom logic (e.g., names → IDs)
3. **Endpoint Operations**: Which API endpoints to call

Based on your earlier answers, this resource needs:
[List of transformations and endpoints needed]

Let me create the transform mixin. Should I start with a simple template and we'll build it up?"

*Wait for confirmation*

**Agent Action**:
1. Create `plugins/plugin_utils/api/v{VERSION}/{RESOURCE_NAME}.py`
2. Start with basic structure

**Agent Question**: "Here's the basic structure:

```python
class {ResourceName}TransformMixin_v{VERSION}(BaseTransformMixin):
    _field_mapping = {
        # TODO: Add field mappings
    }
    
    _transform_registry = {
        # TODO: Add custom transforms
    }
    
    @classmethod
    def get_endpoint_operations(cls):
        # TODO: Define API endpoints
        pass
```

Let's fill this in step by step. Starting with field mappings:

For simple 1:1 mappings (field name same in Ansible and API), list the fields:"

*Iterate through fields*

**For Complex Transformations**:

**Agent Question**: "I see '{FIELD_NAME}' requires transformation (names → IDs).

I'll add:
1. Field mapping with transform references
2. Transform functions in the registry
3. Lookup helpers in PlatformManager if needed

Here's the mapping:

```python
'{FIELD_NAME}': {
    'api_field': '{API_FIELD_NAME}',
    'forward_transform': 'names_to_ids',
    'reverse_transform': 'ids_to_names',
}
```

Does this match the API structure?"

**For Multiple Endpoints**:

**Agent Question**: "This resource requires multiple API calls. Let me map out the flow:

1. Create {RESOURCE_NAME} (POST /api/.../resources/)
2. [Additional operations]

I'll configure these with dependency ordering. Here's the plan:

```python
'create': EndpointOperation(
    path='/api/gateway/v{VERSION}/{RESOURCES}/',
    method='POST',
    fields=[...],
    order=1
),
'sub_operation': EndpointOperation(
    path='/api/gateway/v{VERSION}/{RESOURCES}/{id}/...',
    method='POST',
    fields=[...],
    depends_on='create',
    order=2
)
```

Does this match the API flow?"

---

#### Phase 5: Action Plugin

**Agent Question**: "The transform mixin is complete! Now for the action plugin - this is mostly boilerplate.

I'll create `plugins/action/{RESOURCE_NAME}.py` following the standard pattern:
1. Import generated Ansible dataclass
2. Inherit from base action plugin pattern
3. Set MODULE_NAME = '{RESOURCE_NAME}'

Should I create this now?"

*If yes:*

**Agent Action**:
1. Create action plugin file
2. Use standard template from IMPLEMENTATION_FEATURES.md
3. Customize for resource name

**Agent Question**: "Action plugin created. Here's the structure:

[Show key parts]

This plugin will:
✅ Validate input against DOCUMENTATION
✅ Spawn/connect to manager
✅ Execute operations via RPC
✅ Validate output
✅ Return results

Ready to test?"

---

#### Phase 6: Testing

**Agent Question**: "Let's create a test playbook. I'll set up:

```yaml
- name: Test {ResourceName} Management
  hosts: localhost
  tasks:
    - name: Create {RESOURCE_NAME}
      ansible.platform.{RESOURCE_NAME}:
        # fields
      register: result
    
    - name: Verify creation
      assert:
        that:
          - result is not failed
          - result.changed
```

What scenarios should we test?
a) Create
b) Update
c) Delete
d) All of the above"

*Create test playbook based on response*

**Agent Question**: "Test playbook created at `tests/integration/test_{RESOURCE_NAME}.yml`.

To run:
```bash
ansible-playbook tests/integration/test_{RESOURCE_NAME}.yml -i inventory/hosts.yml
```

Note: You'll need:
- `gateway_url` in inventory
- Valid API credentials

Would you like me to:
a) Create the inventory template?
b) Add more test scenarios?
c) Create unit tests for the transform mixin?"

---

#### Phase 7: Feature Complete

**Agent Statement**: "🎉 The {RESOURCE_NAME} resource is complete!

You've created:
✅ DOCUMENTATION (`docs/{RESOURCE_NAME}.py`)
✅ Ansible dataclass (`ansible_models/{RESOURCE_NAME}.py`) - Generated
✅ API dataclass (`api/v{VERSION}/generated/models.py`) - Generated
✅ Transform mixin (`api/v{VERSION}/{RESOURCE_NAME}.py`) - Your core work
✅ Action plugin (`action/{RESOURCE_NAME}.py`)
✅ Test playbook (`tests/integration/test_{RESOURCE_NAME}.yml`)

Next steps:
1. Run the test playbook
2. Refine based on results
3. Add to collection documentation
4. Repeat for next resource!

Summary of what you built:
- Time spent: ~[estimate based on complexity]
- Lines of custom code (non-generated): ~[estimate]
- Reusable patterns: [list any new patterns created]

Would you like to:
a) Add another resource?
b) Refine this resource?
c) Add more tests?
d) Update documentation?"

---

## Common Agent Patterns

### Pattern: Asking for Information vs. Looking It Up

**DO**: Check existing files before asking:
```python
# Check if foundation exists
base_transform_exists = Path('plugins/plugin_utils/platform/base_transform.py').exists()
```

**DON'T**: Ask user about things you can discover:
```
# BAD: "Does the foundation exist?"
# GOOD: "I see the foundation exists. Let's add a feature!"
```

### Pattern: Progressive Disclosure

**DO**: Build complexity gradually:
1. Start with simple field mappings
2. Add transformations
3. Add multi-endpoint logic
4. Add error handling

**DON'T**: Dump entire complex implementation at once

### Pattern: Show, Don't Tell

**DO**: Show code snippets:
```python
"Here's the mapping I'll add:
```python
'username': 'username',  # 1:1 mapping
'organizations': {       # Complex mapping
    'api_field': 'org_ids',
    'forward_transform': 'names_to_ids',
}
```
Does this look right?"
```

**DON'T**: Just describe abstractly:
```
"I'll add the field mappings now."
```

### Pattern: Reference the Guides

**DO**: Point to relevant examples:
```
"This is similar to the User resource example in IMPLEMENTATION_FEATURES.md 
(section: Complete Example: User Resource). I'll follow that pattern."
```

**DON'T**: Reinvent patterns that are already documented

### Pattern: Validate Assumptions

**DO**: Confirm before proceeding with complex work:
```
"Based on the OpenAPI spec, I see the API uses 'org_ids' (list of integers) 
but your DOCUMENTATION uses 'organizations' (list of names). I'll need to add
a name→ID transformation. Correct?"
```

**DON'T**: Make assumptions silently

---

## Coding Standards

### Always Follow These Rules

1. **Type Hints**: Every function/method must have type hints
   ```python
   def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
       ...
   ```

2. **Google-Style Docstrings**: Every module, class, and function
   ```python
   def example_function(param1: str, param2: int) -> bool:
       """One-line summary.
       
       Longer description if needed.
       
       Args:
           param1: Description of param1
           param2: Description of param2
       
       Returns:
           Description of return value
       
       Raises:
           ValueError: Description of when this is raised
       """
   ```

3. **Imports**: Organized and explicit
   ```python
   # Standard library
   import os
   from pathlib import Path
   from typing import Dict, List, Optional, Any
   
   # Third-party
   import requests
   
   # Local
   from ..platform.base_transform import BaseTransformMixin
   ```

4. **Error Handling**: Explicit and informative
   ```python
   try:
       result = operation()
   except SpecificError as e:
       logger.error(f"Operation failed: {e}", exc_info=True)
       raise ValueError(f"Failed to ...: {e}") from e
   ```

---

## Using the Implementation Guides

### When to Load Each Guide

**IMPLEMENTATION_FOUNDATION.md**:
- Building core components
- Understanding the framework
- Reference for how things work

**IMPLEMENTATION_GENERATORS.md**:
- Setting up code generation
- Understanding what gets generated
- Regenerating after changes

**IMPLEMENTATION_FEATURES.md**:
- Adding new resources
- Primary guide for feature developers
- Examples and patterns

**REQUIREMENTS.md**:
- Understanding architectural decisions
- Reference for "why" questions
- High-level requirements

**IMPLEMENTATION_OVERVIEW.md**:
- Quick orientation
- Deciding which guide to use
- Understanding document relationships

### How to Reference

When referencing guides in conversation:

```
"According to IMPLEMENTATION_FEATURES.md section 'Complete Example: User Resource', 
the transform mixin should include..."
```

Or:

```
"Let me check IMPLEMENTATION_FOUNDATION.md for the BaseTransformMixin 
implementation details..."
```

### Loading Strategy

**For Foundation Work**:
1. Load REQUIREMENTS.md first (architecture context)
2. Load IMPLEMENTATION_FOUNDATION.md (implementation details)
3. Load IMPLEMENTATION_GENERATORS.md (tools)

**For Feature Work**:
1. Load IMPLEMENTATION_FEATURES.md first (main guide)
2. Reference IMPLEMENTATION_FOUNDATION.md as needed
3. Reference REQUIREMENTS.md for "why" questions

---

## Example Agent Conversation Flow

### Foundation Builder Example

```
AGENT: "Hi! I see you're working on the Ansible Platform Collection. 
Let me check what exists..."

[Agent checks filesystem]

AGENT: "I don't see the core framework components yet. Are you building 
the foundation? (Y/N)"

USER: "Yes"

AGENT: "Great! I'll help you build the foundation. Let me load the 
implementation guides into my context..."

[Agent loads REQUIREMENTS.md, IMPLEMENTATION_FOUNDATION.md, 
IMPLEMENTATION_GENERATORS.md]

AGENT: "I've reviewed the architecture. The foundation consists of 
6 main components. We'll build them in this order:
1. Shared types (EndpointOperation)
2. BaseTransformMixin
3. APIVersionRegistry
4. DynamicClassLoader
5. PlatformManager
6. RPC Client

This will take about 8-12 hours total. Ready to start with Shared Types?"

[Continue with Foundation Builder walkthrough...]
```

### Feature Developer Example

```
AGENT: "Hi! I see the foundation exists. Are you adding a new resource 
module? (Y/N)"

USER: "Yes, I want to add the 'team' resource"

AGENT: "Perfect! Let me load the feature guide... 

[Agent loads IMPLEMENTATION_FEATURES.md]

AGENT: "I'll help you add the 'team' resource. A few questions:

1. Does 'team' require name→ID transformations (e.g., converting 
   member names to IDs)?
2. Does it require multiple API endpoints (e.g., create team, 
   then add members)?
3. Which API version? (v1, v2)"

USER: "Yes to both, and v1"

AGENT: "Got it! This is a complex resource (like the User example). 
Estimated time: 3-4 hours. Let's start with the DOCUMENTATION string..."

[Continue with Feature Developer walkthrough...]
```

---

## Troubleshooting Guide for Agents

### Issue: Developer Unclear About Role

**Solution**: Ask direct questions:
```
"Are you:
A) Building the framework from scratch
B) Adding a new resource to an existing framework
C) Something else"
```

### Issue: Foundation Partially Complete

**Solution**: Audit what exists:
```
"I see some foundation components exist:
✅ BaseTransformMixin
✅ APIVersionRegistry
❌ PlatformManager (missing)
❌ RPC Client (missing)

Should we complete the foundation, or work with what exists?"
```

### Issue: Developer Wants to Skip Steps

**Solution**: Explain dependencies:
```
"I understand you want to jump to adding resources, but the foundation 
must be complete first. Without PlatformManager, the action plugins 
can't communicate with the service. 

Can we quickly build the remaining foundation components? It'll take 
about 2-3 hours and then you'll be unblocked."
```

### Issue: Generated Code Has Errors

**Solution**: Identify and fix:
```
"The generator produced code with [ISSUE]. This can happen when 
[REASON]. I'll fix it by [SOLUTION]. 

This is why we review generated code before proceeding."
```

---

## Success Metrics

Track these to gauge progress:

### Foundation Builder Success
- ✅ All core components implemented
- ✅ Test manager script runs
- ✅ Code generators work
- ✅ First test resource works end-to-end

### Feature Developer Success
- ✅ DOCUMENTATION complete and clear
- ✅ Dataclasses generated correctly
- ✅ Transform mixin handles all mappings
- ✅ Action plugin validates input/output
- ✅ Test playbook passes

---

## Final Notes for AI Agents

### Remember

1. **Be proactive**: Check files, load guides, suggest next steps
2. **Be thorough**: Complete implementations, not sketches
3. **Be clear**: Show code, explain decisions, validate assumptions
4. **Be patient**: Build complexity gradually
5. **Be helpful**: Point to examples, reference docs, explain patterns

### Your Goal

Help the developer successfully:
- Build a robust foundation, OR
- Add high-quality resource modules

By being a knowledgeable, patient, thorough coding partner who references the comprehensive implementation guides.