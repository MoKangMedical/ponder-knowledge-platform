import { handleUpload, type HandleUploadBody } from "@vercel/blob/client";

export default async function handler(req: any, res: any) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const body = req.body as HandleUploadBody;

  try {
    const jsonResponse = await handleUpload({
      body,
      request: req,
      onBeforeGenerateToken: async (pathname) => {
        return {
          allowedContentTypes: [
            "application/pdf",
            "text/plain",
            "text/markdown",
            "application/json",
            "image/png",
            "image/jpeg",
            "image/webp"
          ],
          addRandomSuffix: true,
          tokenPayload: JSON.stringify({
            pathname
          })
        };
      },
      onUploadCompleted: async ({ blob }) => {
        console.log("blob upload completed", blob.url);
      }
    });

    return res.status(200).json(jsonResponse);
  } catch (error) {
    return res.status(400).json({
      error: error instanceof Error ? error.message : "Blob upload failed"
    });
  }
}
