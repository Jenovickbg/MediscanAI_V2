import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Brain,
  Cpu,
  Monitor,
  RotateCcw,
  Save,
  SlidersHorizontal,
} from 'lucide-react'

import { fetchAppSettings, updateTriageThresholds } from '../api/settings'
import { PageHeader, PageShell } from '../components/layout'
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  LoadingSpinner,
  Slider,
} from '../components/ui'
import { APP_VERSION } from '../config/navigation'
import { useAuthStore } from '../store/authStore'
import { useSettingsStore } from '../store/settingsStore'
import type { TriageThresholds } from '../types/settings'
import { WINDOW_PRESETS } from '../types/settings'
import { cn } from '../utils/cn'

const MODEL_LABELS: Record<string, string> = {
  model1: 'Modèle 1 — Triage fracture',
  model2: 'Modèle 2 — Localisation',
  model3: 'Modèle 3 — Vertèbre C1–C7',
}

function ModelStatusBadge({ charge, mock }: { charge: boolean; mock: boolean }) {
  if (charge && !mock) {
    return <Badge variant="success">Chargé</Badge>
  }
  if (mock) {
    return <Badge variant="warning">Mode mock</Badge>
  }
  return <Badge variant="danger">Absent</Badge>
}

function ThresholdField({
  label,
  hint,
  value,
  min,
  max,
  step,
  disabled,
  onChange,
}: {
  label: string
  hint?: string
  value: number
  min: number
  max: number
  step: number
  disabled?: boolean
  onChange: (value: number) => void
}) {
  return (
    <div>
      <Slider
        label={label}
        showValue
        valueLabel={step < 1 ? value.toFixed(2) : String(value)}
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {hint && <p className="mt-1 text-[11px] text-text-muted">{hint}</p>}
    </div>
  )
}

