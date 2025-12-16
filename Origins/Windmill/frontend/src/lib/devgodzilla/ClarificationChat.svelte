<script lang="ts">
  import { createEventDispatcher, afterUpdate } from 'svelte';
  import { Button } from '$lib/components/common';
  import { Send } from 'lucide-svelte';
  
  export let questions: Array<{
    id: string;
    question: string;
    options?: string[];
    answer?: string;
    status: 'open' | 'answered';
  }> = [];
  
  const dispatch = createEventDispatcher();
  let chatContainer: HTMLElement;
  let currentAnswer = '';
  
  function handleAnswer(questionId: string, answer: string) {
    dispatch('answer', { questionId, answer });
    currentAnswer = '';
  }
  
  function scrollToBottom() {
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }
  
  afterUpdate(scrollToBottom);
</script>

<div class="flex flex-col h-full bg-surface border rounded-lg overflow-hidden shadow-sm">
  <div class="px-4 py-3 bg-surface-secondary border-b">
    <h3 class="text-sm font-semibold text-primary">Clarification Requests</h3>
  </div>
  
  <div 
    bind:this={chatContainer}
    class="flex-1 overflow-y-auto p-4 space-y-4"
  >
    {#if questions.length === 0}
      <div class="text-center text-secondary py-10 italic">
        No pending clarifications.
      </div>
    {:else}
      {#each questions as q}
        <div class="space-y-2">
          <!-- AI Question -->
          <div class="flex items-start">
            <div class="flex-shrink-0 mr-3">
              <div class="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-200 text-xs font-bold">
                AI
              </div>
            </div>
            <div class="bg-surface-secondary rounded-lg rounded-tl-none p-3 max-w-[85%] text-sm text-primary">
              <p>{q.question}</p>
              {#if q.options && q.status === 'open'}
                <div class="mt-2 space-y-1">
                  {#each q.options as opt}
                    <Button
                      variant="default"
                      unifiedSize="sm"
                      btnClasses="justify-start text-left"
                      on:click={() => handleAnswer(q.id, opt)}
                    >
                      {opt}
                    </Button>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
          
          <!-- User Answer -->
          {#if q.status === 'answered' && q.answer}
            <div class="flex items-start justify-end">
              <div class="bg-surface-accent-primary text-white rounded-lg rounded-tr-none p-3 max-w-[85%] text-sm">
                <p>{q.answer}</p>
              </div>
              <div class="flex-shrink-0 ml-3">
                <div class="h-8 w-8 rounded-full bg-surface-secondary flex items-center justify-center text-secondary text-xs font-bold">
                  You
                </div>
              </div>
            </div>
          {:else if q.status === 'open' && !q.options}
            <div class="flex items-start justify-end">
              <div class="w-full max-w-[85%]">
                <div class="relative">
                  <textarea
                    bind:value={currentAnswer}
                    class="w-full rounded-lg sm:text-sm p-2"
                    placeholder="Type your answer..."
                    rows="3"
                  ></textarea>
                  <div class="absolute bottom-2 right-2">
                    <Button
                      variant="accent"
                      unifiedSize="sm"
                      btnClasses="max-w-fit"
                      startIcon={{ icon: Send }}
                      on:click={() => handleAnswer(q.id, currentAnswer)}
                      disabled={!currentAnswer.trim()}
                    >
                      Send
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>
