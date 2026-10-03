---
type: knowledge
status: developing
aliases:
  - "IDF"
  - "Inverse Document Frequency"
  - "逆文档频率"
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

# IDF（逆文档频率）

## 核心认识

IDF（Inverse Document Frequency）依据一个词项在文档集合中的普遍程度，为它分配区分权重：在文档总数固定时，**包含它的文档越少，IDF 越高**。这里的“少”按 [[DF（文档频率）]] 计，不按某篇里的重复次数计。

例如，每篇酒店介绍都写“酒店”时，这个词很难帮助区分介绍；只有少数介绍提到的词项通常更有区分力。IDF 高表示当前语料中较少文档使用它，不保证业务重要性、事实真实性或用户喜好。

## 两种常见公式

设 $N$ 为文档总数，$\operatorname{df}(t)$ 为包含词项 t 的文档数：

| 版本 | 公式 | 所有文档都出现时 |
| --- | --- | --- |
| 经典教材形式 | $\log(N/\operatorname{df}(t))$ | 0 |
| 本案例 scikit-learn 的平滑加一形式 | $\ln((N+1)/(\operatorname{df}(t)+1))+1$ | 1 |

“逆文档频率”通常不是直接取 $1/\operatorname{df}$。经典公式要求词项的 DF 非零；实际使用需明确公式、对数底、平滑方式与词表规则。这里展示的 scikit-learn 形式使用自然对数。

助手教学计算：固定 $N=3$，使用平滑加一形式：

| 包含词项的文档数 DF | IDF（约） |
| --- | --- |
| 1 | 1.6931 |
| 2 | 1.2877 |
| 3 | 1.0000 |

同一个已拟合语料与词表中，某词项的 IDF 被各篇文档共享；[[TF（词频）]] 则随文档改变。二者结合构成 [[TF-IDF]] 权重。

## 适用边界

- IDF 依赖语料集合。同一个词在酒店介绍和一般新闻中可能得到不同 IDF，不能把权重当作词本身永久的属性。
- 稀有词不一定保留。向量器若先按 `min_df` 过滤词表，过于罕见的词可能根本没有对应维度；增加 IDF 不能恢复已被过滤的特征。
- TF×IDF 之后若再做 [[向量的 L2 归一化]]，最终某一维数值还会受同篇文档其他特征影响，不能把最终数值直接当成 IDF。

## 来源与核验

- 学习出处：[[AI大模型应用课件：Embedding与向量数据库]]；本文将案例中的通用权重解释独立保存。
- [Introduction to Information Retrieval：Inverse document frequency](https://nlp.stanford.edu/IR-book/html/htmledition/inverse-document-frequency-1.html)：支持经典公式与区分力解释。
- [scikit-learn：Text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)：支持默认平滑加一公式及与教材形式的区别。三档数值是助手教学计算。

## 关联

- [[AI工程系统]]：文本特征与检索表示的入口。
- [[DF（文档频率）]]：IDF 的统计输入。
- [[TF-IDF]]：IDF 与文档内词频的组合方法。
