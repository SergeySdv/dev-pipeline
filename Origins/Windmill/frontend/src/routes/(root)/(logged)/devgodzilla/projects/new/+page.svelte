<script lang="ts">
  import { goto } from '$app/navigation';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import ProjectOnboarding from '$lib/devgodzilla/ProjectOnboarding.svelte';

  function handleComplete(event: CustomEvent<{ projectId: number }>) {
    goto(`/devgodzilla/projects/${event.detail.projectId}`);
  }
</script>

<svelte:head>
  <title>New Project - DevGodzilla</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-8 md:px-8 py-6">
  <PageHeader title="New Project" />

  <ProjectOnboarding on:complete={handleComplete} onComplete={(projectId) => goto(`/devgodzilla/projects/${projectId}`)} />
</div>
