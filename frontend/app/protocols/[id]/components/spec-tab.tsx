"use client";

import Link from "next/link";

import { FileJson } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/ui/code-block";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { StatusPill } from "@/components/ui/status-pill";
import { useProtocolSpec } from "@/lib/api";
import { formatDateTime,truncateHash } from "@/lib/format";
import { getSpecificationReviewPath } from "@/lib/project-routes";

interface SpecTabProps {
  protocolId: number;
}

export function SpecTab({ protocolId }: SpecTabProps) {
  const { data: spec, isLoading } = useProtocolSpec(protocolId);

  if (isLoading) return <LoadingState message="Loading spec..." />;

  if (!spec) {
    return (
      <EmptyState
        icon={FileJson}
        title="No spec available"
        description="Protocol spec has not been generated yet."
      />
    );
  }

  const reviewPath =
    typeof spec.spec_run_id === "number" ? getSpecificationReviewPath(spec.spec_run_id) : null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Protocol Specification</CardTitle>
              <CardDescription>
                Hash: {truncateHash(spec.spec_hash, 16)}
                {spec.validated_at && ` • Validated: ${formatDateTime(spec.validated_at)}`}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {reviewPath && (
                <Link href={reviewPath}>
                  <Button variant="outline" size="sm">
                    Review Implementation
                  </Button>
                </Link>
              )}
              <StatusPill
                status={
                  spec.validation_status === "valid"
                    ? "completed"
                    : spec.validation_status === "invalid"
                      ? "failed"
                      : "pending"
                }
                size="sm"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <CodeBlock code={spec.spec} title="spec.json" maxHeight="600px" />
        </CardContent>
      </Card>
    </div>
  );
}
