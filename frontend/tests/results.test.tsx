import { render, screen, waitFor } from '@testing-library/react'
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
})

