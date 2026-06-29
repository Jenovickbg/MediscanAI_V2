import { useState, type FormEvent } from 'react'
import { isAxiosError } from 'axios'
import { Pencil, Plus, Trash2, UserCheck, UserX } from 'lucide-react'

import {
  useCreateMedecinMutation,
  useDeleteMedecinMutation,
  useMedecinsQuery,
  useUpdateMedecinMutation,
} from '../api/medecins'
import { PageHeader, PageShell } from '../components/layout'
import { Badge, Button, Card, CardBody, CardHeader, LoadingSpinner, Modal } from '../components/ui'
import type { Medecin, MedecinCreatePayload } from '../types/medecin'

const inputClassName =
  'w-full rounded-lg border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-cyan focus:outline-none focus:ring-1 focus:ring-accent-cyan/40'

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

function extractError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    if (err.response?.status === 404) {
      return (
        'API médecins introuvable (404). Redémarrez le backend : cd backend puis ' +
        '.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8006'
      )
    }
    if (err.response?.data?.detail) {
      const detail = err.response.data.detail
      return typeof detail === 'string' ? detail : fallback
    }
  }
  return fallback
}

type ModalMode = 'create' | 'edit' | 'delete' | 'toggle' | null

export function MedecinsPage() {
  const { data: medecins = [], isLoading, isError, error } = useMedecinsQuery()
  const createMutation = useCreateMedecinMutation()
  const updateMutation = useUpdateMedecinMutation()
  const deleteMutation = useDeleteMedecinMutation()

  const [modalMode, setModalMode] = useState<ModalMode>(null)
  const [selected, setSelected] = useState<Medecin | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const [nom, setNom] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [actif, setActif] = useState(true)

  function resetForm() {
    setNom('')
    setEmail('')
    setPassword('')
    setActif(true)
    setFormError(null)
  }

  function closeModal() {
    setModalMode(null)
    setSelected(null)
    resetForm()
  }

  function openCreate() {
    resetForm()
    setModalMode('create')
  }

  function openEdit(medecin: Medecin) {
    setSelected(medecin)
    setNom(medecin.nom)
    setEmail(medecin.email)
    setPassword('')
    setActif(medecin.actif)
    setFormError(null)
    setModalMode('edit')
  }

  function openDelete(medecin: Medecin) {
    setSelected(medecin)
    setFormError(null)
    setModalMode('delete')
  }

  function openToggle(medecin: Medecin) {
    setSelected(medecin)
    setFormError(null)
    setModalMode('toggle')
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setFormError(null)

    const payload: MedecinCreatePayload = { nom, email, password, actif }
    try {
      await createMutation.mutateAsync(payload)
      closeModal()
    } catch (err) {
      setFormError(extractError(err, 'Impossible de créer le médecin'))
    }
  }

  async function handleEdit(event: FormEvent) {
    event.preventDefault()
    if (!selected) return
    setFormError(null)

    const payload: Record<string, string | boolean> = { nom, email, actif }
    if (password.trim()) payload.password = password

    try {
      await updateMutation.mutateAsync({ id: selected.id, payload })
      closeModal()
    } catch (err) {
      setFormError(extractError(err, 'Impossible de modifier le médecin'))
    }
  }

  async function handleDelete() {
    if (!selected) return
    setFormError(null)

    try {
      await deleteMutation.mutateAsync(selected.id)
      closeModal()
    } catch (err) {
      setFormError(extractError(err, 'Impossible de supprimer le médecin'))
    }
  }

  async function handleToggle() {
    if (!selected) return
    setFormError(null)

    try {
      await updateMutation.mutateAsync({
        id: selected.id,
        payload: { actif: !selected.actif },
      })
      closeModal()
    } catch (err) {
      setFormError(extractError(err, 'Impossible de modifier le statut'))
    }
  }

  const isSubmitting =
    createMutation.isPending || updateMutation.isPending || deleteMutation.isPending

  return (
    <>
      <PageHeader
        title="Médecins"
        subtitle="Gérez les comptes médecins et leurs accès aux examens."
        actions={
          <Button icon={<Plus className="h-4 w-4" />} onClick={openCreate}>
            Ajouter un médecin
          </Button>
        }
      />

      <PageShell>
        {isError && (
          <div className="mb-4 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error instanceof Error
              ? extractError(error, 'Impossible de charger les médecins')
              : 'Impossible de charger les médecins'}
          </div>
        )}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <span>Liste des médecins</span>
            {!isLoading && (
              <span className="text-xs font-normal text-text-muted">
                {medecins.length} compte{medecins.length > 1 ? 's' : ''}
              </span>
            )}
          </CardHeader>
          <CardBody className="p-0">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner label="Chargement des médecins…" />
              </div>
            ) : medecins.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-text-muted">
                Aucun médecin enregistré. Ajoutez le premier compte.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border bg-bg-secondary/50 text-xs uppercase tracking-wide text-text-muted">
                      <th className="px-4 py-3 font-medium">Nom</th>
                      <th className="px-4 py-3 font-medium">Email</th>
                      <th className="px-4 py-3 font-medium">Examens</th>
                      <th className="px-4 py-3 font-medium">Inscrit le</th>
                      <th className="px-4 py-3 font-medium">Statut</th>
                      <th className="px-4 py-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {medecins.map((medecin) => (
                      <tr
                        key={medecin.id}
                        className="border-b border-border/60 transition-colors hover:bg-bg-elevated/40"
                      >
                        <td className="px-4 py-3 font-medium text-text-primary">{medecin.nom}</td>
                        <td className="px-4 py-3 text-text-secondary">{medecin.email}</td>
                        <td className="px-4 py-3 font-mono text-text-secondary">
                          {medecin.nb_examens}
                        </td>
                        <td className="px-4 py-3 text-text-secondary">
                          {formatDate(medecin.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          {medecin.actif ? (
                            <Badge variant="success">Actif</Badge>
                          ) : (
                            <Badge variant="neutral">Inactif</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="icon"
                              aria-label="Modifier"
                              icon={<Pencil className="h-4 w-4" />}
                              onClick={() => openEdit(medecin)}
                            />
                            <Button
                              variant="icon"
                              aria-label={medecin.actif ? 'Désactiver' : 'Activer'}
                              icon={
                                medecin.actif ? (
                                  <UserX className="h-4 w-4" />
                                ) : (
                                  <UserCheck className="h-4 w-4" />
                                )
                              }
                              onClick={() => openToggle(medecin)}
                            />
                            <Button
                              variant="icon"
                              aria-label="Supprimer"
                              className="text-danger hover:text-danger"
                              icon={<Trash2 className="h-4 w-4" />}
                              onClick={() => openDelete(medecin)}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        </Card>
      </PageShell>

      <Modal
        open={modalMode === 'create'}
        onClose={closeModal}
        title="Ajouter un médecin"
        footer={
          <>
            <Button variant="ghost" onClick={closeModal}>
              Annuler
            </Button>
            <Button type="submit" form="medecin-create-form" loading={isSubmitting}>
              Créer
            </Button>
          </>
        }
      >
        <form id="medecin-create-form" onSubmit={handleCreate} className="space-y-4">
          {formError && (
            <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
              {formError}
            </p>
          )}
          <div>
            <label htmlFor="create-nom" className="mb-1.5 block text-xs text-text-secondary">
              Nom complet
            </label>
            <input
              id="create-nom"
              className={inputClassName}
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              required
              minLength={2}
            />
          </div>
          <div>
            <label htmlFor="create-email" className="mb-1.5 block text-xs text-text-secondary">
              Email
            </label>
            <input
              id="create-email"
              type="email"
              className={inputClassName}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="create-password" className="mb-1.5 block text-xs text-text-secondary">
              Mot de passe
            </label>
            <input
              id="create-password"
              type="password"
              className={inputClassName}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={actif}
              onChange={(e) => setActif(e.target.checked)}
              className="rounded border-border"
            />
            Compte actif
          </label>
        </form>
      </Modal>

      <Modal
        open={modalMode === 'edit'}
        onClose={closeModal}
        title="Modifier le médecin"
        footer={
          <>
            <Button variant="ghost" onClick={closeModal}>
              Annuler
            </Button>
            <Button type="submit" form="medecin-edit-form" loading={isSubmitting}>
              Enregistrer
            </Button>
          </>
        }
      >
        <form id="medecin-edit-form" onSubmit={handleEdit} className="space-y-4">
          {formError && (
            <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
              {formError}
            </p>
          )}
          <div>
            <label htmlFor="edit-nom" className="mb-1.5 block text-xs text-text-secondary">
              Nom complet
            </label>
            <input
              id="edit-nom"
              className={inputClassName}
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              required
              minLength={2}
            />
          </div>
          <div>
            <label htmlFor="edit-email" className="mb-1.5 block text-xs text-text-secondary">
              Email
            </label>
            <input
              id="edit-email"
              type="email"
              className={inputClassName}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="edit-password" className="mb-1.5 block text-xs text-text-secondary">
              Nouveau mot de passe (optionnel)
            </label>
            <input
              id="edit-password"
              type="password"
              className={inputClassName}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              placeholder="Laisser vide pour ne pas changer"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={actif}
              onChange={(e) => setActif(e.target.checked)}
              className="rounded border-border"
            />
            Compte actif
          </label>
        </form>
      </Modal>

      <Modal
        open={modalMode === 'delete'}
        onClose={closeModal}
        title="Supprimer le médecin"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={closeModal}>
              Annuler
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={isSubmitting}>
              Supprimer
            </Button>
          </>
        }
      >
        {formError && (
          <p className="mb-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <p>
          Voulez-vous supprimer définitivement{' '}
          <strong className="text-text-primary">{selected?.nom}</strong> ?
        </p>
        {selected && selected.nb_examens > 0 && (
          <p className="mt-2 text-xs text-warning">
            Ce médecin a {selected.nb_examens} examen(s). La suppression sera refusée — désactivez
            le compte à la place.
          </p>
        )}
      </Modal>

      <Modal
        open={modalMode === 'toggle'}
        onClose={closeModal}
        title={selected?.actif ? 'Désactiver le médecin' : 'Activer le médecin'}
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={closeModal}>
              Annuler
            </Button>
            <Button onClick={handleToggle} loading={isSubmitting}>
              {selected?.actif ? 'Désactiver' : 'Activer'}
            </Button>
          </>
        }
      >
        {formError && (
          <p className="mb-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
            {formError}
          </p>
        )}
        <p>
          {selected?.actif
            ? `Le médecin ${selected.nom} ne pourra plus se connecter ni accéder à ses examens.`
            : `Réactiver le compte de ${selected?.nom} ?`}
        </p>
      </Modal>
    </>
  )
}
