export type SourceType = "pdf" | "web" | "youtube" | "note" | "file";

export type Citation = {
  sourceId: string;
  label: string;
  excerpt: string;
  locator: string;
};

export type Source = {
  id: string;
  type: SourceType;
  title: string;
  summary: string;
  content: string;
  url?: string;
  createdAt: string;
  tags: string[];
  citations: Citation[];
};

export type WorkspaceNodeKind = "claim" | "evidence" | "opportunity" | "risk";

export type WorkspaceNode = {
  id: string;
  kind: WorkspaceNodeKind;
  title: string;
  summary: string;
  linkedSourceIds: string[];
};

export type InsightCard = {
  id: string;
  title: string;
  body: string;
  tone: "signal" | "warning" | "opportunity";
};

export type WorkspaceMetrics = {
  totalSources: number;
  totalClaims: number;
  totalNodes: number;
  totalInsights: number;
  lastUpdatedAt: string;
};

export type WorkspaceState = {
  sources: Source[];
  nodes: WorkspaceNode[];
  insights: InsightCard[];
  metrics: WorkspaceMetrics;
};

export type IntakeTextPayload = {
  title: string;
  content: string;
  type: SourceType;
  tags?: string[];
};

export type IntakeUrlPayload = {
  url: string;
};

export type AskRequest = {
  question: string;
};

export type AnswerResponse = {
  answer: string;
  followUp: string[];
  citations: Citation[];
};

export const demoSources: Source[] = [
  {
    id: "source-ponder-home",
    type: "web",
    title: "Ponder 官网定位",
    summary: "定位为 AI research workspace，强调多源知识组织和研究辅助。",
    content:
      "Ponder 的公开页面强调 AI research workspace、knowledge workspace、多源导入、研究综述、知识图谱和团队协作。",
    createdAt: "2026-03-22T00:00:00.000Z",
    tags: ["positioning", "research-workspace", "public-source"],
    citations: [
      {
        sourceId: "source-ponder-home",
        label: "Ponder 官网定位",
        excerpt: "Ponder 的公开页面强调 AI research workspace、knowledge workspace。",
        locator: "Homepage"
      }
    ]
  },
  {
    id: "source-arch-notes",
    type: "note",
    title: "我方系统架构笔记",
    summary: "MVP 先做多源导入、引用式问答、节点式工作区和导出。",
    content:
      "MVP 不应该先做复杂图数据库。优先能力是多源导入、可引用问答、工作区节点组织、Markdown 导出。后续再做图谱和团队协作。",
    createdAt: "2026-03-22T00:00:00.000Z",
    tags: ["architecture", "mvp", "product-strategy"],
    citations: [
      {
        sourceId: "source-arch-notes",
        label: "我方系统架构笔记",
        excerpt: "MVP 不应该先做复杂图数据库。优先能力是多源导入、可引用问答。",
        locator: "Architecture Notes"
      }
    ]
  },
  {
    id: "source-market-gap",
    type: "note",
    title: "差异化机会",
    summary: "中文证据链、行业模板、持续更新能力是更强方向。",
    content:
      "要比竞品更强，优先做中文资料处理、证据强度展示、垂直行业模板和知识刷新能力。",
    createdAt: "2026-03-22T00:00:00.000Z",
    tags: ["differentiation", "china-market", "advantage"],
    citations: [
      {
        sourceId: "source-market-gap",
        label: "差异化机会",
        excerpt: "优先做中文资料处理、证据强度展示、垂直行业模板和知识刷新能力。",
        locator: "Strategy Memo"
      }
    ]
  }
];

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

export function summarizeText(content: string, max = 120): string {
  const normalized = content.replace(/\s+/g, " ").trim();
  return normalized.length > max ? `${normalized.slice(0, max).trim()}...` : normalized;
}

export function inferTags(content: string, title: string): string[] {
  const corpus = `${title} ${content}`.toLowerCase();
  const mapping: Array<[string, string[]]> = [
    ["research", ["research", "literature", "paper", "综述", "研究"]],
    ["knowledge-graph", ["graph", "knowledge", "知识图谱", "canvas"]],
    ["agent", ["agent", "workflow", "automation", "自动化"]],
    ["china-market", ["中文", "china", "wechat", "feishu", "企业"]],
    ["deployment", ["deploy", "render", "vercel", "github", "上线"]],
    ["evidence", ["citation", "evidence", "证据", "引用"]]
  ];

  const matched = mapping
    .filter(([, words]) => words.some((word) => corpus.includes(word)))
    .map(([tag]) => tag);

  return matched.length > 0 ? matched : ["general"];
}

export function createSource(input: {
  id?: string;
  title: string;
  content: string;
  type: SourceType;
  url?: string;
  tags?: string[];
  createdAt?: string;
}): Source {
  const id = input.id ?? `${input.type}-${slugify(input.title)}-${Date.now()}`;
  const summary = summarizeText(input.content);
  const tags = input.tags && input.tags.length > 0 ? input.tags : inferTags(input.content, input.title);

  return {
    id,
    type: input.type,
    title: input.title,
    summary,
    content: input.content,
    url: input.url,
    createdAt: input.createdAt ?? new Date().toISOString(),
    tags,
    citations: [
      {
        sourceId: id,
        label: input.title,
        excerpt: summarizeText(input.content, 180),
        locator: input.url ? input.url : "Workspace Source"
      }
    ]
  };
}

