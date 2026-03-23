import { useEffect, useState } from "react";
import { MarketingSite } from "../components/marketing-site";
import { WorkspaceShell } from "../components/workspace-shell";

export default function App() {
  const [view, setView] = useState<"landing" | "workspace">(() =>
    typeof window !== "undefined" && window.location.hash === "#workspace" ? "workspace" : "landing"
  );

  useEffect(() => {
    function syncView() {
      setView(window.location.hash === "#workspace" ? "workspace" : "landing");
    }

    window.addEventListener("hashchange", syncView);
    return () => {
      window.removeEventListener("hashchange", syncView);
    };
  }, []);

  function openWorkspace() {
    window.location.hash = "workspace";
  }

  function openLanding() {
    window.location.hash = "";
  }

  if (view === "workspace") {
    return <WorkspaceShell onBack={openLanding} />;
  }

  return <MarketingSite onLaunchWorkspace={openWorkspace} />;
}
