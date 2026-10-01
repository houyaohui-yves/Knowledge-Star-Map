---
type: knowledge
status: developing
topics:
  - AI
  - LLM
  - Tokenization
ai_area: models
domains:
  - Engines
updated: 2026-10-01
source: "https://huggingface.co/learn/llm-course/chapter2/4"
---

# Token（词元）

## 核心认识

Token 是模型处理序列时使用的离散单元。在文本模型中，Tokenizer（分词器）把文字切分并编码成 Token ID；Token 可以对应词、子词、字符或字节片段，也可以是表示边界等作用的特殊符号。

**一个 Token 不固定等于一个汉字或一个英文单词。** 同一句话使用不同分词器，切分结果和数量可能不同，应使用与模型匹配的分词器计数。

## 从文字到模型输入

```text
文字 → 分词与编码 → Token ID 序列 → Token Embedding → 模型处理
```

Token ID 是词表中的编号，Embedding 是模型使用的数字向量；编号大小本身不表示语义距离。文本生成时，模型预测后续 Token，生成出的 ID 再由分词器解码为文字。

例如，一个较少见的英文词可能拆成多个常见片段，而常见词可能作为一个单元。这里只说明可能的切分方式，不给出未经指定分词器验证的中文 Token 数。

## 与 RAG 和 Agent 的关系

上下文管理需要计算实际模型输入占用的 Token：不仅是用户问题，还包括指令、历史、工具说明和检索资料。应为输出预留相应预算，具体输入／输出限制由所用模型决定。

长文档切片按字数可以粗估，接近模型硬上限时应实际分词计数；多模态输入的计量规则也不能从文本字数直接推导。Token 数反映输入规模，不代表信息质量。

## 来源与核验

- 2026-10-01 补全原空白概念；原始提及出处未知。
- [Hugging Face：Tokenizers](https://huggingface.co/learn/llm-course/chapter2/4)：查阅词、字符、子词及 Token 与 ID 编解码说明。
- 输入预算与切片联系是结合本库已有工程笔记的说明，未运行分词实验；具体计费不在本文范围内。

## 关联

- [[模型与训练]]、[[Large Language Model]]、[[Embedding(嵌入)]]。
- [[RAG中的长文档语义切片]]、[[记忆能力(短期记忆与上下文窗口、长期记忆与数据库)]]。
