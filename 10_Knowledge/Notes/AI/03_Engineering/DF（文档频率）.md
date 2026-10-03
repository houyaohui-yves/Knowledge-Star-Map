---
type: knowledge
status: developing
aliases:
  - "DF"
  - "Document Frequency"
  - "文档频率"
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

# DF（文档频率）

## 核心认识

DF（Document Frequency）是**文档集合中包含某词项的文档数量**。设文档集合为 $D$、总文档数为 $N$，则：

$$
\operatorname{df}(t)=\left|\{d\in D:\operatorname{count}(t,d)>0\}\right|
$$

一篇文档内出现一次或很多次，都只为这个词项的 DF 贡献 1。未出现的词项 DF 为 0；已出现词项的 DF 在 1 到 N 之间。

## 与出现次数的区别

助手自拟三篇已分词文本：

```text
文档 A：苹果 / 苹果
文档 B：苹果 / 香蕉
文档 C：香蕉
```

苹果在 A 中的 [[TF（词频）|原始 TF]] 是 2，在全库的总出现次数是 3，但 DF 是 2，因为只有 A、B 包含它。香蕉也出现在两篇文档中，所以其 DF 同样为 2。

这说明 DF 忽略单篇内的重复程度，衡量的是词项覆盖文档的广泛程度。语料库、分词或清洗规则改变后，DF 需要按新的统计范围重新计算。

## 用途与边界

[[IDF（逆文档频率）]] 根据 DF 与文档总数计算区分权重；文本向量器也可用 DF 筛选特征。

例如 [[酒店内容推荐案例：TF-IDF、N-Gram与余弦相似度]] 有 152 篇介绍，`min_df=0.01` 要求词项至少出现在 1% 的文档中，因此至少需要 2 篇。在同一家酒店介绍里重复 100 次，也不能满足这个门槛。

过滤低 DF 词项能减少仅偶然出现的特征，也可能丢掉仅一篇提到的重要信息。DF 高低本身不判定词项是否正确或重要；相同比例阈值在不同规模语料中对应的篇数不同。

## 来源与核验

- 学习出处：[[AI大模型应用课件：Embedding与向量数据库]]；三篇水果文本为助手教学示例，152 篇与参数来自已核验案例。
- [Introduction to Information Retrieval：Inverse document frequency](https://nlp.stanford.edu/IR-book/html/htmledition/inverse-document-frequency-1.html)：支持 DF 的文档计数定义及其与 IDF 的关系。
- [scikit-learn：TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)：支持 `min_df` 的整数次数与比例含义。

## 关联

- [[AI工程系统]]：文本特征与检索表示的入口。
- [[TF（词频）]]：统计当前文档内的频率。
- [[IDF（逆文档频率）]]：将文档覆盖范围转换为加权依据。
