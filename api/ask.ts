import { answer, json } from "./_lib/workspace";

export default function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return json(res, 405, { error: "Method not allowed" });
  }

  const question = req.body?.question;
  if (!question) {
    return json(res, 400, { error: "question is required" });
  }

  return json(res, 200, answer(question));
}
