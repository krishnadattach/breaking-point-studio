import { useState } from "react";
import { createEpisode, listEpisodes } from "../api.js";
import { Badge, ErrorBox, when } from "../components.jsx";
import { stageLabel, needsAction } from "../stages.js";
import usePolling from "../usePolling.js";

const EXAMPLE = "A grain of sand vs 10 levels of speed";

function NewEpisodeForm() {
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { id } = await createEpisode(topic.trim());
      window.location.hash = `#/ep/${id}`;
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="card new-episode" onSubmit={submit}>
      <h2>New episode</h2>
      <p className="muted">Name an object and a hazard. The agents research it, write the script, then wait for you.</p>
      <div className="row">
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder={EXAMPLE}
          minLength={3}
          maxLength={300}
          required
        />
        <button className="btn primary" disabled={busy || topic.trim().length < 3}>
          {busy ? "Starting..." : "Start episode"}
        </button>
      </div>
      <button type="button" className="link" onClick={() => setTopic(EXAMPLE)}>
        Use example: "{EXAMPLE}"
      </button>
      <ErrorBox message={error} />
    </form>
  );
}

export default function EpisodeList() {
  const { data: episodes, error } = usePolling(listEpisodes, [], 3000);

  return (
    <>
      <NewEpisodeForm />
      <section className="card">
        <h2>Episodes</h2>
        <ErrorBox message={error} />
        {!episodes && !error && <p className="muted">Loading...</p>}
        {episodes && episodes.length === 0 && <p className="muted">No episodes yet. Start one above.</p>}
        {episodes && episodes.length > 0 && (
          <table className="list">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Stage</th>
                <th>Status</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {episodes.map((ep) => (
                <tr key={ep.id} className={needsAction(ep.status) ? "attention" : ""}>
                  <td>
                    <a href={`#/ep/${ep.id}`}>{ep.topic}</a>
                  </td>
                  <td>{stageLabel(ep.stage)}</td>
                  <td>
                    <Badge status={ep.status} />
                  </td>
                  <td className="muted">{when(ep.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
