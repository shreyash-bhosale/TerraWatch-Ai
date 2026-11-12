import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ExplorePage from '@/app/explore/page'

const pushMock = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('@/components/map/AoiDrawMap', () => ({
  AoiDrawMap: ({ initialAoi }: { initialAoi: any }) => (
    <div data-testid="mock-aoi-map">{initialAoi ? 'AOI_ACTIVE' : 'AOI_EMPTY'}</div>
  ),
}))

describe('ExplorePage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    pushMock.mockClear()
  })

  it('allows selecting demo area, displays metrics, and clears', () => {
    render(<ExplorePage />)

    const nextBtn = screen.getByRole('button', { name: /next: select observations/i })
    expect(nextBtn).toBeDisabled()

    const demoBtn = screen.getByRole('button', { name: /use demo area/i })
    fireEvent.click(demoBtn)

    expect(screen.getByTestId('mock-aoi-map')).toHaveTextContent('AOI_ACTIVE')
    expect(nextBtn).not.toBeDisabled()

    const clearBtn = screen.getByRole('button', { name: /clear/i })
    fireEvent.click(clearBtn)

    expect(screen.getByTestId('mock-aoi-map')).toHaveTextContent('AOI_EMPTY')
    expect(nextBtn).toBeDisabled()
  })
})
