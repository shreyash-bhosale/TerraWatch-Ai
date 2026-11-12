import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AoiDrawMap } from '@/components/map/AoiDrawMap'
import { ResultsMap } from '@/components/map/ResultsMap'
import { DEMO_AOI, DEMO_BBOX } from '@/lib/geo'
import React from 'react'

type EventCb = (payload?: any) => void

let mockMapInstances: any[] = []

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

    emit(event: string, payload?: any) {
      ;(this.handlers[event] || []).forEach((cb) => cb(payload))
    }

    addSource(id: string, cfg: any) {
      this.sources[id] = {
        ...cfg,
        setData: (d: any) => {
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

vi.mock('terra-draw', () => ({
  TerraDraw: class {
    start = vi.fn()
    stop = vi.fn()
    clear = vi.fn()
    setMode = vi.fn()
    on = vi.fn()
    getSnapshot = vi.fn().mockReturnValue([])
  },
  TerraDrawMapLibreGLAdapter: vi.fn(),
  TerraDrawPolygonMode: vi.fn(),
  TerraDrawRectangleMode: vi.fn(),
  TerraDrawSelectMode: vi.fn(),
  TerraDrawRenderMode: vi.fn(),
}))

describe('MapLibre Components (F-05 & F-06)', () => {
  beforeEach(() => {
    mockMapInstances = []
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({} as any)
    vi.stubGlobal(
      'Image',
      class {
        onload: (() => void) | null = null
        onerror: (() => void) | null = null
        set src(_v: string) {
          queueMicrotask(() => this.onerror?.())
        }
      }
    )
  })

  it('draws initialAoi onto MapLibre source when Use demo area updates props even during tile loading (F-05)', async () => {
    function Harness() {
      const [aoi, setAoi] = React.useState<any>(null)
      return (
        <div>
          <button onClick={() => setAoi(DEMO_AOI)}>External Demo Trigger</button>
          <AoiDrawMap
            initialAoi={aoi}
            onAoiChange={vi.fn()}
            onClear={() => setAoi(null)}
            onUseDemoArea={() => setAoi(DEMO_AOI)}
          />
        </div>
      )
    }

    render(<Harness />)

    await waitFor(() => {
      expect(mockMapInstances.length).toBe(1)
    })

    const map = mockMapInstances[0]
    // Simulate raster tiles still pending so isStyleLoaded() is false right after style.load
    map.isStyleLoaded.mockReturnValue(false)
    await act(async () => {
      map.emit('style.load')
    })

    fireEvent.click(screen.getByText('External Demo Trigger'))

    await waitFor(() => {
      expect(map.getSource('custom-aoi-source')?.data).toEqual(DEMO_AOI)
      expect(map.fitBounds).toHaveBeenCalled()
    })
  })

  it('shows Alert with Retry on map style error in AoiDrawMap and ResultsMap (F-06)', async () => {
    render(
      <AoiDrawMap
        initialAoi={null}
        onAoiChange={vi.fn()}
        onClear={vi.fn()}
        onUseDemoArea={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(mockMapInstances.length).toBe(1)
    })

    await act(async () => {
      mockMapInstances[0].emit('error', { error: new Error('Style load failure') })
    })

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    await waitFor(() => {
      expect(mockMapInstances.length).toBe(2)
    })

    // ResultsMap style error shows Alert with Retry button
    render(
      <ResultsMap
        bounds={DEMO_BBOX}
        layers={{ difference: '/diff.png', before: '/b.png', after: '/a.png' }}
        activeLayer="difference"
      />
    )

    await waitFor(() => {
      expect(mockMapInstances.length).toBe(3)
    })

    await act(async () => {
      mockMapInstances[2].emit('error', { error: new Error('Tile style error') })
    })

    await waitFor(() => {
      const retryButtons = screen.getAllByRole('button', { name: /retry/i })
      expect(retryButtons.length).toBeGreaterThanOrEqual(1)
    })
  })
})
