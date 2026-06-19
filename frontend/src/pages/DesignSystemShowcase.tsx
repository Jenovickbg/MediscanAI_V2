import { useState, type ChangeEvent } from 'react'
import { Activity, Settings } from 'lucide-react'

import {
  Badge,
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Divider,
  LoadingSpinner,
  Modal,
  ProgressBar,
  Slider,
  Tooltip,
} from '../components/ui'

export function DesignSystemShowcase() {
  const [modalOpen, setModalOpen] = useState(false)
  const [sliderValue, setSliderValue] = useState(42)

  return (
    <div className="min-h-full bg-bg-primary p-8 text-text-primary">
      <div className="mx-auto max-w-4xl space-y-8">
        <header>
          <h1>MediScanAI — Design System</h1>
          <p className="mt-1 text-text-secondary">Étape 2 — Composants UI de base</p>
        </header>

        <Divider label="Boutons" />

        <section className="flex flex-wrap items-center gap-3">
          <Button>Primary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="icon" icon={<Settings className="h-4 w-4" />} aria-label="Paramètres" />
          <Button loading>Chargement</Button>
          <Tooltip content="Analyser l'examen">
            <Button icon={<Activity className="h-4 w-4" />}>Avec tooltip</Button>
          </Tooltip>
        </section>

        <Divider label="Badges" />

        <section className="flex flex-wrap gap-2">
          <Badge variant="success">Normal</Badge>
          <Badge variant="warning">Risque modéré</Badge>
          <Badge variant="danger">Fracture</Badge>
          <Badge variant="info">IA active</Badge>
          <Badge variant="neutral">En attente</Badge>
        </section>

        <Divider label="Cartes & progression" />

        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>Score vertèbre C5</CardHeader>
            <CardBody className="space-y-4">
              <ProgressBar value={97} showLabel label="Probabilité fracture" riskLevel="high" />
              <ProgressBar value={23} showLabel label="C2" riskLevel="low" />
              <ProgressBar value={45} showLabel label="C6" riskLevel="medium" />
            </CardBody>
            <CardFooter>
              <Button variant="ghost" className="w-full">
                Voir détail
              </Button>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>Contrôles viewer</CardHeader>
            <CardBody className="space-y-6">
              <Slider
                label="Opacité Grad-CAM"
                min={0}
                max={100}
                value={sliderValue}
                showValue
                valueLabel={`${sliderValue}%`}
                onChange={(e: ChangeEvent<HTMLInputElement>) =>
                  setSliderValue(Number(e.target.value))
                }
              />
              <div className="flex items-center gap-4">
                <LoadingSpinner size="sm" />
                <LoadingSpinner size="md" />
                <LoadingSpinner size="lg" />
              </div>
            </CardBody>
          </Card>
        </div>

        <Divider label="Modale" />

        <Button onClick={() => setModalOpen(true)}>Ouvrir la modale</Button>

        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Confirmation d'analyse"
          footer={
            <>
              <Button variant="ghost" onClick={() => setModalOpen(false)}>
                Annuler
              </Button>
              <Button onClick={() => setModalOpen(false)}>Lancer l&apos;analyse</Button>
            </>
          }
        >
          Le pipeline IA va analyser toutes les coupes DICOM de cet examen cervical.
          Durée estimée : 1 à 3 minutes.
        </Modal>
      </div>
    </div>
  )
}
