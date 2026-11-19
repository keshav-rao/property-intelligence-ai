import Link from 'next/link';
import { GITHUB_URL, PORTFOLIO_URL } from '../lib/site';
import { GitHubIcon } from './Icons';

/** Top-right header links: Evaluation, Portfolio, How it works, and GitHub button */
export default function SiteNav() {
  return (
    <nav className="site-nav" aria-label="Main Navigation">
      <Link href="/admin/evaluation" className="nav-item nav-eval" title="AI Benchmark & Evaluation Suite">
        Evaluation
      </Link>
      <a href={PORTFOLIO_URL} target="_blank" rel="noopener noreferrer" className="nav-item nav-portfolio" title="Portfolio (opens in a new tab)">
        Portfolio
      </a>
      <Link href="/how-it-works" className="nav-item nav-btn" title="How it works">
        How it works
      </Link>
      <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="nav-item nav-gh" aria-label="Source code on GitHub (opens in a new tab)" title="View on GitHub">
        <GitHubIcon size={20} />
      </a>
    </nav>
  );
}
