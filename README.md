# Ponder 对标平台

这是一个可部署的全栈平台雏形，不再只是骨架。当前版本已经具备一个“知识工作台”应有的主流程：

- 文本、URL、文件三种来源导入
- 引用式问答
- 来源库与自动洞察板
- 节点式知识工作区
- Markdown 报告导出
- 单服务生产部署

## 目录

```text
apps/
  api/          # Fastify API，负责 intake / ask / export，并在生产环境托管前端
  web/          # Vite + React 前端工作台
packages/
  shared/       # 共享类型、示例数据、领域模型
```

## 本地运行

```bash
npm install
npm run dev
```

默认端口：

- Web: `http://localhost:3000`
- API: `http://localhost:4000`

## 生产运行

```bash
npm install
npm run build
npm start
```

生产模式下只需要打开：

- `http://localhost:4000`

## 已实现能力

- 手动文本来源导入
- URL 抓取导入
- 文件上传入口
- 来源标签推断
- 引用式回答与后续动作建议
- 洞察卡自动生成
- Markdown 研究报告导出
- JSON 文件持久化工作区
- Render 单服务部署支持

## 当前限制

- PDF 还未接入真正解析器，只先接入上传入口和占位内容。
- 当前存储为本地 JSON 文件，适合 demo 和早期验证，不适合正式多用户生产。
- 问答仍是规则驱动的 grounding 版本，下一步应接入真正的 RAG / LLM。
- 暂未实现登录、权限、多人协作。

## 下一步优先项

1. 把 `intake/file` 接入 PDF/OCR/ASR pipeline。
2. 用 PostgreSQL + pgvector 替换 JSON 文件存储。
3. 用 LLM + retrieval 重写 `ask` 和 `insight`。
4. 增加用户系统、团队协作和分享。

## GitHub 与 Render 上线

仓库已经准备好以下上线材料：

- [.env.example](/Users/linzhang/Desktop/%20%20%20%20%20%20OPC/Ponder对标平台/07-原型与代码/.env.example)
- [render.yaml](/Users/linzhang/Desktop/%20%20%20%20%20%20OPC/Ponder对标平台/07-原型与代码/render.yaml)

推荐上线步骤：

1. 初始化 Git 仓库并推送到 GitHub。
2. 在 Render 新建 Blueprint，直接指向这个仓库。
3. 在 Render 控制台补充需要的环境变量。
4. 部署完成后访问 Render 分配的域名。
