<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { devGodzilla as client } from './client';
    import { Button } from '$lib/components/common';
    import { Rocket, ArrowLeft, ArrowRight, Plus } from 'lucide-svelte';

    let { onComplete = () => {} }: { onComplete?: (projectId: number) => void } = $props();

    const dispatch = createEventDispatcher();
    
    let currentStep = 1;
    const totalSteps = 4;
    
    // Form data
    let projectName = '';
    let repoUrl = '';
    let baseBranch = 'main';
    let projectType: 'python' | 'nodejs' | 'mixed' = 'python';
    let constitutionContent = '';
    let selectedAgents: string[] = ['opencode', 'claude-code'];
    
    const availableAgents = [
        { id: 'codex', name: 'OpenAI Codex' },
        { id: 'opencode', name: 'OpenCode' },
        { id: 'claude-code', name: 'Claude Code' },
        { id: 'gemini-cli', name: 'Gemini CLI' },
    ];
    
    const defaultConstitution = `# Project Constitution

## Core Values
1. **Safety First**: All generated code must be verified in sandboxes
2. **Library First**: Prefer established libraries over custom implementations
3. **Test Driven**: Write tests before implementation where possible

## Quality Gates
- All code must pass linting (ruff/eslint)
- All code must pass type checking (mypy/tsc)
- Tests must pass before merge
- Security scans must pass

## Constraints
- Follow existing code conventions
- Document public APIs
- Use dependency injection for testability
`;
    
    let isSubmitting = false;
    let error = '';
    
    function nextStep() {
        if (currentStep < totalSteps) {
            currentStep++;
        }
    }
    
    function prevStep() {
        if (currentStep > 1) {
            currentStep--;
        }
    }
    
    function toggleAgent(agentId: string) {
        if (selectedAgents.includes(agentId)) {
            selectedAgents = selectedAgents.filter(a => a !== agentId);
        } else {
            selectedAgents = [...selectedAgents, agentId];
        }
    }
    
    async function handleSubmit() {
        isSubmitting = true;
        error = '';
        
        try {
            // Create project
            const project = await client.createProject({
                name: projectName,
                git_url: repoUrl,
                base_branch: baseBranch,
            });
            
            // Initialize SpecKit
            await client.initSpecKit(project.id, constitutionContent || defaultConstitution);
            
            dispatch('complete', { projectId: project.id });
            onComplete(project.id);
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to create project';
        } finally {
            isSubmitting = false;
        }
    }

    const canProceed = $derived(
        currentStep === 1 ? projectName && repoUrl :
        currentStep === 2 ? true :
        currentStep === 3 ? selectedAgents.length > 0 :
        true
    );
</script>

