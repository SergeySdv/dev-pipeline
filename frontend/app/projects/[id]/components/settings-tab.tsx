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

  useEffect(() => {
    if (project) {
      setName(project.name);
      setGitUrl(project.git_url);
      setBaseBranch(project.base_branch);
    }
  }, [project]);

  if (isLoading || !project) return <LoadingState message="Loading settings..." />;

  const hasChanges =
    name !== project.name || gitUrl !== project.git_url || baseBranch !== project.base_branch;

  const handleSave = async () => {
    try {
      await updateProject.mutateAsync({
        projectId,
        data: { name, git_url: gitUrl, base_branch: baseBranch },
      });
      toast.success("Project updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update project");
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
          <Button onClick={handleSave} disabled={updateProject.isPending || !hasChanges}>
            <Save className="mr-2 h-4 w-4" />
            {updateProject.isPending ? "Saving..." : "Save Changes"}
          </Button>
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
