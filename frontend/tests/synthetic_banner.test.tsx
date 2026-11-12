import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SyntheticBanner } from '@/components/SyntheticBanner'
import { apiClient, type HealthResponse, type JobResultsResponse, type JobStatusResponse } from '@/lib/api'

let mockSearchParams = new URLSearchParams('')
let mockPathname = '/dashboard'

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
  usePathname: () => mockPathname,
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getHealth: vi.fn(),
      getAnalysisStatus: vi.fn(),
      getAnalysisResults: vi.fn(),
    },
  }
})

function renderBanner(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const BANNER_REGEX = /DEMO DATA\s*[—-]\s*SYNTHETIC,\s*NOT REAL NISAR OBSERVATIONS/i

describe('SyntheticBanner (F-10b)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParams = new URLSearchParams('')
    mockPathname = '/dashboard'
  })

  it('shows banner while health request is still loading', () => {
    vi.mocked(apiClient.getHealth).mockImplementation(() => new Promise(() => {}))

    renderBanner(<SyntheticBanner />)

    expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
  })

  it('shows banner when health errors / network fails', async () => {
    vi.mocked(apiClient.getHealth).mockRejectedValue(new Error('Network Error'))

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(apiClient.getHealth).toHaveBeenCalled()
    })
    expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
  })

  it('shows banner when health response omits synthetic_mode field', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'local',
      checks: { data_dir: true, fixtures: true },
    } as unknown as HealthResponse)

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(apiClient.getHealth).toHaveBeenCalled()
    })
    expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
  })

  it('hides banner ONLY when health explicitly returns synthetic_mode === false', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'local',
      synthetic_mode: false,
      checks: { data_dir: true, fixtures: true },
    })

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(screen.queryByText(BANNER_REGEX)).not.toBeInTheDocument()
    })
  })

  it('shows banner when health reports synthetic_mode=true', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'mock',
      synthetic_mode: true,
      checks: { data_dir: true, fixtures: true },
    })

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
    })
  })

  it('on results page, shows banner if job.synthetic is true even when health says false', async () => {
    mockPathname = '/results'
    mockSearchParams = new URLSearchParams('job=job_syn')
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'local',
      synthetic_mode: false,
      checks: { data_dir: true, fixtures: true },
    })
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_syn',
      status: 'completed',
      stage: 'completed',
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'syn_before',
      after_id: 'syn_after',
      synthetic: true,
      error: null,
    })

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(apiClient.getAnalysisStatus).toHaveBeenCalledWith('job_syn')
    })
    expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
  })

  it('on results page, shows banner if job.synthetic is undefined even when health says false', async () => {
    mockPathname = '/results'
    mockSearchParams = new URLSearchParams('job=job_missing_flag')
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'local',
      synthetic_mode: false,
      checks: { data_dir: true, fixtures: true },
    })
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_missing_flag',
      status: 'completed',
      stage: 'completed',
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'obs_a',
      after_id: 'obs_b',
      error: null,
    } as unknown as JobStatusResponse)

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(apiClient.getAnalysisStatus).toHaveBeenCalledWith('job_missing_flag')
    })
    expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
  })

  it('on results page, hides banner only when health, job, and results all explicitly return synthetic=false', async () => {
    mockPathname = '/results'
    mockSearchParams = new URLSearchParams('job=job_real')
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'local',
      synthetic_mode: false,
      checks: { data_dir: true, fixtures: true },
    })
    vi.mocked(apiClient.getAnalysisStatus).mockResolvedValue({
      job_id: 'job_real',
      status: 'completed',
      stage: 'completed',
      created_at: '2026-11-12T10:00:00Z',
      before_id: 'real_a',
      after_id: 'real_b',
      synthetic: false,
      error: null,
    })
    vi.mocked(apiClient.getAnalysisResults).mockResolvedValue({
      statistics: {
        valid_pixel_count: 100,
        invalid_pixel_count: 0,
        total_pixel_count: 100,
        mean: 0,
        median: 0,
        min: 0,
        max: 0,
        std: 0,
      },
      bounds: [73.8, 18.496, 73.864, 18.56],
      layers: {
        difference_png: '/files/outputs/job_real/difference.png',
        before_png: '/files/outputs/job_real/before.png',
        after_png: '/files/outputs/job_real/after.png',
      },
      geotiff_url: '/files/outputs/job_real/difference.tif',
      metadata: {},
      limitations: [],
      synthetic: false,
    } as JobResultsResponse)

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(screen.queryByText(BANNER_REGEX)).not.toBeInTheDocument()
    })

    // Also ensure results.synthetic === true keeps banner visible even if job.synthetic was false
    vi.mocked(apiClient.getAnalysisResults).mockResolvedValueOnce({
      statistics: {
        valid_pixel_count: 100,
        invalid_pixel_count: 0,
        total_pixel_count: 100,
        mean: 0,
        median: 0,
        min: 0,
        max: 0,
        std: 0,
      },
      bounds: [73.8, 18.496, 73.864, 18.56],
      layers: {
        difference_png: '/files/outputs/job_real/difference.png',
        before_png: '/files/outputs/job_real/before.png',
        after_png: '/files/outputs/job_real/after.png',
      },
      geotiff_url: '/files/outputs/job_real/difference.tif',
      metadata: {},
      limitations: [],
      synthetic: true,
    } as JobResultsResponse)

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(apiClient.getAnalysisResults).toHaveBeenCalledTimes(2)
    })
    expect(screen.getByText(BANNER_REGEX)).toBeInTheDocument()
  })
})
