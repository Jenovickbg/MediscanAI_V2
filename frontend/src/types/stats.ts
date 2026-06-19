export interface RecentExamen {
  study_id: string
  patient_id: string
  date: string
  vertebres: string[]
  score_global: number | null
  fracture_detectee: boolean | null
  analysed: boolean
}

export interface DashboardStats {
  today_exams: number
  month_fractures: number
  avg_score: number
  avg_time: number
  recent_exams: RecentExamen[]
}

export type StatsPeriod = '7d' | '30d' | '90d'

export interface DailyCount {
  date: string
  count: number
}

export interface ResultDistribution {
  label: string
  value: number
}

export interface VertebraStat {
  vertebre: string
  fracture_count: number
  avg_score: number
}

export interface RecallMetrics {
  recall: number
  auc: number
  f1: number
  model_name: string
}

export interface HistoriqueStats {
  period: StatsPeriod
  daily_counts: DailyCount[]
  result_distribution: ResultDistribution[]
  vertebrae_distribution: VertebraStat[]
  recall_metrics: RecallMetrics
}
