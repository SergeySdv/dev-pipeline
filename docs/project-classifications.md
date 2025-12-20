# Project Classifications (Policy Packs)

This repository supports multiple “project types” by letting the user select a **policy pack** during onboarding. Policy packs define defaults (models/QA/CI), required step sections, required CI checks, and structured clarification questions.

See also:
- `docs/policy-framework.md` — overall framework and rollout notes
- `docs/api-reference.md` — `POST /policy_packs` and project policy endpoints

## Recommended classifications

| Classification | Pack key | Intended users |
|---|---|---|
| General purpose | `default` | Most projects, minimal assumptions |
| Beginner guided | `beginner-guided` | Inexperienced users / high guidance needs |
| Startup fast | `startup-fast` | Fast iteration, minimal overhead |
| Team standard | `team-standard` | Most teams with CI + review habits |
| Enterprise compliance | `enterprise-compliance` | Regulated/audited workflows (pair with `policy_enforcement_mode=block`) |

## Notes on `defaults.models`

Keep `defaults.models` in policy packs (per `docs/policy-framework.md`). It provides a consistent place to define model defaults for planning/decomposition/execution/QA. Current code validates and stores these fields, but not all runtime paths fully enforce model selection from policy yet.

## Payloads ready to `POST /policy_packs`

Each payload below matches `tasksgodzilla/api/schemas.py:PolicyPackCreate` and can be posted as-is.

### `default@1.0`
```json
{
  "key": "default",
  "version": "1.0",
  "name": "Default",
  "description": "General purpose baseline policy pack (warnings by default).",
  "status": "active",
  "pack": {
    "meta": {
      "key": "default",
      "name": "Default",
      "version": "1.0",
      "description": "General purpose baseline policy pack (warnings by default)."
    },
    "defaults": {
      "models": {
        "planning": "zai-coding-plan/glm-4.6",
        "decompose": "zai-coding-plan/glm-4.6",
        "exec": "zai-coding-plan/glm-4.6",
        "qa": "zai-coding-plan/glm-4.6"
      }
      "qa": {
        "policy": "full",
        "auto_after_exec": false,
        "auto_on_ci": false
      },
      "git": {
        "draft_pr_default": true,
        "branch_pattern": "<number>-<task>"
      },
      "ci": {
        "required_checks": []
      }
    },
    "requirements": {
      "protocol_files": [],
      "step_sections": []
    },
    "clarifications": [
      {
        "key": "ci_provider",
        "question": "Which CI provider should be used for PR/MR automation?",
        "options": [
          "github",
          "gitlab"
        ],
        "recommended": "github",
        "blocking": false,
        "applies_to": "onboarding"
      },
    ],
    "enforcement": {
      "mode": "warn",
      "block_codes": [
        "policy.ci.required_check_missing",
        "policy.ci.required_check_not_executable",
        "policy.protocol.missing_file",
        "policy.step.missing_section",
        "policy.step.file_missing"
      ]
    },
    "constraints": {}
  }
}
```

### `beginner-guided@1.0`
```json
{
  "key": "beginner-guided",
  "version": "1.0",
  "name": "Beginner Guided",
  "description": "More structure and safety for inexperienced users (warnings by default).",
  "status": "active",
  "pack": {
    "meta": {
      "key": "beginner-guided",
      "name": "Beginner Guided",
      "version": "1.0",
      "description": "More structure and safety for inexperienced users (warnings by default)."
    },
    "defaults": {
      "models": {
        "planning": "zai-coding-plan/glm-4.6",
        "decompose": "zai-coding-plan/glm-4.6",
        "exec": "zai-coding-plan/glm-4.6",
        "qa": "zai-coding-plan/glm-4.6"
      },
      "qa": {
        "policy": "light",
        "auto_after_exec": true,
        "auto_on_ci": false
      },
      "git": {
        "draft_pr_default": true,
        "branch_pattern": "<number>-<task>"
      },
      "ci": {
        "required_checks": [
          "scripts/ci/test.sh",
          "scripts/ci/lint.sh",
          "scripts/ci/typecheck.sh",
          "scripts/ci/build.sh"
        ]
      }
    },
    "requirements": {
      "protocol_files": [
        "plan.md",
        "context.md",
        "log.md"
      ],
      "step_sections": [
        "Sub-tasks",
        "Verification",
        "Rollback",
        "Definition of Done"
      ]
    },
    "clarifications": [
      {
        "key": "experience_level",
        "question": "What is your experience level with this codebase/stack?",
        "options": [
          "beginner",
          "intermediate",
          "advanced"
        ],
        "recommended": "beginner",
        "blocking": false,
        "applies_to": "onboarding"
      },
      {
        "key": "ci_provider",
        "question": "Which CI provider should be used for PR/MR automation?",
        "options": [
          "github",
          "gitlab"
        ],
        "recommended": "github",
        "blocking": false,
        "applies_to": "onboarding"
      },
      {
        "key": "required_checks_confirm",
        "question": "Confirm the required CI checks for this project.",
        "recommended": [
          "scripts/ci/test.sh",
          "scripts/ci/lint.sh",
          "scripts/ci/typecheck.sh",
          "scripts/ci/build.sh"
        ],
        "blocking": false,
        "applies_to": "planning"
      },
      {
        "key": "pr_policy",
        "question": "Should PRs default to Draft while iterating?",
        "options": [
          "draft",
          "ready"
        ],
        "recommended": "draft",
        "blocking": false,
        "applies_to": "execution"
      }
    ],
    "enforcement": {
      "mode": "warn",
      "block_codes": [
        "policy.ci.required_check_missing",
        "policy.ci.required_check_not_executable",
        "policy.protocol.missing_file",
        "policy.step.missing_section",
        "policy.step.file_missing"
      ]
    },
    "constraints": {}
  }
}
```

