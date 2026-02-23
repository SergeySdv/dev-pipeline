"use client";

import type React from "react";
import { useState } from "react";
import Link from "next/link";

import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink,FileText, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusPill } from "@/components/ui/status-pill";
import { Textarea } from "@/components/ui/textarea";
import { useCreateProtocol,useProjectProtocols } from "@/lib/api";
import type { ProtocolRun } from "@/lib/api/types";
import { formatRelativeTime, truncateHash } from "@/lib/format";

interface ProtocolsTabProps {
  projectId: number;
}

const columns: ColumnDef<ProtocolRun>[] = [
  {
    accessorKey: "protocol_name",
    header: "Protocol",
    cell: ({ row }) => (
      <Link href={`/protocols/${row.original.id}`} className="font-medium hover:underline">
        {row.original.protocol_name}
      </Link>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <StatusPill status={row.original.status} size="sm" />,
  },
  {
    accessorKey: "base_branch",
    header: "Branch",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.base_branch}</span>,
  },
  {
    accessorKey: "spec_hash",
    header: "Spec",
    cell: ({ row }) => (
      <span className="text-muted-foreground font-mono text-xs">
        {truncateHash(row.original.spec_hash)}
      </span>
    ),
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{formatRelativeTime(row.original.created_at)}</span>
    ),
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <Link href={`/protocols/${row.original.id}`}>
        <Button variant="ghost" size="sm">
          <ExternalLink className="h-4 w-4" />
        </Button>
      </Link>
    ),
  },
];

export function ProtocolsTab({ projectId }: ProtocolsTabProps) {
  const { data: protocols, isLoading } = useProjectProtocols(projectId);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  if (isLoading) return <LoadingState message="Loading protocols..." />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Protocols</h3>
          <p className="text-muted-foreground text-sm">Protocol runs for this project</p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Protocol
            </Button>
          </DialogTrigger>
          <CreateProtocolDialog projectId={projectId} onClose={() => setIsCreateOpen(false)} />
        </Dialog>
      </div>

      {!protocols || protocols.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No protocols yet"
          description="Create a protocol to start automating development tasks."
          action={
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Protocol
            </Button>
          }
        />
      ) : (
        <DataTable columns={columns} data={protocols} />
      )}
    </div>
  );
}

function CreateProtocolDialog({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const createProtocol = useCreateProtocol();
  const [formData, setFormData] = useState({
    protocol_name: "",
    description: "",
    base_branch: "",
    template_source: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createProtocol.mutateAsync({
        projectId,
        data: {
          protocol_name: formData.protocol_name,
          description: formData.description || undefined,
          base_branch: formData.base_branch || undefined,
          template_source: formData.template_source || undefined,
        },
      });
      toast.success("Protocol created successfully");
      onClose();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create protocol");
    }
  };

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Create New Protocol</DialogTitle>
        <DialogDescription>Create a new protocol run for this project.</DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit}>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="protocol_name">Protocol Name</Label>
            <Input
              id="protocol_name"
              placeholder="0001-feature-auth"
              value={formData.protocol_name}
              onChange={(e) => setFormData((p) => ({ ...p, protocol_name: e.target.value }))}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description (optional)</Label>
            <Textarea
              id="description"
              placeholder="Implement user authentication..."
              value={formData.description}
              onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="base_branch">Base Branch (optional)</Label>
            <Input
              id="base_branch"
              placeholder="main"
              value={formData.base_branch}
              onChange={(e) => setFormData((p) => ({ ...p, base_branch: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="template_source">Template Source (optional)</Label>
            <Input
              id="template_source"
              placeholder="./templates/feature.yaml"
              value={formData.template_source}
              onChange={(e) => setFormData((p) => ({ ...p, template_source: e.target.value }))}
            />
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={createProtocol.isPending}>
            {createProtocol.isPending ? "Creating..." : "Create Protocol"}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  );
}
