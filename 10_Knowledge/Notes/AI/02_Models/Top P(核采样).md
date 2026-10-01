---
type: knowledge
status: developing
topics:
  - AI
  - LLM
  - 采样
ai_area: models
domains:
  - Engines
updated: 2026-10-01
source: "https://arxiv.org/abs/1904.09751"
---

# Top P（核采样）

## 核心认识

Top-p（Nucleus Sampling，核采样）是一种生成时选择候选 Token 的方法：将当前候选按概率降序排列，保留累计概率达到阈值 p 的最小前缀集合，再在其中按重新归一化的概率采样。

它限制的是累计概率，不是固定候选数量，也不是“只生成正确率达到 p 的词”。

## 一个例子

假设某一步只有四个候选，下面为手写教学分布：

| 候选 | 概率 | 累计概率 |
| --- | --- | --- |
| A | 0.50 | 0.50 |
| B | 0.30 | 0.80 |
| C | 0.15 | 0.95 |
| D | 0.05 | 1.00 |

当 p=0.75 时，保留 A、B：只取 A 不够，加入 B 后达到阈值。重新归一化后，二者概率为 0.625、0.375，而不是各占一半。下一步分布改变时，保留的候选数量也可能改变。

## 与其他采样参数的区别

- **Top-k**：限制保留多少个高概率候选。
- **Top-p**：限制需要覆盖多少累计概率。
- **Temperature**：先后处理顺序由实现决定，其作用是调整概率分布的集中程度；详见 [[Temperature(温度)]]。

p=1 表示这一步不按累计概率裁剪，但不代表其他过滤也关闭，更不表示输出变得确定。较小 p 会缩小选择范围，却不能保证答案更正确；模型、提示和其他解码设置仍影响结果。

## 来源与核验

- 2026-10-01 补全原空白概念；原始提及出处未知。
- [The Curious Case of Neural Text Degeneration](https://arxiv.org/abs/1904.09751)：查阅摘要，支持核采样通过动态候选集合截去分布尾部的研究背景，不将实验效果外推为通用最优参数。
- [Hugging Face：GenerationConfig](https://huggingface.co/docs/transformers/main_classes/text_generation)：查阅 top_p 与 top_k 定义。概率表是教学计算，未调用模型。

## 关联

- [[模型与训练]]、[[Token(词元)]]、[[Temperature(温度)]]。
