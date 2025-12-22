import React from 'react';
import { Link } from '@tanstack/react-router';
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';

import { apiFetchJson } from '@/api/client';
import { type Clarification, type OnboardingSummary, type PolicyPack, type Project, type ProjectCreate, type ProjectPolicyUpdate } from '@/api/types';
import { useSettingsSnapshot } from '@/app/settings/store';
import { useDocumentVisible } from '@/app/polling';

type StepKey = 'repo' | 'defaults' | 'policy' | 'onboarding';

const classifications = [
  { value: '', label: '(none)' },
  { value: 'default', label: 'default' },
  { value: 'beginner-guided', label: 'beginner-guided' },
  { value: 'startup-fast', label: 'startup-fast' },
  { value: 'team-standard', label: 'team-standard' },
  { value: 'enterprise-compliance', label: 'enterprise-compliance' },
] as const;

export function ProjectsNewPage() {
  const settings = useSettingsSnapshot();
  const visible = useDocumentVisible();
  const pollEnabled = settings.polling.enabled && (!settings.polling.disableInBackground || visible);
  const [step, setStep] = React.useState<StepKey>('repo');
  const [draft, setDraft] = React.useState<ProjectCreate>({
    name: '',
    git_url: '',
    base_branch: 'main',
    ci_provider: '',
    project_classification: null,
    default_models: null,
    secrets: null,
  });
  const [defaultModelsJson, setDefaultModelsJson] = React.useState<string>('{}');
  const [created, setCreated] = React.useState<Project | null>(null);

  const packs = useQuery({
    queryKey: ['policyPacks', 'list'],
    queryFn: async () => await apiFetchJson<PolicyPack[]>('/policy_packs'),
    staleTime: 60_000,
  });

  const [policySelection, setPolicySelection] = React.useState<{
    packKey: string;
    packVersion: string;
    enforcementMode: string;
    repoLocalEnabled: boolean;
  }>({ packKey: '', packVersion: '', enforcementMode: 'warn', repoLocalEnabled: true });

  const createProject = useMutation({
    mutationFn: async () => {
      const parsedModels = (() => {
        try {
          const parsed = JSON.parse(defaultModelsJson || '{}');
          if (parsed && typeof parsed === 'object') return parsed as Record<string, string>;
        } catch {
          // ignore; validation below
        }
        return null;
      })();

      const payload: ProjectCreate = {
        ...draft,
        ci_provider: draft.ci_provider ? draft.ci_provider : null,
        project_classification: draft.project_classification ? draft.project_classification : null,
        default_models: parsedModels,
      };

      return await apiFetchJson<Project>('/projects', { method: 'POST', body: JSON.stringify(payload) });
    },
    onSuccess: async (project) => {
      setCreated(project);
      toast.success(`Project created: ${project.name} (#${project.id})`);
      // Apply policy selection (API sets policy via separate endpoint).
      if (policySelection.packKey) {
        const update: ProjectPolicyUpdate = {
          policy_pack_key: policySelection.packKey,
          policy_pack_version: policySelection.packVersion || null,
          policy_repo_local_enabled: policySelection.repoLocalEnabled,
          policy_enforcement_mode: policySelection.enforcementMode,
        };
        await apiFetchJson(`/projects/${project.id}/policy`, { method: 'PUT', body: JSON.stringify(update) });
        toast.success(`Policy applied: ${policySelection.packKey}@${policySelection.packVersion || 'latest'}`);
      }
      setStep('onboarding');
    },
    onError: (err) => {
      toast.error(String(err));
    },
  });

  const onboarding = useQuery({
    queryKey: ['projects', created?.id, 'onboarding'],
    enabled: Boolean(created?.id),
    queryFn: async () => await apiFetchJson<OnboardingSummary>(`/projects/${created!.id}/onboarding`),
    refetchInterval: pollEnabled ? settings.polling.intervalsMs.onboardingSummary : false,
  });

  const clarifications = useQuery({
    queryKey: ['projects', created?.id, 'clarifications', 'open'],
    enabled: Boolean(created?.id),
    queryFn: async () =>
      await apiFetchJson<Clarification[]>(`/projects/${created!.id}/clarifications?status=open`),
    refetchInterval: pollEnabled ? settings.polling.intervalsMs.recentEvents : false,
  });

  const answerClarification = useMutation({
    mutationFn: async (payload: { key: string; answer: string }) => {
      if (!created?.id) throw new Error('project not created');
      return await apiFetchJson<Clarification>(`/projects/${created.id}/clarifications/${payload.key}`, {
        method: 'POST',
        body: JSON.stringify({ answer: payload.answer }),
      });
    },
    onSuccess: async () => {
      await clarifications.refetch();
      toast.success('Clarification answered');
    },
    onError: (err) => toast.error(String(err)),
  });

  const steps: Array<{ key: StepKey; label: string }> = [
    { key: 'repo', label: 'Repo' },
    { key: 'defaults', label: 'Defaults' },
    { key: 'policy', label: 'Policy' },
    { key: 'onboarding', label: 'Onboarding' },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Create Project</h1>
        <Link to="/projects" className="rounded-md border border-border bg-bg-panel px-3 py-2 text-sm hover:bg-bg-muted">
          Back
        </Link>
      </div>

      <div className="flex flex-wrap gap-2 rounded-md border border-border bg-bg-panel p-2">
        {steps.map((s) => (
          <button
            key={s.key}
            type="button"
            onClick={() => setStep(s.key)}
            className={[
              'rounded-md px-3 py-2 text-sm',
              step === s.key ? 'bg-bg-muted text-fg' : 'text-fg-muted hover:bg-bg-muted hover:text-fg',
            ].join(' ')}
            disabled={s.key === 'onboarding' && !created}
          >
            {s.label}
          </button>
        ))}
      </div>

      {step === 'repo' && (
        <div className="rounded-md border border-border bg-bg-panel p-4">
          <div className="text-sm font-medium">Repo connect</div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">Project name</span>
              <input
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                placeholder="my-project"
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">Git URL / local path</span>
              <input
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={draft.git_url}
                onChange={(e) => setDraft({ ...draft, git_url: e.target.value })}
                placeholder="https://github.com/org/repo.git"
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">Base branch</span>
              <input
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={draft.base_branch}
                onChange={(e) => setDraft({ ...draft, base_branch: e.target.value })}
              />
            </label>
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">CI provider</span>
              <select
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={draft.ci_provider ?? ''}
                onChange={(e) => setDraft({ ...draft, ci_provider: e.target.value })}
              >
                <option value="">(none)</option>
                <option value="github">github</option>
                <option value="gitlab">gitlab</option>
              </select>
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="rounded-md border border-border bg-bg-muted px-3 py-2 text-sm hover:bg-bg-panel"
              onClick={() => setStep('defaults')}
              disabled={!draft.name || !draft.git_url}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {step === 'defaults' && (
        <div className="rounded-md border border-border bg-bg-panel p-4">
          <div className="text-sm font-medium">Classification & defaults</div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">Project classification</span>
              <select
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={draft.project_classification ?? ''}
                onChange={(e) =>
                  setDraft({ ...draft, project_classification: e.target.value ? e.target.value : null })
                }
              >
                {classifications.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="rounded-md border border-border bg-bg-muted p-3 text-xs text-fg-muted">
              Classifications map to default policy packs; you can override the pack on the next step.
            </div>

            <label className="grid gap-2 text-sm md:col-span-2">
              <span className="text-xs text-fg-muted">Default models (JSON)</span>
              <textarea
                className="min-h-28 rounded-md border border-border bg-bg-muted px-3 py-2 font-mono text-xs"
                value={defaultModelsJson}
                onChange={(e) => setDefaultModelsJson(e.target.value)}
              />
            </label>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="rounded-md border border-border bg-bg-muted px-3 py-2 text-sm hover:bg-bg-panel"
              onClick={() => setStep('policy')}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {step === 'policy' && (
        <div className="rounded-md border border-border bg-bg-panel p-4">
          <div className="text-sm font-medium">Policy selection</div>
          <div className="mt-1 text-xs text-fg-muted">Pick a policy pack and enforcement mode.</div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">Policy pack</span>
              <select
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={`${policySelection.packKey}@${policySelection.packVersion}`}
                onChange={(e) => {
                  const [k, v] = e.target.value.split('@');
                  setPolicySelection({ ...policySelection, packKey: k || '', packVersion: v || '' });
                }}
              >
                <option value="@">(keep classification default)</option>
                {(packs.data ?? []).map((p) => (
                  <option key={`${p.key}@${p.version}`} value={`${p.key}@${p.version}`}>
                    {p.key}@{p.version} — {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-2 text-sm">
              <span className="text-xs text-fg-muted">Enforcement mode</span>
              <select
                className="rounded-md border border-border bg-bg-muted px-3 py-2"
                value={policySelection.enforcementMode}
                onChange={(e) => setPolicySelection({ ...policySelection, enforcementMode: e.target.value })}
              >
                <option value="warn">warn</option>
                <option value="block">block</option>
                <option value="off">off</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={policySelection.repoLocalEnabled}
                onChange={(e) => setPolicySelection({ ...policySelection, repoLocalEnabled: e.target.checked })}
              />
              <span>Enable repo-local override</span>
            </label>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="rounded-md border border-border bg-bg-muted px-3 py-2 text-sm hover:bg-bg-panel"
              disabled={!draft.name || !draft.git_url || createProject.isPending}
              onClick={() => createProject.mutate()}
            >
              {createProject.isPending ? 'Creating…' : 'Create project'}
            </button>
            {createProject.error ? <div className="text-sm text-red-300">{String(createProject.error)}</div> : null}
          </div>
        </div>
      )}

      {step === 'onboarding' && (
        <div className="rounded-md border border-border bg-bg-panel p-4">
          <div className="text-sm font-medium">Onboarding</div>
          <div className="mt-1 text-xs text-fg-muted">Project setup runs automatically after creation.</div>

          {created ? (
            <div className="mt-3 text-sm">
              Created project{' '}
              <Link
                className="text-sky-300 hover:underline"
                to="/projects/$projectId"
                params={{ projectId: String(created.id) }}
                search={{ tab: 'onboarding' }}
              >
                #{created.id}
              </Link>
            </div>
          ) : null}

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border bg-bg-muted p-3">
              <div className="text-xs text-fg-muted">Status</div>
              <div className="mt-1 text-sm">{onboarding.data?.status ?? '...'}</div>
              {onboarding.data?.hint ? (
                <div className="mt-2 text-xs text-fg-muted">{onboarding.data.hint}</div>
              ) : null}
            </div>
            <div className="rounded-md border border-border bg-bg-muted p-3">
              <div className="text-xs text-fg-muted">Workspace</div>
              <div className="mt-1 text-sm">{onboarding.data?.workspace_path ?? '...'}</div>
            </div>
          </div>

          <div className="mt-4">
            <div className="text-sm font-medium">Stages</div>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              {(onboarding.data?.stages ?? []).map((s) => (
                <div key={s.key} className="rounded-md border border-border bg-bg-muted p-3">
                  <div className="text-sm">{s.name}</div>
                  <div className="mt-1 text-xs text-fg-muted">{s.status}</div>
                  {s.message ? <div className="mt-1 text-xs text-fg-muted">{s.message}</div> : null}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6">
            <div className="text-sm font-medium">Clarifications</div>
            <div className="mt-2 space-y-3">
              {(clarifications.data ?? []).length === 0 ? (
                <div className="text-sm text-fg-muted">No open clarifications.</div>
              ) : (
                (clarifications.data ?? []).map((c) => (
                  <div key={c.id} className="rounded-md border border-border bg-bg-muted p-3">
                    <div className="text-sm font-medium">
                      {c.blocking ? 'BLOCKING' : 'Info'} · {c.key}
                    </div>
                    <div className="mt-1 text-sm text-fg-muted">{c.question}</div>
                    <form
                      className="mt-3 flex gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = e.currentTarget;
                        const input = form.elements.namedItem('answer') as HTMLInputElement;
                        const val = input.value.trim();
                        if (!val) return;
                        answerClarification.mutate({ key: c.key, answer: val });
                        input.value = '';
                      }}
                    >
                      <input
                        name="answer"
                        className="min-w-0 flex-1 rounded-md border border-border bg-bg-panel px-3 py-2 text-sm"
                        placeholder="Answer…"
                      />
                      <button
                        type="submit"
                        className="rounded-md border border-border bg-bg-panel px-3 py-2 text-sm hover:bg-bg-muted"
                        disabled={answerClarification.isPending}
                      >
                        Submit
                      </button>
                    </form>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

