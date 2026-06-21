import type { ResultatAnalyse } from '../../types/analyse'
import type { Examen } from '../../types/examen'
import { VERTEBRAE } from '../../store/viewerStore'
import { expandVertebraScores, niveauLabel } from '../../utils/analyseScores'
import { ReportReferenceImages } from './ReportReferenceImages'

export const INSTITUTION_NAME = 'Centre Hospitalier Universitaire — Kinshasa'

function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

function statusClass(niveau: string): string {
  if (niveau === 'eleve') return 'text-red-700'
  if (niveau === 'incertain') return 'text-amber-700'
  return 'text-emerald-700'
}

interface ClinicalReportContentProps {
  examen: Examen
  result: ResultatAnalyse
}

export function ClinicalReportContent({ examen, result }: ClinicalReportContentProps) {
  const scoresByVertebra = Object.fromEntries(
    expandVertebraScores(result).map((s) => [s.vertebre, s]),
  )
  const examDate = examen.date_examen ?? examen.uploaded_at

  return (
    <article className="mx-auto max-w-4xl px-8 py-10 text-gray-900">
      <header className="border-b-2 border-gray-800 pb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-gray-500">Établissement</p>
            <h1 className="mt-1 text-xl font-bold text-gray-900">{INSTITUTION_NAME}</h1>
            <p className="mt-2 text-sm text-gray-600">
              MediScanAI — Rapport d&apos;analyse cervicale C1–C7
            </p>
          </div>
          <div className="rounded-lg border border-gray-300 px-4 py-2 text-right">
            <p className="text-xs text-gray-500">Version</p>
            <p className="font-mono text-sm font-semibold">v1.0</p>
          </div>
        </div>
      </header>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Informations patient</h2>
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
            <dt className="text-xs text-gray-500">Patient ID</dt>
            <dd className="font-mono font-medium">{examen.patient_id}</dd>
          </div>
          <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
            <dt className="text-xs text-gray-500">Study UID</dt>
            <dd className="break-all font-mono text-xs">{examen.study_instance_uid}</dd>
          </div>
          <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
            <dt className="text-xs text-gray-500">Date examen</dt>
            <dd>{formatDateTime(examDate)}</dd>
          </div>
          <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
            <dt className="text-xs text-gray-500">Nombre de coupes</dt>
            <dd className="font-mono">{examen.nb_coupes}</dd>
          </div>
        </dl>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Résumé de l&apos;analyse</h2>
        <div
          className={`rounded-lg border px-4 py-4 ${
            result.fracture_detectee
              ? 'border-red-300 bg-red-50'
              : 'border-emerald-300 bg-emerald-50'
          }`}
        >
          <p className="text-sm font-semibold uppercase tracking-wide text-gray-600">
            Résultat global
          </p>
          <p
            className={`mt-1 text-xl font-bold ${
              result.fracture_detectee ? 'text-red-700' : 'text-emerald-700'
            }`}
          >
            {result.fracture_detectee
              ? 'Fracture détectée'
              : 'Aucune fracture significative'}
          </p>
          <p className="mt-2 font-mono text-2xl text-gray-900">
            {(result.score_global * 100).toFixed(1)} %
          </p>
          <p className="mt-2 text-xs text-gray-500">
            Analyse du {formatDateTime(result.date_analyse)} — Durée {result.duree_analyse_sec.toFixed(1)} s
            {result.mode_mock && ' — Mode mock'}
          </p>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Détail par vertèbre</h2>
        <div className="overflow-x-auto rounded-lg border border-gray-300">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-gray-800 text-white">
              <tr>
                <th className="px-4 py-2 font-medium">Vertèbre</th>
                <th className="px-4 py-2 font-medium">Score</th>
                <th className="px-4 py-2 font-medium">Statut</th>
                <th className="px-4 py-2 font-medium">Localisation</th>
              </tr>
            </thead>
            <tbody>
              {VERTEBRAE.map((vertebre, index) => {
                const score = scoresByVertebra[vertebre]
                return (
                  <tr
                    key={vertebre}
                    className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                  >
                    <td className="px-4 py-2 font-mono font-semibold">{vertebre}</td>
                    <td className="px-4 py-2 font-mono">
                      {score ? `${(score.probabilite * 100).toFixed(1)} %` : '—'}
                    </td>
                    <td className={`px-4 py-2 font-medium ${score ? statusClass(score.niveau_risque) : ''}`}>
                      {score ? niveauLabel(score.niveau_risque) : '—'}
                    </td>
                    <td className="px-4 py-2 text-gray-700">
                      {score?.localisation ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Explications du modèle</h2>
        <pre className="whitespace-pre-wrap rounded-lg border border-gray-200 bg-gray-50 p-4 font-sans text-sm leading-relaxed text-gray-800">
          {result.rapport_clinique}
        </pre>
      </section>

      <ReportReferenceImages
        studyId={examen.study_instance_uid}
        scores={expandVertebraScores(result)}
      />

      <footer className="mt-10 border-t border-gray-300 pt-4 text-xs text-gray-500">
        Rapport généré par MediScanAI v1.0 — {formatDateTime(new Date().toISOString())} — À valider
        par un médecin qualifié.
      </footer>
    </article>
  )
}
