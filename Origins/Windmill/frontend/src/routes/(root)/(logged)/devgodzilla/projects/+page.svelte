<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert, Badge, Button, Drawer, DrawerContent } from '$lib/components/common';
  import { Plus, Search, Archive, ArchiveRestore, Trash, Pen, MoreVertical, Folder, GitBranch, Clock } from 'lucide-svelte';
  import { devGodzilla, type Project } from '$lib/devgodzilla/client';
  import Dropdown from '$lib/components/DropdownV2.svelte';
  import { sendUserToast } from '$lib/toast';

  let projects: Project[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let searchQuery = $state('');
  let filterStatus = $state('all');
  let actionInProgress = $state(false);
  let confirmDeleteProject: Project | null = $state(null);

  // Stats derived from projects
  const stats = $derived({
    total: projects.length,
    active: projects.filter(p => p.status === 'active' || !p.status).length,
    archived: projects.filter(p => p.status === 'archived').length,
  });

  // Filtered projects
  const filteredProjects = $derived(() => {
    let result = projects;
    
    // Filter by status
    if (filterStatus === 'active') {
      result = result.filter(p => p.status === 'active' || !p.status);
    } else if (filterStatus === 'archived') {
      result = result.filter(p => p.status === 'archived');
    }
    
    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(p =>
        p.name.toLowerCase().includes(query) ||
        (p.description?.toLowerCase().includes(query)) ||
        (p.git_url?.toLowerCase().includes(query))
      );
    }
    
    return result;
  });

  onMount(async () => {
    await loadProjects();
  });

  async function loadProjects() {
    loading = true;
    error = null;
    try {
      projects = await devGodzilla.listProjects();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load projects';
    } finally {
      loading = false;
    }
  }

  async function archiveProject(project: Project) {
    actionInProgress = true;
    try {
      await devGodzilla.archiveProject(project.id);
      sendUserToast(`Archived "${project.name}"`);
      await loadProjects();
    } catch (e) {
      sendUserToast(`Failed to archive project: ${e}`, true);
    } finally {
      actionInProgress = false;
    }
  }

  async function unarchiveProject(project: Project) {
    actionInProgress = true;
    try {
      await devGodzilla.unarchiveProject(project.id);
      sendUserToast(`Unarchived "${project.name}"`);
      await loadProjects();
    } catch (e) {
      sendUserToast(`Failed to unarchive project: ${e}`, true);
    } finally {
      actionInProgress = false;
    }
  }

  async function deleteProject() {
    if (!confirmDeleteProject) return;
    actionInProgress = true;
    try {
      await devGodzilla.deleteProject(confirmDeleteProject.id);
      sendUserToast(`Deleted "${confirmDeleteProject.name}"`);
      confirmDeleteProject = null;
      await loadProjects();
    } catch (e) {
      sendUserToast(`Failed to delete project: ${e}`, true);
    } finally {
      actionInProgress = false;
    }
  }

  function statusColor(status?: string) {
    if (!status || status === 'active') return 'green';
    if (status === 'archived') return 'gray';
    if (status === 'blocked') return 'yellow';
    if (status === 'failed') return 'red';
    return 'gray';
  }

  function formatDate(dateStr?: string) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString();
  }
</script>

<svelte:head>
  <title>Projects - DevGodzilla</title>
</svelte:head>

