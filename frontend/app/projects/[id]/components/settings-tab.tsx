"use client";

import { useEffect, useState } from "react";

import { Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAgentAssignments,
  useAgents,
  useProject,
  useUpdateAgentAssignments,
  useUpdateProject,
} from "@/lib/api";
import type { Agent, AgentAssignments } from "@/lib/api/types";

type AgentReasoningOption = {
  value: string;
  label?: string | null;
  description?: string | null;
};

type AgentModelOption = {
  value: string;
  label?: string | null;
  description?: string | null;
  default_reasoning_effort?: string | null;
  reasoning_efforts?: AgentReasoningOption[];
};

type StageAssignmentDraft = {
  agent_id: string;
  model_override: string;
  reasoning_effort: string;
};

const AUTO_REASONING_VALUE = "__auto_reasoning__";

const taskCycleStages = [
  {
    key: "task_cycle_context",
    label: "Build Context",
    description: "Context pack generation and task analysis.",
  },
  {
    key: "task_cycle_implement",
    label: "Implement",
    description: "Code changes and implementation runs.",
  },
  {
    key: "task_cycle_review",
    label: "Review",
    description: "Implementation review before QA.",
  },
  {
    key: "task_cycle_qa",
    label: "QA",
    description: "Prompt QA and validation gates.",
  },
  {
    key: "task_cycle_pr_ready",
    label: "Mark PR Ready",
    description: "Final PR-ready confirmation step.",
  },
] as const;

interface SettingsTabProps {
  projectId: number;
}

