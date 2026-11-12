import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SyntheticBanner } from '@/components/SyntheticBanner'
import { apiClient } from '@/lib/api'

let mockSearchParams = new URLSearchParams('')

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getHealth: vi.fn(),
      getAnalysisStatus: vi.fn(),
    },
  }
})

function renderBanner(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('SyntheticBanner (F-10)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParams = new URLSearchParams('')
  })

  it('hides banner when health reports synthetic_mode=false and no synthetic job is active', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      provider: 'local',
      synthetic_mode: false,
      checks: { data_dir: true, fixtures: true },
    })

    renderBanner(<SyntheticBanner />)

    await waitFor(() => {
      expect(apiClient.getHealth).toHaveBeenCalled()
    })
    expect(
      screen.queryByText(/DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS/i)
    ).not.toBeInTheDocument()
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
      expect(
        screen.getByText(/DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS/i)
      ).toBeInTheDocument()
    })
  })

  it('shows banner when provider is non-synthetic but inspected job is synthetic', async () => {
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
      expect(
        screen.getByText(/DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS/i)
      ).toBeInTheDocument()
    })
  })
})
