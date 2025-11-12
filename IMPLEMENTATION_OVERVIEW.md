# Implementation Guides Overview

## Three Guides for Different Roles

This project includes three detailed implementation guides, each targeting a specific developer role:

### 1. [IMPLEMENTATION_FOUNDATION.md](IMPLEMENTATION_FOUNDATION.md)
**For: Framework/Infrastructure Developers**

Build the core framework that all features depend on:
- ✅ BaseTransformMixin (universal transformation logic)
- ✅ Shared types (EndpointOperation, etc.)
- ✅ APIVersionRegistry (dynamic version discovery)
- ✅ DynamicClassLoader (runtime class loading)
- ✅ PlatformManager (persistent service)
- ✅ RPC Client (client-server communication)
- ✅ Base Action Plugin pattern

**Build this ONCE**, use it for all resources.

---

### 2. [IMPLEMENTATION_GENERATORS.md](IMPLEMENTATION_GENERATORS.md)
**For: Framework Developers (Setup)**

Set up code generation tools:
- ✅ Ansible dataclass generator (DOCUMENTATION → Python)
- ✅ API model generator (OpenAPI → Python)
- ✅ Usage examples
- ✅ Regeneration workflows

**Set up ONCE**, use repeatedly for each resource.

---

### 3. [IMPLEMENTATION_FEATURES.md](IMPLEMENTATION_FEATURES.md)
**For: Feature Developers**

Add new resources (users, organizations, teams):
- ✅ Step-by-step workflow
- ✅ Complete User example
- ✅ Complete Organization example
- ✅ Common patterns (name↔ID, nested objects, multi-endpoint)
- ✅ Testing strategies

**Repeat for EACH new resource** you add.

---

## Getting Started

### If You're Building the Framework

Read in order:
1. `REQUIREMENTS.md` - Understand the architecture and decisions
2. `IMPLEMENTATION_FOUNDATION.md` - Build core components
3. `IMPLEMENTATION_GENERATORS.md` - Set up code generation
4. `IMPLEMENTATION_FEATURES.md` - Add your first resource (to test)

### If You're Adding Features

Prerequisite: Foundation and generators already built by framework team.

Read:
1. `IMPLEMENTATION_FEATURES.md` - Your main guide
2. Reference `IMPLEMENTATION_FOUNDATION.md` - When you need to understand how things work
3. Reference `IMPLEMENTATION_GENERATORS.md` - When you need to regenerate code

---

## Document Cross-References

```
REQUIREMENTS.md
    ↓
    (Why we're doing it this way)
    ↓
IMPLEMENTATION_FOUNDATION.md ←─┐
    ↓                          │
    (Core framework)           │
    ↓                          │
IMPLEMENTATION_GENERATORS.md   │
    ↓                          │ (Reference)
    (Automate repetitive work) │
    ↓                          │
IMPLEMENTATION_FEATURES.md ────┘
    ↓
    (Add user-facing features)
    ↓
    🎉 Working Collection!
```

---

## Key Architecture Decisions

All three guides implement these principles:

1. **Manager-Side Transformations**: All data transformations happen in the persistent manager, not in action plugins
2. **Round-Trip Data Contract**: Output format always matches input format (single DOCUMENTATION source)
3. **Generic Manager**: Manager is resource-agnostic; resource logic lives in dataclass mixins
4. **Version Hierarchy**: API versioning handled through class inheritance (v1 → v2 → v3)
5. **Dynamic Discovery**: No hardcoded version lists; filesystem-based discovery
6. **Code Generation**: Automate Ansible and API dataclass generation from authoritative sources

See `REQUIREMENTS.md` for detailed rationale.

---

## Example: Full Workflow for Adding "User" Resource

### Phase 1: Foundation (One-Time, Framework Team)
```bash
# Build foundation components
cd ansible.platform/plugins/plugin_utils

# Create directories
mkdir -p platform manager ansible_models api/v1/generated docs

# Implement (see IMPLEMENTATION_FOUNDATION.md):
# - platform/base_transform.py
# - platform/types.py
# - platform/registry.py
# - platform/loader.py
# - manager/platform_manager.py
# - manager/rpc_client.py

# Set up generators (see IMPLEMENTATION_GENERATORS.md)
cd ../../tools/generators
# - generate_ansible_dataclasses.py
# - generate_api_models.sh
```

