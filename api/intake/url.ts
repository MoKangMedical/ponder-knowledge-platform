import { appendUrlSource, getBootstrapPayload, json } from "../_lib/workspace";

export default async function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return json(res, 405, { error: "Method not allowed" });
  }

  const url = req.body?.url;
  if (!url) {
    return json(res, 400, { error: "url is required" });
  }

  try {
    const workspace = await appendUrlSource(url);
    return json(res, 200, {
      ok: true,
      workspace,
      reportMarkdown: getBootstrapPayload().reportMarkdown
    });
  } catch (error) {
    return json(res, 400, {
      error: error instanceof Error ? error.message : "Failed to ingest URL"
    });
  }
}
