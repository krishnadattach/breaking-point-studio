const MAX_SEARCHES = 5; // same hard limit as the backend (backend/bp/nodes/research.py)

function host(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// Shows what the research AGENT decided: every search it chose (in order), what came back,
// and the findings summary it wrote when it decided it had enough.
export default function ResearchPanel({ research, working }) {
  const queries = research?.queries || [];
  const notes = research?.notes;

  return (
    <section className="card">
      <h3>
        Research agent: {queries.length} of {MAX_SEARCHES} searches used
      </h3>
      <p className="muted">
        The agent wrote these search queries itself, read each result, and decided what was still missing. It may stop
        before the limit.
      </p>
      {queries.length === 0 && working && (
        <p className="muted">
          <span className="spinner" /> Waiting for the agent's first search...
        </p>
      )}
      <ol className="searches">
        {queries.map((q) => (
          <li key={q.seq}>
            <div className="search-q">
              <span className="search-n">{q.seq}</span> &ldquo;{q.query}&rdquo;
            </div>
            <div className="muted search-r">
              {q.result_count} result{q.result_count === 1 ? "" : "s"}
              {q.urls.length > 0 && <>: {[...new Set(q.urls.map(host))].join(", ")}</>}
            </div>
          </li>
        ))}
      </ol>
      {notes && (
        <details open>
          <summary>What the agent found</summary>
          <pre className="errtext">{notes}</pre>
        </details>
      )}
    </section>
  );
}
