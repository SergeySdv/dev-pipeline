<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    
    const dispatch = createEventDispatcher();
    
    interface Template {
        id: string;
        name: string;
        type: 'spec' | 'plan' | 'tasks' | 'checklist';
        description: string;
        content: string;
        isDefault: boolean;
        lastModified: string;
    }
    
    let templates: Template[] = [];
    let selectedTemplate: Template | null = null;
    let editing = false;
    let editContent = '';
    let loading = true;
    
    const defaultTemplates: Template[] = [
        {
            id: 'spec-default',
            name: 'Feature Spec Template',
            type: 'spec',
            description: 'Default template for feature specifications',
            content: `# Feature: {{feature_name}}

## Overview
{{description}}

## User Stories
- As a {{user_type}}, I want to {{action}} so that {{benefit}}

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Technical Notes
{{technical_notes}}`,
            isDefault: true,
            lastModified: '2024-01-01T00:00:00Z'
        },
        {
            id: 'plan-default',
            name: 'Implementation Plan Template',
            type: 'plan',
            description: 'Default template for implementation plans',
            content: `# Implementation Plan: {{feature_name}}

## Approach
{{approach}}

## Components
1. {{component_1}}
2. {{component_2}}

## Dependencies
- {{dependency_1}}

## Risks
- {{risk_1}}

## Timeline
- Phase 1: {{phase_1}}`,
            isDefault: true,
            lastModified: '2024-01-01T00:00:00Z'
        },
        {
            id: 'tasks-default',
            name: 'Task List Template',
            type: 'tasks',
            description: 'Default template for task breakdowns',
            content: `# Tasks: {{feature_name}}

## Setup
- [ ] Task 1 [P1] @agent:opencode
- [ ] Task 2 [P1] @agent:claude-code

## Implementation
- [ ] Task 3 [P2] depends:task1
- [ ] Task 4 [P2] depends:task2

## Testing
- [ ] Write unit tests [P1]
- [ ] Write integration tests [P2]

## Documentation
- [ ] Update README [P3]`,
            isDefault: true,
            lastModified: '2024-01-01T00:00:00Z'
        },
        {
            id: 'checklist-default',
            name: 'QA Checklist Template',
            type: 'checklist',
            description: 'Default template for quality checklists',
            content: `# QA Checklist: {{feature_name}}

## Required
- [ ] All tests pass
- [ ] No lint errors
- [ ] Type checking passes
- [ ] Documentation updated

## Recommended
- [ ] Security scan passes
- [ ] Code reviewed

## Optional
- [ ] Performance tested
- [ ] Accessibility checked`,
            isDefault: true,
            lastModified: '2024-01-01T00:00:00Z'
        }
    ];
    
    async function loadTemplates() {
        loading = true;
        try {
            templates = [...defaultTemplates];
        } finally {
            loading = false;
        }
    }
    
    function selectTemplate(template: Template) {
        selectedTemplate = template;
        editing = false;
    }
    
    function startEditing() {
        if (!selectedTemplate) return;
        editContent = selectedTemplate.content;
        editing = true;
    }
    
    function cancelEditing() {
        editing = false;
        editContent = '';
    }
    
    async function saveTemplate() {
        if (!selectedTemplate) return;
        
        selectedTemplate.content = editContent;
        selectedTemplate.lastModified = new Date().toISOString();
        templates = templates;
        editing = false;
        
        dispatch('save', { template: selectedTemplate });
    }
    
    function getTypeIcon(type: string): string {
        switch (type) {
            case 'spec': return '📋';
            case 'plan': return '📝';
            case 'tasks': return '✅';
            case 'checklist': return '☑️';
            default: return '📄';
        }
    }
    
    function getTypeColor(type: string): string {
        switch (type) {
            case 'spec': return 'text-blue-600 dark:text-blue-400';
            case 'plan': return 'text-purple-600 dark:text-purple-400';
            case 'tasks': return 'text-green-600 dark:text-green-400';
            case 'checklist': return 'text-yellow-600 dark:text-yellow-400';
            default: return 'text-secondary';
        }
    }
    
    loadTemplates();
