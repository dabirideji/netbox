import { computed, ref, type Ref } from 'vue';
import { fetchNetworkInterfaces, refreshNetworkIdentity } from '../api';
import { isWifiNameHidden } from '../format';
import type { NetworkIdentity, NetworkInterfaceOption } from '../types';
import { useMonitorStore } from '../stores/monitor';

function selectionWifiName(option: NetworkInterfaceOption): string {
  return option.ssid ?? option.label;
}

export function useNetworkAccess(network: Ref<NetworkIdentity | undefined>) {
  const monitor = useMonitorStore();
  const isRefreshing = ref(false);
  const statusMessage = ref<string | null>(null);
  const modalOpen = ref(false);
  const interfaces = ref<NetworkInterfaceOption[]>([]);
  const interfacesLoading = ref(false);

  const isHidden = computed(() => isWifiNameHidden(network.value));
  const activeInterface = computed(() => network.value?.interface ?? null);

  async function loadInterfaces(): Promise<void> {
    interfacesLoading.value = true;
    try {
      const response = await fetchNetworkInterfaces();
      interfaces.value = response.interfaces;
    } catch {
      interfaces.value = [];
    } finally {
      interfacesLoading.value = false;
    }
  }

  function closeModal(): void {
    modalOpen.value = false;
    statusMessage.value = null;
  }

  function applyNetworkResponse(networkIdentity: NetworkIdentity): void {
    monitor.patchNetwork(networkIdentity);
  }

  async function openNetworkModal(): Promise<void> {
    statusMessage.value = null;
    modalOpen.value = true;
    await loadInterfaces();
  }

  async function refreshNetworkList(): Promise<void> {
    statusMessage.value = null;
    await loadInterfaces();
  }

  async function selectNetworkInterface(option: NetworkInterfaceOption): Promise<void> {
    isRefreshing.value = true;
    statusMessage.value = null;

    try {
      const wifiName = selectionWifiName(option);
      const response = await refreshNetworkIdentity({
        interface: option.interface,
        wifiName,
      });

      applyNetworkResponse(response.network);
      statusMessage.value = response.network.ssid ?? response.network.name;
      modalOpen.value = false;
    } catch (error) {
      statusMessage.value = error instanceof Error ? error.message : 'Could not apply.';
    } finally {
      isRefreshing.value = false;
    }
  }

  async function saveManualNetworkName(ssid: string): Promise<void> {
    isRefreshing.value = true;
    statusMessage.value = null;

    const active = interfaces.value.find((option) => option.active);

    try {
      const response = await refreshNetworkIdentity({
        wifiName: ssid,
        ...(active?.interface ? { interface: active.interface } : {}),
      });

      applyNetworkResponse(response.network);

      if (response.network.ssid) {
        statusMessage.value = response.network.ssid;
        modalOpen.value = false;
        return;
      }

      statusMessage.value = 'Could not save.';
    } catch (error) {
      statusMessage.value = error instanceof Error ? error.message : 'Could not save.';
    } finally {
      isRefreshing.value = false;
    }
  }

  return {
    isHidden,
    isRefreshing,
    statusMessage,
    modalOpen,
    activeInterface,
    interfaces,
    interfacesLoading,
    closeModal,
    openNetworkModal,
    refreshNetworkList,
    selectNetworkInterface,
    saveManualNetworkName,
  };
}
