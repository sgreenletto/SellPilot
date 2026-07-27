<script setup lang="ts">
interface Props {
  padded?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  padded: true,
});
</script>

<template>
  <main :class="['page-container', { 'page-container--padded': props.padded }]">
    <slot />
  </main>
</template>

<style scoped>
.page-container {
  width: 100%;
  max-width: var(--sp-content-max-width);
  margin: 0 auto;
}

.page-container--padded {
  padding: 0 var(--sp-space-8) var(--sp-space-8);
}

@media (max-width: 1023px) {
  .page-container--padded {
    padding: 0 var(--sp-space-5) var(--sp-space-5);
  }
}
</style>