export function ParametresPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'

  const windowCenter = useSettingsStore((s) => s.windowCenter)
  const windowWidth = useSettingsStore((s) => s.windowWidth)
  const windowPreset = useSettingsStore((s) => s.windowPreset)
  const gradCamOpacity = useSettingsStore((s) => s.gradCamOpacity)
  const setWindowCenter = useSettingsStore((s) => s.setWindowCenter)
  const setWindowWidth = useSettingsStore((s) => s.setWindowWidth)
  const applyWindowPreset = useSettingsStore((s) => s.applyWindowPreset)
  const setGradCamOpacity = useSettingsStore((s) => s.setGradCamOpacity)
  const resetDisplaySettings = useSettingsStore((s) => s.resetDisplaySettings)

  const { data: appSettings, isLoading, isError } = useQuery({
    queryKey: ['app-settings'],
    queryFn: fetchAppSettings,
    staleTime: 15_000,
  })

  const [draftSeuils, setDraftSeuils] = useState<TriageThresholds | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  useEffect(() => {
    if (appSettings?.seuils) {
      setDraftSeuils(appSettings.seuils)
    }
  }, [appSettings?.seuils])

  const saveMutation = useMutation({
    mutationFn: updateTriageThresholds,
    onSuccess: (updated) => {
      setDraftSeuils(updated)
      setSaveMessage('Seuils enregistrés — pris en compte immédiatement.')
      void queryClient.invalidateQueries({ queryKey: ['app-settings'] })
      void queryClient.invalidateQueries({ queryKey: ['health'] })
    },
    onError: () => {
      setSaveMessage('Impossible d’enregistrer les seuils.')
    },
  })

  const seuilsChanged =
    draftSeuils &&
    appSettings &&
    JSON.stringify(draftSeuils) !== JSON.stringify(appSettings.seuils)

  return (
    <>
      <PageHeader
        title="Paramètres"
        subtitle="Fenêtrage DICOM, pipeline IA et état du système."
      />

      <PageShell className="max-w-4xl space-y-6">
        {isLoading && (
          <div className="flex justify-center py-16">
            <LoadingSpinner size="lg" label="Chargement des paramètres…" />
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            Impossible de charger les paramètres. Vérifiez que le backend est démarré sur le port
            8001.
          </div>
        )}

        {appSettings && (
          <>
            <Card>
              <CardHeader className="flex items-center gap-2">
                <Monitor className="h-4 w-4 text-accent-cyan" aria-hidden="true" />
                Affichage DICOM
              </CardHeader>
              <CardBody className="space-y-5">
                <p className="text-sm text-text-secondary">
                  Ces réglages s&apos;appliquent aux viewers 2D (axial, sagittal, coronal) lors
                  de l&apos;ouverture d&apos;un examen.
                </p>

                <div className="grid gap-2 sm:grid-cols-2">
                  {WINDOW_PRESETS.map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() =>
                        applyWindowPreset(preset.id, preset.windowCenter, preset.windowWidth)
                      }
                      className={cn(
                        'rounded-lg border p-3 text-left transition-colors',
                        windowPreset === preset.id
                          ? 'border-accent-cyan/50 bg-accent-cyan/10'
                          : 'border-border bg-bg-secondary hover:border-border-light',
                      )}
                    >
                      <p className="text-sm font-medium text-text-primary">{preset.label}</p>
                      <p className="mt-0.5 font-mono text-[11px] text-accent-cyan">
                        WC {preset.windowCenter} · WW {preset.windowWidth}
                      </p>
                      <p className="mt-1 text-[11px] text-text-muted">{preset.description}</p>
                    </button>
                  ))}
                </div>

                <Divider />

                <ThresholdField
                  label="Window Center (WC)"
                  hint="Niveau de gris central de la fenêtre Hounsfield."
                  value={windowCenter}
                  min={-1000}
                  max={1000}
                  step={10}
                  onChange={setWindowCenter}
                />
                <ThresholdField
                  label="Window Width (WW)"
                  hint="Largeur de la fenêtre — contraste de l'image."
                  value={windowWidth}
                  min={1}
                  max={4000}
                  step={10}
                  onChange={setWindowWidth}
                />

                <ThresholdField
                  label="Opacité Grad-CAM par défaut"
                  hint="Transparence de la heatmap dans le viewer axial."
                  value={gradCamOpacity}
                  min={10}
                  max={100}
                  step={5}
                  onChange={setGradCamOpacity}
                />

                <Button
                  variant="ghost"
                  icon={<RotateCcw className="h-4 w-4" />}
                  onClick={resetDisplaySettings}
                >
                  Réinitialiser l&apos;affichage
                </Button>
              </CardBody>
            </Card>

            <Card>
              <CardHeader className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-accent-cyan" aria-hidden="true" />
                Seuils du pipeline IA
              </CardHeader>
              <CardBody className="space-y-5">
                {!isAdmin && (
                  <p className="rounded-lg border border-border bg-bg-secondary px-3 py-2 text-xs text-text-muted">
                    Lecture seule — seuls les administrateurs peuvent modifier les seuils
                    cliniques.
                  </p>
                )}

                {draftSeuils && (
                  <>
                    <ThresholdField
                      label="Seuil bas (normal → incertain)"
                      hint="Probabilité Modèle 1 en dessous : coupe normale."
                      value={draftSeuils.seuil_bas}
                      min={0.01}
                      max={0.5}
                      step={0.01}
                      disabled={!isAdmin}
                      onChange={(v) => setDraftSeuils((s) => s && { ...s, seuil_bas: v })}
                    />
                    <ThresholdField
                      label="Seuil haut (incertain → élevé)"
                      hint="Au-dessus : fracture suspectée avec haute confiance."
                      value={draftSeuils.seuil_haut}
                      min={0.05}
                      max={0.95}
                      step={0.01}
                      disabled={!isAdmin}
                      onChange={(v) => setDraftSeuils((s) => s && { ...s, seuil_haut: v })}
                    />
                    <ThresholdField
                      label="Score minimum RCNN (Modèle 2)"
                      value={draftSeuils.score_thresh_rcnn}
                      min={0.1}
                      max={0.95}
                      step={0.01}
                      disabled={!isAdmin}
                      onChange={(v) =>
                        setDraftSeuils((s) => s && { ...s, score_thresh_rcnn: v })
                      }
                    />
                    <ThresholdField
                      label="NMS RCNN"
                      value={draftSeuils.nms_thresh_rcnn}
                      min={0.1}
                      max={0.9}
                      step={0.01}
                      disabled={!isAdmin}
                      onChange={(v) =>
                        setDraftSeuils((s) => s && { ...s, nms_thresh_rcnn: v })
                      }
                    />

                    <div className="grid gap-3 rounded-lg border border-border bg-bg-secondary p-3 sm:grid-cols-3">
                      {draftSeuils.recall_garanti != null && (
                        <div>
                          <p className="text-[10px] uppercase text-text-muted">Recall M1</p>
                          <p className="font-mono text-sm text-text-primary">
                            {(draftSeuils.recall_garanti * 100).toFixed(1)} %
                          </p>
                        </div>
                      )}
                      {draftSeuils.auc_modele1 != null && (
                        <div>
                          <p className="text-[10px] uppercase text-text-muted">AUC M1</p>
                          <p className="font-mono text-sm text-text-primary">
                            {draftSeuils.auc_modele1.toFixed(3)}
                          </p>
                        </div>
                      )}
                      {draftSeuils.accuracy_modele3 != null && (
                        <div>
                          <p className="text-[10px] uppercase text-text-muted">Accuracy M3</p>
                          <p className="font-mono text-sm text-text-primary">
                            {(draftSeuils.accuracy_modele3 * 100).toFixed(1)} %
                          </p>
                        </div>
                      )}
                    </div>

                    {isAdmin && (
                      <div className="flex flex-wrap items-center gap-3">
                        <Button
                          icon={<Save className="h-4 w-4" />}
                          loading={saveMutation.isPending}
                          disabled={!seuilsChanged}
                          onClick={() => draftSeuils && saveMutation.mutate(draftSeuils)}
                        >
                          Enregistrer les seuils
                        </Button>
                        {saveMessage && (
                          <p className="text-xs text-text-muted">{saveMessage}</p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-accent-cyan" aria-hidden="true" />
                Modèles IA
              </CardHeader>
              <CardBody className="space-y-3">
                {Object.entries(appSettings.modeles).map(([key, model]) => (
                  <div
                    key={key}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-bg-secondary px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium text-text-primary">
                        {MODEL_LABELS[key] ?? key}
                      </p>
                      <p className="text-[11px] text-text-muted">
                        Fichier {model.fichier_present ? 'présent' : 'manquant'}
                      </p>
                    </div>
                    <ModelStatusBadge charge={model.charge} mock={model.mock} />
                  </div>
                ))}
              </CardBody>
            </Card>

            <Card>
              <CardHeader className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-accent-cyan" aria-hidden="true" />
                Système
              </CardHeader>
              <CardBody className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-text-muted">Version application</p>
                  <p className="font-mono text-sm text-text-primary">
                    MediScanAI v{appSettings.version || APP_VERSION}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Device inférence</p>
                  <p className="font-mono text-sm text-text-primary uppercase">
                    {appSettings.device ?? '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Dernière calibration seuils</p>
                  <p className="text-sm text-text-primary">{appSettings.seuils.derniere_maj}</p>
                </div>
              </CardBody>
            </Card>
          </>
        )}
      </PageShell>
    </>
  )
}
