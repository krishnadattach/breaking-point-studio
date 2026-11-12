import { useState } from "react";
import { approve, sendNotes } from "../api.js";
import { ErrorBox, when } from "../components.jsx";

function Source({ url }) {
  if (!url) return <span className="muted">no source</span>;
  let host = url;
  try {
    host = new URL(url).hostname.replace(/^www\./, "");
  } catch {}
  return (
    <a href={url} target="_blank" rel="noreferrer noopener" title={url}>
      {host} &#8599;
    </a>
  );
}

export default function ScriptReview({ ep, onChanged }) {
  const script = ep.script;
  const waiting = ep.status === "waiting_script_review";
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const claimByLevel = Object.fromEntries((script.claims || []).map((c) => [c.level, c]));
  const scriptNotes = ep.approvals.filter((a) => a.kind === "script");

  async function act(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      setNotes("");
      onChanged();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card">
        <div className="meta">
          <span>
            Draft <b>v{script.version}</b>
          </span>
          <span>
            Object: <b>{script.shape}</b>
          </span>
          <span>
            Hazard: <b>{script.hazard}</b>
          </span>
          <span>
            Twist: <b className="orange">level {script.twist_level}</b>
          </span>
        </div>
        <p className="hook">&ldquo;{script.hook}&rdquo;</p>
      </section>

      <section className="levels">
        {script.levels.map((lv) => {
          const claim = claimByLevel[lv.n];
          const twist = lv.n === script.twist_level;
          return (
            <article key={lv.n} className={`level ${twist ? "twist" : ""}`}>
              <div className="level-n">{lv.n}</div>
              <div className="level-body">
                <p className="narration">{lv.narration}</p>
                <div className="level-meta">
                  <span className="value">{lv.value}</span>
                  <span className={`verdict ${lv.verdict === "SURVIVES" ? "survives" : "destroyed"}`}>{lv.verdict}</span>
                  {twist && <span className="twist-tag">TWIST</span>}
                </div>
                <div className="claim">
                  <span className={`check ${claim?.status === "pass" ? "ok" : "no"}`}>
                    {claim?.status === "pass" ? "Checked" : claim ? "Failed" : "Unchecked"}
                  </span>
                  <span className="claim-text">{lv.claim}</span>
                  <Source url={claim?.source_url || lv.source_url} />
                </div>
                {claim?.status !== "pass" && claim?.reason && <p className="reason">{claim.reason}</p>}
              </div>
            </article>
          );
        })}
      </section>

      {scriptNotes.length > 0 && (
        <section className="card">
          <h3>Earlier decisions</h3>
          <ul className="history">
            {scriptNotes.map((a, i) => (
              <li key={i}>
                <b>{a.action}</b> <span className="muted">{when(a.created_at)}</span>
                {a.notes && <div>{a.notes}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {waiting ? (
        <section className="card review-box">
          <h3>Your decision</h3>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes for the writer (only needed if you send it back), e.g. 'make level 7 more surprising'"
            rows={3}
          />
          <div className="row">
            <button className="btn primary" disabled={busy} onClick={() => act(() => approve(ep.id))}>
              Approve script
            </button>
            <button
              className="btn warm"
              disabled={busy || !notes.trim()}
              onClick={() => act(() => sendNotes(ep.id, notes.trim()))}
            >
              Send notes
            </button>
          </div>
          <ErrorBox message={error} />
        </section>
      ) : null}
    </>
  );
}
