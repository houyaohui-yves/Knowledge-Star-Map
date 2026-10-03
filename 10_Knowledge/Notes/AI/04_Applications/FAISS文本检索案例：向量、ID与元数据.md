---
type: knowledge
status: developing
topics:
  - AI/向量数据库
  - AI/语义检索
ai_area: applications
domains:
  - Engines
created: 2026-10-03
updated: 2026-10-03
source: "[[AI大模型应用课件：Embedding与向量数据库]]"
---

# FAISS文本检索案例：向量、ID与元数据

## 任务与阅读范围

课件准备四条关于园区的短文本，用户询问“我想了解一下迪士尼门票的退款流程”。程序为文本和查询生成 Embedding，用 FAISS 找到前三条近邻，再按 ID 返回原文、来源文件、类别和作者。

**这些文本是课件示例材料，不是本笔记核验过的真实迪士尼政策。** “48 小时”“手续费”等只用于解释检索流程，不能据此办理真实退票；来源字段中的文件名也未作为实际政策文件读取。

本笔记保留理解流程所需的输入、配置与输出，不依赖本地课件才能读懂。课件截图的 1024 维向量没有完整保存在笔记中，依赖及模型服务版本也未锁定，因此不承诺可以复算截图中的全部分数。

## 输入：四条记录与两套 ID

以下原文和元数据来自本地 `2-embedding-faiss-元数据.py`，与 PDF 第 48、52 页能看到的部分对照。课件向量 ID 是从 0 开始的循环编号，业务文档 ID 则是 `doc1` 至 `doc4`。

| 向量 ID | 业务 ID | 原始文本 |
| --- | --- | --- |
| 0 | doc1 | 迪士尼乐园的门票一经售出，原则上不予退换。但在特殊情况下，如恶劣天气导致园区关闭，可在官方指引下进行改期或退款。 |
| 1 | doc2 | 购买“奇妙年卡”的用户，可以享受一年内多次入园的特权，并且在餐饮和购物时有折扣。 |
| 2 | doc3 | 对于在线购买的迪士尼门票，如果需要退票，必须在票面日期前48小时通过原购买渠道提交申请，并可能收取手续费。 |
| 3 | doc4 | 园区内的“加勒比海盗”项目因年度维护，将于下周暂停开放。 |

| 业务 ID | source | category | author |
| --- | --- | --- | --- |
| doc1 | official_faq_v1.pdf | 退票政策 | Admin |
| doc2 | annual_pass_rules.docx | 会员权益 | MarketingDept |
| doc3 | online_policy.html | 退票政策 | E-commerceTeam |
| doc4 | maintenance_notice.txt | 园区公告 | OpsDept |

每条记录的结构是 `{id, text, metadata}`；向量在后续生成。`source`、`category`、`author` 描述记录，正文则保留完整可读内容，便于查询后取回。

## 处理：从文本到索引

### 1. 调用模型生成文档表示

课件使用百炼的 OpenAI 兼容接口，端点为 `https://dashscope.aliyuncs.com/compatible-mode/v1`，模型名 `text-embedding-v4`，设置 `dimensions=1024`、`encoding_format="float"`。这些是案例配置，不是对当前推荐模型、价格或各服务支持范围的结论。

对每条 `doc['text']` 调用一次 Embedding，获得一个 1024 维向量。四条都成功时组成 `4×1024` 的 Float32 矩阵：每行表示一条短文本。

这与 [[酒店内容推荐案例：TF-IDF、N-Gram与余弦相似度]] 的区别是：酒店基线用共同词表的 TF-IDF 权重表示文档；这里由训练好的模型编码整条文本，**1024 个坐标不是 1024 个特征词名称**。脚本没有自行训练 Word2Vec，也没有实现词向量平均或 TF-IDF 加权。

### 2. 分别保留向量、ID 和原文

原代码建立三组容器：

```text
vectors_list：    [doc1向量, doc2向量, doc3向量, doc4向量]
vector_ids：     [0, 1, 2, 3]
metadata_store： [doc1记录, doc2记录, doc3记录, doc4记录]
```

每个记录仍含 `text` 和 `metadata`。这是在 FAISS 之外保存的 Python 列表，不是 FAISS 内置的元数据表；只有成功、顺序未变时，列表位置才恰好等于向量 ID。

### 3. 构建精确索引

```python
base = faiss.IndexFlatL2(1024)
index = faiss.IndexIDMap(base)
index.add_with_ids(vectors_np, vector_ids_np)
```

