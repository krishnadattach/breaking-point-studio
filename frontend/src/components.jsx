import { STAGES, STATUS_LABEL, statusTone } from "./stages.js";

export function Badge({ status }) {
  return <span className={`badge ${statusTone(status)}`}>{STATUS_LABEL[status] || status}</span>;
}

export function ErrorBox({ message }) {
  return message ? <div className="error-box">{message}</div> : null;
}

// The row of 8 dots showing how far an episode has got.
export function StageTrack({ stage, status }) {
  const idx = STAGES.findIndex((s) => s.key === stage);
  return (
    <ol className="track">
      {STAGES.map((s, i) => {
        let cls = "";
        if (status === "done" || i < idx) cls = "past";
        else if (i === idx) cls = status === "failed" ? "fail" : status?.startsWith("waiting") ? "wait" : "now";
        return (
          <li key={s.key} className={cls}>
            <span className="dot" />
            <span className="lbl">{s.label}</span>
          </li>
        );
      })}
    </ol>
  );
}

// "2026-11-12T10:00:00" from MySQL -> readable local text
export function when(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return isNaN(d) ? String(ts) : d.toLocaleString();
}
