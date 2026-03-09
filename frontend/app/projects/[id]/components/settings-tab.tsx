"use client";

import { useEffect,useState } from "react";

import { Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import { useProject, useUpdateProject } from "@/lib/api";

interface SettingsTabProps {
  projectId: number;
}

export function SettingsTab({ projectId }: SettingsTabProps) {
  const { data: project, isLoading } = useProject(projectId);
  const updateProject = useUpdateProject();
  const [name, setName] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [baseBranch, setBaseBranch] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubTokenDirty, setGithubTokenDirty] = useState(false);

  useEffect(() => {
    if (project) {
      setName(project.name);
      setGitUrl(project.git_url);
      setBaseBranch(project.base_branch);
      setGithubToken("");
      setGithubTokenDirty(false);
    }
  }, [project]);

  if (isLoading || !project) return <LoadingState message="Loading settings..." />;

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
