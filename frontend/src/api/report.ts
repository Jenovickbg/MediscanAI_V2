import { apiClient } from './client'

export async function downloadReportPdf(studyId: string): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`/images/${studyId}/export-pdf`, {
    responseType: 'blob',
  })
  return data
}

export function triggerPdfDownload(blob: Blob, studyId: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `mediscanai-rapport-${studyId.slice(0, 16)}.pdf`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
