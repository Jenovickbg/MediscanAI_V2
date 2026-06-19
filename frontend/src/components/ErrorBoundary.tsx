import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

import { Button } from './ui/Button'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('MediScanAI ErrorBoundary:', error, info.componentStack)
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, message: '' })
    window.location.href = '/dashboard'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-bg-primary p-6">
          <div className="max-w-md rounded-xl border border-danger/30 bg-bg-secondary p-6 text-center">
            <AlertTriangle className="mx-auto h-10 w-10 text-danger" aria-hidden="true" />
            <h1 className="mt-4 text-lg font-semibold text-text-primary">
              Une erreur est survenue
            </h1>
            <p className="mt-2 text-sm text-text-secondary">
              {this.state.message || 'Erreur inattendue dans l&apos;application.'}
            </p>
            <Button className="mt-6" onClick={this.handleReset}>
              Retour au tableau de bord
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
