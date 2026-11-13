import { useState } from "react";
import { getEpisode, retry } from "../api.js";
import { Badge, ErrorBox, StageTrack } from "../components.jsx";
import usePolling from "../usePolling.js";
import ResearchPanel from "./ResearchPanel.jsx";
import ScriptReview from "./ScriptReview.jsx";
import VideoPage from "./VideoPage.jsx";

// One episode. Which view shows depends on where the episode is:
//   waiting for script review -> script page (can also be opened afterwards)
//   waiting for video review / done -> video page
//   running / failed -> progress
export default function EpisodePage({ id }) {
  // Poll faster while the backend is working, slower once it is waiting for us.
  const [fast, setFast] = useState(true);
  const { data: ep, error, reload } = usePolling(() => getEpisode(id), [id], fast ? 3000 : 6000);
  const [tab, setTab] = useState(null); // null = automatic
  const [retryError, setRetryError] = useState("");

  if (error && !ep) return <ErrorBox message={error} />;
  if (!ep) return <p className="muted">Loading...</p>;

  const working = ep.status === "running";
  if (fast !== working) setFast(working);

  const hasVideo = ep.assets.some((a) => a.kind === "final_video");
  const hasScript = !!ep.script;
  const hasResearch = ep.research.queries.length > 0 || !!ep.research.notes;
  const auto = ep.status === "waiting_script_review" ? "script" : hasVideo ? "video" : hasScript ? "script" : "progress";
  const view = tab || auto;

  async function doRetry() {
    setRetryError("");
    try {
      await retry(id);
      reload();
    } catch (e) {
      setRetryError(e.message);
    }
  }

  return (
    <>
      <a href="#/" className="back">
        &larr; All episodes
      </a>
      <div className="episode-head">
        <h1>{ep.topic}</h1>
        <Badge status={ep.status} />
      </div>
      <StageTrack stage={ep.stage} status={ep.status} />
      <ErrorBox message={error} />

      {ep.status === "failed" && (
        <div className="card danger">
          <h3>This episode hit an error</h3>
          <pre className="errtext">{ep.error || "Unknown error"}</pre>
          <button className="btn warm" onClick={doRetry}>
            Retry from where it stopped
          </button>
          <ErrorBox message={retryError} />
        </div>
      )}

      {(hasScript || hasVideo || hasResearch) && (
        <nav className="tabs">
          {hasResearch && (
            <button className={view === "research" ? "on" : ""} onClick={() => setTab("research")}>
              Research
            </button>
          )}
          {hasScript && (
            <button className={view === "script" ? "on" : ""} onClick={() => setTab("script")}>
              Script
            </button>
          )}
          {hasVideo && (
            <button className={view === "video" ? "on" : ""} onClick={() => setTab("video")}>
              Video
            </button>
          )}
        </nav>
      )}

      {view === "research" && <ResearchPanel research={ep.research} working={working} />}
      {view === "script" && <ScriptReview ep={ep} onChanged={reload} />}
      {view === "video" && <VideoPage ep={ep} onChanged={reload} />}
      {view === "progress" && working && hasResearch && <ResearchPanel research={ep.research} working={working} />}
      {view === "progress" && working && (
        <div className="card">
          <p>
            <span className="spinner" /> The pipeline is working. This page refreshes by itself.
          </p>
        </div>
      )}
      {working && view !== "progress" && (
        <p className="muted">
          <span className="spinner" /> Working on the next step...
        </p>
      )}
    </>
  );
}
