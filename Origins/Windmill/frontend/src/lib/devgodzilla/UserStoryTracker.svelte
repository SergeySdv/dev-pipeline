<script lang="ts">
    import { Badge, Button } from '$lib/components/common';

    interface Story {
        id: string;
        title: string;
        status: 'pending' | 'in_progress' | 'completed' | 'blocked';
        priority: 'P1' | 'P2' | 'P3';
        tasks: Task[];
    }
    
    interface Task {
        id: string;
        name: string;
        status: 'pending' | 'completed' | 'failed';
    }
    
    let stories: Story[] = [];
    let loading = true;
    let filter: 'all' | 'pending' | 'in_progress' | 'completed' = 'all';

    const filteredStories = $derived(stories.filter(s =>
        filter === 'all' || s.status === filter
    ));

    const progress = $derived(stories.length > 0
        ? Math.round((stories.filter(s => s.status === 'completed').length / stories.length) * 100)
        : 0);

    async function loadStories() {
        loading = true;
        try {
            // Mock data - would fetch from API
            stories = [
                {
                    id: 'US1',
                    title: 'User can log in with email/password',
                    status: 'completed',
                    priority: 'P1',
                    tasks: [
                        { id: 'T1', name: 'Create login form', status: 'completed' },
                        { id: 'T2', name: 'Add auth API', status: 'completed' },
                    ]
                },
                {
                    id: 'US2',
                    title: 'User can reset password',
                    status: 'in_progress',
                    priority: 'P1',
                    tasks: [
                        { id: 'T3', name: 'Create reset form', status: 'completed' },
                        { id: 'T4', name: 'Send reset email', status: 'pending' },
                    ]
                },
                {
                    id: 'US3',
                    title: 'User can view profile',
                    status: 'pending',
                    priority: 'P2',
                    tasks: []
                },
            ];
        } finally {
            loading = false;
        }
    }
    
    function getPriorityClass(priority: string): string {
        switch (priority) {
            case 'P1': return 'bg-red-500';
            case 'P2': return 'bg-yellow-500';
            default: return 'bg-green-500';
        }
    }
    
    loadStories();
</script>

<div class="bg-surface rounded-lg border p-4">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-primary">User Story Tracker</h3>
        <div class="relative w-48 h-6 bg-surface-secondary rounded-full overflow-hidden">
            <div 
                class="h-full bg-surface-accent-primary transition-all duration-300" 
                style="width: {progress}%"
            ></div>
            <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold text-primary">
                {progress}% Complete
            </span>
        </div>
    </div>
    
    <div class="flex gap-2 mb-4">
        <Button variant="default" unifiedSize="sm" btnClasses="max-w-fit" selected={filter === 'all'} on:click={() => (filter = 'all')}>
            All
        </Button>
        <Button variant="default" unifiedSize="sm" btnClasses="max-w-fit" selected={filter === 'pending'} on:click={() => (filter = 'pending')}>
            Pending
        </Button>
        <Button
            variant="default"
            unifiedSize="sm"
            btnClasses="max-w-fit"
            selected={filter === 'in_progress'}
            on:click={() => (filter = 'in_progress')}
        >
            In progress
        </Button>
        <Button
            variant="default"
            unifiedSize="sm"
            btnClasses="max-w-fit"
            selected={filter === 'completed'}
            on:click={() => (filter = 'completed')}
        >
            Completed
        </Button>
    </div>
    
    {#if loading}
        <div class="text-center py-8 text-secondary">Loading stories...</div>
    {:else if filteredStories.length === 0}
        <div class="text-center py-8 text-secondary">No stories found</div>
    {:else}
        <div class="flex flex-col gap-3">
            {#each filteredStories as story}
                <div 
                    class="bg-surface-secondary rounded-md p-3 border-l-4 transition-opacity
                        {story.status === 'completed' ? 'opacity-70 border-green-500' : 'border-accent'}"
                >
                    <div class="flex items-center gap-2">
                        <span class="px-1.5 py-0.5 text-2xs font-semibold text-white rounded {getPriorityClass(story.priority)}">
                            {story.priority}
                        </span>
                        <span class="font-semibold text-secondary">{story.id}</span>
                        <span class="text-primary">{story.title}</span>
                        <div class="flex-1"></div>
                        <Badge color={story.status === 'completed' ? 'green' : story.status === 'in_progress' ? 'blue' : story.status === 'blocked' ? 'red' : 'gray'}>
                            {story.status}
                        </Badge>
                    </div>
                    
                    {#if story.tasks.length > 0}
                        <div class="mt-2 pl-6 space-y-1">
                            {#each story.tasks as task}
                                <div class="flex items-center gap-2 text-sm {task.status === 'completed' ? 'line-through text-secondary' : 'text-secondary'}">
                                    <span>{task.name}</span>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>
