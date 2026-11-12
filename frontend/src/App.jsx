import { useEffect, useState } from "react";
import EpisodeList from "./pages/EpisodeList.jsx";
import EpisodePage from "./pages/EpisodePage.jsx";

// Tiny "router": the page is chosen by the part of the URL after the #.
//   #/            -> list of episodes + new-episode form
//   #/ep/<id>     -> one episode (script review / video / progress)
function useHash() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const hash = useHash();
  const match = hash.match(/^#\/ep\/([\w-]+)/);

  return (
    <div className="app">
      <header className="topbar">
        <a href="#/" className="brand">
          <span className="brand-dot" />
          Breaking <b>Point</b> Studio
        </a>
        <span className="tagline">10 levels. One object. Until it fails.</span>
      </header>
      <main>{match ? <EpisodePage id={match[1]} /> : <EpisodeList />}</main>
    </div>
  );
}