### Phase 2: First Resource (Feature Developer)
```bash
# 1. Write documentation
vi plugins/plugin_utils/docs/user.py
# (Write DOCUMENTATION string)

# 2. Generate Ansible dataclass
python tools/generators/generate_ansible_dataclasses.py \
    plugins/plugin_utils/docs/user.py

# 3. Generate API models
cp gateway.json tools/openapi_specs/gateway-v1.json
bash tools/generators/generate_api_models.sh

# 4. Create transform mixin (manual)
vi plugins/plugin_utils/api/v1/user.py
# (See IMPLEMENTATION_FEATURES.md for complete example)

# 5. Create action plugin
vi plugins/action/user.py
# (Thin wrapper following pattern)

# 6. Test
ansible-playbook tests/integration/test_user.yml
```

### Phase 3: Additional Resources
Repeat Phase 2 for each resource (organization, team, etc.)

---

## File Organization

```
ansible.platform/
├── galaxy.yml
├── plugins/
│   ├── action/                         # Action plugins (feature devs)
│   │   ├── user.py
│   │   └── organization.py
│   │
│   └── plugin_utils/
│       ├── platform/                   # Core framework (foundation)
│       │   ├── base_transform.py
│       │   ├── types.py
│       │   ├── registry.py
│       │   └── loader.py
│       │
│       ├── manager/                    # Manager service (foundation)
│       │   ├── platform_manager.py
│       │   └── rpc_client.py
│       │
│       ├── ansible_models/             # Generated + stable
│       │   ├── user.py                 # ← Generated
│       │   └── organization.py         # ← Generated
│       │
│       ├── api/                        # API models (versioned)
│       │   ├── v1/
│       │   │   ├── generated/          # ← Generated
│       │   │   │   └── models.py
│       │   │   ├── user.py             # ← Manual (feature devs)
│       │   │   └── organization.py     # ← Manual (feature devs)
│       │   └── v2/
│       │       └── ...
│       │
│       └── docs/                       # Module documentation
│           ├── user.py                 # ← Manual (feature devs)
│           └── organization.py         # ← Manual (feature devs)
│
└── tools/                              # Development tools
    ├── generators/
    │   ├── generate_ansible_dataclasses.py
    │   └── generate_api_models.sh
    └── openapi_specs/
        ├── gateway-v1.json
        └── gateway-v2.json
```

---

## Time Estimates

| Task | Who | Time (First Time) | Time (Subsequent) |
|------|-----|-------------------|-------------------|
| Build Foundation | Framework team | 8-12 hours | N/A |
| Set up Generators | Framework team | 2-3 hours | N/A |
| Add Simple Resource | Feature dev | 1-2 hours | 1-2 hours |
| Add Complex Resource | Feature dev | 3-4 hours | 2-3 hours |
| Add API Version | Framework team | 1-2 hours | 1-2 hours |

**Total to working system**: ~15 hours initial investment, then 1-4 hours per resource.

---

## Success Criteria

### Foundation Complete When:
- ✅ `BaseTransformMixin` can transform bidirectionally
- ✅ `PlatformManager` spawns and handles RPC calls
- ✅ `APIVersionRegistry` discovers available versions
- ✅ `DynamicClassLoader` loads version-specific classes
- ✅ Test manager script runs without errors

### Generators Working When:
- ✅ Documentation → Ansible dataclass generates correctly
- ✅ OpenAPI → API models generates correctly
- ✅ Regeneration works after schema changes
- ✅ Generated code passes linting

### Feature Complete When:
- ✅ Playbook can create/update/delete resource
- ✅ Input validation catches errors
- ✅ Output validation ensures consistency
- ✅ Manager reused across multiple tasks
- ✅ Complex fields (names↔IDs) transform correctly
- ✅ Multi-endpoint operations execute in correct order

---

## Questions?

Each guide includes:
- Complete, runnable code examples
- Step-by-step instructions
- Common patterns and solutions
- Testing strategies

Start with the guide matching your role:
- **Framework builder** → `IMPLEMENTATION_FOUNDATION.md`
- **Setting up tools** → `IMPLEMENTATION_GENERATORS.md`
- **Adding features** → `IMPLEMENTATION_FEATURES.md`

All guides designed to be complete enough for an AI agent to implement!