export function SettingsTab({ projectId }: SettingsTabProps) {
  const { data: project, isLoading } = useProject(projectId);
  const { data: agents = [] } = useAgents(projectId);
  const { data: assignmentsData } = useAgentAssignments(projectId);
  const updateProject = useUpdateProject();
  const updateAssignments = useUpdateAgentAssignments();
  const [name, setName] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [baseBranch, setBaseBranch] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubTokenDirty, setGithubTokenDirty] = useState(false);
  const [stageDrafts, setStageDrafts] = useState<Record<string, StageAssignmentDraft>>({});

  useEffect(() => {
    if (project) {
      setName(project.name);
      setGitUrl(project.git_url);
      setBaseBranch(project.base_branch);
      setGithubToken("");
      setGithubTokenDirty(false);
    }
  }, [project]);

  useEffect(() => {
    const nextDrafts: Record<string, StageAssignmentDraft> = {};
    taskCycleStages.forEach((stage) => {
      const assignment = assignmentsData?.assignments?.[stage.key];
      const metadata =
        assignment?.metadata && typeof assignment.metadata === "object" ? assignment.metadata : {};
      nextDrafts[stage.key] = {
        agent_id: assignment?.agent_id || "",
        model_override: assignment?.model_override || "",
        reasoning_effort:
          typeof metadata.reasoning_effort === "string" ? metadata.reasoning_effort : "",
      };
    });
    setStageDrafts(nextDrafts);
  }, [assignmentsData]);

  if (isLoading || !project) return <LoadingState message="Loading settings..." />;

  const stageHasChanges = taskCycleStages.some((stage) => {
    const baseline = assignmentsData?.assignments?.[stage.key];
    const metadata =
      baseline?.metadata && typeof baseline.metadata === "object" ? baseline.metadata : {};
    const draft = stageDrafts[stage.key] || {
      agent_id: "",
      model_override: "",
      reasoning_effort: "",
    };
    return (
      (baseline?.agent_id || "") !== draft.agent_id ||
      (baseline?.model_override || "") !== draft.model_override ||
      (typeof metadata.reasoning_effort === "string" ? metadata.reasoning_effort : "") !==
        draft.reasoning_effort
    );
  });

  const hasChanges =
    name !== project.name ||
    gitUrl !== project.git_url ||
    baseBranch !== project.base_branch ||
    (githubTokenDirty && githubToken.trim().length > 0);

  const handleSave = async () => {
    try {
      await updateProject.mutateAsync({
        projectId,
        data: {
          name,
          git_url: gitUrl,
          base_branch: baseBranch,
          ...(githubTokenDirty && githubToken.trim()
            ? { github_token: githubToken.trim() }
            : {}),
        },
      });
      setGithubToken("");
      setGithubTokenDirty(false);
      toast.success("Project updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update project");
    }
  };

  const handleClearGithubToken = async () => {
    try {
      await updateProject.mutateAsync({
        projectId,
        data: { github_token: null },
      });
      setGithubToken("");
      setGithubTokenDirty(false);
      toast.success("Saved GitHub token removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to clear GitHub token");
    }
  };

  const handleSaveTaskCycleAssignments = async () => {
    const toNullable = (value: string) => {
      const trimmed = value.trim();
      return trimmed.length > 0 ? trimmed : null;
    };

    const assignments = Object.fromEntries(
      taskCycleStages.flatMap((stage) => {
        const baseline = assignmentsData?.assignments?.[stage.key];
        const baselineMetadata =
          baseline?.metadata && typeof baseline.metadata === "object" ? baseline.metadata : {};
        const draft = stageDrafts[stage.key] || {
          agent_id: "",
          model_override: "",
          reasoning_effort: "",
        };
        const nextAgent = toNullable(draft.agent_id);
        const nextModel = toNullable(draft.model_override);
        const nextReasoning = toNullable(draft.reasoning_effort);
        const currentAgent = toNullable(baseline?.agent_id || "");
        const currentModel = toNullable(baseline?.model_override || "");
        const currentReasoning =
          typeof baselineMetadata.reasoning_effort === "string"
            ? toNullable(baselineMetadata.reasoning_effort)
            : null;

        if (
          nextAgent === currentAgent &&
          nextModel === currentModel &&
          nextReasoning === currentReasoning
        ) {
          return [];
        }

        return [
          [
            stage.key,
            {
              agent_id: nextAgent,
              model_override: nextModel,
              metadata: nextReasoning ? { reasoning_effort: nextReasoning } : null,
            },
          ],
        ];
      })
    );

    if (Object.keys(assignments).length === 0) {
      toast.success("Brownfield stage assignments already up to date");
      return;
    }

    try {
      await updateAssignments.mutateAsync({
        projectId,
        assignments: {
          assignments,
        } satisfies AgentAssignments,
      });
      toast.success("Brownfield task-cycle assignments updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update brownfield assignments");
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Project Settings</CardTitle>
          <CardDescription>Update project configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="project-name">Project Name</Label>
            <Input id="project-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="git-url">Git URL</Label>
            <Input
              id="git-url"
              value={gitUrl}
              onChange={(e) => setGitUrl(e.target.value)}
              placeholder="https://github.com/org/repo.git"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="base-branch">Base Branch</Label>
            <Input
              id="base-branch"
              value={baseBranch}
              onChange={(e) => setBaseBranch(e.target.value)}
              placeholder="main"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="github-token">GitHub Token</Label>
            <Input
              id="github-token"
              type="password"
              value={githubToken}
              onChange={(e) => {
                setGithubToken(e.target.value);
                setGithubTokenDirty(true);
              }}
              placeholder={
                project.github_token_configured
                  ? "Leave blank to keep saved token"
                  : "Optional: needed for private GitHub clone/push/PR"
              }
            />
            <p className="text-sm text-muted-foreground">
              Status: {project.github_token_configured ? "configured" : "not configured"}.
              Saved tokens are used for GitHub clone, push, and pull request steps for this project.
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={updateProject.isPending || !hasChanges}>
              <Save className="mr-2 h-4 w-4" />
              {updateProject.isPending ? "Saving..." : "Save Changes"}
            </Button>
            {project.github_token_configured && (
              <Button
                variant="outline"
                onClick={handleClearGithubToken}
                disabled={updateProject.isPending}
              >
                Clear GitHub Token
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Brownfield Task Cycle</CardTitle>
          <CardDescription>
            Choose the agent, model, and reasoning profile for each brownfield stage. Runtime
            execution applies immediately for Implement and QA; the other stages persist here so
            the project-level routing is explicit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {taskCycleStages.map((stage) => (
            <TaskCycleStageAssignmentCard
              key={stage.key}
              label={stage.label}
              description={stage.description}
              agents={agents}
              value={
                stageDrafts[stage.key] || {
                  agent_id: "",
                  model_override: "",
                  reasoning_effort: "",
                }
              }
              onChange={(nextValue) =>
                setStageDrafts((prev) => ({
                  ...prev,
                  [stage.key]: nextValue,
                }))
              }
            />
          ))}
          <div className="flex justify-end">
            <Button onClick={handleSaveTaskCycleAssignments} disabled={updateAssignments.isPending || !stageHasChanges}>
              <Save className="mr-2 h-4 w-4" />
              {updateAssignments.isPending ? "Saving..." : "Save Brownfield Routing"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Policy Configuration</CardTitle>
          <CardDescription>
            Current policy settings (read-only, edit via Policy tab)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Policy Pack:</span>
              <span className="ml-2 font-medium">{project.policy_pack_key || "None"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Version:</span>
              <span className="ml-2 font-medium">{project.policy_pack_version || "-"}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Enforcement:</span>
              <span className="ml-2 font-medium capitalize">
                {project.policy_enforcement_mode || "off"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Effective Hash:</span>
              <span className="ml-2 font-mono text-xs">{project.policy_effective_hash || "-"}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TaskCycleStageAssignmentCard({
  label,
  description,
  agents,
  value,
  onChange,
}: {
  label: string;
  description: string;
  agents: Agent[];
  value: StageAssignmentDraft;
  onChange: (value: StageAssignmentDraft) => void;
}) {
  const selectedAgent = agents.find((agent) => agent.id === value.agent_id);
  const models = selectedAgent?.available_models || [];
  const selectedModel =
    models.find((model) => model.value === value.model_override) ||
    models.find((model) => model.value === selectedAgent?.default_model);
  const reasoningOptions = selectedModel?.reasoning_efforts || [];
  const reasoningValue = value.reasoning_effort || AUTO_REASONING_VALUE;

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div>
        <h3 className="font-medium">{label}</h3>
        <p className="text-muted-foreground text-sm">{description}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <Label>{label} Agent</Label>
          <Select
            value={value.agent_id || "__default_agent__"}
            onValueChange={(nextAgentId) => {
              const normalizedAgentId = nextAgentId === "__default_agent__" ? "" : nextAgentId;
              const nextAgent = agents.find((agent) => agent.id === normalizedAgentId);
              const nextModels = nextAgent?.available_models || [];
              const nextModel = nextModels.find((model) => model.value === value.model_override);
              const resolvedModelOverride = nextModel ? value.model_override : "";
              const selectedNextModel =
                nextModel ||
                nextModels.find((model) => model.value === nextAgent?.default_model) ||
                null;
              const nextReasoningOptions = selectedNextModel?.reasoning_efforts || [];
              const nextReasoning = nextReasoningOptions.some(
                (option) => option.value === value.reasoning_effort
              )
                ? value.reasoning_effort
                : "";
              onChange({
                agent_id: normalizedAgentId,
                model_override: resolvedModelOverride,
                reasoning_effort: nextReasoning,
              });
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Use project default agent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__default_agent__">Use project default agent</SelectItem>
              {agents
                .filter((agent) => agent.enabled ?? true)
                .map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>
                    {agent.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>{label} Model</Label>
          <Select
            value={value.model_override || "__default_model__"}
            onValueChange={(nextModel) => {
              const normalizedModel = nextModel === "__default_model__" ? "" : nextModel;
              const nextModelOption = models.find((model) => model.value === normalizedModel);
              const nextReasoningOptions = nextModelOption?.reasoning_efforts || [];
              const nextReasoning = nextReasoningOptions.some(
                (option) => option.value === value.reasoning_effort
              )
                ? value.reasoning_effort
                : "";
              onChange({
                ...value,
                model_override: normalizedModel,
                reasoning_effort: nextReasoning,
              });
            }}
            disabled={!selectedAgent || models.length === 0}
          >
            <SelectTrigger>
              <SelectValue
                placeholder={selectedAgent ? "Use agent default model" : "Select an agent first"}
              />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__default_model__">Use agent default model</SelectItem>
              {models.map((model) => (
                <SelectItem key={model.value} value={model.value}>
                  {model.label || model.value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedModel?.description && (
            <p className="text-muted-foreground text-xs">{selectedModel.description}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>{label} Reasoning</Label>
          <Select
            value={reasoningValue}
            onValueChange={(nextReasoning) =>
              onChange({
                ...value,
                reasoning_effort: nextReasoning === AUTO_REASONING_VALUE ? "" : nextReasoning,
              })
            }
            disabled={!selectedAgent || reasoningOptions.length === 0}
          >
            <SelectTrigger>
              <SelectValue
                placeholder={
                  reasoningOptions.length > 0 ? "Use model default reasoning" : "Not supported"
                }
              />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={AUTO_REASONING_VALUE}>Use model default</SelectItem>
              {reasoningOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {reasoningOptions.length > 0 ? (
            <p className="text-muted-foreground text-xs">
              {reasoningValue === AUTO_REASONING_VALUE
                ? `Uses the selected model default${
                    selectedModel?.default_reasoning_effort
                      ? ` (${selectedModel.default_reasoning_effort})`
                      : ""
                  }.`
                : reasoningOptions.find((option) => option.value === value.reasoning_effort)
                    ?.description || "Controls how much deliberate reasoning the agent spends."}
            </p>
          ) : (
            <p className="text-muted-foreground text-xs">
              This agent/model combination does not expose reasoning controls.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
