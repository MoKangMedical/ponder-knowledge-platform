import formidable from "formidable";
import { appendFileSource, getBootstrapPayload, json } from "../_lib/workspace";

export const config = {
  api: {
    bodyParser: false
  }
};

export default async function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return json(res, 405, { error: "Method not allowed" });
  }

  const form = formidable({
    multiples: false,
    keepExtensions: true
  });

  const { files } = await form.parse(req);
  const rawFile = Array.isArray(files.file) ? files.file[0] : files.file;

  if (!rawFile) {
    return json(res, 400, { error: "file is required" });
  }

  const content = rawFile.originalFilename
    ? `Uploaded file ${rawFile.originalFilename}. Vercel preview keeps a text summary rather than persistent binary storage.`
    : "Uploaded file";

  const workspace = appendFileSource({
    filename: rawFile.originalFilename || "upload.bin",
    mimetype: rawFile.mimetype || undefined,
    content
  });

  return json(res, 200, {
    ok: true,
    workspace,
    reportMarkdown: getBootstrapPayload().reportMarkdown
  });
}
