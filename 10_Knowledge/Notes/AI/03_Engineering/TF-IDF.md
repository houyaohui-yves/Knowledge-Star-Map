---
type: knowledge
status: developing
aliases:
  - "TFIDF"
  - "词频—逆文档频率"
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

# TF-IDF

## 核心认识

TF-IDF 将词项在当前文档内的频率，与它在整个文档集合中的区分权重结合，用于表示一篇文本的加权词项分布：

$$
w_{d,t}=\operatorname{tf}(t,d)\operatorname{idf}(t)
$$

其中 [[TF（词频）]] 回答“当前文档使用它多少次”，[[IDF（逆文档频率）]] 根据 [[DF（文档频率）]] 回答“这个词项在全库多普遍”。具体数值取决于选择的 TF、IDF 公式及后续归一化方式。

## 如何构成文档向量

先对文档集合采用一致的分词与特征规则，建立共同词表；词项可以是单词，也可以是 [[N-Gram]]。按统一列顺序计算每篇的 TF×IDF，就得到文档—特征矩阵：一行是一篇文档，一列是一个词项。

助手自拟简例，手工分词、只取单词，保留全部两个词项：

```text
文档 A：苹果 / 苹果 / 香蕉
文档 B：香蕉
共同词表：[苹果, 香蕉]
```

采用原始 TF 与平滑 IDF $\ln((N+1)/(\operatorname{df}+1))+1$，$N=2$：

| 词项 | A 的 TF | B 的 TF | DF | IDF（约） |
| --- | --- | --- | --- | --- |
| 苹果 | 2 | 0 | 1 | 1.4055 |
| 香蕉 | 1 | 1 | 2 | 1.0000 |

因此，归一化前的向量为 A=`[2.8109, 1]`，B=`[0, 1]`。每个位置在两篇中含义相同；A 反复出现的“苹果”得到更大的权重，B 未出现苹果，该位置为 0。

TF-IDF 加权之后可以另做 [[向量的 L2 归一化]]。例如本地酒店脚本的向量器默认采用这一处理；它将整条非零向量除以其长度，再用 [[余弦相似度]] 比较方向。归一化不是 TF×IDF 乘法本身，也不是所有实现必选的配置。

## 为什么通常是稀疏表示

全库词表通常很大，一篇文档只用到少数词项，其余列为 0，所以常形成 [[稀疏向量与稠密向量|稀疏向量]]。每一维对应一个明确词项；词表外的表达没有对应维度。

这个表示保留词项的加权分布。它不直接核实文字所述事实，也不自动理解同义词、否定范围或完整句法。不同文本若得到相同计数和权重，后续换一种距离度量也无法找回丢失的信息，见 [[向量相似不等于语义一致]]。

## 拟合与使用的边界

- 拟合是从选定语料统计词表、DF 和 IDF，不是训练一个神经网络；不需要用户喜好标签。
- 比较文档或查询时，应使用同一个已拟合向量器。分别拟合可能改变词表顺序与 IDF，即使向量维度相同，也不保证各列可比。
- 停用词、大小写、标点、N-Gram 范围和低频过滤都会改变特征；权重计算无法补回预处理已删除的信息。
- 权重既不是某设施真实有无，也不是用户喜欢的概率。稀疏或稠密描述的是零值分布，并不直接决定语义能力。

## 完整应用

[[酒店内容推荐案例：TF-IDF、N-Gram与余弦相似度]] 保留了另一组三家虚构酒店从文本、权重、归一化到推荐排序的完整演算，并对真实酒店数据给出结果解释。本文维护通用表示方法，案例维护其参数、演算与观测结果。

## 来源与核验

- 学习出处：[[AI大模型应用课件：Embedding与向量数据库]]；水果文本是助手自拟的最小教学例子，不是酒店原始数据。
- [Introduction to Information Retrieval：Tf-idf weighting](https://nlp.stanford.edu/IR-book/html/htmledition/tf-idf-weighting-1.html)：支持乘积加权、统一词表与向量表示。
- [scikit-learn：Text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)：支持计数、平滑 IDF、N-Gram 特征与向量归一化。
- [scikit-learn：TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)：支持拟合词表与转换文本的使用方式；案例的具体默认设置与依赖版本由来源笔记记录。

## 关联

- [[AI工程系统]]：文本特征与检索表示的入口。
- [[Embedding(嵌入)]]：对照统计词项表示与学习得到的表示。
