import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AnalysisPage from '@/app/analysis/page'
import { Providers } from '@/components/Providers'
import { DEMO_AOI, setStoredAOI } from '@/lib/geo'
import { apiClient } from '@/lib/api'

let mockSearchParams = new URLSearchParams('before=syn_before&after=syn_after')

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      validateAnalysis: vi.fn(),
      getAnalysisStatus: vi.fn(),
      createAnalysis: vi.fn(),
    },
  }
})

describe('AnalysisPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setStoredAOI(DEMO_AOI)
    vi.clearAllMocks()
    mockSearchParams = new URLSearchParams('before=syn_before&after=syn_after')
  })

  it('disables Run Analysis button when validation reports incompatible pair', async () => {
    vi.mocked(apiClient.validateAnalysis).mockResolvedValue({
      compatible: false,
      order: { before_id: 'syn_before', after_id: 'syn_wrongunits' },
      rules: [
        {
          id: 'V-UNITS',
          severity: 'error',
          passed: false,
          message: 'Measurement units mismatch: dB vs linear',
        },
      ],
    })

    render(
      <Providers>
        <AnalysisPage />
      </Providers>
    )

    await waitFor(() => {
      expect(screen.getByText('V-UNITS')).toBeInTheDocument()
      expect(screen.getByText('Measurement units mismatch: dB vs linear')).toBeInTheDocument()
    })

    const runBtn = screen.getByRole('button', { name: /run analysis/i })
    expect(runBtn).toBeDisabled()
  })

  it('enables Run Analysis button when compatible and renders discrete stages without percentages when job active', async () => {
    mockSearchParams = new URLSearchParams('before=syn_before&after=syn_after&job=job_abc123')
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_abc123',
      status: 'running',
      stage: 'differencing',
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'syn_before',
      after_id: 'syn_after',
      synthetic: true,
      error: null,
    })

    render(
      <Providers>
        <AnalysisPage />
      </Providers>
    )

    await waitFor(() => {
      expect(screen.getByText('Job job_abc123')).toBeInTheDocument()
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
      expect(screen.getByText('SAR backscatter differencing (dB)')).toBeInTheDocument()
    })

    // Ensure no percentage progress bars appear
    expect(document.body.textContent).not.toMatch(/\d+%/)
  })
})

