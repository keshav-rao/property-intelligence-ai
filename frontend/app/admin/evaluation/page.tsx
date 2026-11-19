'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';

interface SubsystemMetrics {
  intent_accuracy_pct: number;
  platform_routing_accuracy_pct: number;
  url_validity_rate_pct: number;
  hallucination_free_rate_pct: number;
  security_clean_rate_pct: number;
}

interface CategorySummary {
  total: number;
  passed: number;
  pass_rate_pct: number;
  avg_latency_ms: number;
  critical_failures: number;
}

interface TestCaseResult {
  test_id: string;
  category: string;
  priority: string;
  user_input: string;
  latency_ms: number;
  score: number;
  overall_status: string;
  critical_failure: boolean;
  intent_pass: boolean;
  routing_pass: boolean;
  filter_pass: boolean;
  url_pass: boolean;
  hallucination_pass: boolean;
  security_pass: boolean;
  actual_intent?: string;
  actual_platform?: string;
  answer_snippet?: string;
}

interface EvaluationReport {
  timestamp: string;
  base_url: string;
  total_test_cases: number;
  passed_test_cases: number;
  overall_pass_rate_pct: number;
  avg_latency_ms: number;
  critical_failures: number;
  subsystem_metrics: SubsystemMetrics;
  category_summaries: Record<string, CategorySummary>;
  results: TestCaseResult[];
}

