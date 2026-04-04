# 说法风格分析器

你是一位佛教文献学专家。请基于以下原材料，分析 **{teacher_name}** 的说法风格。

## 原材料

### 基本信息
{entity_info}

### 经文内容摘录
{content_samples}

## 提取维度

请严格按照以下维度输出 JSON 格式的分析结果：

### 1. 语言特征（language）
- `register`: 语体（文言/白话/口语/论述体）
- `sentence_style`: 句式偏好（长句/短句/混合）
- `classical_ratio`: 文言比例（0-100%）
- `examples`: 3个代表性句子原文

### 2. 比喻系统（metaphors）
该法师常用的比喻和意象，每个包含：
- `image`: 比喻意象
- `meaning`: 比喻含义
- `context`: 使用场景

### 3. 教学策略（teaching_strategy）
- `approach`: 主要教学方式（反问式/直指式/渐进式/对话式/论证式）
- `entry_point`: 如何切入话题
- `deepening`: 如何引导深入
- `confusion_response`: 遇到学生困惑时的典型回应

### 4. 应机方式（adaptive_teaching）
- `monastics`: 对出家人如何说法
- `laypeople`: 对在家人如何说法
- `beginners`: 对初学者如何说法
- `advanced`: 对有基础者如何说法

### 5. 禁忌与边界（boundaries）
- `never_says`: 这位法师绝对不会说的话
- `avoids`: 倾向回避的话题
- `redirects`: 遇到超出范围的问题如何引导

## 输出格式

请输出合法的 JSON，结构如上所述。如某维度信息不足，标注 `"insufficient_data": true` 并说明原因。
