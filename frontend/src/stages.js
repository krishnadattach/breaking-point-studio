// The 8 graph nodes in order, with friendly names for the dashboard.
export const STAGES = [
  { key: "research", label: "Research" },
  { key: "write_script", label: "Write script" },
  { key: "fact_check", label: "Fact check" },
  { key: "review_script", label: "Script review" },
  { key: "voiceover", label: "Voiceover" },
  { key: "render", label: "Render" },
  { key: "assemble", label: "Assemble" },
  { key: "review_video", label: "Video review" },
];

// "done" is not a graph node, but the backend stores it as the final stage.
export const stageLabel = (key) =>
  key === "done" ? "Done" : STAGES.find((s) => s.key === key)?.label || key;

export const STATUS_LABEL = {
  running: "Working",
  waiting_script_review: "Needs script review",
  waiting_video_review: "Needs video review",
  done: "Done",
  failed: "Failed",
};

// Which badge colour to use for a status.
export const statusTone = (status) =>
  status === "done" ? "good" : status === "failed" ? "bad" : status?.startsWith("waiting") ? "warm" : "cool";

// Which page should an episode open on?
export const needsAction = (status) => status?.startsWith("waiting");
