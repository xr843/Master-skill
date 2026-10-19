# FoJin API 完整参考

本文档供 LLM 在 `rag_query.py` 不够用时即兴写 Python 查询使用。

基础 URL：`https://fojin.app`

## 认证

目前公开只读 API 无需认证。

## 搜索 API

### GET /api/search

关键词搜索佛教文本。

**参数：**
- `q` (必填) - 搜索关键词，最长 200 字符
- `page` (默认 1) - 页码
- `size` (默认 20，最大 100) - 每页结果数
- `dynasty` - 朝代筛选（如"唐"、"宋"）
- `category` - 分类筛选
- `lang` - 语言筛选（lzh=文言汉语, pi=巴利, sa=梵文, bo=藏文, en=英文）
- `sources` - 数据源筛选，逗号分隔（cbeta, suttacentral, gretil）
- `sort` - 排序（relevance, title, dynasty）

**响应：**
```json
{
  "total": 42,
  "page": 1,
  "size": 20,
  "results": [
    {
      "id": 1234,
      "cbeta_id": "T01n0001",
      "title_zh": "长阿含经",
      "translator": "佛陀什",
      "dynasty": "后秦",
      "category": "阿含部",
      "source_code": "cbeta",
      "score": 0.95
    }
  ]
}
```

### GET /api/search/semantic

向量语义搜索（pgvector）。比关键词搜索更能理解语义相似性。

**参数：**
- `q` (必填) - 自然语言问题
- `size` (默认 10) - 返回结果数

### GET /api/search/content

全文内容搜索（带高亮）。

### GET /api/search/cross-language

跨语言搜索（中/英/梵/巴/藏）。

## 文本 API

### GET /api/texts/{text_id}

获取文本元数据。

### GET /api/texts/{text_id}/juans/{juan_num}

获取某卷的完整内容。

**参数：**
- `lang` - 语言代码

**响应：**
```json
{
  "text_id": 1234,
  "cbeta_id": "T01n0001",
  "title_zh": "长阿含经",
  "juan_num": 1,
  "content": "...",
  "prev_juan": null,
  "next_juan": 2
}
```

### GET /api/texts/{text_id}/juans/{juan_num}/similar

通过 pgvector 相似度查找类似段落。**研究级功能**：跨经典找"同义段落"。

### GET /api/texts/lookup-cbeta

CBETA ID 批量映射到内部 text_id。

**参数：**
- `ids` - 逗号分隔的 CBETA ID 列表

### GET /api/texts/{text_id}/juans

列出某部文本的所有卷。

## 知识图谱 API

### GET /api/kg/entities

搜索知识图谱实体。

**参数：**
- `q` (必填) - 搜索词
- `entity_type` - 类型筛选（person, text, school, concept, place, event）
- `limit` (默认 20) - 最大结果数

### GET /api/kg/entities/{entity_id}

获取实体详情（含关系列表）。

### GET /api/kg/entities/{entity_id}/graph

获取实体的关系图谱。**这是利用 23K 师承关系的核心 API。**

**参数：**
- `depth` (默认 2，1-4) - 遍历深度
- `max_nodes` (默认 150) - 节点上限
- `predicates` - 关系类型筛选（逗号分隔）

**响应：**
```json
{
  "nodes": [{"id": 456, "name": "玄奘", "entity_type": "person"}],
  "links": [{"source": 456, "target": 1234, "predicate": "translated"}]
}
```

## 词典 API

### GET /api/dictionary/search

搜索佛学词典。

**参数：**
- `q` (必填) - 搜索词
- `lang` - 语言筛选
- `source` - 词典来源筛选

### GET /api/dictionary/search/grouped

**按词典来源分组返回结果**。利用 FoJin 的 32 部词典，可以看同一术语在不同传承的释义差异。

**响应：**
```json
{
  "query": "般若",
  "groups": [
    {"source_code": "foguang", "source_name": "佛光大辞典", "entries": [...]},
    {"source_code": "dingfubao", "source_name": "丁福保佛学大辞典", "entries": [...]}
  ]
}
```

## 常见用法示例

### 场景 1：查找某法师的所有相关经典

```python
import requests

# 先从 KG 找到实体
r = requests.get("https://fojin.app/api/kg/entities", 
                 params={"q": "玄奘", "entity_type": "person"})
entity_id = r.json()["results"][0]["id"]

# 遍历师承/著作关系
r = requests.get(f"https://fojin.app/api/kg/entities/{entity_id}/graph",
                 params={"depth": 2, "predicates": "translated,authored"})
```

### 场景 2：跨词典对比术语释义

```python
r = requests.get("https://fojin.app/api/dictionary/search/grouped",
                 params={"q": "空性"})
for group in r.json()["groups"]:
    print(f"【{group['source_name']}】")
    for entry in group["entries"]:
        print(f"  {entry['definition'][:100]}")
```

### 场景 3：找与某段经文最相似的其他段落

```python
# 获取某部经的某卷
r = requests.get("https://fojin.app/api/texts/43/juans/1/similar")
for similar in r.json()["similar"]:
    print(f"{similar['title']} 卷{similar['juan_num']}: {similar['score']:.3f}")
```

## 错误处理

- **200** - 成功
- **404** - 资源不存在（text_id 无效等）
- **429** - 速率限制（默认 200 req/min）
- **500** - 服务器错误

连接失败时应优雅降级（见 `tools/rag_query.py` 的 fallback 逻辑）。

## 速率限制

- 默认：200 req/min
- 全文内容搜索：30 req/min
- 聊天 API：登录用户 20/day，匿名 5/day

## 何时使用直接 API 而非 rag_query.py

`rag_query.py` 只封装了 4 种常用查询（search/semantic/dict/kg）。遇到以下情况时，LLM 应直接写 Python 调 API：

- 需要 KG 深度遍历（depth >= 2）
- 需要跨词典分组对比
- 需要按多个维度组合筛选
- 需要相似段落查找
- 需要跨语言对比
