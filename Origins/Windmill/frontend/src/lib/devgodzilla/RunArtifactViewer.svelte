<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { Button } from '$lib/components/common';
    import { Download, FileText, FileDiff, ScrollText, FlaskConical, File } from 'lucide-svelte';
    import { devGodzilla, type ArtifactItem } from '$lib/devgodzilla/client';

    let { stepId = null, initialArtifactId = null }: { stepId?: number | null; initialArtifactId?: string | null } = $props();

    const dispatch = createEventDispatcher();

    type Artifact = ArtifactItem & { content?: string };

    let items: Artifact[] = [];
    let selectedArtifact: Artifact | null = null;
    let loading = false;
    let error: string | null = null;

    $effect(() => {
        (async () => {
            if (!stepId) {
                items = [];
                selectedArtifact = null;
                return;
            }
            loading = true;
            error = null;
            try {
                items = (await devGodzilla.listStepArtifacts(stepId)) as Artifact[];
                // Keep selection if still exists, otherwise pick first
                const preferred = initialArtifactId ? items.find((a) => a.id === initialArtifactId) : null;
                if (preferred) {
                    selectedArtifact = preferred;
                } else if (selectedArtifact) {
                    const stillThere = items.find((a) => a.id === selectedArtifact?.id);
                    selectedArtifact = stillThere ?? (items[0] ?? null);
                } else {
                    selectedArtifact = items[0] ?? null;
                }
                if (selectedArtifact) {
                    await viewArtifact(selectedArtifact);
                }
            } catch (e) {
                error = e instanceof Error ? e.message : 'Failed to load artifacts';
                items = [];
                selectedArtifact = null;
            } finally {
                loading = false;
            }
        })();
    });

    async function viewArtifact(artifact: Artifact) {
        selectedArtifact = artifact;
        loading = true;
        error = null;
        
        try {
            if (!stepId) return;
            const res = await devGodzilla.getStepArtifactContent(stepId, artifact.id);
            artifact.content = res.content;
        } finally {
            loading = false;
        }
    }
    
    function getTypeIcon(type: string): string {
        return type;
    }
    
    function formatSize(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    
    function downloadArtifact(artifact: Artifact) {
        dispatch('download', { artifact });
        if (!stepId) return;
        const url = devGodzilla.getStepArtifactDownloadUrl(stepId, artifact.id);
        window.open(url, '_blank');
    }
</script>

<div class="flex h-[400px] bg-surface rounded-lg overflow-hidden border">
    <!-- Sidebar -->
    <div class="w-60 border-r flex flex-col">
        <h3 class="p-4 text-lg font-semibold text-primary">Artifacts</h3>
        <div class="flex-1 overflow-y-auto px-2 pb-2">
            {#if !stepId}
                <div class="p-4 text-sm text-secondary">Select a step to view artifacts.</div>
            {:else if error}
                <div class="p-4 text-sm text-secondary">{error}</div>
            {:else if items.length === 0}
                <div class="p-4 text-sm text-secondary">No artifacts yet.</div>
            {/if}
            {#each items as artifact}
                <button 
                    class="flex items-center gap-2 w-full p-2 rounded-md text-left transition-all mb-1
                        {selectedArtifact?.id === artifact.id 
                            ? 'bg-surface-accent-primary text-white' 
                            : 'hover:bg-surface-hover text-primary'}"
                    on:click={() => viewArtifact(artifact)}
                >
                    {#if artifact.type === 'log'}
                        <ScrollText size={16} class={selectedArtifact?.id === artifact.id ? 'text-white' : 'text-secondary'} />
                    {:else if artifact.type === 'diff'}
                        <FileDiff size={16} class={selectedArtifact?.id === artifact.id ? 'text-white' : 'text-secondary'} />
                    {:else if artifact.type === 'report'}
                        <FileText size={16} class={selectedArtifact?.id === artifact.id ? 'text-white' : 'text-secondary'} />
                    {:else if artifact.type === 'test'}
                        <FlaskConical size={16} class={selectedArtifact?.id === artifact.id ? 'text-white' : 'text-secondary'} />
                    {:else}
                        <File size={16} class={selectedArtifact?.id === artifact.id ? 'text-white' : 'text-secondary'} />
                    {/if}
                    <div class="flex flex-col overflow-hidden">
                        <span class="text-sm truncate">{artifact.name}</span>
                        <span class="text-xs {selectedArtifact?.id === artifact.id ? 'text-white/70' : 'text-secondary'}">
                            {formatSize(artifact.size)}
                        </span>
                    </div>
                </button>
            {/each}
        </div>
    </div>
    
    <!-- Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
        {#if loading}
            <div class="flex-1 flex items-center justify-center text-secondary">Loading...</div>
        {:else if selectedArtifact}
            <div class="flex justify-between items-center p-4 border-b">
                <h4 class="font-semibold text-primary">
                    {selectedArtifact.name}
                </h4>
                <Button
                    variant="default"
                    unifiedSize="sm"
                    btnClasses="max-w-fit"
                    startIcon={{ icon: Download }}
                    on:click={() => selectedArtifact && downloadArtifact(selectedArtifact)}
                >
                    Download
                </Button>
            </div>
            <div class="flex gap-4 px-4 py-2 text-xs text-secondary bg-surface-secondary">
                <span>Size: {formatSize(selectedArtifact.size)}</span>
            </div>
            <pre class="flex-1 p-4 bg-surface-sunken font-mono text-sm overflow-auto whitespace-pre-wrap
                {selectedArtifact.type === 'log' ? 'text-green-500' : 'text-primary'}"
            >{selectedArtifact.content || 'No content'}</pre>
        {:else}
            <div class="flex-1 flex flex-col items-center justify-center text-secondary">
                <p>Select an artifact to view</p>
            </div>
        {/if}
    </div>
</div>
