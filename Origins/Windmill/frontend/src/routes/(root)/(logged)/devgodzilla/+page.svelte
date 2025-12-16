<script lang="ts">
  import { onMount } from 'svelte';
  import { devGodzilla, type Project, type ProtocolRun } from '$lib/devgodzilla/client';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert, Button } from '$lib/components/common';
  import { Folder, Zap, CheckCircle2, HelpCircle, Plus, Settings2 } from 'lucide-svelte';

  let projects: Project[] = $state([]);
  let recentProtocols: ProtocolRun[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);

  // Stats
  let stats = $state({
    totalProjects: 0,
    activeProtocols: 0,
    completedToday: 0,
    pendingClarifications: 0
  });

  onMount(async () => {
    try {
      // Load projects
      projects = await devGodzilla.listProjects();
      stats.totalProjects = projects.length;

      // Load recent protocols (from all projects)
      const allProtocols: ProtocolRun[] = [];
      for (const project of projects.slice(0, 5)) {
        const protocols = await devGodzilla.listProtocols(project.id);
        allProtocols.push(...protocols);
      }
      recentProtocols = allProtocols
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 10);

      stats.activeProtocols = allProtocols.filter(p => p.status === 'running').length;
      stats.completedToday = allProtocols.filter(p => {
        const today = new Date().toDateString();
        return p.status === 'completed' && new Date(p.created_at).toDateString() === today;
      }).length;

      // Pending clarifications
      const openClarifications = await devGodzilla.listClarifications(undefined, undefined, 'open');
      stats.pendingClarifications = openClarifications.length;

    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load dashboard data';
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>DevGodzilla - Dashboard</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <PageHeader title="DevGodzilla Dashboard" />

  {#if error}
    <Alert type="error" title="Failed to load DevGodzilla dashboard">
      {error}
    </Alert>
  {/if}

  <!-- Stats Cards -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-secondary">Total Projects</p>
          <p class="text-3xl font-bold text-primary">{stats.totalProjects}</p>
        </div>
        <Folder class="text-secondary" size={26} />
      </div>
    </div>

    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-secondary">Active Protocols</p>
          <p class="text-3xl font-bold text-accent">{stats.activeProtocols}</p>
        </div>
        <Zap class="text-secondary" size={26} />
      </div>
    </div>

    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-secondary">Completed Today</p>
          <p class="text-3xl font-bold text-green-600 dark:text-green-400">{stats.completedToday}</p>
        </div>
        <CheckCircle2 class="text-secondary" size={26} />
      </div>
    </div>

    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-secondary">Pending Clarifications</p>
          <p class="text-3xl font-bold text-amber-600 dark:text-amber-400">{stats.pendingClarifications}</p>
        </div>
        <HelpCircle class="text-secondary" size={26} />
      </div>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Recent Projects -->
    <div class="bg-surface rounded-xl shadow-sm border">
      <div class="p-6 border-b flex justify-between items-center">
        <h2 class="text-lg font-semibold text-primary">Recent Projects</h2>
        <a href="/devgodzilla/projects" class="text-sm text-accent hover:opacity-80">View all →</a>
      </div>
      <div class="divide-y">
        {#if loading}
          <div class="p-6 text-center text-secondary">Loading...</div>
        {:else if projects.length === 0}
          <div class="p-6 text-center text-secondary">
            No projects yet. 
            <a href="/devgodzilla/projects/new" class="text-accent hover:underline">Create one</a>
          </div>
        {:else}
          {#each projects.slice(0, 5) as project}
            <a 
              href="/devgodzilla/projects/{project.id}" 
              class="block p-4 hover:bg-surface-hover transition-colors"
            >
              <div class="flex justify-between items-center">
                <div>
                  <p class="font-medium text-primary">{project.name}</p>
                  <p class="text-sm text-secondary">{project.git_url || 'No repository'}</p>
                </div>
                <span class="text-secondary">→</span>
              </div>
            </a>
          {/each}
        {/if}
      </div>
    </div>

    <!-- Recent Protocols -->
    <div class="bg-surface rounded-xl shadow-sm border">
      <div class="p-6 border-b flex justify-between items-center">
        <h2 class="text-lg font-semibold text-primary">Recent Protocols</h2>
        <a href="/devgodzilla/protocols" class="text-sm text-accent hover:opacity-80">View all →</a>
      </div>
      <div class="divide-y">
        {#if loading}
          <div class="p-6 text-center text-secondary">Loading...</div>
        {:else if recentProtocols.length === 0}
          <div class="p-6 text-center text-secondary">No protocol runs yet</div>
        {:else}
          {#each recentProtocols.slice(0, 5) as protocol}
            <a 
              href="/devgodzilla/protocols/{protocol.id}" 
              class="block p-4 hover:bg-surface-hover transition-colors"
            >
              <div class="flex justify-between items-center">
                <div>
                  <p class="font-medium text-primary">{protocol.protocol_name}</p>
                  <p class="text-sm text-secondary">
                    {new Date(protocol.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span class="px-2 py-1 text-xs rounded-full
                  {protocol.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' :
                   protocol.status === 'running' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200' :
                   protocol.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200' :
                   'bg-surface-secondary text-secondary'}">
                  {protocol.status}
                </span>
              </div>
            </a>
          {/each}
        {/if}
      </div>
    </div>
  </div>

  <!-- Quick Actions -->
  <div class="mt-8">
    <h2 class="text-lg font-semibold text-primary mb-4">Quick Actions</h2>
    <div class="flex flex-wrap gap-4">
      <Button
        href="/devgodzilla/projects/new"
        variant="accent"
        unifiedSize="md"
        btnClasses="max-w-fit"
        startIcon={{ icon: Plus }}
      >
        New Project
      </Button>
      <Button
        href="/devgodzilla/agents"
        variant="default"
        unifiedSize="md"
        btnClasses="max-w-fit"
        startIcon={{ icon: Settings2 }}
      >
        Configure Agents
      </Button>
    </div>
  </div>
</div>
