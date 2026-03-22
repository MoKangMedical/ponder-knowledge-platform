import {
  buildReportMarkdown,
  createSource,
  createWorkspaceSnapshot,
  demoSources,
  refreshWorkspaceState,
  type WorkspaceState
} from "@ponder/shared";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export type BrowserStorageMode = "supabase" | "local";

export const storageKey = "ponder-platform-workspace-v1";
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const supabaseWorkspaceId = import.meta.env.VITE_SUPABASE_WORKSPACE_ID || "main";

let supabaseClient: SupabaseClient | null = null;

export function getSeedWorkspace(): WorkspaceState {
  return createWorkspaceSnapshot(
    demoSources.map((source) =>
      createSource({
        ...source,
        id: source.id,
        createdAt: source.createdAt,
        tags: source.tags
      })
    )
  );
}

export function isSupabaseConfigured(): boolean {
  return Boolean(supabaseUrl && supabaseAnonKey);
}

function getSupabaseClient(): SupabaseClient {
  if (!supabaseClient) {
    supabaseClient = createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false
      }
    });
  }

  return supabaseClient;
}

export function loadLocalWorkspace(): WorkspaceState {
  if (typeof window === "undefined") {
    return getSeedWorkspace();
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      const seeded = getSeedWorkspace();
      saveLocalWorkspace(seeded);
      return seeded;
    }

    return refreshWorkspaceState(JSON.parse(raw) as WorkspaceState);
  } catch {
    return getSeedWorkspace();
  }
}

export function saveLocalWorkspace(workspace: WorkspaceState) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(storageKey, JSON.stringify(refreshWorkspaceState(workspace)));
  }
}

export async function loadSupabaseWorkspace(): Promise<WorkspaceState> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("workspace_snapshots")
    .select("workspace")
    .eq("workspace_id", supabaseWorkspaceId)
    .maybeSingle();

  if (error) {
    throw error;
  }

  if (!data?.workspace) {
    const seeded = getSeedWorkspace();
    await saveSupabaseWorkspace(seeded);
    return seeded;
  }

  return refreshWorkspaceState(data.workspace as WorkspaceState);
}

export async function saveSupabaseWorkspace(workspace: WorkspaceState): Promise<WorkspaceState> {
  const supabase = getSupabaseClient();
  const refreshed = refreshWorkspaceState(workspace);
  const { error } = await supabase.from("workspace_snapshots").upsert(
    {
      workspace_id: supabaseWorkspaceId,
      name: "Main Workspace",
      workspace: refreshed
    },
    {
      onConflict: "workspace_id"
    }
  );

  if (error) {
    throw error;
  }

  return refreshed;
}

export async function loadBrowserWorkspace(): Promise<{
  mode: BrowserStorageMode;
  workspace: WorkspaceState;
  reportMarkdown: string;
}> {
  if (isSupabaseConfigured()) {
    try {
      const workspace = await loadSupabaseWorkspace();
      return {
        mode: "supabase",
        workspace,
        reportMarkdown: buildReportMarkdown(workspace)
      };
    } catch {
      // Fallback to local storage if Supabase credentials are set but inaccessible.
    }
  }

  const workspace = loadLocalWorkspace();
  return {
    mode: "local",
    workspace,
    reportMarkdown: buildReportMarkdown(workspace)
  };
}

export async function persistBrowserWorkspace(
  mode: BrowserStorageMode,
  workspace: WorkspaceState
): Promise<WorkspaceState> {
  if (mode === "supabase") {
    return saveSupabaseWorkspace(workspace);
  }

  saveLocalWorkspace(workspace);
  return refreshWorkspaceState(workspace);
}