`IndexFlatL2` 遍历已存向量，按平方欧氏距离取近邻；`IndexIDMap` 使返回值使用指定的整数 ID。本案例没有训练 ANN 索引，也没有把任意 JSON 元数据存进 FAISS。

所有向量的第 i 行与第 i 个 ID 必须对应。课件的 `dimension=1024` 是向量坐标数，`k=3` 是希望返回的候选数量，两者不是同一概念。

## 查询：同样编码，再取回记录

查询文本为“我想了解一下迪士尼门票的退款流程”。脚本用同一模型和 1024 维配置生成查询向量，将其转为 `1×1024` 的 Float32 矩阵，再执行：

```python
distances, retrieved_ids = index.search(query_vector, 3)
```

返回两组 `1×3` 数组。程序依次取出 ID，用它访问 `metadata_store`，打印原文和元数据。向量负责匹配，ID 负责定位，记录提供可读结果，构成一次检索闭环。

这里的 [[欧氏距离与平方欧氏距离|平方欧氏距离]] 越小越近。课件输出标签写“相似度得分／距离”，本笔记将其明确写为平方 L2；不能将 0.3222 解释为 32.22% 的相似度。原代码未显式归一化，也未在本次验证模型输出的长度，因此不将这些值换算成余弦。

## 输出：课件截图展示了什么

以下来自 PDF 第 52 页截图，**不是本机重跑结果**；截图显示四条文档都成功处理、索引含四条向量。

| 排名 | 返回向量 ID | 对应记录 | 平方 L2 距离 | 结果内容及解释 |
| --- | --- | --- | --- | --- |
| 1 | 2 | doc3 | 0.3222 | 直接涉及在线购票退款的渠道、时间与费用条件，和“退款流程”最贴近 |
| 2 | 0 | doc1 | 0.3312 | 涉及一般退换规则与特殊例外，是相关候选，但条件与 doc3 需要进一步辨清 |
| 3 | 1 | doc2 | 1.0135 | 涉及年卡使用与折扣，没有说明退款流程；同属园区购票语境不等于能回答问题 |

维护公告 doc4 未出现在 Top-3 中，截图未展示它的距离。排名解释是助手依据候选文本所作的内容分析，不代表已经解释模型每个维度的决策原因。

这次检索展示了“相关候选优先”的流程，没有证明最终政策判断正确。doc1 与 doc3 的票种、渠道、版本、生效时间没有充分说明，不能将两者合并成一条无条件适用的规则。

程序停在展示候选这一步，没有调用 LLM 生成回答，也没有实现类别或权限过滤、重排、政策核验、索引落盘与元数据持久化。因此它可以作为 RAG 的检索组件示例，但还不是一个完整的 [[RAG（检索增强生成）|RAG 问答系统]]。

## 用二维数字理解查询过程

以下是助手另造的教学向量，不是模型真实输出。用二维替代 1024 维，是为了能手算每一步；顺序与课件记录相同，但数值与截图分数没有换算关系。

查询 `q=[1,0]`：

| ID → 记录 | 教学向量 | 平方距离计算 | 结果 |
| --- | --- | --- | --- |
| 0 → doc1 | `[0.7,0.2]` | `(1−0.7)²+(0−0.2)²` | 0.13 |
| 1 → doc2 | `[0.2,0.6]` | `(1−0.2)²+(0−0.6)²` | 1.00 |
| 2 → doc3 | `[0.8,0.1]` | `(1−0.8)²+(0−0.1)²` | 0.05 |
| 3 → doc4 | `[-0.4,0.3]` | `(1+0.4)²+(0−0.3)²` | 2.05 |

先按距离得到 ID `[2,0,1]`，再查询记录表，得到 doc3、doc1、doc2 和各自来源。这个例子能完整说明数值排序与记录取回，却不能用人为指定的向量证明语义模型的准确性。上述距离与排序已用 NumPy 核算。

## 处理失败时如何保持映射正确

### 原代码的隐患

原脚本处理每条文档时捕获异常并跳过，成功后执行：

```python
vectors_list.append(vector)
metadata_store.append(doc)
vector_ids.append(i)  # i仍是原始documents中的编号
```

如果 doc1 失败而 doc2、doc3 成功，向量 ID 为 `[1,2]`，记录列表却为 `[doc2,doc3]`。用返回 ID 1 访问列表会拿到 doc3，返回 ID 2 则越界。**搜索向量正确，展示内容仍可能错误**。

此问题由代码路径分析发现，并以普通 Python 容器模拟复现；第 52 页四条成功的截图没有触发它。完整原脚本未在本次执行。

### 修正思路：使用显式键，而非列表位置