### `startup-fast@1.0`
```json
{
  "key": "startup-fast",
  "version": "1.0",
  "name": "Startup Fast",
  "description": "Minimal process overhead; focus on iteration speed (warnings by default).",
  "status": "active",
  "pack": {
    "meta": {
      "key": "startup-fast",
      "name": "Startup Fast",
      "version": "1.0",
      "description": "Minimal process overhead; focus on iteration speed (warnings by default)."
    },
    "defaults": {
      "models": {
        "planning": "zai-coding-plan/glm-4.6",
        "decompose": "zai-coding-plan/glm-4.6",
        "exec": "zai-coding-plan/glm-4.6",
        "qa": "zai-coding-plan/glm-4.6"
      },
      "qa": {
        "policy": "full",
        "auto_after_exec": false,
        "auto_on_ci": true
      },
      "git": {
        "draft_pr_default": true,
        "branch_pattern": "<number>-<task>"
      },
      "ci": {
        "required_checks": [
          "scripts/ci/test.sh"
        ]
      }
    },
    "requirements": {
      "protocol_files": [],
      "step_sections": [
        "Sub-tasks",
        "Verification"
      ]
    },
    "clarifications": [
      {
        "key": "release_risk",
        "question": "Release risk tolerance for this project?",
        "options": [
          "low",
          "medium",
          "high"
        ],
        "recommended": "low",
        "blocking": false,
        "applies_to": "planning"
      },
      {
        "key": "auto_qa_on_ci",
        "question": "Automatically enqueue QA when CI succeeds?",
        "options": [
          true,
          false
        ],
        "recommended": true,
        "blocking": false,
        "applies_to": "onboarding"
      }
    ],
    "enforcement": {
      "mode": "warn",
      "block_codes": [
        "policy.ci.required_check_missing",
        "policy.ci.required_check_not_executable"
      ]
    },
    "constraints": {}
  }
}
```

### `team-standard@1.0`
```json
{
  "key": "team-standard",
  "version": "1.0",
  "name": "Team Standard",
  "description": "Balanced defaults for most professional teams (warnings by default).",
  "status": "active",
  "pack": {
    "meta": {
      "key": "team-standard",
      "name": "Team Standard",
      "version": "1.0",
      "description": "Balanced defaults for most professional teams (warnings by default)."
    },
    "defaults": {
      "models": {
        "planning": "zai-coding-plan/glm-4.6",
        "decompose": "zai-coding-plan/glm-4.6",
        "exec": "zai-coding-plan/glm-4.6",
        "qa": "zai-coding-plan/glm-4.6"
      },
      "qa": {
        "policy": "full",
        "auto_after_exec": false,
        "auto_on_ci": true
      },
      "git": {
        "draft_pr_default": true,
        "branch_pattern": "<number>-<task>"
      },
      "ci": {
        "required_checks": [
          "scripts/ci/test.sh",
          "scripts/ci/lint.sh",
          "scripts/ci/typecheck.sh",
          "scripts/ci/build.sh"
        ]
      }
    },
    "requirements": {
      "protocol_files": [
        "plan.md",
        "context.md",
        "log.md"
      ],
      "step_sections": [
        "Context",
        "Scope",
        "Sub-tasks",
        "Verification",
        "Rollback",
        "Observability",
        "Definition of Done"
      ]
    },
    "clarifications": [
      {
        "key": "review_policy",
        "question": "How many approvals are required before merge?",
        "options": [
          "1-approval",
          "2-approvals"
        ],
        "recommended": "1-approval",
        "blocking": false,
        "applies_to": "execution"
      },
      {
        "key": "environments",
        "question": "Which environments exist for deployments?",
        "options": [
          "dev",
          "staging",
          "prod"
        ],
        "recommended": [
          "dev",
          "prod"
        ],
        "blocking": false,
        "applies_to": "planning"
      },
      {
        "key": "rollback_strategy",
        "question": "Preferred rollback strategy?",
        "options": [
          "revert",
          "feature_flag",
          "hotfix"
        ],
        "recommended": "revert",
        "blocking": false,
        "applies_to": "planning"
      }
    ],
    "enforcement": {
      "mode": "warn",
      "block_codes": [
        "policy.ci.required_check_missing",
        "policy.ci.required_check_not_executable",
        "policy.protocol.missing_file",
        "policy.step.missing_section",
        "policy.step.file_missing"
      ]
    },
    "constraints": {}
  }
}
```

