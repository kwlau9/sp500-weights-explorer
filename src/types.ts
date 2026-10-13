export type Holding = {
  rank: number
  ticker: string
  name: string
  weight: number
}

export type WeightsPayload = {
  years: number[]
  byYear: Record<string, Holding[]>
  sourcesByYear: Record<string, string>
  meta: {
    topNStored: number
    approxYears: number[]
    sources: string[]
  }
}
