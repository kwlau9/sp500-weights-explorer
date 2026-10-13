import { useState } from 'react'
import { useWeightsData } from './hooks/useWeightsData'
import './App.css'

function App() {
  const [year, setYear] = useState(2026)
  const [topN, setTopN] = useState(10)
  const { holdings, combined, sourceNote, isApprox, loading, error } =
    useWeightsData(year, topN)
  const maxWeight = holdings[0]?.weight ?? 0
  const sliderProgress = ((year - 1996) / (2026 - 1996)) * 100

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="Index, home">
          <span className="wordmark-mark" aria-hidden="true">I</span>
          <span>INDEX<span className="wordmark-dot">.</span></span>
        </a>
        <span className="topbar-caption">S&amp;P 500 / HISTORICAL WEIGHTS</span>
        <span className="topbar-range">1996 <span aria-hidden="true">—</span> 2026</span>
      </header>

      <main id="top" className="dashboard">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">THE MAKEUP OF THE MARKET</p>
          <h1 id="page-title">A changing market,<br />one year at a time.</h1>
          <p className="intro-copy">Explore how the biggest companies in America’s benchmark index have shifted over three decades.</p>
        </section>

        <section className="explorer" aria-label="Historical S&P 500 weights">
          <div className="explorer-heading">
            <div className="year-heading">
              <span className="section-kicker">YEAR-END SNAPSHOT</span>
              <div className="year-title-line">
                <h2>{year}</h2>
                {isApprox && <span className="approx-badge">ESTIMATE</span>}
              </div>
            </div>
            <div className="view-control" aria-label="Number of stocks shown">
              <span className="section-kicker">SHOW</span>
              <div className="segmented-control">
                {[10, 20].map((count) => (
                  <button
                    key={count}
                    type="button"
                    aria-pressed={topN === count}
                    onClick={() => setTopN(count)}
                  >
                    Top {count}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="summary-strip">
            <span>Combined weight of the top {topN}</span>
            <strong>{combined.toFixed(1)}<small>%</small></strong>
          </div>

          <div className="chart-heading" aria-hidden="true">
            <span>RANK</span>
            <span>COMPANY</span>
            <span>INDEX WEIGHT</span>
            <span>WEIGHT</span>
          </div>

          {loading && <p className="status-message" role="status">Loading historical holdings…</p>}
          {error && <p className="status-message error-message" role="alert">Could not load holdings: {error}</p>}
          {!loading && !error && holdings.length === 0 && (
            <p className="status-message">No holdings are available for {year}.</p>
          )}
          {!loading && !error && holdings.length > 0 && (
            <ol className="holdings-chart" aria-label={`Top ${topN} S&P 500 companies by weight in ${year}`}>
              {holdings.map((holding) => (
                <li className="holding-row" key={holding.ticker}>
                  <span className="holding-rank">{String(holding.rank).padStart(2, '0')}</span>
                  <span className="holding-company">
                    <strong>{holding.ticker}</strong>
                    <span title={holding.name}>{holding.name}</span>
                  </span>
                  <span className="bar-track" aria-hidden="true">
                    <span
                      className={`bar-fill${holding.rank === 1 ? ' bar-fill-leader' : ''}`}
                      style={{ width: `${maxWeight ? (holding.weight / maxWeight) * 100 : 0}%` }}
                    />
                  </span>
                  <strong className="holding-weight">{holding.weight.toFixed(2)}%</strong>
                </li>
              ))}
            </ol>
          )}

          <div className="timeline" aria-label="Choose a year">
            <div className="timeline-labels">
              <label htmlFor="year-slider">EXPLORE BY YEAR</label>
              <output htmlFor="year-slider">{year}</output>
            </div>
            <input
              id="year-slider"
              type="range"
              min="1996"
              max="2026"
              step="1"
              value={year}
              aria-label="Year, from 1996 to 2026"
              aria-valuetext={String(year)}
              style={{ '--slider-progress': `${sliderProgress}%` } as React.CSSProperties}
              onChange={(event) => setYear(Number(event.target.value))}
            />
            <div className="timeline-ticks" aria-hidden="true">
              <span>1996</span><span>2000</span><span>2005</span><span>2010</span><span>2015</span><span>2020</span><span>2026</span>
            </div>
          </div>

          <footer className="data-note">
            <span className="source-dot" aria-hidden="true" />
            <p>{sourceNote || 'Historical constituent weights'}. Top holdings are annual snapshots; percentages may not total 100%.</p>
          </footer>
        </section>
      </main>

      <footer className="page-footer">
        <span>INDEX / DATA EXPLORER</span>
        <span>Built from historical constituent data</span>
      </footer>
    </div>
  )
}

export default App
