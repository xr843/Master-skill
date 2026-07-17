<!--
感谢贡献！请用中文或英文填写以下字段。纯 typo / 格式修复可删除不相关部分。
-->

## 改动类型

<!-- 勾选适用项 -->

- [ ] 代码 / CI / 工具链
- [ ] 文档 / README / 翻译
- [ ] 新增法师内容（`prebuilt/<slug>/`）
- [ ] 修改已有法师内容
- [ ] fidelity 测试用例变更
- [ ] `ETHICS.md` / `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md` 治理条款
- [ ] 其它

## 做了什么 + 为什么

<!-- 描述改动本身，以及它解决了什么问题。不要只列文件。 -->

## 相关 issue / discussion

<!-- Closes #123 / Refs #456 / 相关讨论链接 -->

## 自检清单

<!-- 提交前请自行勾选 -->

- [ ] CI 绿色（validate / fidelity-smoke / verify-links 无 red）
- [ ] 如果改了 `prebuilt/**` → 已 review [`ETHICS.md`](../ETHICS.md) §2（版权 Tier）、§3（教界边界）
- [ ] 如果新增 / 修改 `teaching.md` → 所有教义断言、修行指导与文本解释均附能解析到 `meta.json.sources[]` 的**真实声明来源 ID**
- [ ] 如果新增 / 修改 persona 来源 → `python scripts/validate-citation-contract.py` 绿色
- [ ] 如果新增 `voice.md` → Layer 0（硬规则）已从 ETHICS.md §3 完整复制
- [ ] 如果新增 fidelity 用例 → `python scripts/validate-fidelity.py` 绿色
- [ ] CHANGELOG.md 的 `[Unreleased]` 章节已更新（除非是纯 typo / 格式）
- [ ] PR description 说明了**为什么**这样做，不只是做了什么

## 新增法师（如适用）

<!-- 仅新增 prebuilt/<slug>/ 时填写 -->

- **法师**：
- **slug**：
- **版权 Tier**：A / B / D
- **对应的 New Master issue**：#
- **Tier B 授权证明**：（链接 `prebuilt/<slug>/LICENSE.md`）

## 本地测试

<!-- 说明你本地跑了什么、结果如何 -->

```bash
# 示例
python scripts/validate.py --strict      # ✅
python scripts/test-fidelity.py --master <new> --dry-run   # ✅ 5 条用例
ANTHROPIC_API_KEY=... python scripts/test-fidelity.py --master <new> --max-tests 1   # ✅ 1/1 pass
```

## 截图 / 样例回答

<!-- 可选。展示 AI 角色的实际表现，方便 review -->

---

<!--
PR description 写得详细一点，可以大幅减少来回 review 的次数。感谢！
-->
