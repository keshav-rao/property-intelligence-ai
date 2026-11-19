import type { Metadata } from 'next';
import Link from 'next/link';
import SiteNav from '../../components/SiteNav';
import { ArrowLeftIcon, GitHubIcon } from '../../components/Icons';
import { GITHUB_URL, PORTFOLIO_URL } from '../../lib/site';

export const metadata: Metadata = {
  title: 'How it works · Property Intelligence AI',
  description: 'How the DarGlobal × Wasalt property concierge was designed, built, evaluated and what comes next.',
};

/* ------------------------------------------------------------------ content you can edit
   To show your own architecture diagram, put the image in frontend/public/ (e.g. public/architecture.png)
   and set ARCH_DIAGRAM to its path. Until then a sized placeholder is shown. */
const ARCH_DIAGRAM: string | null = '/architecture.png';

/** Numbers from evaluation/results/evaluation_report.json (109 cases) and eval/evaluation_results.json (18 live-LLM conversations). */
const KPIS = [
  { v: '109/109', l: 'Evaluation cases passed' },
  { v: '0', l: 'Critical failures' },
  { v: '0.99 s', l: 'Avg. turn with live LLM' },
  { v: '23', l: 'Behaviour unit tests' },
];

const CATEGORIES: { name: string; total: number; pass: number; ms: number }[] = [
  { name: 'Intent classification', total: 17, pass: 100, ms: 139 },
  { name: 'DarGlobal discovery', total: 18, pass: 100, ms: 191 },
  { name: 'Wasalt marketplace', total: 15, pass: 100, ms: 151 },
  { name: 'Recommendations', total: 10, pass: 100, ms: 150 },
  { name: 'Navigation', total: 10, pass: 100, ms: 211 },
  { name: 'Hallucination', total: 10, pass: 100, ms: 265 },
  { name: 'Lead capture', total: 8, pass: 100, ms: 101 },
  { name: 'Edge cases', total: 10, pass: 100, ms: 109 },
  { name: 'Security', total: 8, pass: 100, ms: 186 },
  { name: 'Conversation flow', total: 3, pass: 100, ms: 100 },
];

const SUBSYSTEMS: { name: string; value: string; note: string; todo?: boolean }[] = [
  { name: 'Intent accuracy', value: '100%', note: 'Rule-based NLU, 109 cases' },
  { name: 'Platform routing accuracy', value: '100%', note: 'DarGlobal vs Wasalt' },
  { name: 'Hallucination-free answers', value: '100%', note: 'No invented prices, people or facts' },
  { name: 'Security / privacy clean', value: '100%', note: 'Injection attempts, contact-detail redaction' },
  { name: 'Official URL validity', value: '93.6%', note: 'Live check; some sites block automated requests' },
  { name: 'Retrieval accuracy (Recall@5)', value: 'Add your number', note: 'From evaluation/runners/evaluate_rag.py', todo: true },
];

