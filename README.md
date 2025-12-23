# DevGodzilla (main stack)

DevGodzilla is the primary backend in this repo: a FastAPI API (`devgodzilla/api/app.py`) integrated with a Windmill-based UI (served via nginx).

## About DevGodzilla

DevGodzilla is an open-source, specification-driven, AI-powered development platform designed to automate and orchestrate software development workflows. It combines the rigor of specification-driven development with the flexibility of multiple AI coding agents, all orchestrated through an industrial-grade workflow engine.

### Core Philosophy

DevGodzilla operates on a **headless SWE-agent workflow** model where AI agents are the primary actors in the development process. The platform provides:

1. **Specification-First Development**: Every feature starts with a structured specification using SpecKit methodology
2. **Multi-Agent Flexibility**: Users can assign specific AI agents to specific development steps
3. **Git-First Architecture**: All work happens in git worktrees, preserving clean history
4. **Quality Gates**: Constitutional QA ensures code meets project standards before completion
5. **Industrial Orchestration**: Windmill provides scalable, observable workflow execution

### Key Components

| Component | Purpose |
|-----------|---------|
| **SpecKit** | Specification-driven development workflow with constitution governance |
| **Windmill** | Industrial-grade workflow orchestration with DAG execution |
| **Multi-Agent Execution** | 18+ AI coding agents (Codex, Claude, OpenCode, Cursor, etc.) |
| **FastAPI Backend** | REST API for all platform operations |
| **Next.js Frontend** | Modern web interface for project management |
| **PostgreSQL Database** | Persistent storage for projects, protocols, and execution history |

### Design Principles

- **Open Source**: Fully open source solution available as Python library and CLI
- **Agent Assignment**: Users can assign specific agents to specific steps for optimal results
- **No Offline Mode**: System requires online AI agent access for full functionality
- **No Fallbacks**: Clean-cut implementation without backward compatibility layers
- **Gitignore Runtime**: `_runtime/runs/` is gitignored (ephemeral execution data)
- **Hybrid Deployment**: Infrastructure runs in Docker while API/frontend run locally for development

## Architecture

```mermaid
graph TB
    subgraph UserLayer["User Layer"]
        CLI[CLI - Click-based]
        Console[Windmill UI + Extensions]
        API[REST API - FastAPI]
        Frontend[Next.js Frontend]
    end

    subgraph DevGodzillaCore["DevGodzilla Core"]
        direction TB
        APIRoutes[API Routes]
        Services[Services Layer]
        DB[(PostgreSQL DB)]
    end

    subgraph ServicesLayer["Services"]
        direction TB
        SpecService[Specification Service]
        PlanningService[Planning Service]
        ExecutionService[Execution Service]
        QualityService[Quality Service]
        OrchestratorService[Orchestrator Service]
        GitService[Git Service]
        PolicyService[Policy Service]
        ClarifierService[Clarifier Service]
    end

    subgraph Engines["AI Engines"]
        direction TB
        EngineRegistry[Engine Registry]
        Codex[Codex Engine]
        OpenCode[OpenCode Engine]
        ClaudeCode[Claude Code]
        OtherAgents[15+ More Agents]
    end

    subgraph WindmillLayer["Windmill Orchestration"]
        direction TB
        WindmillServer[Windmill Server]
        WindmillWorkers[Worker Pool]
        Flows[Flows]
        Scripts[Scripts]
    end

    subgraph Storage["Storage"]
        direction TB
        FileSystem[File System]
        ProjectsDir[projects/]
        ProtocolsDir[.protocols/]
        SpecsDir[.specify/]
    end

    subgraph Infra["Infrastructure (Docker)"]
        direction TB
        Nginx[Nginx Proxy]
        Redis[Redis]
        LSP[Language Server Protocol]
    end

    %% User Layer connections
    CLI --> API
    Console --> API
    Frontend --> API
    API --> APIRoutes

    %% DevGodzilla Core
    APIRoutes --> Services
    Services --> DB

    %% Services Layer
    Services --> SpecService
    Services --> PlanningService
    Services --> ExecutionService
    Services --> QualityService
    Services --> OrchestratorService
    Services --> GitService
    Services --> PolicyService
    Services --> ClarifierService

    %% Execution flow
    ExecutionService --> EngineRegistry
    EngineRegistry --> Codex
    EngineRegistry --> OpenCode
    EngineRegistry --> ClaudeCode
    EngineRegistry --> OtherAgents

    %% Windmill integration
    OrchestratorService --> WindmillServer
    WindmillServer --> WindmillWorkers
    WindmillServer --> Flows
    WindmillServer --> Scripts

    %% Storage
    SpecService --> FileSystem
    PlanningService --> FileSystem
    ExecutionService --> FileSystem
    GitService --> FileSystem
    FileSystem --> ProjectsDir
    FileSystem --> ProtocolsDir
    FileSystem --> SpecsDir

    %% Infrastructure
    Nginx --> API
    Nginx --> Frontend
    Nginx --> WindmillServer
    Services --> Redis
    WindmillServer --> LSP

    style UserLayer fill:#e1f5fe
    style DevGodzillaCore fill:#f3e5f5
    style ServicesLayer fill:#fff3e0
    style Engines fill:#e8f5e9
    style WindmillLayer fill:#fce4ec
    style Storage fill:#f5f5f5
    style Infra fill:#e3f2fd
```