<div class="max-w-xl mx-auto bg-surface rounded-xl overflow-hidden border">
    <!-- Header with steps -->
    <div class="p-6 bg-surface-accent-primary">
        <h2 class="text-xl font-bold text-white text-center mb-4 flex items-center justify-center gap-2">
            <Rocket size={18} />
            New Project Setup
        </h2>
        <div class="flex justify-center items-center">
            {#each Array(totalSteps) as _, i}
                <div 
                    class="w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm transition-all
                        {i + 1 === currentStep ? 'bg-white text-accent' : 
                         i + 1 < currentStep ? 'bg-surface-accent-secondary text-white' : 
                         'bg-white/20 text-white'}"
                >
                    {i + 1}
                </div>
                {#if i < totalSteps - 1}
                    <div class="w-10 h-0.5 {i + 1 < currentStep ? 'bg-surface-accent-secondary' : 'bg-white/20'}"></div>
                {/if}
            {/each}
        </div>
    </div>
    
    <!-- Content -->
    <div class="p-6 min-h-[350px]">
        {#if currentStep === 1}
            <div>
                <h3 class="text-lg font-semibold text-primary mb-4">Project Details</h3>
                <div class="space-y-4">
                    <div>
                        <label for="name" class="block text-sm text-secondary mb-1">Project Name</label>
                        <input id="name" type="text" bind:value={projectName} placeholder="my-awesome-project" class="w-full" />
                    </div>
                    <div>
                        <label for="repo" class="block text-sm text-secondary mb-1">Repository URL</label>
                        <input id="repo" type="text" bind:value={repoUrl} placeholder="https://github.com/user/repo.git" class="w-full" />
                    </div>
                    <div>
                        <label for="branch" class="block text-sm text-secondary mb-1">Base Branch</label>
                        <input id="branch" type="text" bind:value={baseBranch} placeholder="main" class="w-full" />
                    </div>
                    <div>
                        <label for="type" class="block text-sm text-secondary mb-1">Project Type</label>
                        <select id="type" bind:value={projectType} class="w-full">
                            <option value="python">Python</option>
                            <option value="nodejs">Node.js</option>
                            <option value="mixed">Mixed</option>
                        </select>
                    </div>
                </div>
            </div>
        {:else if currentStep === 2}
            <div>
                <h3 class="text-lg font-semibold text-primary mb-2">Project Constitution</h3>
                <p class="text-sm text-secondary mb-4">Define the rules and constraints for AI agents working on this project.</p>
                <textarea 
                    bind:value={constitutionContent}
                    placeholder={defaultConstitution}
                    rows="15"
                    class="w-full font-mono text-sm"
                ></textarea>
            </div>
        {:else if currentStep === 3}
            <div>
                <h3 class="text-lg font-semibold text-primary mb-2">Select AI Agents</h3>
                <p class="text-sm text-secondary mb-4">Choose which AI agents can work on this project.</p>
                <div class="grid grid-cols-2 gap-4">
                    {#each availableAgents as agent}
                        <button 
                            class="flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all
                                {selectedAgents.includes(agent.id) 
                                    ? 'border-border-selected bg-surface-accent-selected' 
                                    : 'border-transparent bg-surface-secondary hover:border-border-selected'}"
                            on:click={() => toggleAgent(agent.id)}
                        >
                            <span class="text-sm font-medium text-primary">{agent.name}</span>
                        </button>
                    {/each}
                </div>
            </div>
        {:else if currentStep === 4}
            <div>
                <h3 class="text-lg font-semibold text-primary mb-4">Review & Create</h3>
                <div class="bg-surface-secondary rounded-lg p-4 space-y-3">
                    <div class="flex justify-between py-2 border-b border-light">
                        <span class="text-secondary">Project:</span>
                        <span class="font-medium text-primary">{projectName}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-light">
                        <span class="text-secondary">Repository:</span>
                        <span class="font-medium text-primary text-sm">{repoUrl}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-light">
                        <span class="text-secondary">Branch:</span>
                        <span class="font-medium text-primary">{baseBranch}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-light">
                        <span class="text-secondary">Type:</span>
                        <span class="font-medium text-primary">{projectType}</span>
                    </div>
                    <div class="flex justify-between py-2">
                        <span class="text-secondary">Agents:</span>
                        <span class="font-medium text-primary">{selectedAgents.join(', ')}</span>
                    </div>
                </div>
                
                {#if error}
                    <div class="mt-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300 text-sm">
                        {error}
                    </div>
                {/if}
            </div>
        {/if}
    </div>
    
    <!-- Footer -->
    <div class="flex justify-between p-4 bg-surface-secondary border-t">
        {#if currentStep > 1}
            <Button
                variant="subtle"
                unifiedSize="md"
                btnClasses="max-w-fit"
                startIcon={{ icon: ArrowLeft }}
                on:click={prevStep}
                disabled={isSubmitting}
            >
                Back
            </Button>
        {:else}
            <div></div>
        {/if}
        
        {#if currentStep < totalSteps}
            <Button
                variant="accent"
                unifiedSize="md"
                btnClasses="max-w-fit"
                endIcon={{ icon: ArrowRight }}
                on:click={nextStep}
                disabled={!canProceed}
            >
                Next
            </Button>
        {:else}
            <Button
                variant="accent"
                unifiedSize="md"
                btnClasses="max-w-fit"
                startIcon={{ icon: Plus }}
                on:click={handleSubmit}
                disabled={isSubmitting || !canProceed}
            >
                {isSubmitting ? 'Creating...' : 'Create project'}
            </Button>
        {/if}
    </div>
</div>
