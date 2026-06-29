import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  ClipboardList,
  FolderPlus,
  LayoutDashboard,
  Settings,
  Stethoscope,
  User,
} from 'lucide-react'

import type { UserRole } from '../types/auth'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
  roles?: UserRole[]
}

export const MAIN_NAV_ITEMS: NavItem[] = [
  { label: 'Tableau de bord', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Nouvel examen', path: '/import', icon: FolderPlus },
  { label: 'Historique', path: '/historique', icon: ClipboardList },
  { label: 'Statistiques', path: '/statistiques', icon: BarChart3 },
  { label: 'Médecins', path: '/admin/medecins', icon: Stethoscope, roles: ['admin'] },
  { label: 'Paramètres', path: '/parametres', icon: Settings },
  { label: 'Profil', path: '/profil', icon: User },
]

export function getNavItemsForRole(role: UserRole | undefined): NavItem[] {
  return MAIN_NAV_ITEMS.filter((item) => !item.roles || (role && item.roles.includes(role)))
}

export const APP_VERSION = '1.0.0'
