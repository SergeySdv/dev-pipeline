<script lang="ts">
  import { onMount } from 'svelte';
  import { devGodzilla, type AgentInfo } from '$lib/devgodzilla/client';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Alert, Button } from '$lib/components/common';
  import { Settings2, Activity } from 'lucide-svelte';
  import AgentSelector from '$lib/devgodzilla/AgentSelector.svelte';
  import AgentConfigManager from '$lib/devgodzilla/AgentConfigManager.svelte';

  let agents: AgentInfo[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let showConfig = $state(false);

  onMount(async () => {
    try {
      agents = await devGodzilla.listAgents();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load agents';
    } finally {
      loading = false;
    }
  });

  async function checkAgentHealth(agentId: string) {
    try {
      const result = await devGodzilla.checkAgentHealth(agentId);
      agents = agents.map(a => 
        a.id === agentId ? { ...a, status: result.status } : a
      );
    } catch (e) {
      console.error('Health check failed:', e);
    }
  }
</script>

<svelte:head>
  <title>Agents - DevGodzilla</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <PageHeader title="AI Agents" childrenWrapperDivClasses="flex-1 flex flex-row gap-2 flex-wrap justify-end items-center">
    <Button
      variant="default"
      unifiedSize="md"
      btnClasses="max-w-fit"
      startIcon={{ icon: Settings2 }}
      on:click={() => (showConfig = !showConfig)}
    >
      {showConfig ? 'Hide config' : 'Show config'}
    </Button>
  </PageHeader>

  {#if error}
    <Alert type="error" title="Failed to load agents" class="mb-6">
      {error}
    </Alert>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-secondary">Loading agents...</div>
  {:else}
    <!-- Agent Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
      {#each agents as agent}
        <div class="bg-surface rounded-xl shadow-sm border p-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="font-semibold text-primary">{agent.name}</h3>
              <p class="text-sm text-secondary">{agent.id}</p>
            </div>
            <span class="w-3 h-3 rounded-full {agent.status === 'available' ? 'bg-green-500' : 'bg-gray-400'}"></span>
          </div>
          
          <div class="mb-4">
            <span class="px-2 py-1 text-xs rounded bg-surface-secondary text-secondary">
              {agent.kind}
            </span>
          </div>
          
          <div class="flex flex-wrap gap-2 mb-4">
            {#each agent.capabilities as cap}
              <span class="px-2 py-1 text-xs rounded bg-blue-100 dark:bg-blue-900/30 text-accent">
                {cap}
              </span>
            {/each}
          </div>
          
          <Button
            variant="subtle"
            unifiedSize="sm"
            btnClasses="max-w-fit"
            startIcon={{ icon: Activity }}
            on:click={() => checkAgentHealth(agent.id)}
          >
            Check health
          </Button>
        </div>
      {/each}
    </div>

    <!-- Agent Configuration -->
    {#if showConfig}
      <div class="bg-surface rounded-xl shadow-sm border p-6 mb-8">
        <h2 class="text-lg font-semibold text-primary mb-4">Agent Configuration</h2>
        <AgentConfigManager />
      </div>
    {/if}

    <!-- Engine Defaults -->
    <div class="bg-surface rounded-xl shadow-sm border p-6">
      <h2 class="text-lg font-semibold text-primary mb-4">Engine Defaults</h2>
      <p class="text-sm text-secondary mb-4">
        Configure which agent to use by default for each type of operation.
      </p>
      
      <div class="space-y-4">
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div>
            <p class="font-medium text-primary">Discovery</p>
            <p class="text-sm text-secondary">Used for project analysis and onboarding</p>
          </div>
          <AgentSelector on:change={(e) => console.log('Discovery agent:', e.detail)} />
        </div>
        
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div>
            <p class="font-medium text-primary">Planning</p>
            <p class="text-sm text-secondary">Used for specification and planning</p>
          </div>
          <AgentSelector on:change={(e) => console.log('Planning agent:', e.detail)} />
        </div>
        
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div>
            <p class="font-medium text-primary">Execution</p>
            <p class="text-sm text-secondary">Used for code generation</p>
          </div>
          <AgentSelector on:change={(e) => console.log('Execution agent:', e.detail)} />
        </div>
        
        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div>
            <p class="font-medium text-primary">Quality</p>
            <p class="text-sm text-secondary">Used for QA and review</p>
          </div>
          <AgentSelector on:change={(e) => console.log('QA agent:', e.detail)} />
        </div>
      </div>
    </div>
  {/if}
</div>
