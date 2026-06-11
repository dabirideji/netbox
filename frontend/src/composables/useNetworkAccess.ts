import { computed, ref, type Ref } from 'vue';
import { refreshNetworkIdentity } from '../api';
import { isWifiNameHidden } from '../format';
import type { NetworkIdentity } from '../types';

export interface NetworkAccessResponse {
  ok: boolean;
  ssid: string | null;
  message: string;
}

export function useNetworkAccess(network: Ref<NetworkIdentity | undefined>) {
  const isRefreshing = ref(false);
  const statusMessage = ref<string | null>(null);

  const isHidden = computed(() => isWifiNameHidden(network.value));

  async function requestNetworkAccess(): Promise<void> {
    isRefreshing.value = true;
    statusMessage.value = null;

    try {
      if (typeof window !== 'undefined' && window.netboxDesktop?.requestNetworkAccess) {
        const result = (await window.netboxDesktop.requestNetworkAccess()) as NetworkAccessResponse;
        statusMessage.value = result.message;
        if (!result.ok && !result.ssid) {
          return;
        }
        return;
      }

      const response = await refreshNetworkIdentity();
      if (response.network.ssid) {
        statusMessage.value = `Wi‑Fi ${response.network.ssid} is now visible.`;
        return;
      }

      statusMessage.value =
        'Still hidden. On macOS, enable Location Services for your terminal app or Netbox in System Settings → Privacy & Security → Location Services, then try again.';
    } catch (error) {
      statusMessage.value = error instanceof Error ? error.message : 'Unable to refresh network name';
    } finally {
      isRefreshing.value = false;
    }
  }

  return {
    isHidden,
    isRefreshing,
    statusMessage,
    requestNetworkAccess,
  };
}
