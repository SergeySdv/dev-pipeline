<script lang="ts">
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
    
    $: filteredStories = stories.filter(s => 
        filter === 'all' || s.status === filter
    );
    
    $: progress = stories.length > 0
        ? Math.round((stories.filter(s => s.status === 'completed').length / stories.length) * 100)
        : 0;
    
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
    
    function getStatusIcon(status: string): string {
        switch (status) {
            case 'completed': return '✅';
            case 'in_progress': return '🔄';
            case 'blocked': return '🚫';
            default: return '⏳';
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

<div class="bg-surface rounded-lg p-4">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-primary">User Story Tracker</h3>
        <div class="relative w-48 h-6 bg-surface-secondary rounded-full overflow-hidden">
            <div 
                class="h-full bg-blue-500 transition-all duration-300" 
                style="width: {progress}%"
            ></div>
            <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold text-primary">
                {progress}% Complete
            </span>
        </div>
    </div>
    
    <div class="flex gap-2 mb-4">
        <button 
            class="px-3 py-1.5 text-sm rounded transition-colors
                {filter === 'all' ? 'bg-surface-accent-primary text-white' : 'bg-surface-secondary text-secondary hover:bg-surface-hover'}"
            on:click={() => filter = 'all'}
        >
            All
        </button>
        <button 
            class="px-3 py-1.5 text-sm rounded transition-colors
                {filter === 'pending' ? 'bg-surface-accent-primary text-white' : 'bg-surface-secondary text-secondary hover:bg-surface-hover'}"
            on:click={() => filter = 'pending'}
        >
            Pending
        </button>
        <button 
            class="px-3 py-1.5 text-sm rounded transition-colors
                {filter === 'in_progress' ? 'bg-surface-accent-primary text-white' : 'bg-surface-secondary text-secondary hover:bg-surface-hover'}"
            on:click={() => filter = 'in_progress'}
        >
            In Progress
        </button>
        <button 
            class="px-3 py-1.5 text-sm rounded transition-colors
                {filter === 'completed' ? 'bg-surface-accent-primary text-white' : 'bg-surface-secondary text-secondary hover:bg-surface-hover'}"
            on:click={() => filter = 'completed'}
        >
            Completed
        </button>
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
                        <span class="text-lg">{getStatusIcon(story.status)}</span>
                        <span class="px-1.5 py-0.5 text-2xs font-semibold text-white rounded {getPriorityClass(story.priority)}">
                            {story.priority}
                        </span>
                        <span class="font-semibold text-secondary">{story.id}</span>
                        <span class="text-primary">{story.title}</span>
                    </div>
                    
                    {#if story.tasks.length > 0}
                        <div class="mt-2 pl-6 space-y-1">
                            {#each story.tasks as task}
                                <div class="flex items-center gap-2 text-sm {task.status === 'completed' ? 'line-through text-secondary' : 'text-secondary'}">
                                    <span>{task.status === 'completed' ? '☑' : '☐'}</span>
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
