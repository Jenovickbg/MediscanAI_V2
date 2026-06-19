import { create } from 'zustand'

export const VERTEBRAE = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7'] as const
export type VertebraId = (typeof VERTEBRAE)[number]

interface ViewerStore {
  selectedVertebra: VertebraId | null
  targetSliceIndex: number | null
  setSelectedVertebra: (vertebra: VertebraId, coupeReference?: number) => void
  clearTargetSlice: () => void
  reset: () => void
}

export const useViewerStore = create<ViewerStore>((set) => ({
  selectedVertebra: null,
  targetSliceIndex: null,
  setSelectedVertebra: (vertebra, coupeReference) =>
    set({
      selectedVertebra: vertebra,
      targetSliceIndex: coupeReference ?? null,
    }),
  clearTargetSlice: () => set({ targetSliceIndex: null }),
  reset: () => set({ selectedVertebra: null, targetSliceIndex: null }),
}))

export function isVertebraId(value: string): value is VertebraId {
  return (VERTEBRAE as readonly string[]).includes(value)
}
