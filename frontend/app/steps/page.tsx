import Link from "next/link";

import { ArrowRight, FileStack, GitBranch, PlaySquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function StepsIndexPage() {
  return (
    <div className="container py-8 space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Steps</h1>
        <p className="text-muted-foreground">
          Open step details from a protocol or a run. This index exists so console navigation and
          prefetching have a stable destination.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              Protocols
            </CardTitle>
            <CardDescription>Browse protocol steps in execution order.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/protocols">
              <Button variant="outline" className="w-full justify-between">
                Open Protocols
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlaySquare className="h-5 w-5" />
              Runs
            </CardTitle>
            <CardDescription>Inspect execution runs and jump back to their steps.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/runs">
              <Button variant="outline" className="w-full justify-between">
                Open Runs
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileStack className="h-5 w-5" />
              Projects
            </CardTitle>
            <CardDescription>Open a project and drill into task-cycle and protocol work.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/projects">
              <Button variant="outline" className="w-full justify-between">
                Open Projects
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