下面是助手补充的函数片段，用于替换原脚本中收集、建索引与取回的部分。`documents` 采用上表的完整记录；调用者提供 `embed_text(text)`，负责用案例中兼容的模型配置返回一个向量。此片段不配置 API 客户端，未执行远程服务或 FAISS。

```python
import numpy as np
import faiss

def build_index(documents, embed_text, dimension=1024):
    vectors, ids, records_by_id, failed = [], [], {}, []
    for vector_id, doc in enumerate(documents):
        try:
            vector = np.asarray(embed_text(doc['text']), dtype=np.float32)
            if vector.shape != (dimension,) or not np.isfinite(vector).all():
                raise ValueError('向量维度或数值不合法')
        except Exception as error:
            failed.append((doc['id'], str(error)))
            continue
        vectors.append(vector)
        ids.append(vector_id)
        records_by_id[vector_id] = doc  # 按真实标签存记录

    if not vectors:
        raise ValueError('没有可写入的成功向量')
    X = np.ascontiguousarray(np.stack(vectors), dtype=np.float32)
    labels = np.asarray(ids, dtype=np.int64)
    index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
    index.add_with_ids(X, labels)
    return index, records_by_id, failed

def retrieve(index, records_by_id, query_text, embed_text, k=3):
    if k <= 0:
        raise ValueError('k必须大于0')
    vector = np.asarray(embed_text(query_text), dtype=np.float32)
    if vector.shape != (index.d,) or not np.isfinite(vector).all():
        raise ValueError('查询向量维度或数值不合法')
    Q = np.ascontiguousarray(vector.reshape(1, -1))
    distances, labels = index.search(Q, k)
    results = []
    for distance, label in zip(distances[0], labels[0]):
        vector_id = int(label)
        if vector_id == -1:  # 没有足够的邻居
            continue
        if vector_id not in records_by_id:
            raise KeyError(f'索引与记录表不一致：{vector_id}')
        results.append((float(distance), records_by_id[vector_id]))
    return results
```

字典映射不依赖“成功文档数量是否仍等于原始编号”；整数 ID 使用 `int64`，向量使用二维 Float32 矩阵。调用者应检查返回的 `failed`，本片段也没有声称失败文档已经入库。

函数仍是小案例：重新构建时枚举 ID 依赖输入顺序；若需要跨批次更新、删除和重启恢复，应保存稳定的业务 ID—向量 ID 对应关系，并同步索引、正文与元数据。通用原则集中在 [[向量检索中的ID与元数据]]。

## 从案例得到的可复用认识

1. **先表示，再检索**：模型决定表示，索引搜索数值近邻；换索引不能代替改善表示。
2. **ID 是检索闭环的一部分**：只有映射正确，距离结果才能变成正确的原文。
3. **知道返回值的度量**：L2、平方 L2、余弦的数值含义与排序前提需分清。
4. **Top-K 是候选**：近邻可以帮助找材料，相关性、事实适用性与回答正确性仍要评估。
5. **演示与可用系统有边界**：本例的内存索引及记录表还没有覆盖完整的持久化与知识治理。

课件第 57 页的后续任务是给自己的文档生成向量、建立 FAISS 索引、管理元数据并试查准确度。可先保留这四条示例，分别设计“退款流程”“年卡折扣”“项目维护”查询及预期相关文档，再考虑自己的资料；这是候选练习，尚未执行或证明优化有效。

## 来源与核验

- 学习出处：[[AI大模型应用课件：Embedding与向量数据库]]；PDF 第 45–57 页，截图结果仅取第 52 页。
- 本地代码：[2-embedding-faiss-元数据.py](../../../../80_Local/Courses/AI大模型应用课件/4-Embeddings和向量数据库/CASE-向量数据库/2-embedding-faiss-元数据.py)。本次静态读取，未修改原脚本，也未访问其中配置的远程服务。
- [FAISS — Getting started](https://github.com/facebookresearch/faiss/wiki/Getting-started) 与 [FAISS — MetricType and distances](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)：核对矩阵形状、Flat 搜索与返回距离；其他接口和边界依据见 [[FAISS#来源与核验]]。
- 助手补充：二维数据、故障场景、修正函数、结果内容分析和后续验证建议。二维计算和字典映射已在本机验证；修正函数已检查语法，因当前运行时未安装 FAISS，未实际执行其索引调用。

## 关联

- [[AI应用实践]]：从完整案例进入。
- [[向量数据库]]、[[FAISS]]：系统与库的职责。
- [[向量检索中的ID与元数据]]：映射、过滤与更新的通用解释。
- [[向量近邻检索：精确搜索与近似搜索]]：后续规模化搜索的选择。
