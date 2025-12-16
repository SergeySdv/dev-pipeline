<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Button, Badge } from '$lib/components/common';
  import { Save } from 'lucide-svelte';
  
  export let specContent = '';
  export let readOnly = false;
  
  const dispatch = createEventDispatcher();
  
  function handleInput(event: Event) {
    specContent = (event.target as HTMLTextAreaElement).value;
    dispatch('change', specContent);
  }
  
  function handleSave() {
    dispatch('save', specContent);
  }
</script>

<div class="spec-editor flex flex-col h-full border rounded-md overflow-hidden bg-surface">
  <div class="toolbar flex items-center justify-between px-4 py-2 bg-surface-secondary border-b">
    <div class="flex items-center space-x-2">
      <span class="font-semibold text-sm text-primary">Feature Specification</span>
      <Badge color="gray">Markdown/YAML</Badge>
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
      value={specContent}
      on:input={handleInput}
      readonly={readOnly}
      class="w-full h-full p-4 font-mono text-sm resize-none bg-transparent focus:outline-none text-primary"
      placeholder="# Feature Specification\n\nname: New Feature\ndescription: ...\n\n## Requirements\n- ..."
    ></textarea>
  </div>
</div>

<style>
  .spec-editor {
    min-height: 400px;
  }
</style>