## Architecture Deep Dive

### System Architecture

DevGodzilla follows a layered architecture pattern with clear separation of concerns:

1. **User Interface Layer**: Multiple entry points including CLI, Windmill UI, and Next.js frontend
2. **API Layer**: FastAPI-based REST API with dependency injection and middleware
3. **Services Layer**: Business logic organized by domain (specification, planning, execution, quality, etc.)
4. **Data Layer**: PostgreSQL for persistent storage with Alembic migrations
5. **Integration Layer**: Windmill orchestration and AI engine registry
6. **Storage Layer**: File system for project repositories, protocols, and artifacts

### Core Services

| Service | Responsibility | Key Features |
|----------|---------------|--------------|
| **Specification Service** | Manages SpecKit artifacts and constitution | Generates spec.md, plan.md, tasks.md |
| **Planning Service** | Creates execution plans from protocols | Auto-generates step files via headless agent |
| **Execution Service** | Executes steps using AI engines | Supports 18+ agent integrations |
| **Quality Service** | Runs QA gates after execution | Constitutional gates, prompt-based QA |
| **Orchestrator Service** | Manages Windmill integration | Flow generation, job scheduling |
| **Git Service** | Handles git operations | Worktree management, commit tracking |
| **Policy Service** | Manages governance policies | Constitution enforcement |
| **Clarifier Service** | Handles clarification questions | User interaction for ambiguous specs |

### AI Engine Registry

The engine registry provides a unified interface for 18+ AI coding agents:

| Engine | Provider | Default Model | Use Case |
|---------|-----------|----------------|-----------|
| **opencode** | DeepSeek/Llama | `zai-coding-plan/glm-4.6` | Default headless agent |
| **codex** | OpenAI | `gpt-4.1` | General coding |
| **claude-code** | Anthropic | `claude-sonnet-4-20250514` | Complex reasoning |
| **gemini-cli** | Google | `gemini-1.5-pro` | Google ecosystem |
| **cursor** | Cursor IDE | IDE-integrated | Cursor users |
| **copilot** | GitHub | `gpt-4` | GitHub integration |
| **windsurf** | Windsurf | IDE-integrated | Windsurf users |
| **jules** | Jules | IDE-integrated | Jules users |
| **qoder** | Experimental | Experimental | Research |

### Database Schema

DevGodzilla uses PostgreSQL with Alembic for migrations. Key entities include:

- **Projects**: Repository metadata and configuration
- **ProtocolRuns**: Protocol execution instances with status tracking
- **StepRuns**: Individual step executions with results
- **SpecRuns**: SpecKit specification runs
- **Clarifications**: User questions and answers for ambiguous specs
- **PolicyPacks**: Governance policies and rules
- **AgentAssignments**: Per-step agent assignments
- **Sprints**: Agile sprint management with task synchronization

### Quality Assurance System

The QA system operates on two levels:

1. **Prompt-Driven QA**: Headless agent evaluates step outputs against requirements
2. **Constitutional Gates**: Deterministic checks for code quality (lint, type, tests)
3. **Feedback Loops**: Automatic handling of QA failures with clarify/re-plan/retry actions

Constitutional articles enforce:
- Library-First development
- Test-First approach
- Simplicity principles
- Anti-abstraction guidelines
- Integration testing requirements

## Deployment Architecture

### Local Development Setup

DevGodzilla uses a **hybrid deployment** model for local development:

```mermaid
graph TB
    subgraph HostMachine["Host Machine"]
        direction TB
        Backend[DevGodzilla API<br/>uvicorn :8000]
        Frontend[DevGodzilla Frontend<br/>Next.js :3000]
        Projects[projects/ directory]
    end

    subgraph Docker["Docker Containers"]
        direction TB
        Nginx[Nginx Proxy<br/>:8080]
        Windmill[Windmill Server<br/>:8001]
        Workers[Windmill Workers]
        DB[(PostgreSQL<br/>:5432)]
        Redis[Redis<br/>:6379]
        LSP[Language Server<br/>:3001]
    end

    subgraph Network["Network Layer"]
        direction TB
        HostDocker[host.docker.internal]
    end

    Nginx --> HostDocker
    HostDocker --> Backend
    HostDocker --> Frontend
    HostDocker --> Windmill
    Windmill --> Workers
    Windmill --> DB
    Windmill --> Redis
    Windmill --> LSP
    Backend --> DB
    Backend --> Projects
    Backend --> Redis

    style HostMachine fill:#e8f5e9
    style Docker fill:#fff3e0
    style Network fill:#e3f2fd
```

**Benefits of Hybrid Deployment:**
- Fast iteration: Backend/frontend reload instantly without container rebuilds
- Easy debugging: Direct access to code and logs on host
- Resource efficiency: Only infra services run in Docker
- Production parity: Same nginx routing as production

### Docker Services

| Service | Purpose | Resources | Health Check |
|---------|---------|-----------|--------------|
| **nginx** | Reverse proxy and routing | Minimal | HTTP /health |
| **windmill** | Workflow orchestration server | 2GB RAM | API /api/version |
| **windmill_worker** | Python job execution | 1 CPU, 2GB RAM | Process monitoring |
| **windmill_worker_native** | Lightweight in-process jobs | 1 CPU, 2GB RAM, 8 workers | Process monitoring |
| **db** | PostgreSQL database | 1GB shared memory | pg_isready |
| **redis** | Queue and cache | Minimal | Connection test |
| **lsp** | Code intelligence | Cache volume | Connection test |

### Production Deployment Considerations

For production deployment, consider:

1. **Full Containerization**: Run API and frontend in Docker for consistency
2. **High Availability**: Multiple Windmill workers across nodes
3. **Load Balancing**: External load balancer before nginx
4. **Persistent Storage**: Named volumes for database and projects
5. **Monitoring**: Prometheus metrics and centralized logging
6. **Security**: TLS termination, network policies, secrets management

### Environment Configuration

DevGodzilla uses environment variables for configuration across all services:

**Database Configuration:**
- `DEVGODZILLA_DB_URL`: PostgreSQL connection string
- `DEVGODZILLA_DB_PATH`: SQLite fallback (for development)

**Windmill Integration:**
- `DEVGODZILLA_WINDMILL_URL`: Windmill server URL
- `DEVGODZILLA_WINDMILL_WORKSPACE`: Workspace name
- `DEVGODZILLA_WINDMILL_TOKEN`: Authentication token
- `DEVGODZILLA_WINDMILL_ENV_FILE`: Path to token file

**AI Engine Configuration:**
- `DEVGODZILLA_DEFAULT_ENGINE_ID`: Default engine (opencode)
- `DEVGODZILLA_OPENCODE_MODEL`: OpenCode model
- `DEVGODZILLA_AUTO_GENERATE_PROTOCOL`: Auto-generate protocol files

**Project Configuration:**
- `DEVGODZILLA_PROJECTS_ROOT`: Root directory for projects
- `DEVGODZILLA_NGINX_PORT`: Nginx port (default 8080)

### Network Architecture

