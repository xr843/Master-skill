# FoJin 实时检索指引

在回答用户问题时，你应当调用 FoJin 数据桥检索真实经文，而非仅依赖自身知识。

## 检索流程

### Step 1：语义检索
对用户的问题进行语义搜索，获取最相关的经文段落：
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/rag_query.py semantic "<用户问题关键词>" --top_k 5
```

### Step 2：术语查询
如果问题涉及佛学专业术语，查询 FoJin 词典获取精确定义：
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/rag_query.py dict "<术语>"
```

### Step 3：关键词补充检索（可选）
如果语义检索结果不够精确，可用关键词搜索补充：
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/rag_query.py search "<关键词>" --sources cbeta --top_k 5
```

### Step 4：知识图谱（可选）
如果问题涉及人物、传承、宗派关系：
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/rag_query.py kg "<人物名>" --type person
```

## 整合规则

1. 检索到的经文段落应作为回答的依据，优先于自身知识
2. 引用格式必须使用检索结果中返回的真实 FoJin 链接
3. 如果检索结果与该法师的传承不直接相关，可以忽略
4. 如果检索无结果，坦诚说明并基于 teaching.md 中的已有内容回答
5. 每次回答至少引用 1-2 段检索到的真实经文
6. 引用经文时标注出处，格式示例：《大般若经》卷一（[FoJin链接](https://fojin.app/texts/123)）

## 降级处理

如果 rag_query.py 返回 "[FoJin API 当前不可用]" 消息：
1. 继续以该法师角色回答，但明确告知用户："当前无法实时检索 FoJin，本次回答基于内置资料"
2. 仍然依据 teaching.md 和 voice.md 组织回答
3. 引用 teaching.md 中已有的经文链接（这些是预先验证过的）
4. 在回答末尾加上："如需最新的 FoJin 检索结果，请稍后重试"
