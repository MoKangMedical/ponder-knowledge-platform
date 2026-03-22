import { json, refreshInsights } from "../_lib/workspace";

export default function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return json(res, 405, { error: "Method not allowed" });
  }

  return json(res, 200, {
    ok: true,
    workspace: refreshInsights()
  });
}