export function buildInsights(sources: Source[]): InsightCard[] {
  const hasChina = sources.some((source) => source.tags.includes("china-market"));
  const hasEvidence = sources.some((source) => source.tags.includes("evidence"));
  const hasAgent = sources.some((source) => source.tags.includes("agent"));

  return [
    {
      id: "insight-core-loop",
      title: "核心闭环",
      body:
        "平台最应该守住的不是单轮对话，而是来源摄取、证据绑定、节点沉淀和报告输出这条闭环。",
      tone: "signal"
    },
    {
      id: "insight-market-gap",
      title: hasChina ? "中文优势被确认" : "中文优势待放大",
      body: hasChina
        ? "来源中已经明显指向中文资料处理和行业模板，这是超越海外竞品最直接的楔子。"
        : "当前资料还不够强调中文资料处理，建议补充飞书、公众号、会议纪要等中文场景。 ",
      tone: "opportunity"
    },
    {
      id: "insight-grounding",
      title: hasEvidence ? "证据链是卖点" : "证据链是风险",
      body: hasEvidence
        ? "公开资料持续强调来源可追溯，平台必须把引用、定位、证据强度做成默认能力。"
        : "如果回答没有来源回链，产品会退化成普通聊天工具，价值很快被稀释。",
      tone: hasEvidence ? "signal" : "warning"
    },
    {
      id: "insight-agent",
      title: hasAgent ? "Agent 化机会" : "Agent 层待补",
      body: hasAgent
        ? "下一阶段可以把洞察生成、研究计划、资料缺口发现做成多步 agent 工作流。"
        : "先补充 agent 工作流设计，否则平台还停留在资料管理层。",
      tone: "opportunity"
    }
  ];
}

export function generateWorkspaceNodesFromSource(source: Source): WorkspaceNode[] {
  return [
    {
      id: `${source.id}-claim`,
      kind: "claim",
      title: source.title,
      summary: source.summary,
      linkedSourceIds: [source.id]
    },
    {
      id: `${source.id}-evidence`,
      kind: "evidence",
      title: `${source.title} / evidence`,
      summary: summarizeText(source.content, 150),
      linkedSourceIds: [source.id]
    },
    {
      id: `${source.id}-opportunity`,
      kind: "opportunity",
      title: `${source.title} / opportunity`,
      summary: `从 ${source.title} 延展出的可执行机会：${source.tags.join(" / ")}`,
      linkedSourceIds: [source.id]
    }
  ];
}

export function computeWorkspaceMetrics(
  sources: Source[],
  nodes: WorkspaceNode[],
  insights: InsightCard[]
): WorkspaceMetrics {
  return {
    totalSources: sources.length,
    totalClaims: nodes.filter((node) => node.kind === "claim").length,
    totalNodes: nodes.length,
    totalInsights: insights.length,
    lastUpdatedAt: new Date().toISOString()
  };
}

export function createWorkspaceSnapshot(sources: Source[]): WorkspaceState {
  const nodes = sources.flatMap(generateWorkspaceNodesFromSource);
  const insights = buildInsights(sources);

  return {
    sources: [...sources],
    nodes,
    insights,
    metrics: computeWorkspaceMetrics(sources, nodes, insights)
  };
}

export function refreshWorkspaceState(current: WorkspaceState): WorkspaceState {
  const nodes = current.sources.flatMap(generateWorkspaceNodesFromSource);
  const insights = buildInsights(current.sources);

  return {
    sources: current.sources,
    nodes,
    insights,
    metrics: computeWorkspaceMetrics(current.sources, nodes, insights)
  };
}

export function extractKeywords(question: string): string[] {
  return question
    .toLowerCase()
    .split(/[\s，。、“”‘’：:;,.!?！？/]+/)
    .filter((part) => part.length > 1);
}

export function buildAnswer(question: string, sources: Source[]): AnswerResponse {
  const keywords = extractKeywords(question);
  const matchedSources = sources.filter((source) => {
    const haystack = `${source.title} ${source.summary} ${source.content} ${source.tags.join(" ")}`.toLowerCase();
    return keywords.some((keyword) => haystack.includes(keyword));
  });

  const selected = matchedSources.length > 0 ? matchedSources.slice(0, 4) : sources.slice(0, 3);
  const citations = selected.flatMap((source) => source.citations).slice(0, 4);
  const topicLine =
    selected.length > 0
      ? `当前问题主要命中了 ${selected.map((source) => `《${source.title}》`).join("、")} 这些来源。`
      : "当前没有明显命中的来源，因此使用了工作区里最核心的基础资料。";

  return {
    answer: [
      topicLine,
      "从当前资料看，这个平台应该把价值锚点放在“可追溯的知识生产”而不是“更像聊天”。",
      "如果要超越对标产品，优先增强中文资料摄取、证据强度展示、垂直行业模板以及持续刷新能力。"
    ].join(" "),
    followUp: [
      "补一条真实 URL intake 流程并验证摘要质量。",
      "把问答结果沉淀到数据库，而不是只停留在前端状态里。",
      "增加研究缺口发现和任务建议生成。"
    ],
    citations
  };
}

export function buildReportMarkdown(workspace: WorkspaceState): string {
  const sourceLines = workspace.sources
    .slice(0, 6)
    .map((source) => `- ${source.title}: ${source.summary}`)
    .join("\n");

  const insightLines = workspace.insights.map((insight) => `- ${insight.title}: ${insight.body}`).join("\n");

  return [
    "# 战略研究报告",
    "",
    "## 当前判断",
    "应优先构建一个以证据为底座的知识工作台，用来源、节点、洞察和输出构成完整闭环。",
    "",
    "## 本期关键来源",
    sourceLines,
    "",
    "## 关键洞察",
    insightLines,
    "",
    "## 下一步工程动作",
    "1. 接入真实 URL / 文件 intake。",
    "2. 增加数据库持久化和用户工作区。",
    "3. 接入检索增强生成与引用定位。",
    "4. 增加团队协作和行业模板。",
    "",
    `更新时间：${workspace.metrics.lastUpdatedAt}`
  ].join("\n");
}
