import { useEffect, useMemo, useState } from 'react'
import type { Holding, WeightsPayload } from '../types'

const DATA_URL = '/data/sp500-top-weights.json'

export function useWeightsData(year: number, topN: number) {
  const [payload, setPayload] = useState<WeightsPayload | None>(null)
  const [error, setError] = useState<string | None>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetch(DATA_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load weights (${res.status})`)
        return res.json() as Promise<WeightsPayload>
      })
      .then((data) => {
        if (!cancelled) {
          setPayload(data)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load data')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const holdings: Holding[] = useMemo(() => {
    if (!payload) return []
    return (payload.byYear[String(year)] ?? []).slice(0, topN)
  }, [payload, year, topN])

  const combined = useMemo(
    () => holdings.reduce((sum, row) => sum + row.weight, 0),
    [holdings],
  )

  const sourceNote = payload?.sourcesByYear[String(year)] ?? ''
  const isApprox = payload?.meta.approxYears.includes(year) ?? false
  const years = payload?.years ?? []
  const sources = payload?.meta.sources ?? []

  return { payload, holdings, combined, sourceNote, isApprox, years, sources, loading, error }
}

type None = null
