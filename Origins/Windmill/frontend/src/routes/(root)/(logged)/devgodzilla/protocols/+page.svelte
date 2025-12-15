<script lang="ts">
  import { onMount } from 'svelte';
  import { devGodzilla, type Project, type ProtocolRun } from '$lib/devgodzilla/client';

  let protocols: ProtocolRun[] = [];
  let projects: Project[] = [];
  let loading = true;
  let error: string | null = null;
  let filterStatus = '';

  $: filteredProtocols = filterStatus 
    ? protocols.filter(p => p.status === filterStatus)
    : protocols;

  onMount(async () => {
    try {
      projects = await devGodzilla.listProjects();
      
      const allProtocols: ProtocolRun[] = [];
      for (const project of projects) {
        const projectProtocols = await devGodzilla.listProtocols(project.id);
        allProtocols.push(...projectProtocols);
      }
      protocols = allProtocols.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load protocols';
    } finally {
      loading = false;
    }
  });

  function getProjectName(projectId: number): string {
    const project = projects.find(p => p.id === projectId);
    return project?.name || `Project #${projectId}`;
  }
</script>

<svelte:head>
  <title>Protocols - DevGodzilla</title>
</svelte:head>

<div>
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold text-primary">Protocols</h1>
  </div>

  <!-- Filters -->
  <div class="flex gap-4 mb-6">
    <select
      bind:value={filterStatus}
      class="w-auto"
    >
      <option value="">All Statuses</option>
      <option value="pending">Pending</option>
      <option value="running">Running</option>
      <option value="completed">Completed</option>
      <option value="failed">Failed</option>
      <option value="cancelled">Cancelled</option>
    </select>
  </div>

  {#if error}
    <div class="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-4 mb-6">
      <p class="text-red-800 dark:text-red-200">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-secondary">Loading protocols...</div>
  {:else if filteredProtocols.length === 0}
    <div class="text-center py-12 text-secondary">
      {filterStatus ? 'No protocols with this status' : 'No protocols yet'}
    </div>
  {:else}
    <div class="bg-surface rounded-xl shadow-sm border overflow-hidden">
      <table class="w-full table-custom">
        <thead class="bg-surface-secondary">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Name</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Project</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Status</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Created</th>
            <th class="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y">
          {#each filteredProtocols as protocol}
            <tr class="hover:bg-surface-hover">
              <td class="px-6 py-4">
                <a href="/devgodzilla/protocols/{protocol.id}" class="font-medium text-accent hover:opacity-80">
                  {protocol.protocol_name}
                </a>
              </td>
              <td class="px-6 py-4 text-secondary">
                <a href="/devgodzilla/projects/{protocol.project_id}" class="hover:text-accent">
                  {getProjectName(protocol.project_id)}
                </a>
              </td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs rounded-full
                  {protocol.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' :
                   protocol.status === 'running' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200' :
                   protocol.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200' :
                   'bg-surface-secondary text-secondary'}">
                  {protocol.status}
                </span>
              </td>
              <td class="px-6 py-4 text-secondary text-sm">
                {new Date(protocol.created_at).toLocaleString()}
              </td>
              <td class="px-6 py-4 text-right">
                <a href="/devgodzilla/protocols/{protocol.id}" class="text-secondary hover:text-primary">
                  →
                </a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
