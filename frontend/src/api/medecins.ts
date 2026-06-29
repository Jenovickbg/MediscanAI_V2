import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiClient } from './client'
import type { Medecin, MedecinCreatePayload, MedecinUpdatePayload } from '../types/medecin'

export async function fetchMedecins(): Promise<Medecin[]> {
  const { data } = await apiClient.get<Medecin[]>('/medecins')
  return data
}

export async function createMedecin(payload: MedecinCreatePayload): Promise<Medecin> {
  const { data } = await apiClient.post<Medecin>('/medecins', payload)
  return data
}

export async function updateMedecin(id: number, payload: MedecinUpdatePayload): Promise<Medecin> {
  const { data } = await apiClient.put<Medecin>(`/medecins/${id}`, payload)
  return data
}

export async function deleteMedecin(id: number): Promise<void> {
  await apiClient.delete(`/medecins/${id}`)
}

export function useMedecinsQuery() {
  return useQuery({
    queryKey: ['medecins'],
    queryFn: fetchMedecins,
    staleTime: 30_000,
  })
}

export function useCreateMedecinMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMedecin,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['medecins'] })
    },
  })
}

export function useUpdateMedecinMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: MedecinUpdatePayload }) =>
      updateMedecin(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['medecins'] })
    },
  })
}

export function useDeleteMedecinMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteMedecin,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['medecins'] })
    },
  })
}