/** Developer journey: written by Keshav. Each entry is one challenge card. */
const JOURNEY: { title: string; challenge: string[]; solution: string[]; lesson: string }[] = [
  {
    title: 'Two businesses, one assistant',
    challenge: [
      'DarGlobal and Wasalt operate very differently. DarGlobal focuses on luxury developments, while Wasalt is a property marketplace with buying, renting, auctions, and other services.',
      'My early implementation exposed a problem: requests could be routed to the wrong platform. A luxury development search could return marketplace results, and rental requests could trigger irrelevant DarGlobal project searches.',
    ],
    solution: [
      "I decided that platform selection shouldn't be left to the LLM. I designed a routing layer that considers location, brand references, property intent, and whether the user wants to buy or rent.",
      'For locations where both platforms could be relevant, I designed a combined experience. A buyer searching in Riyadh can see Wasalt listings alongside relevant DarGlobal projects.',
    ],
    lesson: 'This was an important architectural decision: one conversational interface, but separate business logic behind it.',
  },
  {
    title: 'Making conversations remember context',
    challenge: [
      "A real conversation isn't a collection of independent search requests. Users change filters, ask unrelated questions, and return to previous searches.",
      'I encountered issues where old filters leaked into new searches and answers to guided questions were interpreted incorrectly.',
    ],
    solution: [
      'I designed a session-based state management approach that tracks the active filters, pending question, and previous results.',
      'I added logic to distinguish between a new search, a valid answer to a pending question, and an unrelated side question.',
    ],
    lesson: "This helped me understand that conversation memory is more than storing chat history. The application needs to understand the current state of the user's intent.",
  },
  {
    title: 'Getting property data without compromising integrity',
    challenge: [
      'Data collection was not straightforward. DarGlobal had bot protection, and Wasalt returned 403 responses to my crawler.',
      "I had to work within the websites' public access restrictions rather than simply trying to bypass them.",
    ],
    solution: [
      "I checked the available public access information, including robots.txt and Wasalt's llms.txt, and used publicly accessible pages through normal browsing to collect and parse available information.",
      'I also implemented data-quality checks because I found inconsistent area values and implausible prices.',
      "I made sure the assistant distinguishes between DarGlobal's prices being available on request and Wasalt's collected listings being a dated snapshot with links to the original listings.",
    ],
    lesson: 'I learned that a chatbot is only as trustworthy as the data behind it.',
  },
  {
    title: 'Making a free LLM reliable',
    challenge: [
      'I wanted to keep the project cost-effective, so I used OpenRouter with free model options.',
      'During testing, I encountered empty responses, inconsistent latency, and answers that occasionally mixed instructions between the two platforms.',
    ],
    solution: [
      "I made a deliberate architectural decision: the LLM should not control the application's critical decisions.",
      'I moved platform routing, filtering, retrieval, and other deterministic behaviour into the backend. The model receives the relevant context and focuses on communicating the answer.',
      'I also disabled unnecessary reasoning to reduce latency, introduced a model fallback chain, and added deterministic responses when the model was unavailable or returned unusable output.',
    ],
    lesson: 'That changed how I thought about LLM integration. The model should enhance the application, not become a single point of failure.',
  },
  {
    title: 'Handling personal information responsibly',
    challenge: [
      "Users might share their phone numbers or email addresses while enquiring about properties. Since the application uses external LLM providers, I didn't want raw contact information unnecessarily reaching model endpoints.",
    ],
    solution: [
      'I designed a privacy layer to detect and redact contact details before model calls.',
      'I separated lead storage from the model conversation and introduced a consent-based enquiry flow. I also made sure that enquiries remain associated with the relevant property or project rather than an outdated search.',
    ],
    lesson: 'This reminded me that privacy needs to be considered at the architecture level, not added as an afterthought.',
  },
  {
    title: 'Understanding how people actually search',
    challenge: [
      "People don't always use exact project names or standardized budgets.",
      'They might search for “Les Vagues” without accents, type “Trump Tower Dubai”, enter just “Neptune”, or express a budget as “1.2M”, “900k”, or “under 1,200,000”.',
      "A basic keyword search wasn't enough.",
    ],
    solution: [
      'I introduced project aliases and accent normalization, along with dedicated parsers for budgets and bedroom counts.',
      'I also added an exact-name boost to retrieval ranking so that direct project-name matches receive appropriate priority.',
    ],
    lesson: "I covered these behaviours with tests so that fixing one edge case wouldn't silently break another.",
  },
];

const SECTIONS = [
  ['concept', 'The concept'],
  ['architecture', 'System architecture'],
  ['stack', 'Tech stack'],
  ['benchmarks', 'Evaluation benchmarks'],
  ['roadmap', 'Future improvements'],
  ['journey', 'Developer journey'],
] as const;

