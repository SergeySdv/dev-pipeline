<script lang="ts">
  export let qaResult: {
    verdict: 'passed' | 'failed' | 'warning';
    summary: string;
    gates: Array<{
      id: string;
      name: string;
      status: 'passed' | 'failed' | 'skipped' | 'warning';
      findings: Array<{
        severity: string;
        message: string;
        file?: string;
        line?: number;
      }>;
    }>;
  } | null = null;
</script>

<div class="bg-surface rounded-lg border shadow-sm overflow-hidden">
  <div class="px-4 py-3 border-b flex justify-between items-center bg-surface-secondary">
    <h3 class="text-sm font-semibold text-primary uppercase tracking-wider">Quality Assurance Report</h3>
    {#if qaResult}
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
        {qaResult.verdict === 'passed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200' : 
         qaResult.verdict === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200' : 
         'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200'}">
        {qaResult.verdict.toUpperCase()}
      </span>
    {/if}
  </div>

  <div class="p-4">
    {#if !qaResult}
      <div class="text-center text-secondary py-4">No QA results available</div>
    {:else}
      <div class="mb-4">
        <p class="text-sm text-secondary">{qaResult.summary}</p>
      </div>

      <div class="space-y-4">
        {#each qaResult.gates as gate}
          <div class="border rounded-md overflow-hidden">
            <div class="px-3 py-2 bg-surface-secondary flex justify-between items-center">
              <span class="font-medium text-sm text-primary">{gate.name}</span>
              <span class="text-xs font-mono 
                {gate.status === 'passed' ? 'text-green-600 dark:text-green-400' : 
                 gate.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-secondary'}">
                {gate.status.toUpperCase()}
              </span>
            </div>
            
            {#if gate.findings.length > 0}
              <div class="border-t">
                {#each gate.findings as finding}
                  <div class="px-3 py-2 border-b last:border-0 flex items-start space-x-2 text-sm">
                    <span class="flex-shrink-0 mt-0.5">
                      {#if finding.severity === 'error'}
                        <svg class="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      {:else}
                         <svg class="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                      {/if}
                    </span>
                    <div class="flex-1">
                      <p class="text-primary">{finding.message}</p>
                      {#if finding.file}
                        <p class="text-xs text-secondary mt-0.5 font-mono">{finding.file}{#if finding.line}:{finding.line}{/if}</p>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>
