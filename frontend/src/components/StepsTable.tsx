import { StatusPill } from '@/components/ui/StatusPill';
import { Button } from '@/components/ui/Button';
import { DataTable, ColumnDef } from '@/components/DataTable';
import { cn } from '@/lib/cn';

interface Step {
  id: number;
  protocol_run_id: number;
  step_index: number;
  step_name: string;
  step_type: string;
  status: string;
  retries: number;
  model?: string;
  engine_id?: string;
  summary?: string;
  runtime_state?: Record<string, any>;
}

interface StepsTableProps {
  steps: Step[];
  onRunStep?: (stepId: number) => void;
  onRunQA?: (stepId: number) => void;
  onApprove?: (stepId: number) => void;
  className?: string;
}

export function StepsTable({ 
  steps, 
  onRunStep, 
  onRunQA, 
  onApprove, 
  className 
}: StepsTableProps) {
  const columns: ColumnDef<Step>[] = [
    {
      key: 'step_index',
      header: 'Idx',
      className: 'w-16',
    },
    {
      key: 'step_name',
      header: 'Name',
    },
    {
      key: 'step_type',
      header: 'Type',
      className: 'w-24',
    },
    {
      key: 'status',
      header: 'Status',
      cell: (status) => <StatusPill status={status} variant="small" />,
      className: 'w-32',
    },
    {
      key: 'engine_id',
      header: 'Engine',
      cell: (engine) => engine || '-',
      className: 'w-24',
    },
    {
      key: 'actions',
      header: 'Actions',
      cell: (_, step) => {
        const canRun = step.status === 'pending';
        const canRunQA = step.status === 'needs_qa';
        const canApprove = step.status === 'needs_qa';
        
        return (
          <div className="flex items-center gap-1">
            {canRun && onRunStep && (
              <Button 
                onClick={() => onRunStep(step.id)} 
                size="tiny" 
                variant="ghost"
              >
                Run
              </Button>
            )}
            {canRunQA && onRunQA && (
              <Button 
                onClick={() => onRunQA(step.id)} 
                size="tiny" 
                variant="ghost"
              >
                Run QA
              </Button>
            )}
            {canApprove && onApprove && (
              <Button 
                onClick={() => onApprove(step.id)} 
                size="tiny" 
                variant="primary"
              >
                Approve
              </Button>
            )}
          </div>
        );
      },
      className: 'w-48',
    },
  ];

  return (
    <DataTable
      data={steps}
      columns={columns}
      className={className}
      emptyMessage="No steps found"
    />
  );
}