export default function HowItWorks() {
  const maxMs = Math.max(...CATEGORIES.map((c) => c.ms));
  return (
    <>
      <header className="doc-top">
        <div className="doc-top-in">
          <Link href="/" className="doc-back"><ArrowLeftIcon /> Back<span className="hide-sm">&nbsp;to the concierge</span></Link>
          <div className="brandline-logo">
            <span className="dg">DarGlobal</span><span className="x">×</span><span className="ws">Wasalt</span>
          </div>
          <SiteNav />
        </div>
      </header>

      <main className="doc">
        {/* 1. Hero */}
        <div className="doc-hero">
          <p className="eyebrow">Case study · Property Intelligence AI</p>
          <h1>Building the <em>Property Concierge</em></h1>
          <p className="lede">
            One assistant for two very different businesses: DarGlobal, an international developer of branded luxury residences,
            and Wasalt, a Saudi property marketplace. This page explains how it decides what to say, why it is built that way,
            how it was tested, and what I learned building it.
          </p>
          <div className="doc-meta">
            <span>Next.js 15</span><span>FastAPI</span><span>Qdrant hybrid search</span><span>OpenRouter LLM</span><span>Docker + Caddy</span>
          </div>
        </div>

        <nav className="toc" aria-label="On this page">
          <b>On this page</b>
          <ol>
            {SECTIONS.map(([id, label]) => <li key={id}><a href={`#${id}`}>{label}</a></li>)}
          </ol>
        </nav>

        {/* 2. Concept */}
        <section id="concept">
          <h2><span className="num">01</span>The concept</h2>
          <p>
            A buyer rarely starts with a filter. They start with an idea: <i>&ldquo;something with three bedrooms in Riyadh, not too
            expensive&rdquo;</i> or <i>&ldquo;what is that Trump project in Jeddah?&rdquo;</i>. On today&apos;s sites that person has to
            know which company to visit, learn two different search UIs and dig for the right form. The concierge turns that into one
            conversation.
          </p>

          <div className="duo">
            <div className="panel">
              <span className="tag dg">DarGlobal</span>
              <h3>Luxury developer</h3>
              <p>38 branded projects in six countries. Buyers want brand, location, handover date and a private conversation with sales. No public prices.</p>
            </div>
            <div className="panel">
              <span className="tag ws">Wasalt</span>
              <h3>Saudi marketplace</h3>
              <p>Homes to buy or rent across Saudi cities, plus auctions, daily rentals and Matchmaker. Buyers want filters, prices and the live listing.</p>
            </div>
          </div>

          <h3>How it works</h3>
          <ol className="flow">
            <li><b>Understand.</b> Each message is parsed into an intent (search, project question, compare, enquiry, service) and slots: city, buy or rent, type, bedrooms, budget, brand.</li>
            <li><b>Remember.</b> Slots are merged into the session, so &ldquo;show villas instead&rdquo; changes one thing and keeps the rest.</li>
            <li><b>Ask only what is missing.</b> A guided workflow asks the single most useful next question, with tap-able quick replies.</li>
            <li><b>Route.</b> The request goes to DarGlobal, Wasalt or both. A Riyadh buyer sees Wasalt listings and the DarGlobal projects in that city.</li>
            <li><b>Retrieve and rank.</b> Hybrid search (dense embeddings + BM25) over the catalogue and knowledge base, with hard filters for budget and location.</li>
            <li><b>Phrase.</b> The LLM writes the answer from a context block of verified facts only, streamed token by token.</li>
            <li><b>Act.</b> Cards, comparison table, verified official links, or a consent-based enquiry form.</li>
          </ol>

          <h3>Why it works</h3>
          <p className="pull">Rules decide. The language model only phrases.</p>
          <p>
            Everything that must be correct (which company, which listings, which link, whether to show the enquiry form) is decided
            by deterministic, tested code. The model never sees a phone number or email and never invents a price, because it only
            sees facts it is allowed to repeat. If the free model is slow or down, a deterministic answer is streamed instead, so search
            and lead capture never break.
          </p>
        </section>

        {/* 3. Architecture */}
        <section id="architecture">
          <h2><span className="num">02</span>System architecture</h2>
          <p>
            The browser talks to one streaming endpoint. The backend runs the dialogue engine, retrieval and the LLM call, and returns
            structured UI (cards, links, forms) alongside the text.
          </p>
          <figure>
            {ARCH_DIAGRAM ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img className="diagram-img" src={ARCH_DIAGRAM} alt="System architecture of Property Intelligence AI" />
            ) : (
              <div className="diagram-slot" role="img" aria-label="Architecture diagram placeholder">
                <div>
                  <b>Architecture diagram</b>
                  <span>Placeholder, 16:10. Add the image to <code>frontend/public/</code> and set <code>ARCH_DIAGRAM</code> in this page.</span>
                </div>
              </div>
            )}
            <figcaption>Next.js widget → FastAPI (NLU · dialogue · retrieval · LLM) → Qdrant and OpenRouter</figcaption>
          </figure>
          <ul className="list">
            <li><code>nlu.py</code> rule-based intent and slot extraction (budgets like &ldquo;1.2M&rdquo;, &ldquo;3BR&rdquo;, city and project aliases).</li>
            <li><code>dialogue.py</code> session state, guided workflow, routing, ranking with relaxation, comparison, leads.</li>
            <li><code>rag.py</code> Qdrant + <code>bge-small-en-v1.5</code> embeddings fused with BM25 and an exact-name boost.</li>
            <li><code>llm.py</code> OpenRouter streaming client with a fallback chain and reasoning disabled for low latency.</li>
            <li><code>destinations.py</code> an allow-list of verified official URLs; the bot can only link to these.</li>
          </ul>
        </section>

        {/* 4. Tech stack */}
        <section id="stack">
          <h2><span className="num">03</span>Tech stack</h2>
          <div className="stack">
            <div className="panel">
              <span className="tag nv">Frontend</span>
              <ul>
                <li><b>Next.js 15 · React 19 · TypeScript</b><span>App Router, standalone build, API proxy rewrites</span></li>
                <li><b>Hand-written CSS</b><span>Light theme in the DarGlobal and Wasalt palettes, mobile full-screen chat</span></li>
                <li><b>Server-Sent Events</b><span>Cards arrive first, then the answer streams in</span></li>
              </ul>
            </div>
            <div className="panel">
              <span className="tag nv">Backend</span>
              <ul>
                <li><b>FastAPI · Pydantic v2 · Uvicorn</b><span>Chat, search, compare, leads, health endpoints</span></li>
                <li><b>Deterministic dialogue engine</b><span>Intents, slots, session memory, guided questions</span></li>
                <li><b>Privacy layer</b><span>Email and phone redaction before any model call</span></li>
              </ul>
            </div>
            <div className="panel">
              <span className="tag dg">Vector database &amp; retrieval</span>
              <ul>
                <li><b>Qdrant</b><span>Embedded on disk locally, a container in production</span></li>
                <li><b>fastembed · BAAI/bge-small-en-v1.5</b><span>ONNX on CPU, no GPU needed</span></li>
                <li><b>Hybrid scoring</b><span>0.65 dense + 0.35 BM25, metadata filters, exact-name boost</span></li>
              </ul>
            </div>
            <div className="panel">
              <span className="tag ws">LLM orchestration</span>
              <ul>
                <li><b>OpenRouter · nemotron-3.5-lightning</b><span>Free tier, reasoning off for 1 to 3 s answers</span></li>
                <li><b>Fallback chain</b><span>Gemma 4 31B, Nemotron Ultra, then a deterministic answer</span></li>
                <li><b>Custom, no framework</b><span>Grounded prompts with per-platform rules, written by hand</span></li>
              </ul>
            </div>
          </div>
          <p className="note" style={{ marginTop: 14 }}>Deployment: Docker Compose (Qdrant, backend, frontend) behind Caddy with automatic Let&apos;s Encrypt HTTPS on a VPS.</p>
        </section>

        {/* 5. Benchmarks */}
        <section id="benchmarks">
          <h2><span className="num">04</span>Evaluation benchmarks</h2>
          <p>
            Two suites run against the live API: 109 single-turn cases across ten categories, and 18 multi-turn conversations with the
            real LLM. A further 23 unit tests cover the dialogue engine without any model.
          </p>
          <div className="kpis">
            {KPIS.map((k) => <div className="kpi" key={k.l}><b>{k.v}</b><span>{k.l}</span></div>)}
          </div>

          <h3>Subsystem metrics</h3>
          <div className="table-wrap">
            <table className="bench">
              <thead><tr><th>Metric</th><th>Result</th><th>What it checks</th></tr></thead>
              <tbody>
                {SUBSYSTEMS.map((s) => (
                  <tr key={s.name}>
                    <td>{s.name}</td>
                    <td className={`n${s.todo ? ' todo' : ''}`}>{s.value}</td>
                    <td>{s.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3>Latency and pass rate by category</h3>
          <div className="table-wrap">
            <table className="bench">
              <thead><tr><th>Category</th><th>Cases</th><th>Pass</th><th>Avg. latency</th><th aria-hidden="true"></th></tr></thead>
              <tbody>
                {CATEGORIES.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td className="n">{c.total}</td>
                    <td className="n">{c.pass}%</td>
                    <td className="n">{c.ms} ms</td>
                    <td aria-hidden="true"><div className="bar"><i style={{ width: `${(c.ms / maxMs) * 100}%` }} /></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            Category latencies are server time for the 109-case suite. With the live free-tier LLM writing every answer, the 18
            conversations averaged 0.99 s per turn. Full results: <Link href="/admin/evaluation">evaluation dashboard</Link>.
          </p>
        </section>

        {/* 6. Roadmap */}
        <section id="roadmap">
          <h2><span className="num">05</span>Future improvements</h2>
          <ul className="roadmap">
            <li><b>Live inventory through partner APIs.</b> Replace the dated Wasalt snapshot and add DarGlobal unit availability and pricing once shared.</li>
            <li><b>Arabic and right-to-left.</b> Bilingual NLU, Arabic embeddings and a mirrored layout for the Saudi audience.</li>
            <li><b>CRM hand-off.</b> Send consented enquiries to each company&apos;s CRM with the conversation summary, instead of local storage.</li>
            <li><b>Smarter retrieval.</b> A cross-encoder re-ranker, learned weights for dense vs keyword, and a Recall@k benchmark in CI.</li>
            <li><b>Shared session store.</b> Redis for sessions and rate limits, so the API scales beyond one instance.</li>
            <li><b>Observability.</b> Per-turn traces, model fallback rates and drop-off points in the guided flow.</li>
            <li><b>More channels.</b> WhatsApp and voice, reusing the same dialogue engine.</li>
            <li><b>Saved searches and alerts.</b> Notify a buyer when a matching listing appears, with explicit opt-in.</li>
          </ul>
        </section>

        {/* 7. Developer journey */}
        <section id="journey" className="journey">
          <h2><span className="num">06</span>Developer journey</h2>
          <div className="j-hero">
            <p className="j-kicker">24 hours. One ambitious idea. An AI-assisted engineering challenge.</p>
            <div className="j-facts">
              <div><b>24h</b><span>Idea to working system</span></div>
              <div><b>6</b><span>Hard problems solved</span></div>
              <div><b>Claude</b><span>AI pair programmer</span></div>
            </div>
          </div>
          <p>
            I took this project as a 24-hour challenge. The goal was to build a working property intelligence assistant that could
            bring together two very different platforms: DarGlobal and Wasalt.
          </p>
          <p>
            I used Claude for AI-assisted development and vibe coding throughout the process. But I didn&apos;t want to simply generate
            code and hope everything worked. I wanted to understand the system I was building.
          </p>
          <p>
            I made the architectural decisions, defined how the components should interact, chose the technologies, and worked through
            the problems that came up during implementation. Claude helped me move faster, explore solutions, and turn those decisions
            into code.
          </p>
          <p className="pull">The biggest challenge wasn&apos;t writing code quickly. It was making the right decisions under a tight deadline.</p>
          <p>Here are some of the problems I encountered and how I approached them.</p>

          <div className="j-list">
            {JOURNEY.map((j, i) => (
              <article className="j-card" key={j.title}>
                <header>
                  <span className="j-num">{String(i + 1).padStart(2, '0')}</span>
                  <h3>{j.title}</h3>
                </header>
                <div className="j-part">
                  <span className="j-label">The challenge</span>
                  {j.challenge.map((p, k) => <p key={k}>{p}</p>)}
                </div>
                <div className="j-part solved">
                  <span className="j-label">How I solved it</span>
                  {j.solution.map((p, k) => <p key={k}>{p}</p>)}
                </div>
                <p className="j-lesson">{j.lesson}</p>
              </article>
            ))}
          </div>

          <h3 className="j-sub">What the 24-hour challenge taught me</h3>
          <p>Vibe coding with Claude helped me move quickly, but speed alone wasn&apos;t the achievement.</p>
          <p>
            I had to make decisions about the architecture, understand how the frontend, backend, retrieval system, vector database, and
            LLM fit together, and decide what should happen when individual components failed.
          </p>
          <p>
            I used Claude as a development partner, not as a replacement for engineering judgment. I was responsible for deciding what to
            build, why to build it that way, and whether the implementation actually met the intended behaviour.
          </p>
          <p>I know the architecture behind this application because I made those decisions throughout the process.</p>
          <p>
            Could the system be improved? Absolutely. Live inventory integrations, Arabic support, CRM integration, shared session storage,
            and deeper observability are among the improvements I&apos;d consider next.
          </p>
          <p>
            But for a 24-hour challenge, I feel I justified the ambition. I didn&apos;t just build a chatbot demo. I built an end-to-end
            system, evaluated its behaviour, and learned a lot about making AI applications more predictable and reliable.
          </p>
          <blockquote className="takeaway">
            <span>My biggest takeaway</span>
            AI can accelerate engineering, but it doesn&apos;t remove the need to understand the engineering.
          </blockquote>

          <div className="author">
            <div className="author-mark" aria-hidden="true">KR</div>
            <div className="author-txt">
              <b>Keshav Rao</b>
              <span>Designed and built Property Intelligence AI. More of my work is on my portfolio.</span>
            </div>
            <div className="author-links">
              <a href={PORTFOLIO_URL} target="_blank" rel="noopener noreferrer" className="nav-btn primary">View portfolio</a>
              <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="nav-gh" aria-label="GitHub repository (opens in a new tab)"><GitHubIcon size={20} /></a>
            </div>
          </div>
        </section>

        <div className="doc-end">
          <Link href="/" className="nav-btn primary">Try the concierge</Link>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="nav-btn">View the code on GitHub</a>
          <a href={PORTFOLIO_URL} target="_blank" rel="noopener noreferrer" className="nav-btn">My portfolio</a>
        </div>
      </main>
    </>
  );
}
