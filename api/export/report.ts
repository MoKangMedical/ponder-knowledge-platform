import { exportReport, json } from "../_lib/workspace";

export default function handler(_req: any, res: any) {
  return json(res, 200, {
    markdown: exportReport()
  });
}