</script>

<div class="flex h-[500px] bg-surface rounded-lg overflow-hidden border">
    <!-- Sidebar -->
    <div class="w-64 border-r flex flex-col">
        <div class="p-4 border-b">
            <h3 class="text-lg font-semibold text-primary">📑 Templates</h3>
        </div>
        
        {#if loading}
            <div class="flex-1 flex items-center justify-center text-secondary">Loading...</div>
        {:else}
            <div class="flex-1 overflow-y-auto p-2">
                {#each templates as template}
                    <button 
                        class="flex items-center gap-2 w-full p-3 rounded-md text-left transition-all mb-1
                            {selectedTemplate?.id === template.id 
                                ? 'bg-surface-accent-primary text-white' 
                                : 'hover:bg-surface-hover text-primary'}"
                        on:click={() => selectTemplate(template)}
                    >
                        <span class="text-xl">{getTypeIcon(template.type)}</span>
                        <div class="flex-1 overflow-hidden">
                            <span class="block text-sm font-medium truncate">{template.name}</span>
                            <span class="block text-xs uppercase {selectedTemplate?.id === template.id ? 'text-white/70' : getTypeColor(template.type)}">
                                {template.type}
                            </span>
                        </div>
                        {#if template.isDefault}
                            <span class="px-1.5 py-0.5 bg-white/20 text-2xs font-semibold rounded">
                                DEFAULT
                            </span>
                        {/if}
                    </button>
                {/each}
            </div>
        {/if}
    </div>
    
    <!-- Content -->
    <div class="flex-1 flex flex-col overflow-hidden">
        {#if selectedTemplate}
            <div class="flex justify-between items-start p-4 border-b">
                <div>
                    <h4 class="text-lg font-semibold text-primary">
                        {getTypeIcon(selectedTemplate.type)} {selectedTemplate.name}
                    </h4>
                    <p class="text-sm text-secondary">{selectedTemplate.description}</p>
                </div>
                <div class="flex gap-2">
                    {#if editing}
                        <button 
                            class="px-3 py-1.5 text-sm bg-surface-secondary text-primary rounded-md hover:bg-surface-hover transition-colors"
                            on:click={cancelEditing}
                        >
                            Cancel
                        </button>
                        <button 
                            class="px-3 py-1.5 text-sm bg-surface-accent-primary text-white rounded-md hover:opacity-90 transition-opacity"
                            on:click={saveTemplate}
                        >
                            Save
                        </button>
                    {:else}
                        <button 
                            class="px-3 py-1.5 text-sm bg-surface-accent-primary text-white rounded-md hover:opacity-90 transition-opacity"
                            on:click={startEditing}
                        >
                            ✏️ Edit
                        </button>
                    {/if}
                </div>
            </div>
            
            {#if editing}
                <textarea 
                    class="flex-1 p-4 bg-surface-sunken font-mono text-sm resize-none border-0 focus:ring-0"
                    bind:value={editContent}
                    spellcheck="false"
                ></textarea>
            {:else}
                <pre class="flex-1 p-4 bg-surface-sunken font-mono text-sm overflow-auto whitespace-pre-wrap text-primary">{selectedTemplate.content}</pre>
            {/if}
            
            <div class="flex justify-between p-3 bg-surface-secondary text-xs text-secondary border-t">
                <span>Last modified: {new Date(selectedTemplate.lastModified).toLocaleString()}</span>
                <span class="font-mono">Variables: {'{{variable_name}}'}</span>
            </div>
        {:else}
            <div class="flex-1 flex flex-col items-center justify-center text-secondary">
                <div class="text-5xl mb-2">📑</div>
                <p>Select a template to view or edit</p>
            </div>
        {/if}
    </div>
</div>
