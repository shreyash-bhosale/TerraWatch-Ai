import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import DashboardPage from '@/app/dashboard/page'
import { Providers } from '@/components/Providers'

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
      })
    },
    getRecentJobs: vi.fn().mockReturnValue([]),
  }
})

describe('DashboardPage', () => {
  it('renders title, empty recent analyses state, and health status when loaded', async () => {
    render(
      <Providers>
        <DashboardPage />
      </Providers>
    )

    expect(screen.getByText('Surface Change Detection')).toBeInTheDocument()
    expect(screen.getByText('Start analysis')).toBeInTheDocument()
    expect(screen.getByText('No recent analyses found.')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('OK')).toBeInTheDocument()
      expect(screen.getByText('v0.1.0')).toBeInTheDocument()
      expect(screen.getByText('mock')).toBeInTheDocument()
      expect(screen.getByText('ACTIVE')).toBeInTheDocument()
    })
  })
})
