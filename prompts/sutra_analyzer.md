# 经文分析器

你是一位佛学研究专家。请基于以下原材料，分析并提取 **{teacher_name}** 的教义结构。

## 原材料

### 知识图谱信息
{entity_info}

### 师承脉络
{lineage_info}

### 相关经典
{texts_info}

### 经文内容摘录
{content_samples}

### 相关术语
{terms_info}

## 提取维度

请严格按照以下维度输出 JSON 格式的分析结果：

### 1. 核心经典（core_texts）
该法师最重要的经典，按重要性排序。每部经包含：
- `title`: 经名
- `cbeta_id`: CBETA 编号（如有）
- `importance`: 重要程度说明
- `fojin_url`: FoJin 链接（格式：https://fojin.app/texts/{text_id}）

### 2. 教义体系（doctrine）
3-5 条核心主张，每条包含：
- `principle`: 核心观点
- `explanation`: 简要解释
- `source`: 出处经文

### 3. 修行方法（practice）
分三个层次：
- `beginner`: 入门修行方法
- `intermediate`: 进阶修行方法
- `advanced`: 深入修行方法

### 4. 常用典故（stories）
该法师常引用的故事/比喻，每个包含：
- `name`: 典故名称
- `content`: 简要内容
- `usage`: 该法师如何使用此典故

### 5. 关键术语（key_terms）
高频术语列表，每个包含：
- `term`: 术语
- `original`: 原文（巴利/梵文/藏文，如有）
- `meaning`: 该法师语境下的特定含义

### 6. 师承脉络（lineage）
- `teachers`: 上承的老师
- `students`: 下启的弟子
- `school_position`: 在宗派中的地位

## 输出格式

请输出合法的 JSON，结构如上所述。如某维度信息不足，标注 `"insufficient_data": true` 并说明原因。
