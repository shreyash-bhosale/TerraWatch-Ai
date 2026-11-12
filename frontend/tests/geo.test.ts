import { describe, it, expect } from 'vitest'
import { DEMO_AOI, validateAOI, calculateBoundingBox, calculateCentroid } from '@/lib/geo'

describe('geo AOI validation', () => {
  it('validates DEMO_AOI successfully with expected bounds and area', () => {
    const res = validateAOI(DEMO_AOI)
    expect(res.valid).toBe(true)
    expect(res.bbox).toEqual([73.8, 18.496, 73.864, 18.56])
    expect(res.areaKm2).toBeGreaterThan(40)
    expect(res.areaKm2).toBeLessThan(60)
    expect(res.vertexCount).toBe(5)
  })

  it('rejects self-intersecting polygon (bowtie)', () => {
    const bowtie = {
      type: 'Polygon' as const,
      coordinates: [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]
    }
    const res = validateAOI(bowtie)
    expect(res.valid).toBe(false)
    expect(res.error).toMatch(/self-intersect/i)
  })

  it('rejects out-of-range coordinates', () => {
    const badCoords = {
      type: 'Polygon' as const,
      coordinates: [[[190, 10], [191, 10], [191, 11], [190, 11], [190, 10]]]
    }
    const res = validateAOI(badCoords)
    expect(res.valid).toBe(false)
  })

  it('computes centroid and bbox correctly', () => {
    const ring = [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]
    expect(calculateBoundingBox(ring)).toEqual([0, 0, 2, 2])
    const [cx, cy] = calculateCentroid(ring)
    expect(cx).toBeCloseTo(1, 5)
    expect(cy).toBeCloseTo(1, 5)
  })
})
