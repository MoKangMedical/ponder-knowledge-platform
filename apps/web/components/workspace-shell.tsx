import { useEffect, useMemo, useState } from "react";
import type { AnswerResponse, Source, WorkspaceState } from "@ponder/shared";

const apiBase =
  typeof window !== "undefined" && window.location.port === "3000"
    ? "http://localhost:4000"
    : "";

type BootstrapResponse = {
  workspace: WorkspaceState;
  reportMarkdown: string;
};

const defaultQuestion = "如果我要把这个平台做得比 Ponder 更强，最应该先补哪三个能力？";

export function WorkspaceShell() {
  const [workspace, setWorkspace] = useState<WorkspaceState | null>(null);
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [question, setQuestion] = useState(defaultQuestion);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [textTitle, setTextTitle] = useState("平台战略笔记");
  const [textType, setTextType] = useState<"note" | "web" | "youtube" | "pdf" | "file">("note");
  const [textContent, setTextContent] = useState(
    "我们的平台要把导入、证据、洞察、行动建议和团队共建做成一个闭环。"
  );
  const [urlValue, setUrlValue] = useState("https://ponder.ing/zh");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function loadWorkspace() {
    const res = await fetch(`${apiBase}/api/bootstrap`);
    const data = (await res.json()) as BootstrapResponse;
    setWorkspace(data.workspace);
    setReportMarkdown(data.reportMarkdown);
  }

  useEffect(() => {
    let ignore = false;

    async function bootstrap() {
      try {
        const res = await fetch(`${apiBase}/api/bootstrap`);
        const data = (await res.json()) as BootstrapResponse;
        if (!ignore) {
          setWorkspace(data.workspace);
          setReportMarkdown(data.reportMarkdown);
        }
      } catch {
        if (!ignore) {
          setError("无法连接平台 API。开发模式下请先执行 npm run dev。");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    bootstrap();
    return () => {
      ignore = true;
    };
  }, []);

  const metrics = useMemo(() => {
    if (!workspace) {
      return [];
    }

    return [
      { label: "Sources", value: String(workspace.metrics.totalSources).padStart(2, "0") },
      { label: "Claims", value: String(workspace.metrics.totalClaims).padStart(2, "0") },
      { label: "Nodes", value: String(workspace.metrics.totalNodes).padStart(2, "0") },
      { label: "Insights", value: String(workspace.metrics.totalInsights).padStart(2, "0") }
    ];
  }, [workspace]);

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await action();
    } catch {
      setError("请求执行失败，请检查服务状态或输入内容。");
    } finally {
      setBusy(false);
    }
  }

  async function handleAsk() {
    await withBusy(async () => {
      const res = await fetch(`${apiBase}/api/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ question })
      });
      const data = (await res.json()) as AnswerResponse;
      setAnswer(data);
    });
  }

  async function handleTextIngest() {
    await withBusy(async () => {
      await fetch(`${apiBase}/api/intake/text`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title: textTitle,
          content: textContent,
          type: textType
        })
      });
      await loadWorkspace();
      setSuccess("文本来源已加入工作区。");
    });
  }

  async function handleUrlIngest() {
    await withBusy(async () => {
      const res = await fetch(`${apiBase}/api/intake/url`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          url: urlValue
        })
      });
      if (!res.ok) {
        throw new Error("URL ingest failed");
      }
      await loadWorkspace();
      setSuccess("URL 来源已抓取并写入工作区。");
    });
  }

  async function handleFileIngest(file: File | null) {
    if (!file) {
      return;
    }

    await withBusy(async () => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${apiBase}/api/intake/file`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        throw new Error("file ingest failed");
      }
      await loadWorkspace();
      setSuccess(`文件 ${file.name} 已加入工作区。`);
    });
  }

  async function handleRefreshInsights() {
    await withBusy(async () => {
      await fetch(`${apiBase}/api/insights/refresh`, {
        method: "POST"
      });
      await loadWorkspace();
      setSuccess("洞察与节点已刷新。");
    });
  }

  function handleDownloadReport() {
    const blob = new Blob([reportMarkdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "strategy-report.md";
    link.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return <main className="loading-screen">Loading knowledge command center...</main>;
  }

  if (!workspace) {
    return <main className="loading-screen error-state">{error || "Workspace unavailable."}</main>;
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Knowledge Foundry / Deployable V1</p>
          <h1>一个能替代“散乱研究流程”的 AI 知识平台。</h1>
          <p className="hero-text">
            这版已经把来源库、引用式问答、洞察板、节点工作区和报告导出压成一个单服务平台，可直接放到
            GitHub 后接入 Render 上线。
          </p>
        </div>
        <div className="metric-row">
          {metrics.map((item) => (
            <div className="metric-card" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="command-strip">
        <button onClick={handleRefreshInsights} disabled={busy}>
          Refresh Insights
        </button>
        <button onClick={handleDownloadReport} disabled={!reportMarkdown}>
          Download Report
        </button>
        <div className="status-chip">{success || "Workspace ready for intake, ask, export."}</div>
      </section>

      <section className="grid top-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>Ingestion Studio</h2>
            <span>Text / URL / File</span>
          </div>
          <div className="subsection">
            <label>
              标题
              <input value={textTitle} onChange={(event) => setTextTitle(event.target.value)} />
            </label>
            <label>
              类型
              <select
                value={textType}
                onChange={(event) =>
                  setTextType(event.target.value as "note" | "web" | "youtube" | "pdf" | "file")
                }
              >
                <option value="note">Note</option>
                <option value="web">Web Summary</option>
                <option value="youtube">YouTube</option>
                <option value="pdf">PDF Note</option>
                <option value="file">File Memo</option>
              </select>
            </label>
            <label>
              内容
              <textarea
                rows={5}
                value={textContent}
                onChange={(event) => setTextContent(event.target.value)}
              />
            </label>
            <button onClick={handleTextIngest} disabled={busy}>
              加入文本来源
            </button>
          </div>

          <div className="subsection">
            <label>
              URL 导入
              <input value={urlValue} onChange={(event) => setUrlValue(event.target.value)} />
            </label>
            <button onClick={handleUrlIngest} disabled={busy}>
              抓取网页
            </button>
          </div>

          <div className="subsection">
            <label className="file-label">
              文件导入
              <input
                type="file"
                onChange={(event) => handleFileIngest(event.target.files?.[0] ?? null)}
              />
            </label>
            <p className="helper-text">当前支持文本类文件，PDF 会先以元数据形式进入工作区。</p>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Ask With Evidence</h2>
            <span>Grounded Answering</span>
          </div>
          <textarea
            rows={6}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button onClick={handleAsk} disabled={busy}>
            生成回答
          </button>
          {answer ? (
            <div className="answer-block">
              <p>{answer.answer}</p>
              <div className="followup-list">
                {answer.followUp.map((item) => (
                  <div className="followup-item" key={item}>
                    {item}
                  </div>
                ))}
              </div>
              <div className="citation-list">
                {answer.citations.map((citation) => (
                  <article className="citation-card" key={`${citation.sourceId}-${citation.locator}`}>
                    <strong>{citation.label}</strong>
                    <span>{citation.locator}</span>
                    <p>{citation.excerpt}</p>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="placeholder-text">提问后会返回回答、后续动作和引用来源。</div>
          )}
        </div>
      </section>

      <section className="grid lower-grid">
        <div className="panel">
          <div className="panel-head">
            <h2>Source Library</h2>
            <span>{workspace.sources.length} Active Sources</span>
          </div>
          <div className="source-list">
            {workspace.sources.map((source) => (
              <SourceCard key={source.id} source={source} />
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Insight Board</h2>
            <span>Beyond Simple Chat</span>
          </div>
          <div className="insight-list">
            {workspace.insights.map((insight) => (
              <article className={`insight-card tone-${insight.tone}`} key={insight.id}>
                <strong>{insight.title}</strong>
                <p>{insight.body}</p>
              </article>
            ))}
          </div>
          <div className="panel-head secondary-head">
            <h2>Knowledge Nodes</h2>
            <span>{workspace.nodes.length} Generated Nodes</span>
          </div>
          <div className="node-grid">
            {workspace.nodes.map((node) => (
              <article className={`node-card node-${node.kind}`} key={node.id}>
                <span>{node.kind}</span>
                <strong>{node.title}</strong>
                <p>{node.summary}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="panel report-panel">
        <div className="panel-head">
          <h2>Strategy Report</h2>
          <span>Markdown Export</span>
        </div>
        <pre>{reportMarkdown}</pre>
      </section>

      {error ? <div className="floating-error">{error}</div> : null}
    </main>
  );
}

function SourceCard({ source }: { source: Source }) {
  return (
    <article className="source-card">
      <div className="source-meta">
        <span>{source.type}</span>
        <time>{new Date(source.createdAt).toLocaleDateString("zh-CN")}</time>
      </div>
      <strong>{source.title}</strong>
      <p>{source.summary}</p>
      <div className="tag-row">
        {source.tags.map((tag) => (
          <span className="tag" key={tag}>
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}
