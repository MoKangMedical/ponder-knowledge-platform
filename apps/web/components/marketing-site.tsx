const highlights = [
  {
    label: "Evidence-first",
    title: "引用式问答，不是裸答案",
    body: "每次回答都绑定来源、定位和后续动作，避免“像是对，但没有证据”的研究幻觉。"
  },
  {
    label: "Chinese-native",
    title: "面向中文资料与复杂项目决策",
    body: "不是把通用聊天界面套上中文壳，而是把资料导入、洞察整理和报告产出打成连续流程。"
  },
  {
    label: "Deployable",
    title: "既能公开演示，也能走正式部署",
    body: "GitHub Pages 用于展示，Vercel / Render / Supabase 用于真正在线运行与持久化。"
  }
];

const capabilityRows = [
  {
    name: "资料导入",
    now: "文本、URL、文件入口",
    next: "PDF / OCR / ASR 管线，结构化抽取"
  },
  {
    name: "证据回答",
    now: "规则驱动引用式问答",
    next: "RAG + LLM + 证据强度评分"
  },
  {
    name: "知识组织",
    now: "洞察卡 + 节点工作区",
    next: "团队协作、任务化跟进、版本对比"
  },
  {
    name: "部署能力",
    now: "本地 API、Vercel 静态、GitHub Pages",
    next: "多租户、权限、云端文件存储"
  }
];

const launchModes = [
  {
    title: "公开展示",
    detail: "GitHub Pages 已上线，适合产品演示、能力说明和外部访问。",
    note: "无需登录，默认运行在浏览器本地工作区。"
  },
  {
    title: "正式试跑",
    detail: "Vercel 静态站可接 Supabase 与 Blob，适合云端持久化验证。",
    note: "适合做在线 Demo、团队内灰度和演示链接。"
  },
  {
    title: "本地全栈",
    detail: "Fastify API + React 工作台可本地跑通完整 intake / ask / export 流程。",
    note: "适合研发、调试、补齐后端能力。"
  }
];

const productSignals = [
  "更强的中文语义处理",
  "证据强度与可信度分层",
  "行业模板与洞察工作流",
  "可部署、可私有化、可团队协作"
];

type MarketingSiteProps = {
  onLaunchWorkspace: () => void;
};

export function MarketingSite({ onLaunchWorkspace }: MarketingSiteProps) {
  return (
    <main className="marketing-shell">
      <section className="marketing-hero">
        <div className="hero-topline">
          <span>Public Product Demo</span>
          <span>GitHub Pages Live</span>
          <span>Deployable Research OS</span>
        </div>

        <div className="marketing-hero-grid">
          <div className="marketing-copy">
            <p className="marketing-kicker">Ponder 对标平台 / Public Showcase</p>
            <h1>把资料、证据、洞察和行动，压进一个能公开展示也能继续扩成产品的平台。</h1>
            <p className="marketing-lead">
              这不是一张“功能列表”网页，而是一套可运行的研究工作台。公开页负责讲清产品，
              交互页负责展示能力，后续还能继续接入 RAG、云端持久化和团队协作。
            </p>

            <div className="hero-actions">
              <button className="hero-primary" onClick={onLaunchWorkspace}>
                进入交互工作台
              </button>
              <a
                className="hero-secondary"
                href="https://github.com/MoKangMedical/ponder-knowledge-platform"
                target="_blank"
                rel="noreferrer"
              >
                查看 GitHub 仓库
              </a>
            </div>

            <div className="hero-signal-row">
              {productSignals.map((signal) => (
                <span className="signal-pill" key={signal}>
                  {signal}
                </span>
              ))}
            </div>
          </div>

          <div className="hero-stage">
            <div className="stage-window">
              <div className="window-chrome">
                <span />
                <span />
                <span />
              </div>
              <div className="stage-grid">
                <article className="stage-card stage-card-main">
                  <p>Strategy Prompt</p>
                  <strong>比 Ponder 更强，先补哪三个能力？</strong>
                  <ul>
                    <li>证据强度分层</li>
                    <li>中文资料 Intake 管线</li>
                    <li>从洞察到行动的项目闭环</li>
                  </ul>
                </article>
                <article className="stage-card stage-card-evidence">
                  <p>Evidence Graph</p>
                  <strong>12 条来源 / 4 个洞察 / 8 个节点</strong>
                </article>
                <article className="stage-card stage-card-report">
                  <p>Export</p>
                  <strong>Markdown 战略报告可直接导出</strong>
                </article>
                <article className="stage-card stage-card-mode">
                  <p>Runtime</p>
                  <strong>Pages 展示 / Vercel 试跑 / Full-stack 本地研发</strong>
                </article>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="marketing-strip">
        {highlights.map((item) => (
          <article className="strip-card" key={item.title}>
            <span>{item.label}</span>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
          </article>
        ))}
      </section>

      <section className="marketing-section">
        <div className="section-heading">
          <p className="section-kicker">Why This Exists</p>
          <h2>目标不是复刻一个聊天框，而是把知识工作流变成操作系统。</h2>
        </div>

        <div className="capability-table">
          {capabilityRows.map((row) => (
            <article className="capability-row" key={row.name}>
              <div>
                <span className="capability-label">模块</span>
                <strong>{row.name}</strong>
              </div>
              <div>
                <span className="capability-label">当前已做</span>
                <p>{row.now}</p>
              </div>
              <div>
                <span className="capability-label">超越路径</span>
                <p>{row.next}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section launch-section">
        <div className="section-heading">
          <p className="section-kicker">Demo Access</p>
          <h2>公开演示、云端试跑和本地研发，已经分层准备好。</h2>
        </div>

        <div className="launch-grid">
          {launchModes.map((mode) => (
            <article className="launch-card" key={mode.title}>
              <strong>{mode.title}</strong>
              <p>{mode.detail}</p>
              <span>{mode.note}</span>
            </article>
          ))}
        </div>

        <div className="demo-note">
          <strong>演示账号说明</strong>
          <p>
            当前公开站点无需登录，不存在固定 Demo 账号。GitHub Pages 会以浏览器本地工作区模式运行；
            配置 Supabase 后可切到云端持久化。
          </p>
        </div>
      </section>

      <section className="marketing-cta">
        <div>
          <p className="section-kicker">Launch The Product</p>
          <h2>如果你是外部访客，先看公开页；如果你要验证能力，直接进入工作台。</h2>
        </div>
        <div className="cta-actions">
          <button className="hero-primary" onClick={onLaunchWorkspace}>
            打开交互式演示
          </button>
          <a
            className="hero-secondary"
            href="https://mokangmedical.github.io/ponder-knowledge-platform/"
            target="_blank"
            rel="noreferrer"
          >
            复制公开地址
          </a>
        </div>
      </section>
    </main>
  );
}
