<script setup lang="ts">
import { ChevronDown } from "@lucide/vue";

export interface SelectOption {
  label: string;
  value: string;
  disabled?: boolean;
}

interface Props {
  modelValue: string;
  options: SelectOption[];
  label?: string;
  placeholder?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  label: "",
  placeholder: "请选择",
  disabled: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

function updateValue(event: Event) {
  emit("update:modelValue", (event.target as HTMLSelectElement).value);
}
</script>

<template>
  <label class="sp-select-field">
    <span v-if="props.label" class="sp-select-field__label">{{ props.label }}</span>
    <span class="sp-select-field__control">
      <select
        :value="props.modelValue"
        :disabled="props.disabled"
        :aria-label="props.label || props.placeholder"
        @change="updateValue"
      >
        <option value="" disabled>{{ props.placeholder }}</option>
        <option
          v-for="option in props.options"
          :key="option.value"
          :value="option.value"
          :disabled="option.disabled"
        >
          {{ option.label }}
        </option>
      </select>
      <ChevronDown :size="15" aria-hidden="true" />
    </span>
  </label>
</template>

<style scoped>
.sp-select-field {
  display: grid;
  gap: var(--sp-space-2);
}

.sp-select-field__label {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}

.sp-select-field__control {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}

.sp-select-field__control select {
  width: 100%;
  padding-right: var(--sp-space-6);
  color: inherit;
  cursor: pointer;
  appearance: none;
  background: transparent;
  border: 0;
  outline: none;
}

.sp-select-field__control svg {
  position: absolute;
  right: var(--sp-space-3);
  pointer-events: none;
}

.sp-select-field__control:focus-within {
  border-color: var(--sp-color-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-color-accent-blue) 18%, transparent);
}
</style>
