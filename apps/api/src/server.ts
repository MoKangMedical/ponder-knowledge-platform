import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import Fastify from "fastify";
import cors from "@fastify/cors";
import multipart from "@fastify/multipart";
import fastifyStatic from "@fastify/static";
import {
  buildAnswer,
  buildReportMarkdown,
  refreshWorkspaceState,
  type AskRequest,
  type IntakeTextPayload,
  type IntakeUrlPayload,
  type WorkspaceState
} from "@ponder/shared";
import { ingestFile, ingestText, ingestUrl } from "./ingest.js";
import { appendSource, loadWorkspace, saveWorkspace } from "./storage.js";

const app = Fastify({
  logger: true,
  bodyLimit: Number(process.env.MAX_UPLOAD_BYTES ?? 10 * 1024 * 1024)
});
const repoRoot = resolve(process.cwd(), "../..");

await app.register(cors, {
  origin: true
});

await app.register(multipart);

let state: WorkspaceState = await loadWorkspace();

app.get("/health", async () => {
  return {
    ok: true,
    service: "ponder-platform",
    timestamp: new Date().toISOString()
  };
});

app.get("/api/bootstrap", async () => {
  state = refreshWorkspaceState(await loadWorkspace());
  return {
    workspace: state,
    reportMarkdown: buildReportMarkdown(state)
  };
});

app.get("/api/workspace", async () => {
  state = refreshWorkspaceState(await loadWorkspace());
  return state;
});

app.post<{ Body: IntakeTextPayload }>("/api/intake/text", async (request, reply) => {
  const { title, content, type, tags } = request.body;

  if (!title || !content || !type) {
    return reply.code(400).send({
      error: "title, content and type are required"
    });
  }

  const source = await ingestText({ title, content, type, tags });
  state = await appendSource(source);

  return {
    ok: true,
    source,
    workspace: state
  };
});

app.post<{ Body: IntakeUrlPayload }>("/api/intake/url", async (request, reply) => {
  const { url } = request.body;

  if (!url) {
    return reply.code(400).send({ error: "url is required" });
  }

  try {
    const source = await ingestUrl(url);
    state = await appendSource(source);

    return {
      ok: true,
      source,
      workspace: state
    };
  } catch (error) {
    return reply.code(400).send({
      error: error instanceof Error ? error.message : "Failed to ingest URL"
    });
  }
});

app.post("/api/intake/file", async (request, reply) => {
  const file = await request.file();

  if (!file) {
    return reply.code(400).send({ error: "file is required" });
  }

  const buffer = await file.toBuffer();
  const source = await ingestFile({
    filename: file.filename,
    mimetype: file.mimetype,
    buffer
  });
  state = await appendSource(source);

  return {
    ok: true,
    source,
    workspace: state
  };
});

app.post<{ Body: AskRequest }>("/api/ask", async (request, reply) => {
  const { question } = request.body;

  if (!question) {
    return reply.code(400).send({ error: "question is required" });
  }

  state = refreshWorkspaceState(await loadWorkspace());
  return buildAnswer(question, state.sources);
});

app.post("/api/insights/refresh", async () => {
  state = refreshWorkspaceState(await loadWorkspace());
  await saveWorkspace(state);

  return {
    ok: true,
    workspace: state
  };
});

app.post("/api/export/report", async () => {
  state = refreshWorkspaceState(await loadWorkspace());
  return {
    markdown: buildReportMarkdown(state)
  };
});

const webDist = resolve(repoRoot, "apps/web/dist");
const webAssets = resolve(webDist, "assets");
const webIndex = resolve(webDist, "index.html");

if (existsSync(webDist)) {
  await app.register(fastifyStatic, {
    root: webAssets,
    prefix: "/assets/"
  });

  app.get("/", async (_request, reply) => {
    return reply.type("text/html").send(await readFile(webIndex, "utf8"));
  });

  app.setNotFoundHandler(async (request, reply) => {
    if (request.raw.url?.startsWith("/api/")) {
      return reply.code(404).send({ error: "API route not found" });
    }

    return reply.type("text/html").send(await readFile(webIndex, "utf8"));
  });
}

const port = Number(process.env.PORT ?? 4000);
await app.listen({
  host: "0.0.0.0",
  port
});
