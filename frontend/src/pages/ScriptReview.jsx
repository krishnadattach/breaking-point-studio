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
  const [confirming, setConfirming] = useState(false); // second click needed when claims failed

  const claimByLevel = Object.fromEntries((script.claims || []).map((c) => [c.level, c]));
  // Claims that did not pass fact-check (or were never checked): approving with these needs a confirmation.
  // Claim 0 is the hook; older scripts have no hook claim, so it is only counted when it exists.
  const hookClaim = claimByLevel[0];
  const failedLevels = [
    ...(hookClaim && hookClaim.status !== "pass" ? ["the hook"] : []),
    ...script.levels.filter((lv) => claimByLevel[lv.n]?.status !== "pass").map((lv) => `level ${lv.n}`),
  ];
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
        {hookClaim && (
          <div className="claim">
            <span className={`check ${hookClaim.status === "pass" ? "ok" : "no"}`}>
              {hookClaim.status === "pass" ? "Hook checked" : "Hook failed"}
            </span>
            {hookClaim.source_url ? <Source url={hookClaim.source_url} /> : <span className="muted">no facts claimed</span>}
          </div>
        )}
        {hookClaim?.status !== "pass" && hookClaim?.reason && <p className="reason">{hookClaim.reason}</p>}
        {script.twist_expectation && (
          <p className="twist-why">
            <b className="orange">Twist, level {script.twist_level}:</b> viewers expect: {script.twist_expectation.trim().replace(/[.\s]+$/, "")}.{" "}
            {script.twist_explanation}
          </p>
        )}
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
          {failedLevels.length > 0 && (
            <div className="warn-box">
              <b>
                Warning: {failedLevels.length} claim{failedLevels.length === 1 ? "" : "s"} failed fact-check (
                {failedLevels.join(", ")}).
              </b>{" "}
              These numbers may not be supported by their sources. Check the orange reasons above, or send notes so the
              writer fixes them.
            </div>
          )}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes for the writer (only needed if you send it back), e.g. 'make level 7 more surprising'"
            rows={3}
          />
          <div className="row">
            {confirming ? (
              <>
                <button
                  className="btn warm"
                  disabled={busy}
                  onClick={() => act(async () => { await approve(ep.id); setConfirming(false); })}
                >
                  Yes, approve with {failedLevels.length} failed claim{failedLevels.length === 1 ? "" : "s"}
                </button>
                <button className="btn" disabled={busy} onClick={() => setConfirming(false)}>
                  Cancel
                </button>
              </>
            ) : (
              <button
                className="btn primary"
                disabled={busy}
                onClick={() => (failedLevels.length > 0 ? setConfirming(true) : act(() => approve(ep.id)))}
              >
                Approve script
              </button>
            )}
            <button
              className="btn warm"
              disabled={busy || confirming || !notes.trim()}
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
