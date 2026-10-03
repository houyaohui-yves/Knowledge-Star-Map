---
type: knowledge
status: developing
aliases:
  - "TF"
  - "Term Frequency"
  - "词频"
topics:
  - AI/文本表示
  - AI/TF-IDF
ai_area: engineering
domains:
  - Constants
  - Engines
created: 2026-10-03
updated: 2026-10-03
source:
  - "[[AI大模型应用课件：Embedding与向量数据库]]"
---

# TF（词频）

## 核心认识

TF（Term Frequency）描述一个词项在**当前文档内**出现的频率。在原始计数定义下，$\operatorname{tf}(t,d)=\operatorname{count}(t,d)$：$t$ 是词项，$d$ 是当前文档。词项既可以是单词，也可以是 [[N-Gram]] 提取的连续片段。

TF 的统计单位是一篇文档。同一个词项在不同文档里可以有不同 TF；它与统计“有多少篇文档包含这个词项”的 [[DF（文档频率）]] 不同。

## 一个最小例子

助手自拟文本，人为分词为 `苹果 / 苹果 / 香蕉`：按原始次数计，苹果的 TF 为 2，香蕉为 1，未出现的梨为 0。这些数描述文字出现次数，不代表水果的真实数量。

TF 存在多种定义，必须说明所用版本：

| 形式 | 在此例中怎样理解 |
| --- | --- |
| 原始次数 | 苹果为 2，香蕉为 1 |
| 次数除以文档词项总数 | 苹果为 2/3，香蕉为 1/3 |
| 对数缩放 | 对出现次数做对数变换，减弱反复出现带来的增长；具体公式依实现而定 |

因此，TF 并非必须是百分比。文本清洗、分词方式与 N-Gram 范围改变后，计数对象也会改变。

## TF 怎样参与文本表示

在 [[TF-IDF]] 中，TF 与衡量词项全库区分力的 [[IDF（逆文档频率）]] 相乘。高 TF 仅说明当前文本反复使用这个表达，不能单独说明它能区分文档、符合用户需求或具有事实重要性。

[[酒店内容推荐案例：TF-IDF、N-Gram与余弦相似度]] 中，向量器先采用原始计数（`sublinear_tf=False`），乘以 IDF 后再做 [[向量的 L2 归一化]]。这一步向量归一化与“把词频除以总词数”是不同处理。

## 来源与核验

- 学习出处：[[AI大模型应用课件：Embedding与向量数据库]]；由酒店案例中的通用解释提炼，示例为助手教学设计。
- [Introduction to Information Retrieval：Tf-idf weighting](https://nlp.stanford.edu/IR-book/html/htmledition/tf-idf-weighting-1.html)：支持词项计数与 TF×IDF 加权。
- [scikit-learn：Text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)：支持计数、默认 TF 与对数缩放的区别；具体默认设置对应原案例核验版本。

## 关联

- [[AI工程系统]]：文本特征与检索表示的入口。
- [[DF（文档频率）]]：比较“出现多少次”与“出现于多少篇”。
- [[TF-IDF]]：将文档内频率与全库权重组合。
