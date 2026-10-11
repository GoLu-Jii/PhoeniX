import { useState, useEffect, useRef } from 'react'
import './App.css'

export interface SayDoGap {
  claim: string
  reality: string
  verdict: 'supported' | 'partly_supported' | 'no_public_corroboration' | 'contradictory_evidence' | 'unannounced_move' | string
}

export interface AnalysisData {
  analysis_source?: 'groq' | 'rule_based' | string
  stated_focus: string
  engineering_reality: string
  say_do_gaps: SayDoGap[]
  strategic_verdict: string
  warnings?: Array<{ scope?: string; message: string }>
}

export interface Finding {
  title: string
  committed_repo: string
  description: string
}

export interface WebsiteData {
  url?: string
  title?: string
  description?: string
  headings?: string[]
  status?: string
}

export interface RepositorySummary {
  name: string
  full_name?: string
  url?: string
  description?: string
  topics?: string[]
  language?: string
  languages?: Record<string, number>
  created_at?: string
  updated_at?: string
  pushed_at?: string
  evidence_id?: string
  recent_commits_count?: number
  recent_commits?: Array<{ sha: string; message: string; committed_at?: string; url?: string }>
  weekly_commit_activity?: Array<{ week: string; total: number; days?: number[] }>
}

export interface InvestigationSummary {
  total_public_repositories?: number
  active_repositories_count?: number
  total_recent_commits?: number
  top_languages?: Record<string, number>
}

export interface InvestigationResult {
  status: string
  account?: {
    login: string
    name?: string
    type?: string
    url?: string
    avatar_url?: string
  }
  detection_source?: 'groq' | 'rule_based' | string
  analysis?: AnalysisData
  findings?: Finding[]
  backing_commits?: string[]
  website?: WebsiteData
  summary?: InvestigationSummary
  repositories_summary?: Array<Record<string, unknown>>
  warnings?: Array<{ scope?: string; message: string; repository?: string }>
  repositories?: RepositorySummary[]
  parsed_commits?: Array<Record<string, unknown>>
}

const PRESETS = [
  {
    name: 'Vercel',
    github: 'https://github.com/vercel',
    website: 'https://vercel.com/home',
    label: 'Vercel (Agentic Infra)',
  },
  {
    name: 'Encode',
    github: 'https://github.com/encode',
    website: 'https://www.encode.io',
    label: 'Encode (HTTPX / APIs)',
  },
  {
    name: 'Octocat',
    github: 'https://github.com/octocat',
    website: 'https://example.com',
    label: 'Octocat (Reference)',
  },
]

const PROGRESS_STEPS = [
  'Connecting to GitHub API & retrieving public repositories...',
  'Parsing 45-day commit histories & detecting velocity bursts...',
  'Interpreting engineering signals with Groq AI (Stage 1)...',
  'Scraping official website narrative & stated product claims...',
  'Synthesizing Say-Do Gaps & Strategic Verdict with Groq AI (Stage 2)...',
]

