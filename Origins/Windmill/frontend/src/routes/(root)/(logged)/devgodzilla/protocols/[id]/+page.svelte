<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { devGodzilla, type ProtocolRun, type StepRun, type Clarification, type QAResult, type ProtocolArtifactItem } from '$lib/devgodzilla/client';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert, Badge, Button, Tab, Tabs } from '$lib/components/common';
  import {
    ArrowLeft,
    FileText,
    ListChecks,
    ListTodo,
    MessageSquareText,
    Package,
    Pause,
    Play,
    RefreshCcw,
    ScrollText,
    ShieldCheck,
    XCircle
  } from 'lucide-svelte';
  import TaskDAGViewer from '$lib/devgodzilla/TaskDAGViewer.svelte';
  import ClarificationChat from '$lib/devgodzilla/ClarificationChat.svelte';
  import QADashboard from '$lib/devgodzilla/QADashboard.svelte';
  import ChecklistViewer from '$lib/devgodzilla/ChecklistViewer.svelte';
  import RunArtifactViewer from '$lib/devgodzilla/RunArtifactViewer.svelte';
  import FeedbackPanel from '$lib/devgodzilla/FeedbackPanel.svelte';
  import UserStoryTracker from '$lib/devgodzilla/UserStoryTracker.svelte';

  const protocolId = $derived(Number($page.params.id));

  let protocol: ProtocolRun | null = null;
  let steps: StepRun[] = [];
  let clarifications: Clarification[] = [];
  let loading = true;
  let error: string | null = null;
  let activeTab = 'steps';
  let selectedStep: StepRun | null = null;
  let qaResult: QAResult | null = null;
  let busy = false;
  let protocolArtifacts: ProtocolArtifactItem[] = [];
  let artifactFocus: { stepId: number; artifactId: string } | null = null;

  const tabs = [
    { id: 'steps', label: 'Steps' },
    { id: 'stories', label: 'Stories' },
    { id: 'qa', label: 'QA' },
    { id: 'checklist', label: 'Checklist' },
    { id: 'artifacts', label: 'Artifacts' },
    { id: 'clarifications', label: 'Clarifications' },
    { id: 'logs', label: 'Logs' }
  ];

  const currentStepId = $derived(steps.find(s => s.status === 'running')?.id ?? undefined);
  const selectedStepId = $derived(selectedStep?.id ?? currentStepId ?? steps[0]?.id);

  $effect(() => {
    if (steps.length > 0 && !selectedStep) {
      const autoSelectId = currentStepId ?? steps[0]?.id;
      if (autoSelectId) {
        selectedStep = steps.find(s => s.id === autoSelectId) ?? null;
      }
    }
  });

  onMount(async () => {
    await loadProtocol();
  });

  async function loadProtocol() {
    loading = true;
    error = null;
    try {
      protocol = await devGodzilla.getProtocol(protocolId);
      steps = await devGodzilla.listSteps(protocolId);
      clarifications = await devGodzilla.listClarifications(undefined, protocolId);
      protocolArtifacts = await devGodzilla.listProtocolArtifacts(protocolId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load protocol';
    } finally {
      loading = false;
    }
  }

  async function startProtocol() {
    try {
      protocol = await devGodzilla.startProtocol(protocolId);
      await loadProtocol();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to start protocol';
    }
  }

  async function pauseProtocol() {
    try {
      protocol = await devGodzilla.pauseProtocol(protocolId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to pause protocol';
    }
  }

  async function cancelProtocol() {
    if (!confirm('Are you sure you want to cancel this protocol?')) return;
    try {
      protocol = await devGodzilla.cancelProtocol(protocolId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to cancel protocol';
    }
  }

  function handleStepSelect(event: CustomEvent) {
    selectedStep = event.detail as StepRun;
  }

  async function handleClarificationAnswer(event: CustomEvent) {
    const { questionId, answer } = event.detail;
    try {
      await devGodzilla.answerClarification(questionId, answer);
      clarifications = await devGodzilla.listClarifications(undefined, protocolId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to answer clarification';
    }
  }

  async function executeSelectedStep() {
    if (!selectedStep) return;
    busy = true;
    error = null;
    try {
      await devGodzilla.executeStep(selectedStep.id);
      await loadProtocol();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to execute step';
    } finally {
      busy = false;
    }
  }

  async function runQAForSelectedStep() {
    if (!selectedStep) return;
    busy = true;
    error = null;
    try {
      qaResult = await devGodzilla.runStepQA(selectedStep.id);
      await loadProtocol();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to run QA';
    } finally {
      busy = false;
    }
  }

  function qaFindingsToFeedback() {
    if (!qaResult) return [];
    const findings = qaResult.gates.flatMap((g) =>
      (g.findings ?? []).map((f, idx) => ({
        id: `${g.id}:${idx}`,
        category: g.name,
        message: f.message,
        suggestedAction: qaResult.verdict === 'failed' ? 'retry' : 'block'
      }))
    );
    return findings.slice(0, 20);
  }

  function formatClarifications(items: Clarification[]) {
    return items.map(c => ({
      id: String(c.id),
      question: c.question,
      options: c.options ?? [],
      answer: c.answer ? JSON.stringify(c.answer) : undefined,
      status: c.status
    }));
  }
</script>

<svelte:head>
  <title>{protocol?.protocol_name || 'Protocol'} - DevGodzilla</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <div class="mb-4">
    <Button
      href="/devgodzilla/protocols"
      variant="subtle"
      unifiedSize="sm"
      btnClasses="max-w-fit"
      startIcon={{ icon: ArrowLeft }}
    >
      Back to protocols
    </Button>
  </div>

  {#if error}
    <Alert type="error" title="Failed to load protocol" class="mb-6">
      {error}
    </Alert>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-secondary">Loading protocol...</div>
  {:else if protocol}
    <PageHeader
      title={protocol.protocol_name}
      childrenWrapperDivClasses="flex-1 flex flex-row gap-2 flex-wrap justify-end items-center"
    >
      <Badge
        color={protocol.status === 'completed'
          ? 'green'
          : protocol.status === 'running'
            ? 'blue'
            : protocol.status === 'failed'
              ? 'red'
              : protocol.status === 'paused'
                ? 'yellow'
                : 'gray'}
      >
        {protocol.status}
      </Badge>

      {#if protocol.status === 'pending'}
        <Button variant="accent" unifiedSize="md" btnClasses="max-w-fit" startIcon={{ icon: Play }} on:click={startProtocol}>
          Start
        </Button>
      {:else if protocol.status === 'running'}
        <Button variant="default" unifiedSize="md" btnClasses="max-w-fit" startIcon={{ icon: Pause }} on:click={pauseProtocol}>
          Pause
        </Button>
        <Button
          variant="default"
          unifiedSize="md"
          btnClasses="max-w-fit"
          destructive
          startIcon={{ icon: XCircle }}
          on:click={cancelProtocol}
        >
          Cancel
        </Button>
      {:else if protocol.status === 'paused'}
        <Button variant="accent" unifiedSize="md" btnClasses="max-w-fit" startIcon={{ icon: Play }} on:click={startProtocol}>
          Resume
        </Button>
      {/if}
    </PageHeader>

    {#if protocol.summary}
      <div class="mt-2 mb-6 text-secondary">{protocol.summary}</div>
    {/if}

    <!-- Tabs -->
    <div class="w-full overflow-auto scrollbar-hidden pb-2 mb-6">
      <Tabs values={tabs.map(t => t.id)} bind:selected={activeTab}>
        <Tab value="steps" label="Steps" icon={FileText} />
        <Tab value="stories" label="Stories" icon={ListTodo} />
        <Tab value="qa" label="QA" icon={ShieldCheck} />
        <Tab value="checklist" label="Checklist" icon={ListChecks} />
        <Tab value="artifacts" label="Artifacts" icon={Package} />
        <Tab value="clarifications" label="Clarifications" icon={MessageSquareText} />
        <Tab value="logs" label="Logs" icon={ScrollText} />
      </Tabs>
    </div>

    <!-- Tab Content -->
    {#if activeTab === 'steps'}
      {#if steps.length === 0}
        <div class="text-center py-12 text-secondary">No steps yet. Start the protocol to begin execution.</div>
      {:else}
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="lg:col-span-1">
            <TaskDAGViewer {steps} {currentStepId} on:select={handleStepSelect} />
          </div>
          <div class="lg:col-span-2 space-y-6">
            <div class="bg-surface rounded-xl shadow-sm border p-6">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div class="text-sm text-secondary uppercase tracking-wider">Selected step</div>
                  <div class="text-lg font-semibold text-primary">{selectedStep?.step_name ?? '—'}</div>
                  <div class="text-sm text-secondary">{selectedStep?.status ?? ''}</div>
                </div>
                <div class="flex flex-wrap gap-2">
                  <Button
                    variant="default"
                    unifiedSize="md"
                    btnClasses="max-w-fit"
                    startIcon={{ icon: RefreshCcw }}
                    on:click={loadProtocol}
                    disabled={busy}
                  >
                    Refresh
                  </Button>
                  <Button
                    variant="accent"
                    unifiedSize="md"
                    btnClasses="max-w-fit"
                    startIcon={{ icon: Play }}
                    on:click={executeSelectedStep}
                    disabled={!selectedStep || busy}
                  >
                    Execute
                  </Button>
                  <Button
                    variant="default"
                    unifiedSize="md"
                    btnClasses="max-w-fit"
                    startIcon={{ icon: ShieldCheck }}
                    on:click={runQAForSelectedStep}
                    disabled={!selectedStep || busy}
                  >
                    Run QA
                  </Button>
                </div>
              </div>
            </div>

            <QADashboard qaResult={qaResult} />

            {#if qaResult && qaResult.verdict !== 'passed'}
              <FeedbackPanel findings={qaFindingsToFeedback()} />
            {/if}
          </div>
        </div>
      {/if}

    {:else if activeTab === 'qa'}
      <div class="space-y-4">
        <div class="flex justify-end">
          <Button
            variant="default"
            unifiedSize="md"
            btnClasses="max-w-fit"
            startIcon={{ icon: ShieldCheck }}
            on:click={runQAForSelectedStep}
            disabled={!selectedStep || busy}
          >
            Run QA for selected step
          </Button>
        </div>
        <QADashboard qaResult={qaResult} />
      </div>

    {:else if activeTab === 'stories'}
      <UserStoryTracker />

    {:else if activeTab === 'checklist'}
      <ChecklistViewer />

    {:else if activeTab === 'artifacts'}
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-1 bg-surface rounded-xl shadow-sm border overflow-hidden">
          <div class="p-4 border-b bg-surface-secondary">
            <div class="text-sm font-semibold text-primary">Protocol artifacts</div>
            <div class="text-xs text-secondary mt-1">Click an item to open it in the viewer.</div>
          </div>
          <div class="divide-y max-h-[520px] overflow-auto">
            {#if protocolArtifacts.length === 0}
              <div class="p-4 text-sm text-secondary">No artifacts yet.</div>
            {:else}
              {#each protocolArtifacts as a (a.id)}
                <button
                  class="w-full text-left p-3 hover:bg-surface-hover transition-colors"
                  on:click={() => {
                    artifactFocus = { stepId: a.step_run_id, artifactId: a.name };
                  }}
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <div class="text-sm font-medium text-primary truncate">{a.name}</div>
                      <div class="text-xs text-secondary truncate">
                        Step: {a.step_name || a.step_run_id} • {a.type} • {Math.round((a.size / 1024) * 10) / 10} KB
                      </div>
                    </div>
                    <div class="text-xs text-secondary shrink-0">→</div>
                  </div>
                </button>
              {/each}
            {/if}
          </div>
        </div>
        <div class="lg:col-span-2">
          <RunArtifactViewer
            stepId={(artifactFocus?.stepId ?? selectedStep?.id) ?? null}
            initialArtifactId={(artifactFocus?.artifactId ?? null)}
          />
        </div>
      </div>

    {:else if activeTab === 'clarifications'}
      {#if clarifications.length === 0}
        <div class="text-center py-12 text-secondary">No clarifications needed</div>
      {:else}
        <div class="h-[500px]">
          <ClarificationChat 
            questions={formatClarifications(clarifications)} 
            on:answer={handleClarificationAnswer} 
          />
        </div>
      {/if}

    {:else if activeTab === 'logs'}
      <div class="text-center py-12 text-secondary">Logs coming soon</div>
    {/if}
  {/if}
</div>
