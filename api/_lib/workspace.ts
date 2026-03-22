import {
  buildAnswer,
  buildInsights,
  buildReportMarkdown,
  createSource,
  createWorkspaceSnapshot,
  demoSources,
  refreshWorkspaceState,
  type AnswerResponse,
  type IntakeTextPayload,
  type InsightCard,
  type Source,
  type WorkspaceNode,
  type WorkspaceState
} from "../../packages/shared/src/index";

type WorkspaceMemory = {
  workspace: WorkspaceState;
};

declare global {
  var __ponderWorkspaceMemory__: WorkspaceMemory | undefined;
}

function createSeedWorkspace(): WorkspaceState {
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

function getMemory(): WorkspaceMemory {
  if (!globalThis.__ponderWorkspaceMemory__) {
    globalThis.__ponderWorkspaceMemory__ = {
      workspace: createSeedWorkspace()
    };
  }

  return globalThis.__ponderWorkspaceMemory__;
}

export function getWorkspace(): WorkspaceState {
  const memory = getMemory();
  memory.workspace = refreshWorkspaceState(memory.workspace);
  return memory.workspace;
}

export function replaceWorkspace(workspace: WorkspaceState): WorkspaceState {
  const memory = getMemory();
  memory.workspace = refreshWorkspaceState(workspace);
  return memory.workspace;
}

export function appendSource(source: Source): WorkspaceState {
  const current = getWorkspace();
  return replaceWorkspace({
    ...current,
    sources: [source, ...current.sources]
  });
}

export function appendTextSource(input: IntakeTextPayload): WorkspaceState {
  const source = createSource({
    title: input.title,
    content: input.content,
    type: input.type,
    tags: input.tags
  });

  return appendSource(source);
}

export async function appendUrlSource(url: string): Promise<WorkspaceState> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Unable to fetch URL: ${response.status}`);
  }

  const html = await response.text();
  const titleMatch = html.match(/<title>([\s\S]*?)<\/title>/i);
  const title = titleMatch?.[1]?.trim() || url;
  const content = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();

  const source = createSource({
    title,
    content,
    type: "web",
    url
  });

  return appendSource(source);
}

export function appendFileSource(input: {
  filename: string;
  mimetype?: string;
  content: string;
}): WorkspaceState {
  const source = createSource({
    title: input.filename,
    content:
      input.content ||
      `Uploaded file ${input.filename}. Current preview deployment stores a text summary for this file.`,
    type: input.mimetype?.includes("pdf") || /\.pdf$/i.test(input.filename) ? "pdf" : "file"
  });

  return appendSource(source);
}

export function getBootstrapPayload(): {
  workspace: WorkspaceState;
  reportMarkdown: string;
} {
  const workspace = getWorkspace();
  return {
    workspace,
    reportMarkdown: buildReportMarkdown(workspace)
  };
}

export function answer(question: string): AnswerResponse {
  return buildAnswer(question, getWorkspace().sources);
}

export function refreshInsights(): WorkspaceState {
  const workspace = getWorkspace();
  const refreshed: WorkspaceState = {
    ...workspace,
    insights: buildInsights(workspace.sources),
    nodes: refreshWorkspaceState(workspace).nodes
  };

  return replaceWorkspace(refreshed);
}

export function exportReport(): string {
  return buildReportMarkdown(getWorkspace());
}

export function json(res: any, status: number, data: unknown) {
  res.status(status).setHeader("Content-Type", "application/json; charset=utf-8");
  res.send(JSON.stringify(data));
}

export function getWorkspaceSections(workspace: WorkspaceState): {
  sources: Source[];
  nodes: WorkspaceNode[];
  insights: InsightCard[];
} {
  return {
    sources: workspace.sources,
    nodes: workspace.nodes,
    insights: workspace.insights
  };
}
