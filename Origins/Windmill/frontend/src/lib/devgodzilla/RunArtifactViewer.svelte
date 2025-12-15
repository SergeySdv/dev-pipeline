<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    
    export let artifacts: Artifact[] = [];
    
    const dispatch = createEventDispatcher();
    
    interface Artifact {
        id: string;
        type: 'log' | 'diff' | 'file' | 'report' | 'test';
        name: string;
        size: number;
        createdAt: string;
        content?: string;
    }
    
    let selectedArtifact: Artifact | null = null;
    let loading = false;
    
    // Default artifacts if none provided
    $: items = artifacts.length ? artifacts : [
        { id: '1', type: 'log' as const, name: 'execution.log', size: 12450, createdAt: '2024-01-15T10:30:00Z' },
        { id: '2', type: 'diff' as const, name: 'changes.diff', size: 3200, createdAt: '2024-01-15T10:31:00Z' },
        { id: '3', type: 'file' as const, name: 'output.json', size: 850, createdAt: '2024-01-15T10:31:30Z' },
        { id: '4', type: 'report' as const, name: 'quality-report.md', size: 2100, createdAt: '2024-01-15T10:32:00Z' },
        { id: '5', type: 'test' as const, name: 'test-results.xml', size: 5600, createdAt: '2024-01-15T10:33:00Z' },
    ];
    
    async function viewArtifact(artifact: Artifact) {
        selectedArtifact = artifact;
        loading = true;
        
        try {
            await new Promise(r => setTimeout(r, 500));
            
            if (artifact.type === 'log') {
                artifact.content = `[10:30:00] Starting execution...
[10:30:01] Loading workspace at /home/user/project
[10:30:02] Running agent: opencode
[10:30:15] Agent completed with 3 file changes
[10:30:16] Running QA gates...
[10:30:45] LintGate: PASS (0 issues)
[10:30:50] TypeGate: PASS
[10:31:00] TestGate: PASS (15 tests)
[10:31:00] Execution complete!`;
            } else if (artifact.type === 'diff') {
                artifact.content = `diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -12,6 +12,15 @@ def login(username, password):
     user = get_user(username)
     if not user:
         return None
+    
+    if not verify_password(password, user.password_hash):
+        log_failed_attempt(username)
+        return None
+    
+    session = create_session(user)
+    return session.token

 def logout(session_id):
     invalidate_session(session_id)`;
            } else if (artifact.type === 'report') {
                artifact.content = `# Quality Report

## Summary
- **Verdict:** PASS
- **Duration:** 45.2s
- **Gates:** 3/3 passed

## Gate Results

### ✅ LintGate
No issues found.

### ✅ TypeGate  
No type errors.

### ✅ TestGate
15/15 tests passed.`;
            } else {
                artifact.content = `// Content of ${artifact.name}\n// ${artifact.size} bytes`;
            }
        } finally {
            loading = false;
        }
    }
    
    function getTypeIcon(type: string): string {
        switch (type) {
            case 'log': return '📜';
            case 'diff': return '📝';
            case 'file': return '📄';
            case 'report': return '📊';
            case 'test': return '🧪';
            default: return '📁';
        }
    }
    
    function formatSize(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    
    function formatDate(dateStr: string): string {
        return new Date(dateStr).toLocaleString();
    }
    
    function downloadArtifact(artifact: Artifact) {
        dispatch('download', { artifact });
    }
</script>

<div class="flex h-[400px] bg-surface rounded-lg overflow-hidden border">
    <!-- Sidebar -->
    <div class="w-60 border-r flex flex-col">
        <h3 class="p-4 text-lg font-semibold text-primary">📦 Artifacts</h3>
        <div class="flex-1 overflow-y-auto px-2 pb-2">
            {#each items as artifact}
                <button 
                    class="flex items-center gap-2 w-full p-2 rounded-md text-left transition-all mb-1
                        {selectedArtifact?.id === artifact.id 
                            ? 'bg-surface-accent-primary text-white' 
                            : 'hover:bg-surface-hover text-primary'}"
                    on:click={() => viewArtifact(artifact)}
                >
                    <span class="text-xl">{getTypeIcon(artifact.type)}</span>
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
                    {getTypeIcon(selectedArtifact.type)} {selectedArtifact.name}
                </h4>
                <button 
                    class="px-2 py-1 text-xs bg-surface-secondary hover:bg-surface-hover rounded text-primary transition-colors"
                    on:click={() => selectedArtifact && downloadArtifact(selectedArtifact)}
                >
                    ⬇️ Download
                </button>
            </div>
            <div class="flex gap-4 px-4 py-2 text-xs text-secondary bg-surface-secondary">
                <span>Size: {formatSize(selectedArtifact.size)}</span>
                <span>Created: {formatDate(selectedArtifact.createdAt)}</span>
            </div>
            <pre class="flex-1 p-4 bg-surface-sunken font-mono text-sm overflow-auto whitespace-pre-wrap
                {selectedArtifact.type === 'log' ? 'text-green-500' : 'text-primary'}"
            >{selectedArtifact.content || 'No content'}</pre>
        {:else}
            <div class="flex-1 flex flex-col items-center justify-center text-secondary">
                <div class="text-5xl mb-2">📂</div>
                <p>Select an artifact to view</p>
            </div>
        {/if}
    </div>
</div>
