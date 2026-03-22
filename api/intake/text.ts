import { appendTextSource, getBootstrapPayload, json } from "../_lib/workspace";

export default function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return json(res, 405, { error: "Method not allowed" });
  }

  const { title, content, type, tags } = req.body ?? {};
  if (!title || !content || !type) {
    return json(res, 400, { error: "title, content and type are required" });
  }

  const workspace = appendTextSource({ title, content, type, tags });
  return json(res, 200, {
    ok: true,
    workspace,
    reportMarkdown: getBootstrapPayload().reportMarkdown
  });
}
