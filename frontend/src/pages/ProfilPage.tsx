import { PageHeader, PageShell } from '../components/layout'
import { Badge, Card, CardBody, CardHeader, Divider } from '../components/ui'
import { useAuthStore } from '../store/authStore'

export function ProfilPage() {
  const user = useAuthStore((s) => s.user)

  if (!user) return null

  return (
    <>
      <PageHeader title="Profil" subtitle="Informations de votre compte." />

      <PageShell>
        <Card className="max-w-lg">
          <CardHeader>Détails du compte</CardHeader>
          <CardBody className="space-y-4">
            <div>
              <p className="text-xs text-text-muted">Nom</p>
              <p className="text-sm text-text-primary">{user.nom}</p>
            </div>
            <Divider />
            <div>
              <p className="text-xs text-text-muted">Email</p>
              <p className="font-mono text-sm text-text-primary">{user.email}</p>
            </div>
            <Divider />
            <div>
              <p className="mb-2 text-xs text-text-muted">Rôle</p>
              <Badge variant="info" className="capitalize">
                {user.role}
              </Badge>
            </div>
            <Divider />
            <div>
              <p className="text-xs text-text-muted">Membre depuis</p>
              <p className="text-sm text-text-primary">
                {new Date(user.created_at).toLocaleDateString('fr-FR', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                })}
              </p>
            </div>
          </CardBody>
        </Card>
      </PageShell>
    </>
  )
}
