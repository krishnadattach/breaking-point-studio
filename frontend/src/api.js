// All talking to the backend lives here, so the pages stay simple.
export const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function call(path, options) {
  const res = await fetch(API + path, options);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

const post = (path, body) =>
  call(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

export const listEpisodes = () => call("/episodes");
export const getEpisode = (id) => call(`/episodes/${id}`);
export const createEpisode = (topic) => post("/episodes", { topic });
export const approve = (id) => post(`/episodes/${id}/approve`);
export const sendNotes = (id, notes) => post(`/episodes/${id}/reject`, { notes });
export const retry = (id) => post(`/episodes/${id}/retry`);
export const videoUrl = (id) => `${API}/episodes/${id}/video`;
