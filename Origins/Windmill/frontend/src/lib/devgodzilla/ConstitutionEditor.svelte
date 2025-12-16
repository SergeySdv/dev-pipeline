<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Badge, Button } from '$lib/components/common';
  import { Save } from 'lucide-svelte';
  
  export let constitution = '';
  export let version = '1.0';
  export let readOnly = false;
  
  const dispatch = createEventDispatcher();
  
  function handleInput(event: Event) {
    constitution = (event.target as HTMLTextAreaElement).value;
    dispatch('change', constitution);
  }
  
  function handleSave() {
    dispatch('save', { constitution, version });
  }
</script>

<div class="constitution-editor flex flex-col h-full border rounded-md overflow-hidden bg-surface">
  <div class="toolbar flex items-center justify-between px-4 py-2 bg-surface-secondary border-b">
    <div class="flex items-center space-x-2">
      <span class="font-semibold text-sm text-primary">Project Constitution</span>
      <Badge color="gray">v{version}</Badge>
    </div>
    
    <div class="actions">
      {#if !readOnly}
        <Button
          variant="accent"
          unifiedSize="sm"
          btnClasses="max-w-fit"
          startIcon={{ icon: Save }}
          on:click={handleSave}
        >
          Save
        </Button>
      {/if}
    </div>
  </div>
  
  <div class="editor-container flex-1 relative">
    <textarea
      value={constitution}
      on:input={handleInput}
      readonly={readOnly}
      class="w-full h-full p-4 font-mono text-sm leading-relaxed resize-none bg-transparent focus:outline-none text-primary"
      placeholder="# Article I: Library-First\n\nCode shall be organized..."
    ></textarea>
  </div>
</div>
