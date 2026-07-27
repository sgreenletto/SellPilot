import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const MOBILE_BREAKPOINT = 1024;

export function useBreakpoint() {
  const width = ref(typeof window === "undefined" ? 1440 : window.innerWidth);

  function updateWidth() {
    width.value = window.innerWidth;
  }

  onMounted(() => window.addEventListener("resize", updateWidth, { passive: true }));
  onBeforeUnmount(() => window.removeEventListener("resize", updateWidth));

  return {
    width,
    isMobile: computed(() => width.value < MOBILE_BREAKPOINT),
    isCompact: computed(() => width.value >= MOBILE_BREAKPOINT && width.value < 1280),
  };
}
