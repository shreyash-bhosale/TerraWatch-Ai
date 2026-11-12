import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ExplorePage from '@/app/explore/page'
import { DEMO_AOI, getStoredAOI, setStoredAOI } from '@/lib/geo'

const pushMock = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}))

type EventCb = (payload?: unknown, ...rest: unknown[]) => void

let mockMapInstances: any[] = []
let mockTerraDrawInstances: any[] = []

vi.mock('maplibre-gl', () => {
  class MockMap {
    handlers: Record<string, EventCb[]> = {}
    sources: Record<string, any> = {}
    layers: Record<string, any> = {}
    fitBounds = vi.fn()
    addControl = vi.fn()
    resize = vi.fn()
    remove = vi.fn()
    isStyleLoaded = vi.fn().mockReturnValue(true)
    getStyle = vi.fn().mockReturnValue({ version: 8 })
    setLayoutProperty = vi.fn()
    setPaintProperty = vi.fn()

    constructor() {
      mockMapInstances.push(this)
    }

    on(event: string, cb: EventCb) {
      this.handlers[event] = this.handlers[event] || []
      this.handlers[event].push(cb)
    }

    emit(event: string, payload?: unknown) {
      ;(this.handlers[event] || []).forEach((cb) => cb(payload))
    }

    addSource(id: string, cfg: any) {
      this.sources[id] = {
        ...cfg,
        setData: (d: unknown) => {
          this.sources[id].data = d
        },
      }
    }

    getSource(id: string) {
      return this.sources[id]
    }

    removeSource(id: string) {
      delete this.sources[id]
    }

    addLayer(cfg: any) {
      this.layers[cfg.id] = cfg
    }

    getLayer(id: string) {
      return this.layers[id]
    }

    removeLayer(id: string) {
      delete this.layers[id]
    }
  }

  return {
    default: {
      Map: MockMap,
      NavigationControl: vi.fn(),
    },
  }
})

vi.mock('terra-draw', () => {
  class MockTerraDraw {
    handlers: Record<string, EventCb[]> = {}
    snapshot: any[] = []
    start = vi.fn()
    stop = vi.fn()
    clear = vi.fn(() => {
      this.snapshot = []
    })
    setMode = vi.fn()

    constructor() {
      mockTerraDrawInstances.push(this)
    }

    on(event: string, cb: EventCb) {
      this.handlers[event] = this.handlers[event] || []
      this.handlers[event].push(cb)
    }

    emit(event: string, ...args: unknown[]) {
      ;(this.handlers[event] || []).forEach((cb) => cb(...args))
    }

    getSnapshot = vi.fn(() => this.snapshot)
  }

  return {
    TerraDraw: MockTerraDraw,
    TerraDrawMapLibreGLAdapter: vi.fn(),
    TerraDrawPolygonMode: vi.fn(),
    TerraDrawRectangleMode: vi.fn(),
    TerraDrawSelectMode: vi.fn(),
    TerraDrawRenderMode: vi.fn(),
  }
})

describe('ExplorePage (real AoiDrawMap integration)', () => {
  beforeEach(() => {
    sessionStorage.clear()
    pushMock.mockClear()
    mockMapInstances = []
    mockTerraDrawInstances = []
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({} as any)
  })

  it('uses real AoiDrawMap to load demo area, update MapLibre source & metrics, clear, and navigate', async () => {
    render(<ExplorePage />)

    await waitFor(() => expect(mockMapInstances.length).toBeGreaterThan(0))
    act(() => {
      mockMapInstances[0].emit('style.load')
    })

    const nextBtn = screen.getByRole('button', { name: /next: select observations/i })
    expect(nextBtn).toBeDisabled()
    expect(screen.getByText('No area selected yet')).toBeInTheDocument()

    // Click Use demo area rendered by the real AoiDrawMap toolbar
    const demoButtons = screen.getAllByRole('button', { name: /use demo area/i })
    expect(demoButtons).toHaveLength(2)
    fireEvent.click(demoButtons[1])

    await waitFor(() => {
      expect(mockMapInstances[0].sources['custom-aoi-source']).toBeDefined()
    })
    expect(mockMapInstances[0].sources['custom-aoi-source'].data).toEqual(DEMO_AOI)
    expect(mockMapInstances[0].fitBounds).toHaveBeenCalled()
    expect(screen.getByText('Valid Geometry')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(getStoredAOI()).toEqual(DEMO_AOI)
    expect(nextBtn).not.toBeDisabled()

    // Click Next and verify navigation
    fireEvent.click(nextBtn)
    expect(pushMock).toHaveBeenCalledWith('/observations')

    // Click Clear rendered by AoiDrawMap toolbar and verify full reset
    const clearButtons = screen.getAllByRole('button', { name: /clear/i })
    expect(clearButtons).toHaveLength(2)
    fireEvent.click(clearButtons[1])

    await waitFor(() => {
      expect(mockMapInstances[0].sources['custom-aoi-source']).toBeUndefined()
    })
    expect(screen.getByText('No area selected yet')).toBeInTheDocument()
    expect(getStoredAOI()).toBeNull()
    expect(nextBtn).toBeDisabled()
  })

  it('shows invalid geometry error Alert and disables Next when TerraDraw finishes a self-intersecting polygon', async () => {
    render(<ExplorePage />)

    await waitFor(() => expect(mockMapInstances.length).toBeGreaterThan(0))
    act(() => {
      mockMapInstances[0].emit('style.load')
    })
    await waitFor(() => expect(mockTerraDrawInstances.length).toBeGreaterThan(0))

    const bowtiePolygon = {
      type: 'Polygon' as const,
      coordinates: [[[73.8, 18.4], [73.9, 18.5], [73.9, 18.4], [73.8, 18.5], [73.8, 18.4]]],
    }

    act(() => {
      mockTerraDrawInstances[0].snapshot = [{ geometry: bowtiePolygon }]
      mockTerraDrawInstances[0].emit('finish')
    })

    await waitFor(() => {
      expect(screen.getByText('Invalid Geometry')).toBeInTheDocument()
    })
    expect(screen.getByText('Polygon is self-intersecting.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next: select observations/i })).toBeDisabled()
  })

  it('displays Map Style Load Failed Alert on MapLibre error and re-initializes on Retry while preserving stored AOI', async () => {
    setStoredAOI(DEMO_AOI)
    render(<ExplorePage />)

    await waitFor(() => expect(mockMapInstances.length).toBe(1))
    act(() => {
      mockMapInstances[0].emit('error', { error: new Error('tile fetch failed') })
    })

    await waitFor(() => {
      expect(screen.getByText('Map Style Load Failed')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /retry/i }))

    await waitFor(() => {
      expect(mockMapInstances.length).toBe(2)
    })
    expect(screen.queryByText('Map Style Load Failed')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next: select observations/i })).not.toBeDisabled()
  })
})
