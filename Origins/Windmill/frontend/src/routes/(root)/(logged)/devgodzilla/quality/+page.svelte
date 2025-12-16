<script lang="ts">
  import { onMount } from 'svelte';
  import { devGodzilla, type Project } from '$lib/devgodzilla/client';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert } from '$lib/components/common';

  let projects: Project[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);

  // Placeholder QA stats
  let qaStats = $state({
    totalChecks: 0,
    passed: 0,
    warnings: 0,
    failed: 0
  });

  onMount(async () => {
    try {
      projects = await devGodzilla.listProjects();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load data';
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>Quality - DevGodzilla</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <PageHeader title="Quality Assurance" />

  {#if error}
    <Alert type="error" title="Failed to load quality data" class="mb-6">
      {error}
    </Alert>
  {/if}

  <!-- QA Overview Stats -->
  <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <p class="text-sm text-secondary">Total Checks</p>
      <p class="text-3xl font-bold text-primary">{qaStats.totalChecks}</p>
    </div>
    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <p class="text-sm text-secondary">Passed</p>
      <p class="text-3xl font-bold text-green-600">{qaStats.passed}</p>
    </div>
    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <p class="text-sm text-secondary">Warnings</p>
      <p class="text-3xl font-bold text-amber-600">{qaStats.warnings}</p>
    </div>
    <div class="bg-surface rounded-xl shadow-sm p-6 border">
      <p class="text-sm text-secondary">Failed</p>
      <p class="text-3xl font-bold text-red-600">{qaStats.failed}</p>
    </div>
  </div>

  <!-- Constitutional Gates -->
  <div class="bg-surface rounded-xl shadow-sm border p-6 mb-8">
    <h2 class="text-lg font-semibold text-primary mb-4">Constitutional Gates</h2>
    <p class="text-secondary">
      Quality gates are checked against each step output to ensure compliance with project constitution.
    </p>
    
    <div class="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div class="p-4 border rounded-lg">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-green-500">✓</span>
          <span class="font-medium text-primary">Article III: Test-First</span>
        </div>
        <p class="text-sm text-secondary">Tests must exist before implementation</p>
      </div>
      
      <div class="p-4 border rounded-lg">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-green-500">✓</span>
          <span class="font-medium text-primary">Article VII: Simplicity</span>
        </div>
        <p class="text-sm text-secondary">No unnecessary complexity</p>
      </div>
      
      <div class="p-4 border rounded-lg">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-green-500">✓</span>
          <span class="font-medium text-primary">Article IX: Integration</span>
        </div>
        <p class="text-sm text-secondary">Integration tests required</p>
      </div>
    </div>
  </div>

  <!-- Recent QA Results -->
  <div class="bg-surface rounded-xl shadow-sm border">
    <div class="p-6 border-b">
      <h2 class="text-lg font-semibold text-primary">Recent QA Results</h2>
    </div>
    <div class="p-6 text-center text-secondary">
      No QA results yet. Results will appear here after protocol steps are executed.
    </div>
  </div>
</div>
