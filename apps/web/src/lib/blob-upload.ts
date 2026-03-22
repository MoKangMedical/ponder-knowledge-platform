import { upload } from "@vercel/blob/client";

export async function uploadFileToBlob(file: File): Promise<string | null> {
  try {
    const blob = await upload(`research-assets/${file.name}`, file, {
      access: "public",
      handleUploadUrl: "/api/blob/upload"
    });

    return blob.url;
  } catch {
    return null;
  }
}
