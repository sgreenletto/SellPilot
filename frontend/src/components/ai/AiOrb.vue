<script setup lang="ts">
interface Props {
  size?: "sm" | "md" | "lg";
}

const props = withDefaults(defineProps<Props>(), {
  size: "md",
});
</script>

<template>
  <div :class="['ai-orb', `ai-orb--${props.size}`]" role="img" aria-label="SellPilot AI 抽象光球">
    <span class="ai-orb__glow"></span>
    <svg viewBox="0 0 220 220" aria-hidden="true">
      <defs>
        <radialGradient id="sp-orb-core" cx="50%" cy="42%" r="58%">
          <stop offset="0%" stop-color="var(--sp-color-surface-strong)" stop-opacity="0.95" />
          <stop offset="45%" stop-color="var(--sp-color-accent-blue-soft)" stop-opacity="0.72" />
          <stop offset="100%" stop-color="var(--sp-color-accent-purple)" stop-opacity="0.16" />
        </radialGradient>
        <linearGradient id="sp-orb-stroke-a" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="var(--sp-color-accent-pink)" />
          <stop offset="50%" stop-color="var(--sp-color-accent-purple)" />
          <stop offset="100%" stop-color="var(--sp-color-accent-blue)" />
        </linearGradient>
        <linearGradient id="sp-orb-stroke-b" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="var(--sp-color-accent-blue)" />
          <stop offset="100%" stop-color="var(--sp-color-accent-pink)" />
        </linearGradient>
        <filter id="sp-orb-blur">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
      </defs>
      <circle cx="110" cy="110" r="74" fill="url(#sp-orb-core)" />
      <g fill="none" stroke-linecap="round">
        <ellipse
          cx="110"
          cy="110"
          rx="78"
          ry="43"
          stroke="url(#sp-orb-stroke-a)"
          stroke-width="3.2"
          transform="rotate(-18 110 110)"
        />
        <ellipse
          cx="110"
          cy="110"
          rx="75"
          ry="36"
          stroke="url(#sp-orb-stroke-b)"
          stroke-width="2.6"
          transform="rotate(48 110 110)"
        />
        <ellipse
          cx="110"
          cy="110"
          rx="70"
          ry="31"
          stroke="url(#sp-orb-stroke-a)"
          stroke-width="2.2"
          transform="rotate(102 110 110)"
        />
        <path
          d="M45 113c28-52 83-68 130-16s-9 86-63 66-75-50-31-92 93-4 96 40"
          stroke="url(#sp-orb-stroke-b)"
          stroke-width="2.4"
          opacity="0.72"
          filter="url(#sp-orb-blur)"
        />
        <path
          d="M58 76c44 16 37 85 82 84s54-54 19-82-89-28-107 17 31 78 78 56"
          stroke="url(#sp-orb-stroke-a)"
          stroke-width="2"
          opacity="0.62"
        />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.ai-orb {
  position: relative;
  display: grid;
  place-items: center;
  isolation: isolate;
  margin-inline: auto;
  animation: sp-orb-float 5.5s ease-in-out infinite;
}

.ai-orb svg {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
}

.ai-orb__glow {
  position: absolute;
  width: 64%;
  height: 64%;
  background: color-mix(in srgb, var(--sp-color-accent-blue) 20%, transparent);
  filter: blur(28px);
  border-radius: var(--sp-radius-pill);
}

.ai-orb--sm {
  width: 112px;
  height: 112px;
}

.ai-orb--md {
  width: 172px;
  height: 172px;
}

.ai-orb--lg {
  width: 220px;
  height: 220px;
}

@keyframes sp-orb-float {
  0%,
  100% {
    transform: translateY(0) rotate(-1deg);
  }
  50% {
    transform: translateY(-6px) rotate(1.5deg);
  }
}
</style>
