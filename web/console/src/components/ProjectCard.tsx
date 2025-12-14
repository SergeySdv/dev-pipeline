import { StatusPill } from '@/components/ui/StatusPill';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

interface Project {
  id: number;
  name: string;
  git_url: string;
  base_branch: string;
  ci_provider: string | null;
  policy_pack_key: string | null;
  policy_enforcement_mode: string | null;
  onboarding_status?: string;
  protocols_count?: number;
  last_protocol_at?: string;
  clarifications_pending?: number;
}

interface ProjectCardProps {
  project: Project;
  onSelect: (project: Project) => void;
  className?: string;
}

export function ProjectCard({ project, onSelect, className }: ProjectCardProps) {
  const hasWarnings = project.policy_enforcement_mode === 'warn';
  
  return (
    <div 
      className={cn(
        'border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer',
        className
      )}
      onClick={() => onSelect(project)}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-medium text-gray-900">{project.name}</h3>
        {hasWarnings && (
          <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">warn</span>
        )}
      </div>
      
      <div className="space-y-1 text-sm text-gray-600 mb-3">
        <div className="flex items-center gap-2">
          <span>{project.git_url}</span>
          <span>•</span>
          <span>{project.base_branch}</span>
          {project.ci_provider && (
            <>
              <span>•</span>
              <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{project.ci_provider}</span>
            </>
          )}
        </div>
      </div>
      
      <div className="flex items-center gap-3 text-xs">
        {project.onboarding_status && (
          <StatusPill status={project.onboarding_status} variant="small" />
        )}
        {project.policy_pack_key && (
          <span className="text-gray-500">
            policy: {project.policy_pack_key}
          </span>
        )}
        {project.protocols_count !== undefined && (
          <span className="text-gray-500">
            {project.protocols_count} protocols
          </span>
        )}
        {project.clarifications_pending && project.clarifications_pending > 0 && (
          <span className="text-yellow-600 font-medium">
            {project.clarifications_pending} clarifications pending
          </span>
        )}
      </div>
      
      {project.last_protocol_at && (
        <div className="mt-2 text-xs text-gray-500">
          Last: {new Date(project.last_protocol_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}