<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert, Badge, Button, Tab, Tabs, Drawer, DrawerContent } from '$lib/components/common';
  import { BookText, FileText, GitBranch, LayoutGrid, MessageSquareText, Play, Plus, Wand2, Settings, Archive, ArchiveRestore, Trash, MoreVertical, Save, Loader2 } from 'lucide-svelte';
  import {
    devGodzilla,
    type Project,
    type ProtocolRun,
    type Clarification,
    type SpecKitStatus,
    type SpecListItem
  } from '$lib/devgodzilla/client';
  import ConstitutionEditor from '$lib/devgodzilla/ConstitutionEditor.svelte';
  import Dropdown from '$lib/components/DropdownV2.svelte';
  import { sendUserToast } from '$lib/toast';

  const projectId = $derived(Number($page.params.id));

  let project: Project | null = $state(null);
  let protocols: ProtocolRun[] = $state([]);
  let clarifications: Clarification[] = $state([]);
  let specKitStatus: SpecKitStatus | null = $state(null);
  let specs: SpecListItem[] = $state([]);
  let constitutionContent = $state('');
  let featureDescription = $state('');
  let runningSpecKit = $state(false);

  let loading = $state(true);
  let error: string | null = $state(null);
  let saved = $state(false);
  let activeTab = $state('overview');
  let actionInProgress = $state(false);
  let confirmDelete = $state(false);
  
  // Settings form state
  let editName = $state('');
  let editDescription = $state('');
  let editGitUrl = $state('');
  let editBaseBranch = $state('');

  onMount(async () => {
    await load();
  });

  async function load() {
    loading = true;
    error = null;
    saved = false;

    try {
      project = await devGodzilla.getProject(projectId);

      // Best-effort: these may fail if project isn't fully onboarded yet.
      protocols = await devGodzilla.listProtocols(projectId);
      clarifications = await devGodzilla.listClarifications(projectId, undefined, 'open');

      try {
        specKitStatus = await devGodzilla.getSpecKitStatus(projectId);
        specs = (await devGodzilla.listSpecs(projectId)) ?? [];
      } catch {
        specKitStatus = null;
        specs = [];
      }

      try {
        const c = await devGodzilla.getConstitution(projectId);
        constitutionContent = c.content;
      } catch {
        constitutionContent = '';
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load project';
    } finally {
      loading = false;
      if (project) {
        editName = project.name;
        editDescription = project.description || '';
        editGitUrl = project.git_url || '';
        editBaseBranch = project.base_branch;
      }
    }
  }

  async function saveConstitution(event: CustomEvent<{ constitution: string; version: string }>) {
    try {
      await devGodzilla.updateConstitution(projectId, event.detail.constitution);
      saved = true;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save constitution';
    }
  }

  async function initSpecKit() {
    runningSpecKit = true;
    error = null;
    try {
      await devGodzilla.initSpecKit(projectId);
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to init SpecKit';
    } finally {
      runningSpecKit = false;
    }
  }

  async function runSpecify() {
    runningSpecKit = true;
    error = null;
    try {
      const res = await devGodzilla.runSpecify(projectId, featureDescription);
      if (!res.success) {
        throw new Error(res.error || 'Specify failed');
      }
      featureDescription = '';
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to generate spec';
    } finally {
      runningSpecKit = false;
    }
  }

  async function runPlanForSpec(spec: SpecListItem) {
    runningSpecKit = true;
    error = null;
    try {
      const primary = `${spec.path}/feature-spec.md`;
      const fallback = `${spec.path}/spec.md`;
      let res = await devGodzilla.runPlan(projectId, primary);
      if (!res.success) {
        res = await devGodzilla.runPlan(projectId, fallback);
      }
      if (!res.success) {
        throw new Error(res.error || 'Plan failed');
      }
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to generate plan';
    } finally {
      runningSpecKit = false;
    }
  }

  async function runTasksForSpec(spec: SpecListItem) {
    runningSpecKit = true;
    error = null;
    try {
      const planPath = `${spec.path}/plan.md`;
      const res = await devGodzilla.runTasks(projectId, planPath);
      if (!res.success) {
        throw new Error(res.error || 'Tasks failed');
      }
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to generate tasks';
    } finally {
      runningSpecKit = false;
    }
  }

  function statusColor(status?: string) {
    if (!status) return 'gray';
    if (status === 'active') return 'green';
    if (status === 'archived') return 'gray';
    if (status === 'blocked') return 'yellow';
    if (status === 'failed') return 'red';
    return 'gray';
  }

  async function saveSettings() {
    if (!project) return;
    actionInProgress = true;
    error = null;
    try {
      project = await devGodzilla.updateProject(project.id, {
        name: editName,
        description: editDescription || undefined,
        git_url: editGitUrl || undefined,
        base_branch: editBaseBranch,
      });
      sendUserToast('Project settings saved');
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save settings';
    } finally {
      actionInProgress = false;
    }
  }

  async function archiveProject() {
    if (!project) return;
    actionInProgress = true;
    try {
      project = await devGodzilla.archiveProject(project.id);
      sendUserToast(`Project "${project.name}" archived`);
    } catch (e) {
      sendUserToast(`Failed to archive: ${e}`, true);
    } finally {
      actionInProgress = false;
    }
  }

  async function unarchiveProject() {
    if (!project) return;
    actionInProgress = true;
    try {
      project = await devGodzilla.unarchiveProject(project.id);
      sendUserToast(`Project "${project.name}" restored`);
    } catch (e) {
      sendUserToast(`Failed to unarchive: ${e}`, true);
    } finally {
      actionInProgress = false;
    }
  }

  async function deleteProject() {
    if (!project) return;
    actionInProgress = true;
    try {
      await devGodzilla.deleteProject(project.id);
      sendUserToast(`Project "${project.name}" deleted`);
      goto('/devgodzilla/projects');
    } catch (e) {
      sendUserToast(`Failed to delete: ${e}`, true);
    } finally {
      actionInProgress = false;
      confirmDelete = false;
    }
  }
</script>

<svelte:head>
  <title>{project?.name || 'Project'} - DevGodzilla</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  {#if project}
    <PageHeader
      title={project.name}
      childrenWrapperDivClasses="flex-1 flex flex-row gap-2 flex-wrap justify-end items-center"
    >
      <Badge color={statusColor(project.status)}>
        {project.status || 'active'}
      </Badge>
      {#if project.description}
        <span class="text-sm text-secondary hidden md:inline">{project.description}</span>
      {/if}
      <Button href="/devgodzilla/protocols" variant="default" unifiedSize="md" btnClasses="max-w-fit" startIcon={{ icon: Play }}>
        Protocols
      </Button>
      <Dropdown
        items={[
          project.status === 'archived'
            ? { displayName: 'Unarchive', action: unarchiveProject, icon: ArchiveRestore }
            : { displayName: 'Archive', action: archiveProject, icon: Archive },
          { displayName: 'Delete', action: () => confirmDelete = true, icon: Trash, type: 'delete' },
        ]}
      >
        <button class="p-2 rounded-lg hover:bg-surface-secondary">
          <MoreVertical class="w-4 h-4 text-secondary" />
        </button>
      </Dropdown>
    </PageHeader>
  {:else}
    <PageHeader title="Project" />
  {/if}

  {#if error}
    <Alert type="error" title="Project error" class="mb-6">
      {error}
    </Alert>
  {/if}

  {#if saved}
    <Alert type="success" title="Constitution saved" class="mb-6" />
  {/if}

  {#if loading}
    <div class="text-center py-12 text-secondary">Loading project...</div>
  {:else if !project}
    <div class="text-center py-12 text-secondary">Project not found</div>
  {:else}
    <div class="w-full overflow-auto scrollbar-hidden pb-2 mb-6">
      <Tabs values={['overview', 'constitution', 'specs', 'protocols', 'clarifications', 'settings']} bind:selected={activeTab}>
        <Tab value="overview" label="Overview" icon={LayoutGrid} />
        <Tab value="constitution" label="Constitution" icon={BookText} />
        <Tab value="specs" label="SpecKit" icon={FileText} />
        <Tab value="protocols" label="Protocols" icon={GitBranch} />
        <Tab value="clarifications" label="Clarifications" icon={MessageSquareText} />
        <Tab value="settings" label="Settings" icon={Settings} />
      </Tabs>
    </div>

    {#if activeTab === 'overview'}
      <div class="bg-surface rounded-xl shadow-sm border p-6">
        <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt class="text-xs text-secondary uppercase tracking-wider">Repository</dt>
            <dd class="text-sm text-primary mt-1 break-all">{project.git_url || '—'}</dd>
          </div>
          <div>
            <dt class="text-xs text-secondary uppercase tracking-wider">Base branch</dt>
            <dd class="text-sm text-primary mt-1">{project.base_branch}</dd>
          </div>
          <div>
            <dt class="text-xs text-secondary uppercase tracking-wider">Local path</dt>
            <dd class="text-sm text-primary mt-1 break-all">{project.local_path || '—'}</dd>
          </div>
          <div>
            <dt class="text-xs text-secondary uppercase tracking-wider">Created</dt>
            <dd class="text-sm text-primary mt-1">{project.created_at ? new Date(project.created_at).toLocaleString() : '—'}</dd>
          </div>
        </dl>
      </div>

    {:else if activeTab === 'constitution'}
      <div class="h-[600px]">
        <ConstitutionEditor constitution={constitutionContent} version={project.constitution_version || '1.0'} on:save={saveConstitution} />
      </div>

    {:else if activeTab === 'specs'}
      <div class="bg-surface rounded-xl shadow-sm border p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="text-sm font-semibold text-primary">SpecKit</div>
            <div class="text-sm text-secondary">
              {#if specKitStatus?.initialized}
                Initialized. {specKitStatus.spec_count} specs.
              {:else}
                Not initialized yet.
              {/if}
            </div>
          </div>
          {#if !specKitStatus?.initialized}
            <Button
              variant="accent"
              unifiedSize="md"
              btnClasses="max-w-fit"
              startIcon={{ icon: Plus }}
              on:click={initSpecKit}
              disabled={runningSpecKit}
            >
              Initialize
            </Button>
          {/if}
        </div>

        <div class="mt-6 bg-surface-secondary rounded-lg p-4 border">
          <div class="text-sm font-semibold text-primary mb-1">Generate a new spec</div>
          <div class="text-sm text-secondary mb-3">
            Provide a short feature description; DevGodzilla will create `.specify/specs/.../spec.md`.
          </div>
          <div class="flex flex-col sm:flex-row gap-2">
            <input
              class="flex-1"
              bind:value={featureDescription}
              placeholder="e.g. Add OAuth2 login with GitHub"
            />
            <Button
              variant="accent"
              unifiedSize="md"
              btnClasses="max-w-fit"
              startIcon={{ icon: Wand2 }}
              on:click={runSpecify}
              disabled={!featureDescription.trim() || runningSpecKit || !specKitStatus?.initialized}
            >
              Specify
            </Button>
          </div>
          {#if !specKitStatus?.initialized}
            <div class="mt-2 text-sm text-secondary">
              Initialize SpecKit first.
            </div>
          {/if}
        </div>

        <div class="mt-4">
          {#if specs.length === 0}
            <div class="text-secondary">No specs found.</div>
          {:else}
            <div class="space-y-2">
              {#each specs as s}
                <div class="flex items-center justify-between gap-4 border rounded-lg p-3">
                  <div>
                    <div class="text-sm font-medium text-primary">{s.name}</div>
                    <div class="text-xs text-secondary font-mono break-all">{s.path}</div>
                  </div>
                  <div class="flex items-center gap-2 flex-wrap justify-end">
                    <Badge color={s.has_spec ? 'green' : 'gray'}>spec</Badge>
                    <Badge color={s.has_plan ? 'green' : 'gray'}>plan</Badge>
                    <Badge color={s.has_tasks ? 'green' : 'gray'}>tasks</Badge>
                    <Button
                      variant="default"
                      unifiedSize="sm"
                      btnClasses="max-w-fit"
                      on:click={() => runPlanForSpec(s)}
                      disabled={!s.has_spec || runningSpecKit}
                    >
                      Plan
                    </Button>
                    <Button
                      variant="default"
                      unifiedSize="sm"
                      btnClasses="max-w-fit"
                      on:click={() => runTasksForSpec(s)}
                      disabled={!s.has_plan || runningSpecKit}
                    >
                      Tasks
                    </Button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>

    {:else if activeTab === 'protocols'}
      {#if protocols.length === 0}
        <div class="text-center py-12 text-secondary">No protocols for this project yet.</div>
      {:else}
        <div class="bg-surface rounded-xl shadow-sm border overflow-hidden">
          <table class="w-full table-custom">
            <thead class="bg-surface-secondary">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Name</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Created</th>
                <th class="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y">
              {#each protocols as p}
                <tr class="hover:bg-surface-hover">
                  <td class="px-6 py-4">
                    <a href="/devgodzilla/protocols/{p.id}" class="font-medium text-accent hover:opacity-80">{p.protocol_name}</a>
                  </td>
                  <td class="px-6 py-4 text-secondary text-sm">{p.status}</td>
                  <td class="px-6 py-4 text-secondary text-sm">{new Date(p.created_at).toLocaleString()}</td>
                  <td class="px-6 py-4 text-right">
                    <a href="/devgodzilla/protocols/{p.id}" class="text-secondary hover:text-primary">→</a>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

    {:else if activeTab === 'clarifications'}
      {#if clarifications.length === 0}
        <div class="text-center py-12 text-secondary">No open clarifications for this project.</div>
      {:else}
        <div class="bg-surface rounded-xl shadow-sm border overflow-hidden">
          <div class="p-6 border-b bg-surface-secondary">
            <div class="text-sm font-semibold text-primary">Open clarifications</div>
          </div>
          <div class="divide-y">
            {#each clarifications as c}
              <div class="p-6">
                <div class="text-sm text-primary">{c.question}</div>
                <div class="text-xs text-secondary mt-1">Protocol: {c.protocol_run_id || '—'}</div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

    {:else if activeTab === 'settings'}
      <div class="space-y-6">
        <!-- Project Settings Form -->
        <div class="bg-surface rounded-xl shadow-sm border p-6">
          <h2 class="text-lg font-semibold text-primary mb-4">Project Settings</h2>
          <div class="space-y-4 max-w-xl">
            <div>
              <label for="name" class="block text-sm font-medium text-secondary mb-1">Project Name</label>
              <input 
                id="name"
                type="text" 
                bind:value={editName}
                class="w-full px-3 py-2 bg-surface border rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <div>
              <label for="description" class="block text-sm font-medium text-secondary mb-1">Description</label>
              <textarea 
                id="description"
                bind:value={editDescription}
                rows={2}
                placeholder="Optional description..."
                class="w-full px-3 py-2 bg-surface border rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-accent resize-none"
              ></textarea>
            </div>
            <div>
              <label for="git_url" class="block text-sm font-medium text-secondary mb-1">Git Repository URL</label>
              <input 
                id="git_url"
                type="text" 
                bind:value={editGitUrl}
                placeholder="https://github.com/..."
                class="w-full px-3 py-2 bg-surface border rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <div>
              <label for="branch" class="block text-sm font-medium text-secondary mb-1">Base Branch</label>
              <input 
                id="branch"
                type="text" 
                bind:value={editBaseBranch}
                class="w-full px-3 py-2 bg-surface border rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <div class="pt-2">
              <Button variant="accent" on:click={saveSettings} disabled={actionInProgress} startIcon={{ icon: actionInProgress ? Loader2 : Save }}>
                {actionInProgress ? 'Saving...' : 'Save settings'}
              </Button>
            </div>
          </div>
        </div>

        <!-- Danger Zone -->
        <div class="bg-surface rounded-xl shadow-sm border border-red-200 dark:border-red-900 p-6">
          <h2 class="text-lg font-semibold text-red-600 dark:text-red-400 mb-4">Danger Zone</h2>
          <div class="space-y-4">
            <div class="flex items-center justify-between gap-4 p-4 border border-red-200 dark:border-red-800 rounded-lg bg-red-50 dark:bg-red-900/10">
              <div>
                <p class="font-medium text-primary">Archive this project</p>
                <p class="text-sm text-secondary">Mark as archived. You can unarchive it later.</p>
              </div>
              {#if project.status === 'archived'}
                <Button variant="subtle" on:click={unarchiveProject} disabled={actionInProgress} startIcon={{ icon: ArchiveRestore }}>
                  Unarchive
                </Button>
              {:else}
                <Button variant="subtle" on:click={archiveProject} disabled={actionInProgress} startIcon={{ icon: Archive }}>
                  Archive
                </Button>
              {/if}
            </div>
            <div class="flex items-center justify-between gap-4 p-4 border border-red-200 dark:border-red-800 rounded-lg bg-red-50 dark:bg-red-900/10">
              <div>
                <p class="font-medium text-primary">Delete this project</p>
                <p class="text-sm text-secondary">Permanently delete the project and all data. This cannot be undone.</p>
              </div>
              <Button variant="subtle" color="red" on:click={() => confirmDelete = true} disabled={actionInProgress} startIcon={{ icon: Trash }}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- Delete Confirmation Drawer -->
<Drawer bind:open={confirmDelete} size="400px">
  <DrawerContent title="Delete Project?" on:close={() => confirmDelete = false}>
    <div class="p-4">
      <p class="text-primary mb-4">
        Are you sure you want to delete <strong>{project?.name}</strong>?
      </p>
      <p class="text-sm text-secondary mb-6">
        This will permanently delete the project and all associated protocols, steps, and clarifications. This action cannot be undone.
      </p>
      <div class="flex gap-2 justify-end">
        <Button variant="subtle" on:click={() => confirmDelete = false}>Cancel</Button>
        <Button variant="accent" color="red" on:click={deleteProject} disabled={actionInProgress}>
          {actionInProgress ? 'Deleting...' : 'Delete Project'}
        </Button>
      </div>
    </div>
  </DrawerContent>
</Drawer>
