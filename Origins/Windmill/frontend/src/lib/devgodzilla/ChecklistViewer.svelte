<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { Badge } from '$lib/components/common';
    import { CheckCircle2, Circle, Sparkles } from 'lucide-svelte';

    interface ChecklistItem {
        id: string;
        text: string;
        category: 'required' | 'recommended' | 'optional';
        checked: boolean;
        autoVerified?: boolean;
        verificationNote?: string;
    }

    let { checklistItems = [] }: { checklistItems?: ChecklistItem[] } = $props();

    const dispatch = createEventDispatcher();

    // Default checklist if none provided
    const items = $derived(checklistItems.length ? checklistItems : [
        { id: '1', text: 'Document public APIs', category: 'required' as const, checked: true, autoVerified: true },
        { id: '2', text: 'Add unit tests for new logic', category: 'required' as const, checked: false, autoVerified: true },
        { id: '3', text: 'Update architecture diagrams', category: 'recommended' as const, checked: false, autoVerified: false },
        { id: '4', text: 'Add performance benchmarks', category: 'optional' as const, checked: false, autoVerified: false },
        { id: '5', text: 'Security scan passes', category: 'recommended' as const, checked: true, autoVerified: true },
        { id: '6', text: 'Code reviewed', category: 'recommended' as const, checked: false, autoVerified: false },
        { id: '7', text: 'Performance tested', category: 'optional' as const, checked: false, autoVerified: false },
    ]);

    const requiredItems = $derived(items.filter(i => i.category === 'required'));
    const recommendedItems = $derived(items.filter(i => i.category === 'recommended'));
    const optionalItems = $derived(items.filter(i => i.category === 'optional'));

    const requiredComplete = $derived(requiredItems.every(i => i.checked));
    const progress = $derived(Math.round((items.filter(i => i.checked).length / items.length) * 100));

    function toggleItem(item: ChecklistItem) {
        if (item.autoVerified) return;
        item.checked = !item.checked;
        dispatch('change', { id: item.id, checked: item.checked });
    }
</script>

<div class="bg-surface rounded-lg border p-4">
    <div class="flex justify-between items-center mb-3">
        <h3 class="text-lg font-semibold text-primary">QA Checklist</h3>
        <Badge color={requiredComplete ? 'green' : 'gray'}>
            {requiredComplete ? 'Ready' : 'Pending'}
        </Badge>
    </div>
    
    <!-- Progress bar -->
    <div class="h-1 bg-surface-secondary rounded-full overflow-hidden mb-4">
        <div 
            class="h-full bg-surface-accent-primary transition-all duration-300" 
            style="width: {progress}%"
        ></div>
    </div>
    
    {#if requiredItems.length > 0}
        <div class="mb-4">
            <h4 class="flex items-center gap-2 text-sm text-secondary mb-2">
                <span class="w-2 h-2 rounded-full bg-red-500"></span>
                Required
            </h4>
            {#each requiredItems as item}
                <label 
                    class="flex items-center gap-3 p-3 bg-surface-secondary rounded-md mb-1 transition-all
                        {item.autoVerified ? 'cursor-default' : 'cursor-pointer hover:bg-surface-hover'}
                        {item.checked ? 'opacity-70' : ''}"
                >
                    <input 
                        type="checkbox" 
                        checked={item.checked}
                        disabled={item.autoVerified}
                        on:change={() => toggleItem(item)}
                        class="hidden"
                    />
                    <div 
                        class="w-5 h-5 rounded border-2 flex items-center justify-center text-xs transition-all
                            {item.checked 
                                ? 'bg-surface-accent-secondary border-surface-accent-secondary text-white' 
                                : 'border-secondary'}"
                    >
                        {#if item.checked}
                            <CheckCircle2 size={14} />
                        {:else}
                            <Circle size={14} />
                        {/if}
                    </div>
                    <span class="flex-1 text-sm {item.checked ? 'line-through text-secondary' : 'text-primary'}">
                        {item.text}
                    </span>
                    {#if item.autoVerified}
                        <span class="flex items-center gap-1 text-2xs text-accent font-semibold">
                            <Sparkles size={12} />
                            Auto
                        </span>
                    {/if}
                </label>
            {/each}
        </div>
    {/if}
    
    {#if recommendedItems.length > 0}
        <div class="mb-4">
            <h4 class="flex items-center gap-2 text-sm text-secondary mb-2">
                <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
                Recommended
            </h4>
            {#each recommendedItems as item}
                <label 
                    class="flex items-center gap-3 p-3 bg-surface-secondary rounded-md mb-1 transition-all
                        {item.autoVerified ? 'cursor-default' : 'cursor-pointer hover:bg-surface-hover'}
                        {item.checked ? 'opacity-70' : ''}"
                >
                    <input 
                        type="checkbox" 
                        checked={item.checked}
                        disabled={item.autoVerified}
                        on:change={() => toggleItem(item)}
                        class="hidden"
                    />
                    <div 
                        class="w-5 h-5 rounded border-2 flex items-center justify-center text-xs transition-all
                            {item.checked 
                                ? 'bg-surface-accent-secondary border-surface-accent-secondary text-white' 
                                : 'border-secondary'}"
                    >
                        {#if item.checked}
                            <CheckCircle2 size={14} />
                        {:else}
                            <Circle size={14} />
                        {/if}
                    </div>
                    <span class="flex-1 text-sm {item.checked ? 'line-through text-secondary' : 'text-primary'}">
                        {item.text}
                    </span>
                    {#if item.autoVerified}
                        <span class="flex items-center gap-1 text-2xs text-accent font-semibold">
                            <Sparkles size={12} />
                            Auto
                        </span>
                    {/if}
                </label>
            {/each}
        </div>
    {/if}
    
    {#if optionalItems.length > 0}
        <div class="mb-4">
            <h4 class="flex items-center gap-2 text-sm text-secondary mb-2">
                <span class="w-2 h-2 rounded-full bg-green-500"></span>
                Optional
            </h4>
            {#each optionalItems as item}
                <label 
                    class="flex items-center gap-3 p-3 bg-surface-secondary rounded-md mb-1 transition-all
                        {item.autoVerified ? 'cursor-default' : 'cursor-pointer hover:bg-surface-hover'}
                        {item.checked ? 'opacity-70' : ''}"
                >
                    <input 
                        type="checkbox" 
                        checked={item.checked}
                        disabled={item.autoVerified}
                        on:change={() => toggleItem(item)}
                        class="hidden"
                    />
                    <div 
                        class="w-5 h-5 rounded border-2 flex items-center justify-center text-xs transition-all
                            {item.checked 
                                ? 'bg-surface-accent-secondary border-surface-accent-secondary text-white' 
                                : 'border-secondary'}"
                    >
                        {#if item.checked}
                            <CheckCircle2 size={14} />
                        {:else}
                            <Circle size={14} />
                        {/if}
                    </div>
                    <span class="flex-1 text-sm {item.checked ? 'line-through text-secondary' : 'text-primary'}">
                        {item.text}
                    </span>
                    {#if item.autoVerified}
                        <span class="flex items-center gap-1 text-2xs text-accent font-semibold">
                            <Sparkles size={12} />
                            Auto
                        </span>
                    {/if}
                </label>
            {/each}
        </div>
    {/if}
    
    <div class="text-center text-sm text-secondary">
        {items.filter(i => i.checked).length} / {items.length} complete
    </div>
</div>
