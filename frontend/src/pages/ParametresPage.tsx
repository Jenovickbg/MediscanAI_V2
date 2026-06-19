import { PageHeader, PageShell, PlaceholderPanel } from '../components/layout'

export function ParametresPage() {
  return (
    <>
      <PageHeader title="Paramètres" subtitle="Configuration de l'application." />
      <PageShell>
        <PlaceholderPanel
          title="Préférences"
          description="Options d'affichage et de fenêtrage DICOM — à venir."
        />
      </PageShell>
    </>
  )
}
