---
type: knowledge
status: developing
aliases:
  - "N元语法"
  - "N-gram"
  - "N元片段"
topics:
  - AI/文本表示
  - AI/语言模型
ai_area: models
domains:
  - Constants
  - Engines
created: 2026-10-03
updated: 2026-10-03
source:
  - "[[2026-10-02 Embedding与向量数据库学习记录]]"
---

# N-Gram

## 核心认识

N-Gram 是序列中连续 N 个单元组成的片段。单元可以是词、字符或 Token，使用时须说明粒度。它描述片段结构；**N 不表示向量维度，也不是把长文档分成 N 份**。

教学示例：人为按词切分“我 / 喜欢 / 学习 / AI”，不添加句首、句尾标记：

| N | 名称 | 连续片段 |
| --- | --- | --- |
| 1 | Unigram | 我；喜欢；学习；AI |
| 2 | Bigram | 我 喜欢；喜欢 学习；学习 AI |
| 3 | Trigram | 我 喜欢 学习；喜欢 学习 AI |

这些片段通过滑动窗口获得，可以重叠。字符级示例：“向量数据库”的字符 Bigram 为“向量、量数、数据、据库”。这不等于某个模型的实际 Token 切分结果。

需要区分两个用法：

- **N-Gram 特征**：统计连续片段的出现次数，用于文本表示或匹配；片段计数可构成稀疏向量，但不会自动建立不同表达之间的语义联系。
- **N-Gram 语言模型**：用前 N−1 个单元近似完整历史，估计下一个单元的概率。例如 Bigram 模型用 $P(w_t\mid w_{t-1})$ 近似 $P(w_t\mid w_1,\ldots,w_{t-1})$。

N-Gram 提供局部顺序与统计信息，不能单凭片段相同与否充分判断语义。例如“购买”和“买入”字面不同，表达的意思却可能相近。它不是 Embedding 的必经前处理步骤；统计特征与学习得到的向量也可以结合使用。

## 与分词及 Embedding 的区别

分词先确定有序的基本单元，N-Gram 再组合相邻单元；它不是分词的同义词。在“我 / 喜欢 / 学习 / AI”的例子中，把 N 从 1 改为 2，基本切分未变，改变的是用于计数的特征。

[[Embedding(嵌入)]] 的向量还取决于后续编码与训练目标。现代文本编码器通常不要求先手工提取 Bigram 或 Trigram；分词、特征提取与学习表示的衔接见 [[Embedding(嵌入)#Tokenization、N-Gram 与文本 Embedding 的分工]]。

## 适用边界与课件表述校准

- “只依赖前 N−1 个词”是 N-Gram 语言模型对当前词概率的近似假设；是忽略更早历史的模型选择，不是现实语言中其他词都不相关的事实。
- “N 个 item 的序列”应明确为原序列中连续 N 个单元；`A B C D E` 的 Bigram 为 `AB、BC、CD、DE`。
- “相邻两个关键词的特征组合”只描述 N=2 的 Bigram；一般 N-Gram 组合的是 N 个连续单元，不要求它们是关键词。

截图及其识别范围见 [[2026-10-02 Embedding与向量数据库学习记录#N-Gram 课件截图]]。

加入更长片段能保留更多局部顺序，也可能增加稀疏性、减少不同措辞间的匹配。片段不同并不意味着模型已识别逻辑矛盾，具体反例见 [[向量相似不等于语义一致]]。

## 来源与核验

- 学习出处：[[2026-10-02 Embedding与向量数据库学习记录]]；只核对用户提供的一页截图，完整课程出处未知。分词和片段为教学示例。
- [Jurafsky 与 Martin：Speech and Language Processing，第 3 章 N-gram Language Models](https://web.stanford.edu/~jurafsky/slp3/3.pdf)：查阅连续词序列、N−1 阶历史近似与计数估计，支持 N-Gram 与 N-Gram 语言模型的区别。
- [Introduction to Information Retrieval：k-gram indexes for wildcard queries](https://nlp.stanford.edu/IR-book/html/htmledition/k-gram-indexes-for-wildcard-queries-1.html)：支持字符级连续片段的定义；本文未展开通配符索引实现。
- [scikit-learn：Text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)：查阅 tokenizer 与 N-Gram 提取职责、Bigram 保留局部顺序，以及 bag-of-N-Grams 仍丢失大量结构的限制；支持统计特征的改进与边界。

## 关联

- [[模型与训练]]：序列表示与语言模型的入口。
- [[TF-IDF]]：用词项或 N-Gram 的计数与权重构造文档向量。
- [[酒店内容推荐案例：TF-IDF、N-Gram与余弦相似度]]：实际同时提取 1～3 Gram，保留清洗前后的具体示例。
