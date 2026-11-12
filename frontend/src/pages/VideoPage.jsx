import { useState } from "react";
import { approve, sendNotes, videoUrl } from "../api.js";
import { ErrorBox } from "../components.jsx";

export default function VideoPage({ ep, onChanged }) {
  const waiting = ep.status === "waiting_video_review";
  const final = ep.assets.find((a) => a.kind === "final_video");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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

  // ?v= makes the browser reload the file when the episode is re-rendered
  const src = `${videoUrl(ep.id)}?v=${encodeURIComponent(final?.seconds ?? "")}-${ep.updated_at}`;

  return (
    <div className="video-layout">
      <div className="player-wrap">
        <video key={src} className="player" src={src} controls playsInline />
      </div>
      <div className="video-side">
        <section className="card">
          <h3>Final video</h3>
          <p className="muted">
            1080&times;1920 vertical MP4{final?.seconds ? `, about ${Math.round(final.seconds)} seconds` : ""}.
          </p>
          <a className="btn" href={videoUrl(ep.id)} download={`${ep.id}.mp4`}>
            Download MP4
          </a>
        </section>

        {waiting && (
          <section className="card review-box">
            <h3>Final approval</h3>
            <p className="muted">Happy with it? Approving finishes the episode.</p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes (only needed if you send it back)"
              rows={3}
            />
            <div className="row">
              <button className="btn primary" disabled={busy} onClick={() => act(() => approve(ep.id))}>
                Approve video
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
        )}

        {ep.status === "done" && <div className="card done-card">Approved. This episode is finished.</div>}
      </div>
    </div>
  );
}
