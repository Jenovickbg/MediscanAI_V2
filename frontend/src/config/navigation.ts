import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  ClipboardList,
  FolderPlus,
  LayoutDashboard,
  Settings,
  User,
} from 'lucide-react'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
}

export const MAIN_NAV_ITEMS: NavItem[] = [
  { label: 'Tableau de bord', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Nouvel examen', path: '/import', icon: FolderPlus },
  { label: 'Historique', path: '/historique', icon: ClipboardList },
  { label: 'Statistiques', path: '/statistiques', icon: BarChart3 },
  { label: 'Paramètres', path: '/parametres', icon: Settings },
  { label: 'Profil', path: '/profil', icon: User },
]

export const APP_VERSION = '1.0.0'
