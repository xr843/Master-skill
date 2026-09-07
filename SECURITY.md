# Security Policy

## Supported Versions

Master-skill 以 `main` 为持续发布分支。我们仅对以下版本承诺 security fix：

| 版本 | 状态 |
|------|------|
| `main` (latest) | ✅ 持续修复 |
| `0.11.x` (当前发行线) | ✅ 持续修复 |
| `< 0.11.0` | ❌ 不再维护 |

> 这张表 2026-09-06 之前一直停在 `0.8.x`，而主线已经走到 0.11 —— 一份安全策略
> 承诺维护一条早已不存在的发行线，本身就是一条要修的记录。

---

## 报告安全漏洞

**请勿通过公开 issue 报告安全漏洞。** 公开披露会让攻击者先行利用。

### 推荐方式：GitHub Security Advisory

1. 访问 https://github.com/xr843/Master-skill/security/advisories/new
2. 填写漏洞描述、复现步骤、影响范围
3. 维护者会在 72 小时内确认收悉

### 备选：邮件

邮件发送至 **xianren843@protonmail.com**，主题请包含 `[SECURITY]`。

**推荐用 GPG / PGP 加密**：公钥可通过 keys.openpgp.org 搜索该邮箱获取（或在 issue 中 request）。

---

## 本项目关心的安全类别

Master-skill 作为 AgentSkill 插件 + NPX CLI，主要关注以下安全面：

### 1. **Prompt Injection**

- 预置法师的 `SKILL.md` / `voice.md` / `sources/` 被恶意注入，导致 AI 绕过 HARD-GATE 或伦理边界
- `/create-master` 生成管线中的 prompt 模板被污染
- 用户问题中的诱导越狱（"假装你是个能传戒的 AI..."）

### 2. **Supply Chain**

- `package.json` 依赖被投毒（当前依赖极少，但未来可能增加）
- FoJin API 返回的文本被篡改以影响 fidelity test
- CBETA ID 伪造（已有 `scripts/validate.py` 防线，但需持续完善）

### 3. **Secret Leakage**

- `ANTHROPIC_API_KEY` 在 CI 日志中意外泄露
- 用户在 issue / discussion 中误粘自己的 API key（自动检测 + 立即清除）
- **评测报告里的 provider 原始报错**：`test-fidelity.py` 会把异常字符串写进
  结果 JSON，而结果 JSON 既上传成 CI artifact 也提交进 `eval/reports/`
  （`0.10.1-c697d5d.json` 里就有 127 条）。这些报错现在过一遍
  `redact_secrets()`，凭证形态的子串替换为 `[REDACTED]`，可诊断的部分保留。

### 4. **Installer Safety**

- `bin/cli.mjs` (`npx master-skill install`) 的目录操作是否存在路径穿越
- 安装到 `~/.claude/skills/` 时的符号链接注入

### 5. **Religious-Boundary Violation via Adversarial Input**

- 特别 crafted 的用户问题使法师角色逾越 [`ETHICS.md`](ETHICS.md) §3 的禁止行为
- 这类属于**安全 + 伦理**交叉问题，优先级等同 S 级漏洞

---

## 非安全范畴（请走普通 issue）

以下不属于 security policy 范围：

- 某位法师回答不够"像"该祖师 → 开 bug report
- 引经错误（而非伪造）→ 开 bug report
- FoJin API 不可用 → 项目已有 graceful degradation，非安全问题
- UX / 文档问题 → 普通 issue

---

## 响应 SLA

| 严重级 | 首次回复 | 修复目标 | 公开披露 |
|-------|---------|---------|---------|
| Critical（0day、泄密、Prompt injection 破 HARD-GATE）| 24h | 7 天内发 patch | 修复后 7 天 |
| High（影响正常功能但非系统性）| 72h | 14 天内发 patch | 修复后 30 天 |
| Medium / Low | 7 天 | 下一版本 | 与版本同步 |

---

## 安全奖励

本项目目前**无法提供现金奖励**（个人维护，非商业项目）。但会：

- 在 `CHANGELOG.md` 显著位置署名感谢（除非你希望匿名）
- 对严重漏洞发现者提供一份定制化感谢文书（PDF + 项目维护者签名）
- 愿与你共同起草 CVE 条目（如适用）

---

## 相关文档

