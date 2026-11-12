import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ResultsPage from '@/app/results/page'
import { SyntheticBanner } from '@/components/SyntheticBanner'
import { Providers } from '@/components/Providers'
import { apiClient } from '@/lib/api'

let mockSearchParams = new URLSearchParams('job=job_test123')

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}))

vi.mock('@/components/map/ResultsMap', () => ({
  ResultsMap: ({ activeLayer }: { activeLayer: string }) => (
    <div data-testid="mock-results-map">Layer: {activeLayer}</div>
  ),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getAnalysisStatus: vi.fn(),
      getAnalysisResults: vi.fn(),
    },
  }
})

describe('ResultsPage & SyntheticBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParams = new URLSearchParams('job=job_test123')
  })

  it('renders SyntheticBanner text accurately', () => {
    render(<SyntheticBanner show={true} />)
    expect(screen.getByText(/DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS/i)).toBeInTheDocument()
  })

  it('renders completed results, stats, deterministic summary, limitations, and synthetic badge', async () => {
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_test123',
      status: 'completed',
      stage: 'completed',
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'syn_before',
      after_id: 'syn_after',
      synthetic: true,
      error: null,
    })

    vi.mocked(apiClient.getAnalysisResults).mockResolvedValue({
      statistics: {
        valid_pixel_count: 4064,
        invalid_pixel_count: 32,
        total_pixel_count: 4096,
        mean: -0.6889764070510864,
        median: 0.0,
        min: -7.0,
        max: 0.0,
        std: 2.0852208986801357,
      },
      bounds: [73.8, 18.496, 73.864, 18.56],
      layers: {
        difference_png: '/files/outputs/job_test123/difference.png',
        before_png: '/files/outputs/job_test123/before.png',
        after_png: '/files/outputs/job_test123/after.png',
      },
      geotiff_url: '/files/outputs/job_test123/difference.tif',
      metadata: {
        color_scales: {
          difference: { vmin: -7.0, vmax: 7.0, units: 'dB' },
          before: { vmin: -15.0, vmax: -14.0, units: 'dB' },
          after: { vmin: -22.0, vmax: -15.0, units: 'dB' },
        },
      },
      limitations: [
        'Difference of calibrated SAR backscatter (dB) between two dates; it is not a classified event map.',
        'DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS. No real-world conclusion can be drawn.',
      ],
      synthetic: true,
    })

    render(
      <Providers>
        <ResultsPage />
      </Providers>
    )

    await waitFor(() => {
      expect(screen.getByTestId('stat-mean')).toHaveTextContent('-0.6890 dB')
      expect(screen.getByTestId('stat-valid-pixels')).toHaveTextContent('4,064')
      expect(screen.getByTestId('deterministic-summary')).toHaveTextContent('Mean difference -0.69 dB over 4,064 valid pixels')
      expect(screen.getByText('DEMO DATA — SYNTHETIC')).toBeInTheDocument()
      expect(screen.getByText(/not a classified event map/i)).toBeInTheDocument()
    })
  })

  it('renders empty state when no job parameter is provided', () => {
    mockSearchParams = new URLSearchParams('')
    render(
      <Providers>
        <ResultsPage />
      </Providers>
    )
    expect(screen.getByText('No Analysis Selected')).toBeInTheDocument()
  })

  it('renders failed state cleanly when job failed', async () => {
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_fail',
      status: 'failed',
      stage: 'failed',
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'syn_before',
      after_id: 'syn_after',
      synthetic: true,
      error: { code: 'ALIGNMENT_MISMATCH', message: 'Pixel sizes differ' },
    })

    render(
      <Providers>
        <ResultsPage />
      </Providers>
    )

    await waitFor(() => {
      expect(screen.getByText('Analysis Job Failed')).toBeInTheDocument()
      expect(screen.getByText(/ALIGNMENT_MISMATCH/)).toBeInTheDocument()
    })
  })

  it('shows Alert with Retry when GET /api/analysis/{id} fails, preserves last-known state, and recovers on Retry (F-05)', async () => {
    const statusPayload = {
      job_id: 'job_test123',
      status: 'completed' as const,
      stage: 'completed' as const,
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'syn_before',
      after_id: 'syn_after',
      synthetic: true,
      error: null,
    }
    const resultsPayload = {
      statistics: {
        valid_pixel_count: 4064,
        invalid_pixel_count: 32,
        total_pixel_count: 4096,
        mean: -0.6889764070510864,
        median: 0.0,
        min: -7.0,
        max: 0.0,
        std: 2.0852208986801357,
      },
      bounds: [73.8, 18.496, 73.864, 18.56] as [number, number, number, number],
      layers: {
        difference_png: '/files/outputs/job_test123/difference.png',
        before_png: '/files/outputs/job_test123/before.png',
        after_png: '/files/outputs/job_test123/after.png',
      },
      geotiff_url: '/files/outputs/job_test123/difference.tif',
      metadata: {
        color_scales: {
          difference: { vmin: -7.0, vmax: 7.0, units: 'dB' },
          before: { vmin: -15.0, vmax: -14.0, units: 'dB' },
          after: { vmin: -22.0, vmax: -15.0, units: 'dB' },
        },
      },
      limitations: [
        'Difference of calibrated SAR backscatter (dB) between two dates; it is not a classified event map.',
      ],
      synthetic: true,
    }

    vi.mocked(apiClient.getAnalysisStatus)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(statusPayload)
      .mockRejectedValueOnce(new Error('Status refresh failed'))
      .mockResolvedValueOnce(statusPayload)
    vi.mocked(apiClient.getAnalysisResults).mockResolvedValue(resultsPayload)

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={qc}>
        <ResultsPage />
      </QueryClientProvider>
    )

    // Initial failure shows Alert + Retry button
    await waitFor(() => {
      expect(screen.getByText(/results not available|status connection error/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    // Clicking Retry re-requests status and loads results
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    await waitFor(() => {
      expect(screen.getByTestId('stat-mean')).toHaveTextContent('-0.6890 dB')
    })
    expect(apiClient.getAnalysisStatus).toHaveBeenCalledTimes(2)

    // Subsequent status failure keeps last-known results visible AND shows Retry Alert
    await qc.invalidateQueries({ queryKey: ['analysis-status-for-results', 'job_test123'] })
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })
    expect(screen.getByTestId('stat-mean')).toHaveTextContent('-0.6890 dB')

    // Retry clears error while preserving results
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
    })
    expect(apiClient.getAnalysisStatus).toHaveBeenCalledTimes(4)
    expect(screen.getByTestId('stat-mean')).toHaveTextContent('-0.6890 dB')
  })
})

