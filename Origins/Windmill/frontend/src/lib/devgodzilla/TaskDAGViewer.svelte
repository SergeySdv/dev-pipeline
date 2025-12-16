<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { StepRun } from './client';
  import { Badge } from '$lib/components/common';
  import { CheckCircle2, XCircle, Loader2, Circle } from 'lucide-svelte';
  
  export let steps: StepRun[] = [];
  export let currentStepId: number | undefined = undefined;
  
  const dispatch = createEventDispatcher();
  
  function statusColor(status: string) {
    if (status === 'completed') return 'green';
    if (status === 'failed') return 'red';
    if (status === 'running') return 'blue';
    return 'gray';
  }
  
  function handleSelect(step: StepRun) {
    dispatch('select', step);
  }
</script>

<div class="flex flex-col space-y-2">
  <h3 class="text-sm font-medium text-secondary uppercase tracking-wider mb-2">Protocol Execution Plan</h3>
  
  <div class="space-y-3">
    {#each steps as step (step.id)}
      <div 
        class="relative flex items-start p-3 bg-surface border rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer
          {step.id === currentStepId ? 'border-border-selected bg-surface-accent-selected' : ''}"
        on:click={() => handleSelect(step)}
        on:keydown={(e) => e.key === 'Enter' && handleSelect(step)}
        role="button"
        tabindex="0"
      >
        <!-- Status Indicator -->
        <div class="flex-shrink-0 mt-0.5">
          {#if step.status === 'completed'}
            <CheckCircle2 size={18} class="text-green-600 dark:text-green-400" />
          {:else if step.status === 'failed'}
            <XCircle size={18} class="text-red-600 dark:text-red-400" />
          {:else if step.status === 'running'}
            <Loader2 size={18} class="text-secondary animate-spin" />
          {:else}
            <Circle size={18} class="text-secondary" />
          {/if}
        </div>
        
        <div class="ml-3 flex-1">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-medium text-primary">{step.step_name}</h4>
            <div class="flex items-center gap-2">
              <Badge color={statusColor(step.status)}>{step.status}</Badge>
              <span class="text-xs text-secondary font-mono">{step.step_type}</span>
            </div>
          </div>
          {#if step.summary}
            <p class="mt-1 text-sm text-secondary line-clamp-2">{step.summary}</p>
          {/if}
        </div>
      </div>
      
      <!-- Connector Line -->
      {#if step.step_index < steps.length - 1}
        <div class="flex justify-center -my-2">
          <div class="w-0.5 h-4 bg-surface-secondary"></div>
        </div>
      {/if}
    {/each}
  </div>
</div>