- 负责任披露：[GitHub Security Advisory Policy](https://docs.github.com/en/code-security/security-advisories)
- 内容安全边界：[`ETHICS.md`](ETHICS.md) §3
- 社区安全：[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

---

## 供应链安全（Supply Chain Security）

本仓库已实施以下供应链加固措施（v0.8 起）：

- **GitHub Actions 全部 SHA pin**：所有 `uses:` 引用都锁定到完整 commit SHA + 版本注释，防止 tag 被重打（mutable tag attack）。Dependabot 每周一自动开 PR 升级。
- **npm 发布使用 OIDC Trusted Publishing**：发版无需长期 `NPM_TOKEN` secret，改用 GitHub Actions OIDC id-token 在 npmjs.com 换取短期发布凭据。
- **npm provenance attestation**：每次 `npm publish` 附带 sigstore 透明日志可验证的构建溯源，安装方可通过 `npm install --foreground-scripts master-skill` + `npm audit signatures` 验证。
- **发布二进制的溯源**：`master-skill-desktop` 的三平台产物随发布附带 `.sha256`，并由
  `actions/attest-build-provenance` 签发 Sigstore 构建证明。校验：
  `gh attestation verify <file> --repo xr843/Master-skill`。
- **代码扫描（SAST）与漏洞库比对**（`security-scan.yml`，2026-09-06 新增；此前全仓**零** SAST、
  四个生态**零**告警库比对）：
  - **CodeQL** `security-extended` 查 `python` / `javascript-typescript` / `actions`
    三个语言（`actions` 查的是 workflow `run:` 块里的脚本注入 —— 本仓已经为此推理过一次，
    见 `validate-and-test.yml` 里 `SMOKE_MASTER` 的注释）。
  - **cargo audit** 比对 RustSec，覆盖桌面版那 408 个 crate。
  - **pip-audit** 比对 PyPI 告警库，两个 requirements 文件都查。
  - **dependency-review** 在 PR 上拦截**新引入**的高危依赖与 GPL/AGPL 许可。

  > 📌 2026-09-06 记录：在此之前本仓的 **Dependency graph 一直是关闭的**
  > （`dependency-graph/sbom` 与 `vulnerability-alerts` 双 404）。后果不只是
  > `dependency-review` 跑不了 —— **同一个开关也管着 Dependabot 安全告警**：
  > 关着的时候，某个已持有依赖爆出 CVE，GitHub 一声不吭，`dependabot.yml` 覆盖
  > 几个生态都没用；而版本更新 PR 照常每周一到，所以这个缺口极难察觉。
  > 两者已于当日开启。`security-scan.yml` 里**故意没有**"检测到关闭就跳过"的分支：
  > 若日后再被关掉，这个 job 就该亮红 —— 它所依赖的告警在同一刻也哑了。

  Dependabot 回答的是"依赖旧了吗"，回答不了"我们钉的这个版本有没有已知 CVE"，
  也完全不看本仓自己写的代码。这四项补的是后者。

  > **为什么开了 Dependabot 告警还要单独跑 `cargo audit`** —— 2026-09-07 实测：
  > 本仓 5 条 RustSec 告警里，GitHub 告警库（GHSA）只收了 1 条
  > （`webbrowser`，且是 2023 年那条 `< 0.8.3`，与本仓的 1.2.x 无关）。
  > `event-listener` / `quick-xml` / `paste` / `ttf-parser` 的告警 GHSA **一条都没有**。
  > 我们实际修掉的 RUSTSEC-2026-0257（`webbrowser` 的 Unix `BROWSER` 参数注入）
  > 也不在 GHSA 里。
  > 结论：**GHSA 的 Rust 覆盖显著薄于 RustSec，两者不是冗余关系**。
  > 依赖图开启后 Dependabot 告警仍为 0 条是**正确结果**，不是扫描没跑 ——
  > 该报的它都报了，只是它能报的本来就少。Python 侧则相反：PYSEC-2026-1845
  > 是 `pip-audit` 抓到的。它们暂未进分支保护 —— 但**会亮红叉**，
  这和"绿勾但什么都没查"是两回事：前者是有人做了不管的决定，后者是没人做过任何决定。
- **Dependabot 四生态**：`github-actions` / `npm` / `pip` / `cargo` 每周一统一开 PR；major bump 必须人工 review。
  （`cargo` 是 2026-09-06 才补上的 —— 桌面版那 408 个 crate 是唯一会变成"下载即执行"的产物，
  却恰恰是此前唯一没人盯的生态。）
- **评测依赖硬钉版本**：`requirements-eval.txt` 里 `anthropic` 用 `==` 而非 `>=`。
  这些包被装进**带着 live `ANTHROPIC_API_KEY` 的那个 job**，下限约束在那儿不算防线。
- **主分支保护**：required status checks 实际为
  `Validate SKILL.md & fidelity structure`、`Fidelity smoke (1 master × 1 fixture)`、
  `GitGuardian Security Checks`；禁止 force push 与分支删除。

> ⚠️ **`Fidelity smoke` 是 required，但它不评分。**
> 本项目的既定政策是 CI 不为 LLM-as-judge 付费（见 CONTRIBUTING.md §2），所以
> `ANTHROPIC_API_KEY` 从未配置，这个检查每次约 10 秒变绿，走的是"缺 key → 写
> `{"skipped": true}` → exit 0"那条路。**绿勾代表结构校验通过，不代表任何一次
> 模型回答被评过分。**
>
> 这条以前只存在于工作流的 shell 里，没有任何地方说出来 —— 而一个 required
> 检查的绿勾，两种情况下长得一模一样。现在：
>
> - 每个"缺 secret 即 exit 0"的 job 必须登记在 `scripts/check-gate-liveness.py`
>   的 `ADVISORY_GATES` 里并写明它**没查**什么，未登记的直接失败；
> - 该名单在每次 `npm test` 成功时打印，不用问就能看到；
> - 配上 secret 后把仓库变量 `FIDELITY_GRADING_REQUIRED` 设为 `true`，缺 key
>   就从"警告"变成"硬失败"。
>
> 此前 SECURITY.md 在这里列的是 `Fidelity smoke` 与
> `Persona-fidelity schema + advisory eval`。前者名字不全（分支保护按 check
> 全名匹配），后者根本不在 required 列表里，而 `GitGuardian Security Checks`
> 在列表里却没写。已按 2026-09-06 实测的分支保护设置更正。

如需复核或质疑某条措施，欢迎在 Discussion 提出。

---

感谢你让本项目更安全。
