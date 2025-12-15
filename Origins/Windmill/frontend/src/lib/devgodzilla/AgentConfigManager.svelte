<script lang="ts">
    import { createEventDispatcher, onMount } from 'svelte';
    import Toggle from '$lib/components/Toggle.svelte';
    
    const dispatch = createEventDispatcher();
    
    interface Agent {
        id: string;
        name: string;
        kind: 'cli' | 'ide' | 'api';
        enabled: boolean;
        model: string;
        sandbox: string;
        capabilities: string[];
        status: 'available' | 'unavailable' | 'checking';
    }
    
    let agents: Agent[] = [];
    let loading = true;
    
    async function loadAgents() {
        loading = true;
        try {
            // Mock data - would fetch from /agents API
            agents = [
                {
                    id: 'codex',
                    name: 'OpenAI Codex',
                    kind: 'cli',
                    enabled: true,
                    model: 'gpt-4.1',
                    sandbox: 'workspace-write',
                    capabilities: ['code_gen', 'review', 'refactor'],
                    status: 'available'
                },
                {
                    id: 'opencode',
                    name: 'OpenCode',
                    kind: 'cli',
                    enabled: true,
                    model: 'claude-sonnet-4-20250514',
                    sandbox: 'workspace-write',
                    capabilities: ['code_gen', 'review', 'refactor'],
                    status: 'available'
                },
                {
                    id: 'claude-code',
                    name: 'Claude Code',
                    kind: 'cli',
                    enabled: true,
                    model: 'claude-sonnet-4-20250514',
                    sandbox: 'workspace-write',
                    capabilities: ['code_gen', 'review', 'refactor', 'long_context'],
                    status: 'available'
                },
                {
                    id: 'gemini-cli',
                    name: 'Gemini CLI',
                    kind: 'cli',
                    enabled: true,
                    model: 'gemini-2.5-pro',
                    sandbox: 'workspace-write',
                    capabilities: ['code_gen', 'review', 'multimodal'],
                    status: 'checking'
                },
                {
                    id: 'cursor',
                    name: 'Cursor Editor',
                    kind: 'ide',
                    enabled: false,
                    model: 'gpt-4',
                    sandbox: 'none',
                    capabilities: ['code_gen', 'interactive'],
                    status: 'unavailable'
                }
            ];
        } finally {
            loading = false;
        }
    }
    
    async function toggleAgent(agent: Agent) {
        agent.enabled = !agent.enabled;
        agents = agents;
        dispatch('change', { agentId: agent.id, enabled: agent.enabled });
    }
    
    async function checkHealth(agent: Agent) {
        agent.status = 'checking';
        agents = agents;
        
        // Simulate health check
        await new Promise(r => setTimeout(r, 1500));
        agent.status = Math.random() > 0.3 ? 'available' : 'unavailable';
        agents = agents;
    }
    
    function getStatusColor(status: string): string {
        switch (status) {
            case 'available': return 'bg-green-500';
            case 'unavailable': return 'bg-red-500';
            default: return 'bg-yellow-500';
        }
    }
    
    function getKindIcon(kind: string): string {
        switch (kind) {
            case 'cli': return '⌨️';
            case 'ide': return '🖥️';
            case 'api': return '🌐';
            default: return '🤖';
        }
    }
    
    onMount(loadAgents);
</script>

<div class="bg-surface rounded-lg p-4">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-primary">🤖 Agent Configuration</h3>
        <button 
            class="px-2 py-1 text-xs bg-surface-secondary hover:bg-surface-hover rounded text-secondary transition-colors"
            on:click={loadAgents}
        >
            ↻ Refresh
        </button>
    </div>
    
    {#if loading}
        <div class="text-center py-8 text-secondary">Loading agents...</div>
    {:else}
        <div class="flex flex-col gap-3">
            {#each agents as agent}
                <div 
                    class="flex justify-between items-center p-4 bg-surface-secondary rounded-lg border-l-4 transition-opacity"
                    class:opacity-50={!agent.enabled}
                    class:border-accent={agent.enabled}
                    class:border-secondary={!agent.enabled}
                >
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-lg">{getKindIcon(agent.kind)}</span>
                            <span class="font-semibold text-primary">{agent.name}</span>
                            <span class="w-2 h-2 rounded-full {getStatusColor(agent.status)}"></span>
                        </div>
                        <div class="flex gap-4 text-xs text-secondary mb-2">
                            <span>📦 {agent.model}</span>
                            <span>🔒 {agent.sandbox}</span>
                        </div>
                        <div class="flex flex-wrap gap-1">
                            {#each agent.capabilities as cap}
                                <span class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-accent text-2xs rounded">
                                    {cap}
                                </span>
                            {/each}
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-4">
                        <button 
                            class="text-xl hover:opacity-70 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Check health"
                            on:click={() => checkHealth(agent)}
                            disabled={agent.status === 'checking'}
                        >
                            {agent.status === 'checking' ? '⏳' : '🔍'}
                        </button>
                        
                        <Toggle 
                            checked={agent.enabled}
                            on:change={() => toggleAgent(agent)}
                        />
                    </div>
                </div>
            {/each}
        </div>
        
        <div class="mt-4 text-center text-sm text-secondary">
            {agents.filter(a => a.enabled).length} / {agents.length} agents enabled
        </div>
    {/if}
</div>