export default function App() {
  const [githubUrl, setGithubUrl] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [includeRaw, setIncludeRaw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [progressStep, setProgressStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<InvestigationResult | null>(null)
  const [showRawJson, setShowRawJson] = useState(false)
  const [expandedFindings, setExpandedFindings] = useState<Record<number, boolean>>({})

  const resultsRef = useRef<HTMLDivElement>(null)

  // Progress animation while loading
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined
    if (loading) {
      interval = setInterval(() => {
        setProgressStep((prev) => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev))
      }, 3500)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [loading])

  const handleInvestigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!githubUrl.trim()) {
      setError('Please enter a GitHub username or organization URL (e.g., https://github.com/vercel).')
      return
    }

    setProgressStep(0)
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const payload: Record<string, unknown> = {
        github_url: githubUrl.trim(),
        website_url: websiteUrl.trim() || undefined,
        include_raw: includeRaw,
      }

      const response = await fetch('/api/investigations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server returned HTTP ${response.status}`)
      }

      const data: InvestigationResult = await response.json()
      setResult(data)

      // Smooth scroll down to results
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth' })
      }, 200)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Investigation failed.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const applyPreset = (preset: typeof PRESETS[0]) => {
    setGithubUrl(preset.github)
    setWebsiteUrl(preset.website)
    setError(null)
  }

  const toggleFindingExpanded = (index: number) => {
    setExpandedFindings((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  const getVerdictBadge = (verdict: string) => {
    const v = (verdict || '').toLowerCase()
    if (v.includes('unannounced')) {
      return {
        label: '★ UNANNOUNCED MOVE',
        className: 'badge-mono',
        style: {
          backgroundColor: 'var(--verdict-unannounced-bg)',
          color: 'var(--verdict-unannounced-text)',
          borderColor: 'var(--verdict-unannounced-border)',
        },
      }
    }
    if (v.includes('supported') && !v.includes('partly')) {
      return {
        label: '✓ SUPPORTED',
        className: 'badge-mono',
        style: {
          backgroundColor: 'var(--verdict-supported-bg)',
          color: 'var(--verdict-supported-text)',
          borderColor: 'var(--verdict-supported-border)',
        },
      }
    }
    if (v.includes('partly')) {
      return {
        label: '⚡ PARTLY SUPPORTED',
        className: 'badge-mono',
        style: {
          backgroundColor: 'var(--verdict-partly-bg)',
          color: 'var(--verdict-partly-text)',
          borderColor: 'var(--verdict-partly-border)',
        },
      }
    }
    if (v.includes('contra')) {
      return {
        label: '⚠ CONTRADICTION',
        className: 'badge-mono',
        style: {
          backgroundColor: 'var(--verdict-contradictory-bg)',
          color: 'var(--verdict-contradictory-text)',
          borderColor: 'var(--verdict-contradictory-border)',
        },
      }
    }
    return {
      label: '○ NO PUBLIC TRACE',
      className: 'badge-mono',
      style: {
        backgroundColor: 'var(--verdict-no-evidence-bg)',
        color: 'var(--verdict-no-evidence-text)',
        borderColor: 'var(--verdict-no-evidence-border)',
      },
    }
  }

  return (
    <div className="app-container">
      {/* 1. Navbar */}
      <header className="hf-navbar">
        <div className="nav-brand">
          <span>PHOENIX</span>
          <span className="brand-badge">26</span>
        </div>

        <ul className="nav-links">
          <li>
            <a href="#investigate" className="nav-link">
              Investigation
            </a>
          </li>
          {result && (
            <>
              <li>
                <a href="#signals" className="nav-link">
                  Signals
                </a>
              </li>
              <li>
                <a href="#matrix" className="nav-link">
                  Say-Do Matrix
                </a>
              </li>
              <li>
                <a href="#repos" className="nav-link">
                  Repositories
                </a>
              </li>
            </>
          )}
          <li>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="nav-link"
            >
              API Docs ↗
            </a>
          </li>
        </ul>

        <div className="nav-actions">
          <button
            type="button"
            className="btn-hf-coral"
            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
            onClick={() => {
              window.scrollTo({ top: 0, behavior: 'smooth' })
            }}
          >
            New Intel
          </button>
        </div>
      </header>

      {/* 2. Hero Section (Hacktoberfest 2026 Homage) */}
      <section className="hf-hero hero-dot-matrix" id="investigate">
        <div className="hero-content">
          <div className="hero-kicker">
            OCTOBER 2026 · PUBLIC REPOSITORIES · WEB NARRATIVES · SAY-DO GAPS
          </div>

          <h1 className="hero-headline">
            500+ Commits. <span className="coral-accent">One private truth.</span>
          </h1>

          <p className="hero-subhead">
            Cross-examine official corporate marketing claims against verifiable GitHub engineering traces.
            Detect silent pivots, stealth AI features, and synchronized release bursts with Groq AI.
          </p>

          {/* Dual Search Box Card */}
          <form className="hero-search-card" onSubmit={handleInvestigate}>
            <div className="input-field-group">
              <span className="input-icon" title="GitHub Account or URL">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
              </span>
              <input
                type="text"
                className="hf-input"
                placeholder="GitHub Org (e.g. vercel or https://github.com/vercel)"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="input-field-group">
              <span className="input-icon" title="Company Website URL">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
              </span>
              <input
                type="text"
                className="hf-input"
                placeholder="Company Website (e.g. https://vercel.com)"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                disabled={loading}
              />
            </div>

            <button type="submit" className="btn-hf-coral" disabled={loading}>
              {loading ? 'Analyzing...' : 'Investigate Company'}
            </button>
          </form>

          {/* Quick Presets & Options */}
          <div className="options-row">
            <div className="samples-strip">
              <span>Quick Samples:</span>
              {PRESETS.map((p) => (
                <button
                  key={p.name}
                  type="button"
                  className="btn-pill-sample"
                  onClick={() => applyPreset(p)}
                  disabled={loading}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <label className="debug-checkbox-label" title="Return complete raw 52-week activity & commit histories">
              <input
                type="checkbox"
                checked={includeRaw}
                onChange={(e) => setIncludeRaw(e.target.checked)}
                disabled={loading}
              />
              <span>Full Raw History (Debug)</span>
            </label>
          </div>
        </div>
      </section>

      {/* 3. Ticker Banner (Screenshot 1 Bottom Strip) */}
      <div className="hf-ticker-strip">
        <div className="ticker-item">
          <span>PHOENIX 2026:</span>
          <span className="accent-text">Evidence belongs to everyone.</span>
        </div>
        <div className="ticker-item">
          <span>POWERED BY:</span>
          <span>GROQ OSS · FASTAPI · BEAUTIFULSOUP</span>
        </div>
        <div className="ticker-item">
          <span>STRICT GROUNDING:</span>
          <span className="accent-text">Zero Unverified Speculation.</span>
        </div>
      </div>

      {/* 4. Loading / Radar Scanner State */}
      {loading && (
        <div className="loading-scanner-container">
          <div className="scanner-radar-visual">
            <div className="scanner-pulse-dot" />
          </div>

          <h2 style={{ fontSize: '1.8rem', marginBottom: '0.5rem', color: '#ffffff' }}>
            Investigating Public Footprint...
          </h2>
          <p style={{ color: 'var(--hf-light-muted)', fontSize: '0.95rem' }}>
            Live multi-stage analysis with GitHub trace ingestion & dual Groq reasoning.
          </p>

          <div className="scanner-steps-list">
            {PROGRESS_STEPS.map((step, idx) => {
              const isDone = progressStep > idx
              const isActive = progressStep === idx
              return (
                <div
                  key={step}
                  className={`scanner-step-item ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}
                >
                  <span>{isDone ? '✓' : isActive ? '▶' : '○'}</span>
                  <span>{step}</span>
                  {isActive && <span className="scanner-pulse-dot" style={{ marginLeft: 'auto' }} />}
                </div>
              )
            })}
          </div>
          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--hf-light-muted)' }}>
            Typically takes 12–25 seconds depending on repository volume.
          </div>
        </div>
      )}

      {/* 5. Error State */}
      {error && !loading && (
        <div className="error-card-container">
          <h3 className="error-title">Investigation Alert</h3>
          <div className="error-message">{error}</div>
          <button type="button" className="btn-hf-coral" onClick={() => handleInvestigate()}>
            Retry Investigation
          </button>
        </div>
      )}

      {/* 6. Results Dashboard */}
      {result && !loading && (
        <main className="results-dashboard" ref={resultsRef}>
          {/* Company Overview Card */}
          <div className="overview-card">
            <div className="company-identity">
              {result.account?.avatar_url ? (
                <img
                  src={result.account.avatar_url}
                  alt={result.account.name || result.account.login}
                  className="company-avatar"
                />
              ) : (
                <div className="company-avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                  {result.account?.login?.slice(0, 2).toUpperCase() || 'PX'}
                </div>
              )}
              <div className="company-details">
                <h2>
                  {result.account?.name || result.account?.login}
                  <span className="badge-mono badge-pop">
                    {result.account?.type || 'Organization'}
                  </span>
                </h2>
                <div className="meta-links">
                  {result.account?.url && (
                    <a href={result.account.url} target="_blank" rel="noreferrer" className="meta-link">
                      github.com/{result.account.login} ↗
                    </a>
                  )}
                  {result.website?.url && (
                    <a href={result.website.url} target="_blank" rel="noreferrer" className="meta-link">
                      {result.website.url.replace(/^https?:\/\//, '')} ↗
                    </a>
                  )}
                </div>
              </div>
            </div>

            <div className="stats-grid">
              <div className="stat-box">
                <div className="stat-num">{result.repositories?.length || 0}</div>
                <div className="stat-label">Monitored Repos</div>
              </div>
              <div className="stat-box">
                <div className="stat-num">{result.findings?.length || 0}</div>
                <div className="stat-label">Detected Signals</div>
              </div>
              <div className="stat-box">
                <div className="stat-num">{result.analysis?.say_do_gaps?.length || 0}</div>
                <div className="stat-label">Say-Do Gaps</div>
              </div>
              <div className="stat-box">
                <div className="stat-num" style={{ color: result.detection_source === 'groq' ? '#16a34a' : '#ca8a04' }}>
                  {result.detection_source === 'groq' ? 'GROQ' : 'RULES'}
                </div>
                <div className="stat-label">Engine</div>
              </div>
            </div>
          </div>

          {/* Section: Strategic Big Picture (Stated Focus vs Engineering Reality) */}
          <div className="hf-section-header">
            <div>
              <div className="hero-kicker" style={{ color: 'var(--hf-muted-text)', marginBottom: '0.25rem' }}>
                EXECUTIVE SYNTHESIS
              </div>
              <h2 className="section-title">
                The Big Picture. <span className="coral-accent">Stated vs. Actual.</span>
              </h2>
            </div>
            <p className="section-subtitle">
              Comparing public marketing promises on the company homepage with concrete engineering commits.
            </p>
          </div>

          <div className="comparative-hero-card">
            <div className="comparative-columns">
              <div className="comp-col left-col">
                <div className="comp-header">
                  <span className="comp-title" style={{ color: '#2563eb' }}>
                    <span>🌐</span> Stated Focus (What They Say)
                  </span>
                  <span className="badge-mono" style={{ fontSize: '0.7rem' }}>
                    HOMEPAGE CLAIMS
                  </span>
                </div>
                <p className="comp-text">
                  {result.analysis?.stated_focus || 'No stated focus available.'}
                </p>
                {result.website?.headings && result.website.headings.length > 0 && (
                  <div style={{ marginTop: '1rem', display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {result.website.headings.slice(0, 4).map((h) => (
                      <span key={h} className="topic-tag">
                        {h}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="comp-col right-col">
                <div className="comp-header">
                  <span className="comp-title" style={{ color: '#16a34a' }}>
                    <span>💻</span> Engineering Reality (What They Code)
                  </span>
                  <span className="badge-mono" style={{ fontSize: '0.7rem' }}>
                    PUBLIC TRACES
                  </span>
                </div>
                <p className="comp-text">
                  {result.analysis?.engineering_reality || 'No engineering reality available.'}
                </p>
              </div>
            </div>

            <div className="verdict-callout">
              <div className="verdict-kicker">STRATEGIC VERDICT & TRAJECTORY</div>
              <p className="verdict-body">
                {result.analysis?.strategic_verdict || 'Synthesis complete.'}
              </p>
            </div>
          </div>

          {/* Section: Say-Do Gaps Matrix */}
          <div className="hf-section-header" id="matrix">
            <div>
              <div className="hero-kicker" style={{ color: 'var(--hf-muted-text)', marginBottom: '0.25rem' }}>
                VERIFIED COMPARISON
              </div>
              <h2 className="section-title">
                Claim vs. Evidence <span className="coral-accent">Matrix.</span>
              </h2>
            </div>
            <p className="section-subtitle">
              Specific claims compared against public code reality, labeled with objective evidence verdicts.
            </p>
          </div>

          {result.analysis?.say_do_gaps && result.analysis.say_do_gaps.length > 0 ? (
            <div className="cards-editorial-grid">
              {result.analysis.say_do_gaps.map((gap, i) => {
                const badge = getVerdictBadge(gap.verdict)
                return (
                  <div key={i} className="gap-card">
                    <div>
                      <div className="gap-card-top">
                        <span className={badge.className} style={badge.style}>
                          {badge.label}
                        </span>
                      </div>
                      <h3 className="claim-title" style={{ marginTop: '0.85rem' }}>
                        &ldquo;{gap.claim}&rdquo;
                      </h3>
                    </div>

                    <div className="reality-box">
                      <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: 'var(--hf-muted-text)', marginBottom: '0.2rem' }}>
                        OBSERVED REALITY:
                      </div>
                      <div>{gap.reality}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="hf-card-static" style={{ padding: '2rem', textAlign: 'center', marginBottom: '3rem' }}>
              <p style={{ margin: 0, color: 'var(--hf-muted-text)' }}>
                No significant Say-Do divergence detected between public claims and public repositories.
              </p>
            </div>
          )}

          {/* Section: Observed Signals (Screenshot 2 Style) */}
          <div className="hf-section-header" id="signals">
            <div>
              <div className="hero-kicker" style={{ color: 'var(--hf-muted-text)', marginBottom: '0.25rem' }}>
                COMMITS & TIMING ANOMALIES
              </div>
              <h2 className="section-title">
                Observed <span className="coral-accent">Signals.</span>
              </h2>
            </div>
            <p className="section-subtitle">
              Significant engineering shifts, synchronized activity bursts, and provider expansions detected in recent history.
            </p>
          </div>

          {result.findings && result.findings.length > 0 ? (
            <div className="cards-editorial-grid">
              {result.findings.map((finding, idx) => {
                const isBurst = finding.title.toLowerCase().includes('burst') || finding.title.toLowerCase().includes('pace')
                const isExpanded = Boolean(expandedFindings[idx])
                return (
                  <div key={idx} className="signal-card">
                    <div className="signal-card-main">
                      <div className="signal-badge-row">
                        <span className="badge-mono badge-pop">
                          {finding.committed_repo || 'GENERAL'}
                        </span>
                        {isBurst && (
                          <span className="badge-mono badge-amber">
                            VELOCITY BURST
                          </span>
                        )}
                      </div>

                      <h3 className="signal-title">{finding.title}</h3>
                      <p className="signal-desc">{finding.description}</p>

                      {/* Supporting commits list */}
                      {result.backing_commits && result.backing_commits.length > 0 && !isBurst && (
                        <div className="commits-accordion">
                          <button
                            type="button"
                            className="commits-toggle-btn"
                            onClick={() => toggleFindingExpanded(idx)}
                          >
                            <span>{isExpanded ? '▼ Hide Supporting Commits' : '▶ View Supporting Commits'}</span>
                          </button>

                          {isExpanded && (
                            <ul className="commits-list">
                              {result.backing_commits.map((msg, cIdx) => (
                                <li key={cIdx}>{msg}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Right-side Badge Box (Hacktoberfest Screenshot 2 style) */}
                    <div className="signal-side-badge">
                      <div className="badge-date-top">SIGNAL</div>
                      <div className="badge-date-main">#{idx + 1}</div>
                      <div className="badge-date-bottom">
                        {isBurst ? 'BURST' : 'FEATURE'}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="hf-card-static" style={{ padding: '2rem', textAlign: 'center', marginBottom: '3rem' }}>
              <p style={{ margin: 0, color: 'var(--hf-muted-text)' }}>
                No anomalous or suspicious commit bursts detected across monitored public repositories.
              </p>
            </div>
          )}

          {/* Section: Monitored Repositories */}
          <div className="hf-section-header" id="repos">
            <div>
              <div className="hero-kicker" style={{ color: 'var(--hf-muted-text)', marginBottom: '0.25rem' }}>
                CODEBASE OVERVIEW
              </div>
              <h2 className="section-title">
                Monitored <span className="coral-accent">Repositories.</span>
              </h2>
            </div>
            <p className="section-subtitle">
              Public repositories actively analyzed for commit frequency, topics, and development patterns.
            </p>
          </div>

          {result.repositories && result.repositories.length > 0 ? (
            <div className="cards-editorial-grid three-col">
              {result.repositories.map((repo) => (
                <div key={repo.name} className="repo-card">
                  <div>
                    <a
                      href={repo.url}
                      target="_blank"
                      rel="noreferrer"
                      className="repo-name"
                    >
                      {repo.name}
                      <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>↗</span>
                    </a>
                    <p className="repo-desc" style={{ marginTop: '0.5rem' }}>
                      {repo.description || 'No repository description provided.'}
                    </p>
                  </div>

                  <div>
                    {repo.topics && repo.topics.length > 0 && (
                      <div className="repo-topics" style={{ marginBottom: '0.75rem' }}>
                        {repo.topics.slice(0, 3).map((t) => (
                          <span key={t} className="topic-tag">
                            #{t}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="repo-footer">
                      <span>{repo.language || 'Code'}</span>
                      <span>
                        {typeof repo.recent_commits_count === 'number'
                          ? `${repo.recent_commits_count} commits`
                          : repo.evidence_id || 'monitored'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="hf-card-static" style={{ padding: '2rem', textAlign: 'center', marginBottom: '3rem' }}>
              <p style={{ margin: 0, color: 'var(--hf-muted-text)' }}>
                No public repositories found for this account.
              </p>
            </div>
          )}

          {/* Warnings Section (if any) */}
          {result.warnings && result.warnings.length > 0 && (
            <div className="warnings-section">
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '0.85rem', color: '#92400e', marginBottom: '0.5rem' }}>
                TECHNICAL NOTICES & LIMITATIONS:
              </div>
              {result.warnings.map((w, wIdx) => (
                <div key={wIdx} className="warning-item">
                  <span>⚠</span>
                  <span>[{w.scope || 'system'}] {w.message}</span>
                </div>
              ))}
            </div>
          )}

          {/* Developer Raw JSON Inspection Button */}
          <div style={{ marginTop: '3.5rem', textAlign: 'center' }}>
            <button
              type="button"
              className="btn-hf-ghost"
              style={{ color: 'var(--hf-black)', borderColor: 'var(--hf-black)' }}
              onClick={() => setShowRawJson(!showRawJson)}
            >
              {showRawJson ? 'Hide Raw JSON Payload' : 'Inspect Raw JSON Payload (API Inspection)'}
            </button>

            {showRawJson && (
              <pre
                style={{
                  marginTop: '1.5rem',
                  padding: '1.5rem',
                  backgroundColor: 'var(--hf-black)',
                  color: '#a7f3d0',
                  borderRadius: '6px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.8rem',
                  textAlign: 'left',
                  overflowX: 'auto',
                  maxHeight: '400px',
                  border: '2px solid var(--hf-black)',
                }}
              >
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </main>
      )}

      {/* 7. Empty State Welcome (when no investigation has run) */}
      {!result && !loading && !error && (
        <section style={{ maxWidth: '960px', margin: '4rem auto', padding: '0 1.5rem', textAlign: 'center' }}>
          <div className="hf-section-header" style={{ justifyContent: 'center', textAlign: 'center', borderBottom: 'none' }}>
            <div>
              <div className="hero-kicker" style={{ color: 'var(--hf-muted-text)', marginBottom: '0.5rem' }}>
                HOW PHOENIX WORKS
              </div>
              <h2 className="section-title">
                Three-Stage <span className="coral-accent">Code Recon.</span>
              </h2>
            </div>
          </div>

          <div className="cards-editorial-grid three-col" style={{ marginTop: '2rem' }}>
            <div className="hf-card" style={{ padding: '1.75rem', textAlign: 'left' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🛰️</div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>1. Trace Public Code</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--hf-muted-text)', margin: 0 }}>
                Retrieves up to 10 monitored repositories, daily commit distributions, and velocity spikes over the past 45 days.
              </p>
            </div>

            <div className="hf-card" style={{ padding: '1.75rem', textAlign: 'left' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔍</div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>2. Harvest Web Claims</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--hf-muted-text)', margin: 0 }}>
                Safely scrapes official product positioning, feature announcements, and marketing taglines from the homepage.
              </p>
            </div>

            <div className="hf-card" style={{ padding: '1.75rem', textAlign: 'left' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⚖️</div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>3. Say-Do Arbitration</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--hf-muted-text)', margin: 0 }}>
                Groq AI cross-examines claims against verifiable code evidence, flagging unannounced moves with zero speculation.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* 8. Footer */}
      <footer className="hf-footer">
        <div className="footer-inner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 800 }}>
            <span>PHOENIX INTELLIGENCE 2026</span>
            <span className="brand-badge">26</span>
          </div>
          <p style={{ margin: 0, maxWidth: '600px', fontSize: '0.8rem' }}>
            Built for competitive intelligence & open-source engineering verification. All findings are derived from public GitHub activity and official homepages.
          </p>
          <div className="footer-links">
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">FastAPI Docs</a>
            <a href="https://github.com" target="_blank" rel="noreferrer">GitHub API</a>
            <a href="https://groq.com" target="_blank" rel="noreferrer">Groq AI</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
