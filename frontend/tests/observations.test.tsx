import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ObservationsPage from '@/app/observations/page'
import { Providers } from '@/components/Providers'
import { DEMO_AOI, setStoredAOI } from '@/lib/geo'
import { apiClient } from '@/lib/api'

const pushMock = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}))

const mockObservations = [
  {
    id: 'obs_2',
    provider: 'synthetic_demo',
    synthetic: true,
    acquisition_date: '2026-01-13T00:00:00Z',
    geometry: DEMO_AOI,
    asset_location: 'syn_after.tif',
    asset_format: 'GTiff',
    polarization: null,
    frequency_band: 'L',
    orbit_direction: null,
    measurement_units: 'dB',
  },
  {
    id: 'obs_1',
    provider: 'synthetic_demo',
    synthetic: true,
    acquisition_date: '2026-01-01T00:00:00Z',
    geometry: DEMO_AOI,
    asset_location: 'syn_before.tif',
    asset_format: 'GTiff',
    polarization: 'HH',
    frequency_band: 'L',
    orbit_direction: 'ascending',
    measurement_units: 'dB',
  },
  {
    id: 'obs_3',
    provider: 'synthetic_demo',
    synthetic: true,
    acquisition_date: '2026-01-25T00:00:00Z',
    geometry: DEMO_AOI,
    asset_location: 'syn_misaligned.tif',
    asset_format: 'GTiff',
    polarization: 'HH',
    frequency_band: 'L',
    orbit_direction: 'ascending',
    measurement_units: 'dB',
  },
]

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      searchObservations: vi.fn(),
    },
  }
})

describe('ObservationsPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setStoredAOI(DEMO_AOI)
    pushMock.mockClear()
    vi.mocked(apiClient.searchObservations).mockResolvedValue({
      observations: mockObservations,
      warnings: [],
    })
  })

  it('renders observations with Not provided fallback, enforces 2-selection limit, and assigns chronological order', async () => {
    render(
      <Providers>
        <ObservationsPage />
      </Providers>
    )

    await waitFor(() => {
      expect(screen.getByText('obs_1')).toBeInTheDocument()
      expect(screen.getByText('obs_2')).toBeInTheDocument()
    })

    // Missing polarization / orbit fields show "Not provided"
    expect(screen.getAllByText('Not provided').length).toBeGreaterThanOrEqual(2)

    // Click obs_2 (later) then obs_1 (earlier)
    fireEvent.click(screen.getByText('obs_2'))
    fireEvent.click(screen.getByText('obs_1'))

    // Trying to select a 3rd observation displays hint
    fireEvent.click(screen.getByText('obs_3'))
    expect(screen.getByText('You can only select two observations. Deselect one first.')).toBeInTheDocument()

    // Proceed button enabled and navigates with chronological order (obs_1=before, obs_2=after)
    const proceedBtn = screen.getByRole('button', { name: /proceed to analysis/i })
    expect(proceedBtn).not.toBeDisabled()
    fireEvent.click(proceedBtn)

    expect(pushMock).toHaveBeenCalledWith('/analysis?before=obs_1&after=obs_2')
  })
})