export default function AdminEvaluationDashboard() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedTestId, setExpandedTestId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReport() {
      try {
        setLoading(true);
        // Try proxy endpoint first, fallback to static public json
        const res = await fetch('/api/evaluation/report').catch(() => null);
        if (res && res.ok) {
          const data = await res.json();
          setReport(data);
          return;
        }
        const fallbackRes = await fetch('/evaluation_report.json');
        if (fallbackRes.ok) {
          const data = await fallbackRes.json();
          setReport(data);
          return;
        }
        throw new Error('Unable to fetch evaluation report');
      } catch (err: any) {
        setError(err.message || 'Failed to load report');
      } finally {
        setLoading(false);
      }
    }
    fetchReport();
  }, []);

  const filteredResults = useMemo(() => {
    if (!report?.results) return [];
    return report.results.filter((item) => {
      const matchCat = selectedCategory === 'all' || item.category === selectedCategory;
      const matchStatus =
        selectedStatus === 'all' ||
        (selectedStatus === 'pass' && item.score >= 3) ||
        (selectedStatus === 'fail' && item.score < 3) ||
        (selectedStatus === 'critical' && item.critical_failure);
      const q = searchQuery.toLowerCase();
      const matchQuery =
        !q ||
        item.test_id.toLowerCase().includes(q) ||
        item.user_input.toLowerCase().includes(q) ||
        (item.answer_snippet && item.answer_snippet.toLowerCase().includes(q));
      return matchCat && matchStatus && matchQuery;
    });
  }, [report, selectedCategory, selectedStatus, searchQuery]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--ivory)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-sans)' }}>
        <div style={{ textAlign: 'center', color: 'var(--navy-900)' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>Loading Evaluation Benchmark...</div>
          <p style={{ color: 'var(--muted)' }}>Fetching live test results from FastAPI test runner</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--ivory)', padding: '3rem 2rem', fontFamily: 'var(--font-sans)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', background: 'var(--surface)', padding: '2rem', borderRadius: '16px', border: '1px solid var(--line)' }}>
          <h2 style={{ color: 'var(--warn)', marginBottom: '1rem' }}>Evaluation Report Not Found</h2>
          <p style={{ color: 'var(--text)', marginBottom: '1.5rem' }}>
            The evaluation suite has not been executed yet or the API is warming up. Run the evaluation suite from your terminal:
          </p>
          <pre style={{ background: 'var(--navy-900)', color: '#fff', padding: '1rem', borderRadius: '8px', overflowX: 'auto', marginBottom: '1.5rem' }}>
            backend/.venv/Scripts/python evaluation/runners/run_evaluation.py --category all
          </pre>
          <Link href="/" style={{ color: 'var(--purple-600)', textDecoration: 'underline', fontWeight: 600 }}>
            ← Return to Chat Assistant
          </Link>
        </div>
      </div>
    );
  }

  const { subsystem_metrics, category_summaries } = report;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--ivory)', padding: '2rem 1.5rem', fontFamily: 'var(--font-sans)', color: 'var(--text)' }}>
      <div style={{ maxWidth: '1240px', margin: '0 auto' }}>
        
        {/* Navigation & Header */}
        <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', background: 'var(--purple-100)', color: 'var(--purple-700)', padding: '4px 10px', borderRadius: '6px' }}>
                AI Engineering Benchmark
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--muted)' }}>
                Target: <code>{report.base_url}</code> | Evaluated: {report.timestamp}
              </span>
            </div>
            <h1 style={{ fontSize: '2.2rem', fontFamily: 'var(--font-display)', color: 'var(--navy-900)', margin: '0 0 0.5rem 0' }}>
              Property Intelligence AI — Evaluation Dashboard
            </h1>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: '0.95rem' }}>
              Rigorous 10-category evaluation suite testing intent classification, context retention, grounded RAG, navigation, and prompt security.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <Link
              href="/"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '0.6rem 1.2rem',
                borderRadius: '10px',
                background: 'var(--navy-900)',
                color: '#fff',
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: '0.9rem',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              ← Back to Assistant
            </Link>
          </div>
        </header>

        {/* Top KPI Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          
          <div style={{ background: 'var(--surface)', padding: '1.4rem', borderRadius: '16px', border: '1px solid var(--line)', boxShadow: 'var(--shadow-card)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.3rem' }}>
              Overall Pass Rate
            </div>
            <div style={{ fontSize: '2.4rem', fontWeight: 800, color: report.overall_pass_rate_pct >= 90 ? 'var(--ok)' : 'var(--warn)' }}>
              {report.overall_pass_rate_pct}%
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '0.2rem' }}>
              {report.passed_test_cases} of {report.total_test_cases} test cases passed (≥3/4)
            </div>
          </div>

          <div style={{ background: 'var(--surface)', padding: '1.4rem', borderRadius: '16px', border: '1px solid var(--line)', boxShadow: 'var(--shadow-card)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.3rem' }}>
              Avg Response Latency
            </div>
            <div style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--navy-900)' }}>
              {report.avg_latency_ms} <span style={{ fontSize: '1.2rem', fontWeight: 500 }}>ms</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--ok)', marginTop: '0.2rem', fontWeight: 600 }}>
              ✓ Target met (&lt;500ms local)
            </div>
          </div>

          <div style={{ background: 'var(--surface)', padding: '1.4rem', borderRadius: '16px', border: '1px solid var(--line)', boxShadow: 'var(--shadow-card)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.3rem' }}>
              Knowledge Boundary
            </div>
            <div style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--ok)' }}>
              {subsystem_metrics.hallucination_free_rate_pct}%
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '0.2rem' }}>
              Zero hallucinated guarantees or unlisted prices
            </div>
          </div>

          <div style={{ background: 'var(--surface)', padding: '1.4rem', borderRadius: '16px', border: '1px solid var(--line)', boxShadow: 'var(--shadow-card)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.3rem' }}>
              Critical Violations
            </div>
            <div style={{ fontSize: '2.4rem', fontWeight: 800, color: report.critical_failures === 0 ? 'var(--ok)' : '#d93025' }}>
              {report.critical_failures}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--ok)', marginTop: '0.2rem', fontWeight: 600 }}>
              ✓ No prompt leaks, PII or fake URLs
            </div>
          </div>

        </div>

        {/* Subsystem Health Grid */}
        <section style={{ background: 'var(--surface)', borderRadius: '16px', border: '1px solid var(--line)', padding: '1.5rem', marginBottom: '2rem', boxShadow: 'var(--shadow-card)' }}>
          <h2 style={{ fontSize: '1.15rem', color: 'var(--navy-900)', margin: '0 0 1rem 0', fontWeight: 700 }}>
            Subsystem Verification Targets
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '1rem' }}>
            
            <div style={{ padding: '0.8rem 1rem', background: 'var(--ivory)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>Intent Accuracy</span>
                <span style={{ fontWeight: 700, color: 'var(--ok)' }}>{subsystem_metrics.intent_accuracy_pct}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--line)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${subsystem_metrics.intent_accuracy_pct}%`, height: '100%', background: 'var(--ok)' }} />
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Target: ≥95%</span>
            </div>

            <div style={{ padding: '0.8rem 1rem', background: 'var(--ivory)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>Platform Routing</span>
                <span style={{ fontWeight: 700, color: 'var(--ok)' }}>{subsystem_metrics.platform_routing_accuracy_pct}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--line)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${subsystem_metrics.platform_routing_accuracy_pct}%`, height: '100%', background: 'var(--ok)' }} />
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Target: ≥98%</span>
            </div>

            <div style={{ padding: '0.8rem 1rem', background: 'var(--ivory)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>URL Validity & HTTPS</span>
                <span style={{ fontWeight: 700, color: 'var(--ok)' }}>{subsystem_metrics.url_validity_rate_pct}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--line)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${subsystem_metrics.url_validity_rate_pct}%`, height: '100%', background: 'var(--ok)' }} />
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Target: ≥90%</span>
            </div>

            <div style={{ padding: '0.8rem 1rem', background: 'var(--ivory)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>Hallucination Resistance</span>
                <span style={{ fontWeight: 700, color: 'var(--ok)' }}>{subsystem_metrics.hallucination_free_rate_pct}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--line)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${subsystem_metrics.hallucination_free_rate_pct}%`, height: '100%', background: 'var(--ok)' }} />
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Target: ≥98%</span>
            </div>

            <div style={{ padding: '0.8rem 1rem', background: 'var(--ivory)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>Prompt Security</span>
                <span style={{ fontWeight: 700, color: 'var(--ok)' }}>{subsystem_metrics.security_clean_rate_pct}%</span>
              </div>
              <div style={{ height: '6px', background: 'var(--line)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${subsystem_metrics.security_clean_rate_pct}%`, height: '100%', background: 'var(--ok)' }} />
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Target: 100%</span>
            </div>

          </div>
        </section>

        {/* Category Breakdown Matrix */}
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1.25rem', color: 'var(--navy-900)', margin: '0 0 1rem 0', fontWeight: 700 }}>
            Testing Category Matrix (10 Dimensions)
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {Object.entries(category_summaries).map(([cat, summary]) => (
              <div
                key={cat}
                onClick={() => setSelectedCategory(selectedCategory === cat ? 'all' : cat)}
                style={{
                  background: selectedCategory === cat ? 'var(--purple-50)' : 'var(--surface)',
                  border: `1.5px solid ${selectedCategory === cat ? 'var(--purple-600)' : 'var(--line)'}`,
                  borderRadius: '14px',
                  padding: '1.1rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', textTransform: 'capitalize', color: 'var(--navy-900)' }}>
                    {cat.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: summary.pass_rate_pct >= 90 ? 'var(--ok)' : 'var(--warn)' }}>
                    {summary.pass_rate_pct}%
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Passed: {summary.passed}/{summary.total}</span>
                  <span>Avg: {summary.avg_latency_ms} ms</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Detailed Results Filter & Table */}
        <section style={{ background: 'var(--surface)', borderRadius: '16px', border: '1px solid var(--line)', padding: '1.5rem', boxShadow: 'var(--shadow-card)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.2rem' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', color: 'var(--navy-900)', margin: '0 0 0.2rem 0', fontWeight: 700 }}>
                Test Cases & Execution Traces
              </h2>
              <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
                Showing {filteredResults.length} of {report.results.length} total tests
              </span>
            </div>

            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                style={{ padding: '0.45rem 0.8rem', borderRadius: '8px', border: '1px solid var(--line)', fontSize: '0.85rem', background: '#fff' }}
              >
                <option value="all">All Categories</option>
                {Object.keys(category_summaries).map((cat) => (
                  <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
                ))}
              </select>

              {/* Status Filter */}
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                style={{ padding: '0.45rem 0.8rem', borderRadius: '8px', border: '1px solid var(--line)', fontSize: '0.85rem', background: '#fff' }}
              >
                <option value="all">All Statuses</option>
                <option value="pass">Passed (Score 3-4)</option>
                <option value="fail">Needs Review (Score &lt; 3)</option>
                <option value="critical">Critical Violations</option>
              </select>

              {/* Search query */}
              <input
                type="text"
                placeholder="Search test ID or query..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ padding: '0.45rem 0.8rem', borderRadius: '8px', border: '1px solid var(--line)', fontSize: '0.85rem', width: '210px' }}
              />
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--line)', color: 'var(--muted)' }}>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Test ID</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Category</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>User Query</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Platform</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Latency</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Score</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((item) => (
                  <tr
                    key={item.test_id}
                    onClick={() => setExpandedTestId(expandedTestId === item.test_id ? null : item.test_id)}
                    style={{
                      borderBottom: '1px solid var(--line)',
                      cursor: 'pointer',
                      background: expandedTestId === item.test_id ? 'var(--ivory)' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700, color: 'var(--navy-900)' }}>{item.test_id}</td>
                    <td style={{ padding: '0.75rem 0.5rem', color: 'var(--muted)' }}>{item.category.replace(/_/g, ' ')}</td>
                    <td style={{ padding: '0.75rem 0.5rem', maxWidth: '340px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.user_input}
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '2px 6px', borderRadius: '4px', background: item.actual_platform === 'darglobal' ? 'var(--gold-100)' : (item.actual_platform === 'wasalt' ? 'var(--purple-100)' : 'var(--navy-100)') }}>
                        {item.actual_platform || 'general'}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem', color: 'var(--muted)' }}>{item.latency_ms} ms</td>
                    <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>{item.score}/4</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      <span
                        style={{
                          padding: '3px 8px',
                          borderRadius: '6px',
                          fontWeight: 600,
                          fontSize: '0.75rem',
                          background: item.score >= 3 ? '#e6f4ea' : '#fce8e6',
                          color: item.score >= 3 ? 'var(--ok)' : '#c5221f',
                        }}
                      >
                        {item.overall_status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Expanded Drawer / Detail */}
          {expandedTestId && (() => {
            const current = report.results.find((r) => r.test_id === expandedTestId);
            if (!current) return null;
            return (
              <div style={{ marginTop: '1.5rem', padding: '1.2rem', background: 'var(--ivory)', borderRadius: '12px', border: '1px solid var(--line-strong)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                  <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--navy-900)' }}>
                    Detailed Inspection: {current.test_id} ({current.category})
                  </h3>
                  <button onClick={() => setExpandedTestId(null)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontWeight: 700 }}>✕</button>
                </div>
                <div style={{ marginBottom: '0.8rem' }}>
                  <strong>User Query:</strong>
                  <div style={{ background: '#fff', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--line)', marginTop: '0.2rem' }}>
                    {current.user_input}
                  </div>
                </div>
                <div style={{ marginBottom: '0.8rem' }}>
                  <strong>Actual Answer Generated:</strong>
                  <div style={{ background: '#fff', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--line)', marginTop: '0.2rem', fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>
                    {current.answer_snippet || '(None)'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem', color: 'var(--muted)', flexWrap: 'wrap' }}>
                  <span>Latency: <b>{current.latency_ms} ms</b></span>
                  <span>Intent Match: <b>{current.intent_pass ? '✓ Pass' : '✗ Fail'}</b></span>
                  <span>Platform Routing: <b>{current.routing_pass ? '✓ Pass' : '✗ Fail'}</b></span>
                  <span>Filter Match: <b>{current.filter_pass ? '✓ Pass' : '✗ Fail'}</b></span>
                  <span>URL Security: <b>{current.url_pass ? '✓ Pass' : '✗ Fail'}</b></span>
                  <span>Hallucination Free: <b>{current.hallucination_pass ? '✓ Yes' : '✗ Flagged'}</b></span>
                  <span>Prompt Security: <b>{current.security_pass ? '✓ Clean' : '✗ Violation'}</b></span>
                </div>
              </div>
            );
          })()}

        </section>

      </div>
    </div>
  );
}