### `enterprise-compliance@1.0`
```json
{
  "key": "enterprise-compliance",
  "version": "1.0",
  "name": "Enterprise Compliance",
  "description": "Regulated/audited workflows; designed for policy_enforcement_mode=block.",
  "status": "active",
  "pack": {
    "meta": {
      "key": "enterprise-compliance",
      "name": "Enterprise Compliance",
      "version": "1.0",
      "description": "Regulated/audited workflows; designed for policy_enforcement_mode=block."
    },
    "defaults": {
      "models": {
        "planning": "zai-coding-plan/glm-4.6",
        "decompose": "zai-coding-plan/glm-4.6",
        "exec": "zai-coding-plan/glm-4.6",
        "qa": "zai-coding-plan/glm-4.6"
      },
      "qa": {
        "policy": "full",
        "auto_after_exec": false,
        "auto_on_ci": true
      },
      "git": {
        "draft_pr_default": false,
        "branch_pattern": "<number>-<task>"
      },
      "ci": {
        "required_checks": [
          "scripts/ci/test.sh",
          "scripts/ci/lint.sh",
          "scripts/ci/typecheck.sh",
          "scripts/ci/build.sh",
          "scripts/ci/security.sh"
        ]
      }
    },
    "requirements": {
      "protocol_files": [
        "plan.md",
        "context.md",
        "log.md"
      ],
      "step_sections": [
        "Context",
        "Risk Assessment",
        "Security Considerations",
        "Sub-tasks",
        "Verification",
        "Rollback",
        "Audit Notes",
        "Definition of Done"
      ]
    },
    "clarifications": [
      {
        "key": "data_classification",
        "question": "What data classification applies to this project?",
        "options": [
          "public",
          "internal",
          "confidential",
          "regulated"
        ],
        "recommended": "internal",
        "blocking": true,
        "applies_to": "onboarding"
      },
      {
        "key": "change_window",
        "question": "When are changes allowed to be deployed/merged?",
        "options": [
          "anytime",
          "business_hours",
          "scheduled"
        ],
        "recommended": "scheduled",
        "blocking": true,
        "applies_to": "planning"
      },
      {
        "key": "security_gate",
        "question": "Is a security gate required for merges?",
        "options": [
          "required",
          "optional"
        ],
        "recommended": "required",
        "blocking": true,
        "applies_to": "onboarding"
      },
      {
        "key": "audit_artifacts",
        "question": "Which artifacts must be captured for audit?",
        "recommended": [
          "quality-report.md",
          "CI logs",
          "Approvals/Reviewer sign-off"
        ],
        "blocking": true,
        "applies_to": "execution"
      },
      {
        "key": "required_checks_confirm",
        "question": "Confirm the required CI checks for this project.",
        "recommended": [
          "scripts/ci/test.sh",
          "scripts/ci/lint.sh",
          "scripts/ci/typecheck.sh",
          "scripts/ci/build.sh",
          "scripts/ci/security.sh"
        ],
        "blocking": true,
        "applies_to": "onboarding"
      }
    ],
    "enforcement": {
      "mode": "warn",
      "block_codes": [
        "policy.ci.required_check_missing",
        "policy.ci.required_check_not_executable",
        "policy.protocol.missing_file",
        "policy.step.missing_section",
        "policy.step.file_missing"
      ]
    },
    "constraints": {}
  }
}
```
