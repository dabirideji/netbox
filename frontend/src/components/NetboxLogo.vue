<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number;
  }>(),
  {
    size: 18,
  },
);
</script>

<template>
  <span class="netbox-logo" :style="{ '--netbox-logo-size': `${size}px` }" aria-hidden="true">
    <img class="netbox-logo__image netbox-logo__image--light" src="/icons/black.png" alt="" />
    <img class="netbox-logo__image netbox-logo__image--dark" src="/icons/white.png" alt="" />
  </span>
</template>
