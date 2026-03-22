import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import {
  createSource,
  createWorkspaceSnapshot,
  demoSources,
  refreshWorkspaceState,
  type Source,
  type WorkspaceState
} from "@ponder/shared";

const repoRoot = resolve(process.cwd(), "../..");
const storagePath = resolve(
  repoRoot,
  process.env.PONDER_STORAGE_PATH ?? "data/workspace.json"
);

async function ensureParentDirectory() {
  await mkdir(dirname(storagePath), { recursive: true });
}

export async function loadWorkspace(): Promise<WorkspaceState> {
  await ensureParentDirectory();

  try {
    const raw = await readFile(storagePath, "utf8");
    const parsed = JSON.parse(raw) as WorkspaceState;
    return refreshWorkspaceState(parsed);
  } catch {
    const seeded = createWorkspaceSnapshot(
      demoSources.map((source) =>
        createSource({
          ...source,
          id: source.id,
          createdAt: source.createdAt,
          tags: source.tags
        })
      )
    );
    await saveWorkspace(seeded);
    return seeded;
  }
}

export async function saveWorkspace(workspace: WorkspaceState): Promise<void> {
  await ensureParentDirectory();
  await writeFile(storagePath, JSON.stringify(refreshWorkspaceState(workspace), null, 2), "utf8");
}

export async function appendSource(source: Source): Promise<WorkspaceState> {
  const current = await loadWorkspace();
  const next = refreshWorkspaceState({
    ...current,
    sources: [source, ...current.sources]
  });
  await saveWorkspace(next);
  return next;
}
