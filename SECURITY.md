# Security Policy

## Supported Versions

Master-skill 以 `main` 为持续发布分支。我们仅对以下版本承诺 security fix：

| 版本 | 状态 |
|------|------|
| `main` (latest) | ✅ 持续修复 |
| `0.7.x` | ✅ 持续修复 |
| `< 0.7.0` | ❌ 不再维护 |

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
- **Dependabot 三生态**：`github-actions` / `npm` / `pip` 每周一统一开 PR；major bump 必须人工 review。
- **主分支保护**：required status checks 包含 `Validate SKILL.md & fidelity structure`、`Fidelity smoke`、`Persona-fidelity schema + advisory eval`；禁止 force push 与分支删除。

如需复核或质疑某条措施，欢迎在 Discussion 提出。

---

感谢你让本项目更安全。
