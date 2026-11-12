import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DashboardPage from '@/app/dashboard/page'
import { Providers } from '@/components/Providers'
import { apiClient, getRecentJobs } from '@/lib/api'
import { DEMO_AOI, setStoredAOI } from '@/lib/geo'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getHealth: vi.fn().mockResolvedValue({
        status: 'ok',
        version: '0.1.0',
        provider: 'mock',
        synthetic_mode: true,
        checks: { data_dir: true, fixtures: true }
      }),
      getAnalysisStatus: vi.fn(),
    },
    getRecentJobs: vi.fn().mockReturnValue([]),
  }
})

describe('DashboardPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.mocked(getRecentJobs).mockReturnValue([])
    vi.mocked(apiClient.getAnalysisStatus).mockReset()
  })

  it('renders title, empty recent analyses state, empty study area, and health status when loaded', async () => {
    render(
      <Providers>
        <DashboardPage />
      </Providers>
    )

    expect(screen.getByText('Surface Change Detection')).toBeInTheDocument()
    expect(screen.getByText('Start analysis')).toBeInTheDocument()
    expect(screen.getByText('No recent analyses found.')).toBeInTheDocument()
    expect(screen.getByText(/no study area selected/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('OK')).toBeInTheDocument()
      expect(screen.getByText('v0.1.0')).toBeInTheDocument()
      expect(screen.getByText('mock')).toBeInTheDocument()
      expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    })
  })

  it('renders study area summary from stored AOI and live job status with retry on error (F-06)', async () => {
    setStoredAOI(DEMO_AOI)
    vi.mocked(getRecentJobs).mockReturnValue([
      {
        jobId: 'job_live_1',
        beforeId: 'syn_before',
        afterId: 'syn_after',
        createdAt: '2026-11-12T10:00:00Z',
        synthetic: true,
      },
    ])
    vi.mocked(apiClient.getAnalysisStatus)
      .mockRejectedValueOnce(new Error('Jobs API unreachable'))
      .mockResolvedValueOnce({
        job_id: 'job_live_1',
        status: 'completed',
        stage: 'completed',
        created_at: '2026-11-12T10:00:00Z',
        before_id: 'syn_before',
        after_id: 'syn_after',
        synthetic: true,
        error: null,
      })

    render(
      <Providers>
        <DashboardPage />
      </Providers>
    )

    // Study area summary card
    expect(screen.getByText(/study area summary/i)).toBeInTheDocument()
    expect(screen.getByText(/5 vertices/i)).toBeInTheDocument()

    // Error state + Retry when GET /api/analysis/{job_id} fails
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /retry/i }))

    await waitFor(() => {
      expect(apiClient.getAnalysisStatus).toHaveBeenCalledWith('job_live_1')
      expect(screen.getByText('COMPLETED')).toBeInTheDocument()
    })
  })
})
