<script lang="ts">
  // Settings page for DevGodzilla configuration
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert, Button } from '$lib/components/common';

  let apiUrl = '';
  let saved = false;

  // Load initial value (client-side)
  if (typeof window !== 'undefined') {
    apiUrl = localStorage.getItem('devgodzilla_api_url') ?? '';
  }

  function saveSettings() {
    // In a real implementation, this would persist to localStorage or backend
    localStorage.setItem('devgodzilla_api_url', apiUrl);
    saved = true;
    setTimeout(() => saved = false, 2000);
  }
</script>

<svelte:head>
  <title>Settings - DevGodzilla</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <PageHeader title="Settings" />

  {#if saved}
    <Alert type="success" title="Settings saved" class="mb-6" />
  {/if}

  <div class="space-y-6">
    <!-- API Configuration -->
    <div class="bg-surface rounded-xl shadow-sm border p-6">
      <h2 class="text-lg font-semibold text-primary mb-4">API Configuration</h2>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-secondary mb-2">
            DevGodzilla API URL
          </label>
          <input
            type="text"
            bind:value={apiUrl}
            class="w-full max-w-md"
            placeholder="(optional) e.g. http://localhost:8011"
          />
          <p class="mt-1 text-sm text-secondary">Optional override for the DevGodzilla API base URL.</p>
        </div>
      </div>
    </div>

    <!-- Default Behaviors -->
    <div class="bg-surface rounded-xl shadow-sm border p-6">
      <h2 class="text-lg font-semibold text-primary mb-4">Default Behaviors</h2>
      
      <div class="space-y-4">
        <label class="flex items-center gap-3">
          <input type="checkbox" class="w-4 h-4 rounded">
          <span class="text-secondary">Auto-start protocols after creation</span>
        </label>
        
        <label class="flex items-center gap-3">
          <input type="checkbox" class="w-4 h-4 rounded" checked>
          <span class="text-secondary">Show notifications for clarification requests</span>
        </label>
        
        <label class="flex items-center gap-3">
          <input type="checkbox" class="w-4 h-4 rounded" checked>
          <span class="text-secondary">Require QA approval before step completion</span>
        </label>
      </div>
    </div>

    <!-- Constitution Defaults -->
    <div class="bg-surface rounded-xl shadow-sm border p-6">
      <h2 class="text-lg font-semibold text-primary mb-4">Constitution Defaults</h2>
      
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-secondary mb-2">
            Default Classification
          </label>
          <select class="w-full max-w-md">
            <option value="default">Default</option>
            <option value="startup-fast">Startup Fast</option>
            <option value="team-standard">Team Standard</option>
            <option value="enterprise">Enterprise Compliance</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Save Button -->
    <div class="flex justify-end">
      <Button variant="accent" unifiedSize="md" btnClasses="max-w-fit" on:click={saveSettings}>
        Save settings
      </Button>
    </div>
  </div>
</div>
