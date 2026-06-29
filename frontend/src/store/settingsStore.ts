import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { WindowPresetId } from '../types/settings'

interface SettingsStore {
  windowCenter: number
  windowWidth: number
  windowPreset: WindowPresetId
  gradCamOpacity: number
  setWindowCenter: (value: number) => void
  setWindowWidth: (value: number) => void
  setWindowPreset: (preset: WindowPresetId) => void
  applyWindowPreset: (preset: WindowPresetId, center: number, width: number) => void
  setGradCamOpacity: (value: number) => void
  resetDisplaySettings: () => void
}

const DEFAULTS = {
  windowCenter: 300,
  windowWidth: 1500,
  windowPreset: 'bone' as WindowPresetId,
  gradCamOpacity: 60,
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      ...DEFAULTS,
      setWindowCenter: (windowCenter) => set({ windowCenter, windowPreset: 'custom' }),
      setWindowWidth: (windowWidth) => set({ windowWidth, windowPreset: 'custom' }),
      setWindowPreset: (windowPreset) => set({ windowPreset }),
      applyWindowPreset: (windowPreset, windowCenter, windowWidth) =>
        set({ windowPreset, windowCenter, windowWidth }),
      setGradCamOpacity: (gradCamOpacity) => set({ gradCamOpacity }),
      resetDisplaySettings: () => set({ ...DEFAULTS }),
    }),
    { name: 'mediscanai-settings' },
  ),
)
