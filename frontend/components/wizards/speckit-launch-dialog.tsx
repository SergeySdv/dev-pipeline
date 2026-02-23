"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { FileText, FolderKanban,Lightbulb, ListTodo } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { useProjects } from "@/lib/api";
import { cn } from "@/lib/utils";

export type SpecKitWizardAction = "generate-specs" | "design-solution" | "implement-feature";

const ACTION_COPY: Record<
  SpecKitWizardAction,
  { title: string; description: string; icon: typeof FileText; button: string }
> = {
  "generate-specs": {
    title: "Generate Specification",
    description: "Pick a project to launch the SpecKit specification wizard.",
    icon: FileText,
    button: "Launch Spec Wizard",
  },
  "design-solution": {
    title: "Design Solution",
    description: "Pick a project to generate an implementation plan.",
    icon: Lightbulb,
    button: "Launch Plan Wizard",
  },
  "implement-feature": {
    title: "Generate Tasks",
    description: "Pick a project to generate implementation tasks.",
    icon: ListTodo,
    button: "Launch Task Wizard",
  },
};

interface SpecKitLaunchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  action?: SpecKitWizardAction;
}

export function SpecKitLaunchDialog({ open, onOpenChange, action }: SpecKitLaunchDialogProps) {
  const router = useRouter();
  const { data: projects, isLoading, error } = useProjects();
  const [search, setSearch] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [manualAction, setManualAction] = useState<SpecKitWizardAction | null>(null);
  const selectedAction = manualAction ?? action ?? "generate-specs";

  const { title, description, icon: Icon, button } = ACTION_COPY[selectedAction];

  const filteredProjects = useMemo(() => {
    if (!projects) return [];
    const query = search.trim().toLowerCase();
    if (!query) return projects;
    return projects.filter(
      (project) =>
        project.name.toLowerCase().includes(query) || project.git_url.toLowerCase().includes(query)
    );
  }, [projects, search]);

  const handleLaunch = () => {
    if (!selectedProjectId) {
      toast.error("Select a project to continue");
      return;
    }
    router.push(`/projects/${selectedProjectId}?wizard=${selectedAction}`);
    onOpenChange(false);
    setSearch("");
    setSelectedProjectId("");
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      setSearch("");
      setSelectedProjectId("");
      setManualAction(null);
    }
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent size="2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Icon className="text-primary h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <LoadingState message="Loading projects..." />
        ) : error ? (
          <div className="text-muted-foreground py-6 text-sm">Failed to load projects.</div>
        ) : projects && projects.length > 0 ? (
          <div className="space-y-4">
            <div className="bg-muted/60 inline-flex items-center gap-1 rounded-full p-1">
              {(Object.keys(ACTION_COPY) as SpecKitWizardAction[]).map((key) => (
                <button
                  key={key}
                  onClick={() => setManualAction(key)}
                  className={cn(
                    "flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                    selectedAction === key
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {key === "generate-specs" && <FileText className="mr-2 h-4 w-4" />}
                  {key === "design-solution" && <Lightbulb className="mr-2 h-4 w-4" />}
                  {key === "implement-feature" && <ListTodo className="mr-2 h-4 w-4" />}
                  {key === "generate-specs" && "Spec"}
                  {key === "design-solution" && "Plan"}
                  {key === "implement-feature" && "Tasks"}
                </button>
              ))}
            </div>
            <Input
              placeholder="Search projects..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {filteredProjects.length === 0 ? (
                <div className="text-muted-foreground py-4 text-center text-sm">
                  No projects match this search.
                </div>
              ) : (
                filteredProjects.map((project) => {
                  const isSelected = selectedProjectId === project.id.toString();
                  return (
                    <button
                      key={project.id}
                      type="button"
                      onClick={() => setSelectedProjectId(project.id.toString())}
                      className={cn(
                        "w-full rounded-lg border px-4 py-3 text-left transition-colors",
                        isSelected
                          ? "border-primary bg-primary/10"
                          : "border-muted hover:border-primary/60 hover:bg-muted/60"
                      )}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <FolderKanban className="text-muted-foreground h-4 w-4" />
                            <span className="font-medium">{project.name}</span>
                          </div>
                          <p className="text-muted-foreground mt-1 text-xs">{project.git_url}</p>
                        </div>
                        <div className="text-muted-foreground flex items-center gap-2 text-xs">
                          {project.policy_pack_key && (
                            <Badge variant="secondary">{project.policy_pack_key}</Badge>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        ) : (
          <div className="text-muted-foreground py-6 text-center text-sm">
            No projects yet. Create one in Projects to launch SpecKit.
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            Cancel
          </Button>
          <Button onClick={handleLaunch} disabled={!selectedProjectId}>
            {button}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