The platform uses nginx as a single entrypoint with intelligent routing:

- **DevGodzilla API routes**: `/projects`, `/protocols`, `/steps`, `/speckit`, `/sprints`, etc.
- **Windmill UI**: Default route `/` for Windmill dashboard
- **DevGodzilla Frontend**: `/console` route for Next.js application
- **API Documentation**: `/docs` for OpenAPI/Swagger UI
- **WebSocket Support**: `/ws/events` for real-time updates, `/ws/` for Windmill LSP

Nginx handles:
- SSL/TLS termination (in production)
- WebSocket proxying
- CORS configuration
- Request buffering and timeouts
- Health check routing

### Scaling Strategy

DevGodzilla supports horizontal scaling through:

1. **Windmill Workers**: Add more worker containers for parallel job execution
2. **Native Workers**: Use native workers for lightweight in-process jobs
3. **Worker Groups**: Separate workers by job type (default, native)
4. **Database Pooling**: Connection pooling for high concurrency
5. **Redis Clustering**: For distributed queue management

## Key Workflows

### Headless SWE-Agent Workflow

DevGodzilla's main workflow is **agent-driven**: it runs a headless SWE-agent (default engine `opencode`, default model `zai-coding-plan/glm-4.6`) using prompts under `prompts/`, writes artifacts into the repo/worktree, and DevGodzilla only validates/records those outputs.

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant API
    participant PlanningService
    participant HeadlessAgent
    participant ExecutionService
    participant QualityService
    participant Git

    User->>CLI: project create --repo <url>
    CLI->>API: POST /projects
    API->>Git: Clone repository
    API-->>User: Project created

    User->>CLI: project discover <id> --agent --pipeline
    CLI->>API: POST /projects/{id}/actions/onboard
    API->>HeadlessAgent: Run discovery agent
    HeadlessAgent->>Git: Write discovery artifacts
    HeadlessAgent-->>API: Discovery complete
    API-->>User: Discovery complete

    User->>CLI: protocol create <id> <name>
    CLI->>API: POST /protocols
    API-->>User: Protocol created

    User->>CLI: protocol worktree <id>
    CLI->>API: POST /protocols/{id}/actions/worktree
    API->>Git: Create git worktree

    User->>CLI: protocol plan <id>
    CLI->>API: POST /protocols/{id}/actions/start
    API->>PlanningService: Plan protocol
    alt Protocol files missing
        PlanningService->>HeadlessAgent: Generate plan.md + step-*.md
        HeadlessAgent->>Git: Write protocol files
    end
    PlanningService->>PlanningService: Create StepRun rows
    API-->>User: Protocol planned

    loop For each step
        User->>CLI: POST /protocols/{id}/actions/run_next_step
        CLI->>API: Select next runnable step
        API-->>CLI: Return step_run_id

        User->>CLI: step execute <step_run_id>
        CLI->>API: POST /steps/{id}/actions/execute
        API->>ExecutionService: Execute step
        ExecutionService->>HeadlessAgent: Run in worktree
        HeadlessAgent->>Git: Write code changes
        HeadlessAgent-->>ExecutionService: Execution complete
        ExecutionService->>Git: Write git report artifacts
        ExecutionService-->>API: Step executed

        API->>QualityService: Run QA
        QualityService->>HeadlessAgent: Prompt-driven QA
        HeadlessAgent-->>QualityService: QA verdict
        QualityService-->>API: QA result

        alt QA passed
            API->>API: Mark step complete
        else QA failed
            API-->>User: QA failed, manual review needed
        end
    end

    API->>API: Update protocol status to completed/failed
    API-->>User: Protocol complete
