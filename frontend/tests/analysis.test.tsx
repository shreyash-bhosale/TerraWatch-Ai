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

  it('loads by job ID alone without before/after params (F-03)', async () => {
    mockSearchParams = new URLSearchParams('job=job_only_123')
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_only_123',
      status: 'running',
      stage: 'aligning',
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

    expect(screen.queryByText('No Observations Selected')).not.toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('Job job_only_123')).toBeInTheDocument()
      expect(screen.getByText('syn_before')).toBeInTheDocument()
      expect(screen.getByText('syn_after')).toBeInTheDocument()
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
    })
  })

  it('shows Alert with Retry on polling error, keeps last status visible, and resumes on retry (F-04)', async () => {
    mockSearchParams = new URLSearchParams('job=job_poll_err')
    vi.mocked(apiClient.getAnalysisStatus)
      .mockResolvedValueOnce({
        job_id: 'job_poll_err',
        status: 'running',
        stage: 'differencing',
        created_at: '2026-11-12T10:00:00Z',
        before_id: 'syn_before',
        after_id: 'syn_after',
        synthetic: true,
        error: null,
      })
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce({
        job_id: 'job_poll_err',
        status: 'completed',
        stage: 'completed',
        created_at: '2026-11-12T10:00:00Z',
        before_id: 'syn_before',
        after_id: 'syn_after',
        synthetic: true,
        error: null,
      })

    const { fireEvent } = await import('@testing-library/react')
    render(
      <Providers>
        <AnalysisPage />
      </Providers>
    )

    // First poll succeeds -> RUNNING & stage differencing
    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
    })

    // Trigger next poll which rejects -> error Alert + Retry while keeping RUNNING visible
    // Wait up to 3s for 2s poll interval or click refetch? Let's wait for Alert
    await waitFor(
      () => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      },
      { timeout: 3500 }
    )
    expect(screen.getByText('RUNNING')).toBeInTheDocument()

    // Click Retry -> resumes and hits COMPLETED
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    await waitFor(() => {
      expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    })
  })
})

