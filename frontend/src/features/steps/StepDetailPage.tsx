import { useState } from 'react';
import { useParams } from '@tanstack/react-router';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusPill } from '@/components/ui/StatusPill';
import { StepsTable } from '@/components/StepsTable';
import { Timeline } from '@/components/Timeline';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { useStep, useStepRuns, useStepPolicyFindings } from './hooks';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { toast } from 'sonner';

export function StepDetailPage() {
  const { stepId } = useParams({ from: '/steps/$stepId' });
  const queryClient = useQueryClient();
  const { data: step, isLoading: stepLoading, error: stepError } = useStep(parseInt(stepId));
  const { data: runs } = useStepRuns(parseInt(stepId));
  const { data: findings } = useStepPolicyFindings(parseInt(stepId));
  const [activeTab, setActiveTab] = useState('overview');

  const runStepMutation = useMutation({
    mutationFn: () => apiClient.fetch(`/steps/${stepId}/actions/run`, { method: 'POST' }),
    onSuccess: () => {
      toast.success('Step execution started');
      queryClient.invalidateQueries({ queryKey: ['steps', 'detail', parseInt(stepId)] });
    },
    onError: (error) => {
      toast.error(`Failed to run step: ${error}`);
    },
  });

  const runQAMutation = useMutation({
    mutationFn: () => apiClient.fetch(`/steps/${stepId}/actions/run_qa`, { method: 'POST' }),
    onSuccess: () => {
      toast.success('QA run started');
      queryClient.invalidateQueries({ queryKey: ['steps', 'runs', parseInt(stepId)] });
    },
    onError: (error) => {
      toast.error(`Failed to run QA: ${error}`);
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => apiClient.fetch(`/steps/${stepId}/actions/approve`, { method: 'POST' }),
    onSuccess: () => {
      toast.success('Step approved');
      queryClient.invalidateQueries({ queryKey: ['steps', 'detail', parseInt(stepId)] });
    },
    onError: (error) => {
      toast.error(`Failed to approve step: ${error}`);
    },
  });

  if (stepLoading) {
    return <LoadingState message="Loading step details..." />;
  }

  if (stepError || !step) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">Failed to load step details</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  const handleRunStep = () => runStepMutation.mutate();
  const handleRunQA = () => runQAMutation.mutate();
  const handleApprove = () => approveMutation.mutate();

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">
              Step: {step.step_name}
            </h1>
            <div className="flex items-center gap-4 text-sm text-gray-600">
              <span>Protocol: {step.protocol_run_id}</span>
              <span>Index: {step.step_index}</span>
              <span>Type: {step.step_type}</span>
              <StatusPill status={step.status} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {step.status === 'pending' && (
            <Button onClick={handleRunStep} loading={runStepMutation.isPending}>
              Run
            </Button>
          )}
          {step.status === 'needs_qa' && (
            <>
              <Button onClick={handleRunQA} loading={runQAMutation.isPending} variant="secondary">
                Run QA
              </Button>
              <Button onClick={handleApprove} loading={approveMutation.isPending}>
                Approve
              </Button>
            </>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mt-4">
          <div>
            <span className="text-gray-500">Retries:</span>
            <div className="font-medium">{step.retries}</div>
          </div>
          <div>
            <span className="text-gray-500">Engine:</span>
            <div className="font-medium">{step.engine_id || '-'}</div>
          </div>
          {step.model && (
            <div>
              <span className="text-gray-500">Model:</span>
              <div className="font-medium">{step.model}</div>
            </div>
          )}
        </div>

        {step.runtime_state && Object.keys(step.runtime_state).length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Runtime State</h3>
            <CodeBlock code={JSON.stringify(step.runtime_state, null, 2)} language="json" />
          </div>
        )}

        {step.summary && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Summary</h3>
            <p className="text-sm text-gray-600">{step.summary}</p>
          </div>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="policy">Policy Findings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Step Overview</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Step Name:</span>
                  <div>{step.step_name}</div>
                </div>
                <div>
                  <span className="font-medium">Step Type:</span>
                  <div>{step.step_type}</div>
                </div>
                <div>
                  <span className="font-medium">Status:</span>
                  <div><StatusPill status={step.status} /></div>
                </div>
                <div>
                  <span className="font-medium">Retries:</span>
                  <div>{step.retries}</div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="runs">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Step Runs</h3>
            {runs && runs.length > 0 ? (
              <div className="space-y-2">
                {runs.map((run) => (
                  <div key={run.run_id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-mono text-sm">{run.run_id.slice(0, 12)}...</span>
                        <span className="ml-2 text-sm text-gray-600">{run.run_kind}</span>
                      </div>
                      <StatusPill status={run.status} variant="small" />
                    </div>
                    <div className="mt-2 text-sm text-gray-600">
                      Created: {new Date(run.created_at).toLocaleString()}
                      {run.finished_at && (
                        <span className="ml-4">
                          Finished: {new Date(run.finished_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No runs yet" description="Execute this step to see run history." />
            )}
          </div>
        </TabsContent>

        <TabsContent value="policy">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Policy Findings</h3>
            {findings && findings.length > 0 ? (
              <div className="space-y-3">
                {findings.map((finding, index) => (
                  <div key={index} className="border border-yellow-200 bg-yellow-50 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-yellow-600">⚡</span>
                      <div className="flex-1">
                        <div className="font-medium text-sm">{finding.code}</div>
                        <div className="text-sm text-gray-700 mt-1">{finding.message}</div>
                        {finding.suggestion && (
                          <div className="text-sm text-gray-600 mt-2">
                            <span className="font-medium">Suggestion:</span> {finding.suggestion}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No policy findings" description="This step complies with all applicable policies." />
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}