```

### Windmill Orchestration Workflow

```mermaid
graph TB
    subgraph Flows["Windmill Flows"]
        OnboardFlow[onboard_to_tasks]
        SpecToTasksFlow[spec_to_tasks]
        SpecToProtoFlow[spec_to_protocol]
        ProtoStartFlow[protocol_start]
        NextStepFlow[run_next_step]
        StepExecFlow[step_execute_with_qa]
        ExecProtoFlow[execute_protocol]
    end

    subgraph Scripts["Windmill Scripts (API Wrappers)"]
        Clone[clone_repo]
        Analyze[analyze_project]
        Init[initialize_speckit]
        Setup[project_setup]
        SpecSpec[speckit_specify_api]
        SpecPlan[speckit_plan_api]
        SpecTasks[speckit_tasks_api]
        ProtoFromSpec[protocol_from_spec_api]
        ProtoPlan[protocol_plan_and_wait]
        ExecStep[step_execute_api]
        StepQA[step_run_qa_api]
        OpenPR[open_pr]
    end

    subgraph DevGodzillaAPI["DevGodzilla API"]
        ProjectsAPI[POST /projects]
        SpecKitAPI[POST /speckit/*]
        ProtocolsAPI[POST /protocols/*]
        StepsAPI[POST /steps/*]
    end

    OnboardFlow --> Clone & Analyze & Init & Setup
    SpecToTasksFlow --> SpecSpec & SpecPlan & SpecTasks
    SpecToProtoFlow --> ProtoFromSpec & ProtoPlan
    ProtoStartFlow --> ProtoPlan
    NextStepFlow --> ExecStep
    StepExecFlow --> ExecStep & StepQA
    ExecProtoFlow --> ExecStep

    Clone --> ProjectsAPI
    Analyze --> ProjectsAPI
    Init --> SpecKitAPI
    Setup --> ProjectsAPI
    SpecSpec --> SpecKitAPI
    SpecPlan --> SpecKitAPI
    SpecTasks --> SpecKitAPI
    ProtoFromSpec --> ProtocolsAPI
    ProtoPlan --> ProtocolsAPI
    ExecStep --> StepsAPI
    StepQA --> StepsAPI
    OpenPR --> ProtocolsAPI

    style Flows fill:#e8f5e9
    style Scripts fill:#fff3e0
    style DevGodzillaAPI fill:#e3f2fd
```

### SpecKit Integration Workflow

```mermaid
graph LR
    subgraph SpecKitArtifacts["SpecKit Artifacts (.specify/)"]
        Constitution[memory/constitution.md]
        Templates[templates/]
        Specs[specs/<feature>/]
        Runtime[_runtime/]
    end

    subgraph DevGodzillaServices["DevGodzilla Services"]
        SpecService[Specification Service]
        PlanningService[Planning Service]
        ExecutionService[Execution Service]
    end

    subgraph Outputs["Generated Files"]
        SpecMD[spec.md]
        PlanMD[plan.md]
        TasksMD[tasks.md]
        ContextMD[_runtime/context.md]
        LogMD[_runtime/log.md]
    end

    subgraph ProtocolFiles["Protocol Files (.protocols/)"]
        ProtocolPlan[plan.md]
        StepFiles[step-*.md]
        Artifacts[.devgodzilla/steps/*/artifacts/*]
    end

    SpecService --> Constitution
    SpecService --> Templates
    SpecService --> SpecMD
    SpecService --> PlanMD
    SpecService --> TasksMD

    PlanningService --> SpecMD
    PlanningService --> PlanMD
    PlanningService --> TasksMD
    PlanningService --> ProtocolPlan
    PlanningService --> StepFiles

    ExecutionService --> StepFiles
    ExecutionService --> Artifacts
    ExecutionService --> ContextMD
    ExecutionService --> LogMD

    style SpecKitArtifacts fill:#e3f2fd
    style DevGodzillaServices fill:#fff3e0
    style Outputs fill:#e8f5e9
    style ProtocolFiles fill:#fce4ec
```

## Quick start (local dev)

```bash
scripts/run-local-dev.sh dev
```

- UI: `http://localhost:8080` (or `$DEVGODZILLA_NGINX_PORT`)
- API docs: `http://localhost:8080/docs`

Notes:
- `docker compose up --build -d` starts infra only (nginx + windmill + workers + db + redis + lsp). The API + frontend run locally on the host.
- Import Windmill assets (optional): `scripts/run-local-dev.sh import`.

## Runtime Topology

Default infra stack runs:
- `nginx`: single entrypoint for UI + API (proxies to host backend/frontend via `nginx.local.conf`)
- `windmill`: Windmill server + UI (built from `Origins/Windmill`)
- `windmill_worker` / `windmill_worker_native`: Windmill workers
- `db`: Postgres (shared by DevGodzilla + Windmill)
- `redis`: Redis (queues/cache)
- `lsp`: Windmill LSP (optional)

Host processes (started via `scripts/run-local-dev.sh dev`) run:
- DevGodzilla API: `uvicorn devgodzilla.api.app:app` on `:8000`
- DevGodzilla frontend (Next.js) on `:3000`

## Headless SWE-Agent Workflow (TasksGodzilla-style)

**Key artifact locations:**
- Repo discovery outputs (agent-written): `specs/discovery/_runtime/DISCOVERY.md`, `specs/discovery/_runtime/DISCOVERY_SUMMARY.json`, `specs/discovery/_runtime/ARCHITECTURE.md`, `specs/discovery/_runtime/API_REFERENCE.md`, `specs/discovery/_runtime/CI_NOTES.md`
- Protocol definition (agent-written, per worktree): `.protocols/<protocol_name>/plan.md` + `.protocols/<protocol_name>/step-*.md`
- Execution "git report" artifacts (DevGodzilla-written): `.protocols/<protocol_name>/.devgodzilla/steps/<step_run_id>/artifacts/*`

Default engine/model for headless workflows:
- Engine: `opencode` (`DEVGODZILLA_DEFAULT_ENGINE_ID`)
- Model: `zai-coding-plan/glm-4.6` (`DEVGODZILLA_OPENCODE_MODEL`)

## Windmill Integration

### Supported execution model

**Supported**: Windmill scripts are thin API adapters that call DevGodzilla API.

Examples:
- `u/devgodzilla/protocol_plan_and_wait` (calls `/protocols/{id}/actions/start` and polls)
- `u/devgodzilla/step_execute_api` (calls `/steps/{id}/actions/execute`)
- `u/devgodzilla/step_run_qa_api` (calls `/steps/{id}/actions/qa` for manual re-runs)
- `u/devgodzilla/onboard_to_tasks_api` (one-script pipeline alternative)

This avoids requiring the Windmill worker runtime to import the `devgodzilla` Python package.

### Supported flows

Recommended flows to use in the default stack:
- `f/devgodzilla/onboard_to_tasks`
- `f/devgodzilla/protocol_start`
- `f/devgodzilla/step_execute_with_qa`
- `f/devgodzilla/run_next_step` (selection only)

See: `docs/DevGodzilla/WINDMILL-WORKFLOWS.md`.

## CLI Commands

| Command Group | Description |
|---------------|-------------|
| `devgodzilla spec` | SpecKit commands (init, specify, plan, tasks) |
| `devgodzilla protocol` | Protocol management (create, start, status, pause) |
| `devgodzilla project` | Project CRUD operations |
| `devgodzilla agent` | Agent management and health checks |
| `devgodzilla clarify` | Handle clarification questions |
| `devgodzilla step` | Step execution and QA |
| `devgodzilla qa` | Quality assurance gates |

## API

DevGodzilla provides a FastAPI-based REST API:

```bash
# Start the API server
python -m devgodzilla.api.app

# API available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /projects` | Create a new project |
| `POST /speckit/init` | Initialize SpecKit |
| `POST /speckit/specify` | Generate specification |
| `POST /protocols` | Create protocol |
| `POST /protocols/{id}/actions/start` | Start protocol |
| `POST /steps/{id}/actions/execute` | Execute step |

## Directory Structure

```
devgodzilla/
├── api/                    # FastAPI REST API
│   ├── app.py             # Main FastAPI application
│   ├── dependencies.py     # Dependency injection
│   ├── schemas.py         # Pydantic schemas
│   └── routes/           # API route handlers
├── cli/                   # Click-based CLI
│   ├── main.py           # CLI entry point
│   ├── projects.py       # Project commands
│   ├── protocols.py      # Protocol commands
│   └── speckit.py       # SpecKit commands
├── services/              # Core business logic
│   ├── specification.py  # SpecKit integration
│   ├── planning.py       # Protocol planning
│   ├── execution.py      # Agent execution
│   ├── quality.py        # QA gates
│   ├── orchestrator.py   # Windmill orchestration
│   ├── git.py           # Git operations
│   ├── policy.py        # Policy management
│   └── clarifier.py     # Clarification handling
├── engines/              # AI agent integrations
│   ├── registry.py      # Engine registry
│   ├── codex.py         # OpenAI Codex
│   ├── opencode.py      # OpenCode engine
│   ├── claude_code.py   # Anthropic Claude
│   └── ...              # 15+ more agents
├── qa/                   # Quality assurance
│   ├── gates/           # QA gates (constitutional, prompt, security)
│   └── feedback.py      # Feedback loop handling
├── db/                   # Database schema
│   ├── database.py      # Database connection
│   └── schema.py        # SQLAlchemy models
├── windmill/            # Windmill integration
│   ├── client.py        # Windmill API client
│   ├── flow_generator.py # Flow generation
│   └── worker.py        # Worker integration
└── alembic/            # Database migrations
```

## Testing

```bash
# Run DevGodzilla tests
pytest tests/test_devgodzilla_*.py -v

# Run specific test module
pytest tests/test_devgodzilla_speckit.py -v
```

### E2E workflow tests (real public repo; validates agent outputs)

E2E tests are opt-in (they clone a real public GitHub repo):

```bash
DEVGODZILLA_RUN_E2E=1 scripts/ci/test_e2e_real_repo.sh
```

To run with a real `opencode` installation (no stub), use:

```bash
DEVGODZILLA_RUN_E2E_REAL_AGENT=1 scripts/ci/test_e2e_real_agent.sh
```

## Legacy backend (TasksGodzilla orchestrator)

The older TasksGodzilla orchestrator API is archived under `archive/` and is not part of the main stack.

```bash
docker compose -f archive/docker-compose.tasksgodzilla.yml up --build -d
```

- UI/console: `http://localhost:8011/console` (or `$TASKSGODZILLA_NGINX_PORT`)

## Documentation

- DevGodzilla overview: `devgodzilla/README.md`
- DevGodzilla deployment: `DEPLOYMENT.md`
- DevGodzilla architecture docs: `docs/DevGodzilla/`
  - `ARCHITECTURE.md` - Full architecture design
  - `CURRENT_STATE.md` - Current runtime state
  - `WINDMILL-WORKFLOWS.md` - Windmill integration details
  - `API-ARCHITECTURE.md` - REST API specification
  - `subsystems/` - Detailed subsystem documentation

## Development Workflow

### Complete Development Lifecycle

DevGodzilla supports a complete development lifecycle from specification to deployment:

1. **Project Onboarding**: Clone repository, analyze structure, initialize SpecKit
2. **Discovery Phase** (Optional): Run headless agent to understand codebase architecture
3. **Specification**: Create feature specs with user stories and requirements
4. **Planning**: Generate technical implementation plans and task breakdowns
5. **Protocol Creation**: Create protocol runs with git worktrees
6. **Execution**: Run steps with AI agents in isolated worktrees
7. **Quality Assurance**: Constitutional QA gates and prompt-driven validation
8. **Integration**: Sync with agile sprints and track velocity
9. **Deployment**: Create pull requests and merge changes

### Artifact Locations

DevGodzilla organizes artifacts in specific locations for clarity and version control:

**Project Root Structure:**
```
projects/<project_id>/
├── <repo>/                          # Git repository clone
│   ├── .specify/                    # SpecKit artifacts
│   │   ├── memory/
│   │   │   └── constitution.md       # Project governance
│   │   ├── templates/
│   │   │   ├── spec-template.md
│   │   │   ├── plan-template.md
│   │   │   └── tasks-template.md
│   │   └── specs/<feature>/
│   │       ├── spec.md                # Feature specification
│   │       ├── plan.md                # Implementation plan
│   │       ├── tasks.md               # Task breakdown
│   │       └── _runtime/
│   │           ├── context.md          # Execution context
│   │           ├── log.md             # Execution log
│   │           └── runs/             # GITIGNORED
│   ├── .protocols/<protocol_name>/    # Protocol definitions
│   │   ├── plan.md                  # Protocol plan
│   │   ├── step-001.md             # Step definitions
│   │   ├── step-002.md
│   │   └── .devgodzilla/
│   │       └── steps/
│   │           └── <step_run_id>/
│   │               └── artifacts/       # Execution artifacts
│   │                   ├── execution.json
│   │                   ├── stdout.log
│   │                   ├── stderr.log
│   │                   ├── git-status.txt
│   │                   └── diffs/
│   └── specs/discovery/_runtime/     # Discovery artifacts
│       ├── DISCOVERY.md
│       ├── DISCOVERY_SUMMARY.json
│       ├── ARCHITECTURE.md
│       ├── API_REFERENCE.md
│       └── CI_NOTES.md
```

### Sprint Integration

DevGodzilla integrates with agile development practices through sprint management:

- **Task Import**: Import SpecKit tasks.md into sprints
- **Protocol Linkage**: Link protocols to sprints for tracking
- **Status Updates**: Automatic task status updates on step completion
- **Velocity Tracking**: Calculate actual sprint velocity from completed steps
- **Bidirectional Sync**: Changes in sprints reflect in protocols and vice versa

**Supported Sprint Operations:**
- Create sprints from protocols
- Import tasks from SpecKit artifacts
- Sync task status with step execution
- Complete sprints with final metrics
- Track sprint velocity over time

### Git Worktree Management

DevGodzilla uses git worktrees for isolated protocol execution:

1. **Worktree Creation**: Each protocol gets its own worktree
2. **Isolated Execution**: Steps run in isolated environments
3. **Clean History**: Main branch remains clean until PR merge
4. **Artifact Tracking**: Execution artifacts stored in worktree
5. **PR Creation**: Generate pull requests from worktree changes

**Benefits:**
- Parallel development on same codebase
- Clean git history
- Easy rollback and comparison
- Isolated testing environments

### Quality Gates

The quality assurance system enforces project standards through multiple gates:

**Constitutional Gates:**
- Library-First: Prefer existing libraries over custom code
- Test-First: Write tests before implementation
- Simplicity: Avoid over-engineering
- Anti-Abstraction: Don't abstract prematurely
- Integration Testing: Ensure components work together

**Deterministic Gates:**
- Linting: Code style and formatting checks
- Type Checking: Static type validation
- Unit Tests: Test coverage and passing tests
- Security Scans: Vulnerability detection

**Prompt-Driven QA:**
- AI agent evaluates code against requirements
- Checks for edge cases and error handling
- Validates adherence to specification
- Provides detailed feedback

### Error Handling and Recovery

DevGodzilla implements robust error handling:

1. **Automatic Retry**: Transient failures trigger automatic retries
2. **Feedback Loops**: QA failures trigger clarify/re-plan/retry actions
3. **User Intervention**: Clarification questions for ambiguous requirements
4. **Partial Recovery**: Continue with completed steps on failure
5. **Rollback Support**: Revert worktree changes on protocol failure

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVGODZILLA_DB_URL` | `postgresql://devgodzilla:changeme@localhost:5432/devgodzilla_db` | PostgreSQL connection URL |
| `DEVGODZILLA_LOG_LEVEL` | `DEBUG` | Logging level |
| `DEVGODZILLA_WINDMILL_URL` | `http://localhost:8001` | Windmill server URL |
| `DEVGODZILLA_WINDMILL_WORKSPACE` | `demo1` | Windmill workspace |
| `DEVGODZILLA_WINDMILL_ENV_FILE` | `windmill/apps/devgodzilla-react-app/.env.development` | Windmill token file |
| `DEVGODZILLA_PROJECTS_ROOT` | `$PROJECT_DIR/projects` | Projects root directory |
| `DEVGODZILLA_DEFAULT_ENGINE_ID` | `opencode` | Default AI engine |
| `DEVGODZILLA_OPENCODE_MODEL` | `zai-coding-plan/glm-4.6` | Default OpenCode model |
| `DEVGODZILLA_AUTO_GENERATE_PROTOCOL` | `true` | Auto-generate protocol files |
| `WINDMILL_FEATURES` | `static_frontend python deno_core` | Windmill build features |
| `DEVGODZILLA_NGINX_PORT` | `8080` | Nginx port |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest tests/`
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.
