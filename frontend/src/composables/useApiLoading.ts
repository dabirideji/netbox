import { ref } from 'vue';

const apiPendingCount = ref(0);

export function useApiLoading() {
  return { apiPendingCount };
}

export function incrementApiLoading(): void {
  apiPendingCount.value += 1;
}

export function decrementApiLoading(): void {
  if (apiPendingCount.value > 0) {
    apiPendingCount.value -= 1;
  }
}
