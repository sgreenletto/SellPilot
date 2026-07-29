<script setup lang="ts">
import type { AssistantResultPresentation } from "@/utils/assistantPresentation";

defineProps<{
  presentation: AssistantResultPresentation;
}>();
</script>

<template>
  <div class="assistant-result" data-testid="assistant-task-answer">
    <p class="assistant-result__summary">{{ presentation.summary }}</p>
    <dl v-if="presentation.metrics.length" class="assistant-result__metrics">
      <div v-for="metric in presentation.metrics" :key="metric.label">
        <dt>{{ metric.label }}</dt>
        <dd>{{ metric.value }}</dd>
      </div>
    </dl>
    <div v-if="presentation.items.length" class="assistant-result__items">
      <article v-for="item in presentation.items" :key="item.id">
        <div>
          <strong>{{ item.title }}</strong>
          <p v-if="item.subtitle">{{ item.subtitle }}</p>
        </div>
        <ul v-if="item.meta.length">
          <li v-for="meta in item.meta" :key="meta">{{ meta }}</li>
        </ul>
      </article>
    </div>
  </div>
</template>

<style scoped>
.assistant-result {
  display: grid;
  gap: var(--sp-space-3);
  min-width: 0;
}

.assistant-result__summary {
  color: var(--sp-color-text);
}

.assistant-result__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
  margin: 0;
}

.assistant-result__metrics > div {
  display: grid;
  min-width: 108px;
  gap: var(--sp-space-1);
  padding: var(--sp-space-2) var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-control);
}

.assistant-result__metrics dt {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.assistant-result__metrics dd {
  margin: 0;
  font-weight: 750;
}

.assistant-result__items {
  display: grid;
  gap: var(--sp-space-2);
  max-width: 100%;
  overflow-x: auto;
}

.assistant-result__items article {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  justify-content: space-between;
  min-width: 0;
  padding: var(--sp-space-3);
  background: color-mix(in srgb, var(--sp-color-surface-strong) 72%, transparent);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}

.assistant-result__items article > div {
  min-width: 0;
}

.assistant-result__items strong,
.assistant-result__items p {
  overflow-wrap: anywhere;
}

.assistant-result__items p {
  margin: var(--sp-space-1) 0 0;
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}

.assistant-result__items ul {
  display: grid;
  flex: 0 0 auto;
  gap: var(--sp-space-1);
  max-width: 46%;
  text-align: right;
}

.assistant-result__items li {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}

@media (max-width: 767px) {
  .assistant-result__items article {
    display: grid;
  }

  .assistant-result__items ul {
    max-width: 100%;
    text-align: left;
  }
}
</style>