<!-- Delete Confirmation Drawer -->
<Drawer bind:open={() => confirmDeleteProject !== null, (v) => { if (!v) confirmDeleteProject = null; }} size="400px">
  <DrawerContent title="Delete Project?" on:close={() => confirmDeleteProject = null}>
    {#if confirmDeleteProject}
      <div class="p-4">
        <p class="text-primary mb-4">
          Are you sure you want to delete <strong>{confirmDeleteProject.name}</strong>?
        </p>
        <p class="text-sm text-secondary mb-6">
          This will permanently delete the project and all associated protocols, steps, and clarifications. This action cannot be undone.
        </p>
        <div class="flex gap-2 justify-end">
          <Button variant="subtle" on:click={() => confirmDeleteProject = null}>Cancel</Button>
          <Button variant="accent" color="red" on:click={deleteProject} disabled={actionInProgress}>
            {actionInProgress ? 'Deleting...' : 'Delete Project'}
          </Button>
        </div>
      </div>
    {/if}
  </DrawerContent>
</Drawer>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <PageHeader title="Projects" childrenWrapperDivClasses="flex-1 flex flex-row gap-2 flex-wrap justify-end items-center">
    <Button href="/devgodzilla/projects/new" variant="accent" unifiedSize="md" btnClasses="max-w-fit" startIcon={{ icon: Plus }}>
      New project
    </Button>
  </PageHeader>

  {#if error}
    <Alert type="error" title="Failed to load projects" class="mb-6">
      {error}
    </Alert>
  {/if}

  <!-- Stats Cards -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
    <button 
      class="bg-surface rounded-xl shadow-sm border p-4 text-left transition-all hover:shadow-md {filterStatus === 'all' ? 'ring-2 ring-accent' : ''}"
      onclick={() => filterStatus = 'all'}
    >
      <div class="flex items-center gap-3">
        <div class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
          <Folder class="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p class="text-2xl font-bold text-primary">{stats.total}</p>
          <p class="text-sm text-secondary">Total Projects</p>
        </div>
      </div>
    </button>

    <button 
      class="bg-surface rounded-xl shadow-sm border p-4 text-left transition-all hover:shadow-md {filterStatus === 'active' ? 'ring-2 ring-accent' : ''}"
      onclick={() => filterStatus = 'active'}
    >
      <div class="flex items-center gap-3">
        <div class="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
          <GitBranch class="w-5 h-5 text-green-600 dark:text-green-400" />
        </div>
        <div>
          <p class="text-2xl font-bold text-primary">{stats.active}</p>
          <p class="text-sm text-secondary">Active</p>
        </div>
      </div>
    </button>

    <button 
      class="bg-surface rounded-xl shadow-sm border p-4 text-left transition-all hover:shadow-md {filterStatus === 'archived' ? 'ring-2 ring-accent' : ''}"
      onclick={() => filterStatus = 'archived'}
    >
      <div class="flex items-center gap-3">
        <div class="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <Archive class="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </div>
        <div>
          <p class="text-2xl font-bold text-primary">{stats.archived}</p>
          <p class="text-sm text-secondary">Archived</p>
        </div>
      </div>
    </button>
  </div>

  <!-- Search Bar -->
  <div class="mb-4">
    <div class="relative">
      <Search class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-secondary" />
      <input
        type="text"
        placeholder="Search projects..."
        class="w-full pl-10 pr-4 py-2 bg-surface border rounded-lg text-primary focus:outline-none focus:ring-2 focus:ring-accent"
        bind:value={searchQuery}
      />
    </div>
  </div>

  {#if loading}
    <div class="text-center py-12 text-secondary">Loading projects...</div>
  {:else if filteredProjects().length === 0}
    <div class="bg-surface rounded-xl shadow-sm border p-12 text-center">
      <Folder class="w-12 h-12 text-secondary mx-auto mb-4" />
      <p class="text-secondary mb-2">
        {searchQuery || filterStatus !== 'all' ? 'No projects match your filters' : 'No projects yet'}
      </p>
      {#if !searchQuery && filterStatus === 'all'}
        <a class="text-accent hover:opacity-80" href="/devgodzilla/projects/new">Create your first project</a>
      {:else}
        <button class="text-accent hover:opacity-80" onclick={() => { searchQuery = ''; filterStatus = 'all'; }}>
          Clear filters
        </button>
      {/if}
    </div>
  {:else}
    <div class="bg-surface rounded-xl shadow-sm border overflow-hidden">
      <table class="w-full table-custom">
        <thead class="bg-surface-secondary">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Name</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider hidden md:table-cell">Repository</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider hidden sm:table-cell">Branch</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">Status</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider hidden lg:table-cell">Created</th>
            <th class="px-6 py-3 w-10"></th>
          </tr>
        </thead>
        <tbody class="divide-y">
          {#each filteredProjects() as project}
            <tr class="hover:bg-surface-hover group">
              <td class="px-6 py-4">
                <a href="/devgodzilla/projects/{project.id}" class="font-medium text-accent hover:opacity-80">
                  {project.name}
                </a>
                {#if project.description}
                  <p class="text-xs text-secondary truncate max-w-xs">{project.description}</p>
                {/if}
              </td>
              <td class="px-6 py-4 text-secondary text-sm hidden md:table-cell">
                <span class="truncate max-w-xs block">{project.git_url || '—'}</span>
              </td>
              <td class="px-6 py-4 text-secondary text-sm hidden sm:table-cell">
                <code class="text-xs bg-surface-secondary px-2 py-0.5 rounded">{project.base_branch}</code>
              </td>
              <td class="px-6 py-4">
                <Badge color={statusColor(project.status)} small>
                  {project.status || 'active'}
                </Badge>
              </td>
              <td class="px-6 py-4 text-secondary text-sm hidden lg:table-cell">
                {formatDate(project.created_at)}
              </td>
              <td class="px-6 py-4 text-right">
                <Dropdown
                  items={[
                    { displayName: 'Edit', action: () => goto(`/devgodzilla/projects/${project.id}`), icon: Pen },
                    project.status === 'archived'
                      ? { displayName: 'Unarchive', action: () => unarchiveProject(project), icon: ArchiveRestore }
                      : { displayName: 'Archive', action: () => archiveProject(project), icon: Archive },
                    { displayName: 'Delete', action: () => confirmDeleteProject = project, icon: Trash, type: 'delete' },
                  ]}
                >
                  <button class="p-1 rounded hover:bg-surface-secondary opacity-0 group-hover:opacity-100 transition-opacity">
                    <MoreVertical class="w-4 h-4 text-secondary" />
                  </button>
                </Dropdown>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

