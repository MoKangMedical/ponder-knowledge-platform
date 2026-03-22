import { basename } from "node:path";
import { createSource, inferTags, summarizeText, type Source } from "@ponder/shared";

function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function extractTitle(html: string, url: string): string {
  const titleMatch = html.match(/<title>([\s\S]*?)<\/title>/i);
  if (titleMatch?.[1]) {
    return titleMatch[1].trim();
  }

  try {
    return new URL(url).hostname;
  } catch {
    return "Imported URL";
  }
}

export async function ingestUrl(url: string): Promise<Source> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Unable to fetch URL: ${response.status}`);
  }

  const html = await response.text();
  const title = extractTitle(html, url);
  const content = stripHtml(html);

  return createSource({
    title,
    content,
    type: "web",
    url,
    tags: inferTags(content, title)
  });
}

export async function ingestText(input: {
  title: string;
  content: string;
  type: "note" | "web" | "youtube" | "pdf" | "file";
  tags?: string[];
}): Promise<Source> {
  return createSource({
    title: input.title,
    content: input.content,
    type: input.type,
    tags: input.tags
  });
}

export async function ingestFile(input: {
  filename: string;
  mimetype: string;
  buffer: Buffer;
}): Promise<Source> {
  const { filename, mimetype, buffer } = input;
  const isTextLike =
    mimetype.startsWith("text/") ||
    mimetype.includes("json") ||
    /\.(md|txt|json|csv)$/i.test(filename);
  const isPdf = mimetype.includes("pdf") || /\.pdf$/i.test(filename);

  let content: string;
  if (isTextLike) {
    content = buffer.toString("utf8");
  } else if (isPdf) {
    content = [
      `Uploaded PDF: ${filename}`,
      "当前版本已接受该文件并记录元数据，但尚未接入真正的 PDF 解析/OCR worker。",
      "下一步建议接入 pdf-parse 或专门文档解析服务。"
    ].join("\n");
  } else {
    content = [
      `Uploaded file: ${filename}`,
      `Detected content-type: ${mimetype || "unknown"}`,
      "当前版本已保存文件入口，但尚未解析该二进制格式。"
    ].join("\n");
  }

  return createSource({
    title: basename(filename),
    content,
    type: isPdf ? "pdf" : "file",
    tags: inferTags(`${filename} ${summarizeText(content, 200)}`, filename)
  });
}
