export interface Medecin {
  id: number
  email: string
  nom: string
  actif: boolean
  created_at: string
  nb_examens: number
}

export interface MedecinCreatePayload {
  email: string
  nom: string
  password: string
  actif?: boolean
}

export interface MedecinUpdatePayload {
  email?: string
  nom?: string
  password?: string
  actif?: boolean
}
