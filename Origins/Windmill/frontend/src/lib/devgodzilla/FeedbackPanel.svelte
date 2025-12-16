<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Button, Badge } from '$lib/components/common';
  import { Wrench, RefreshCcw, ArrowUpRight } from 'lucide-svelte';
  
  export let findings: Array<{
    id: string;
    message: string;
    category: string;
    suggestedAction: 'auto_fix' | 'retry' | 'escalate' | 'block';
  }> = [];
  
  const dispatch = createEventDispatcher();
  
  function handleAction(findingId: string, action: string) {
    dispatch('action', { findingId, action });
  }
  
  function handleFixAll() {
    dispatch('fixAll');
  }
</script>

<div class="bg-surface rounded-lg border p-4">
  <div class="flex justify-between items-center mb-4">
    <h3 class="text-sm font-semibold text-primary">Feedback Required</h3>
    
    {#if findings.some(f => f.suggestedAction === 'auto_fix')}
      <Button variant="default" unifiedSize="sm" btnClasses="max-w-fit" startIcon={{ icon: Wrench }} on:click={handleFixAll}>
        Auto-fix all
      </Button>
    {/if}
  </div>
  
  <div class="space-y-3">
    {#each findings as finding}
      <div class="bg-surface p-3 rounded border shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-bold uppercase tracking-wide text-secondary">{finding.category}</span>
            <Badge color="gray">{finding.suggestedAction}</Badge>
          </div>
          <p class="text-sm text-primary">{finding.message}</p>
        </div>
        
        <div class="actions flex gap-2 shrink-0">
          {#if finding.suggestedAction === 'auto_fix'}
            <Button
              variant="default"
              unifiedSize="sm"
              btnClasses="max-w-fit"
              startIcon={{ icon: Wrench }}
              on:click={() => handleAction(finding.id, 'auto_fix')}
            >
              Fix
            </Button>
          {/if}
          
          <Button
            variant="default"
            unifiedSize="sm"
            btnClasses="max-w-fit"
            startIcon={{ icon: RefreshCcw }}
            on:click={() => handleAction(finding.id, 'retry')}
          >
            Retry
          </Button>
          
          <Button
            variant="default"
            unifiedSize="sm"
            btnClasses="max-w-fit"
            startIcon={{ icon: ArrowUpRight }}
            on:click={() => handleAction(finding.id, 'escalate')}
          >
            Escalate
          </Button>
        </div>
      </div>
    {/each}
  </div>
</div>
