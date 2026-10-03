---
type: knowledge
status: developing
aliases:
  - Faiss
topics:
  - AI/向量数据库
  - AI/向量检索
ai_area: engineering
domains:
  - Engines
created: 2026-10-03
updated: 2026-10-03
source: "[[AI大模型应用课件：Embedding与向量数据库]]"
---

# FAISS

## 核心认识

FAISS（Facebook AI Similarity Search）是进行向量相似检索和聚类的库。程序把已有向量交给它，它负责建立索引、添加向量和搜索近邻；**它不生成文本 Embedding，也不自带管理业务正文与任意元数据的数据库系统**。

应用可以把 FAISS、记录存储和服务接口组合成检索系统。课件第 42 页将其放在常见向量数据库列表中，第 56 页又明确标为“核心算法库，非数据库”，应以后者理解组件边界。

## 怎样读课件的索引

```python
base_index = faiss.IndexFlatL2(1024)
index = faiss.IndexIDMap(base_index)
index.add_with_ids(vectors_np, vector_ids_np)
distances, retrieved_ids = index.search(query_vector, 3)
```

这是课件核心接口摘要，依赖 `faiss`、已有的向量矩阵与 ID，未在本机运行。

| 对象／操作 | 含义 | 需要分清 |
| --- | --- | --- |
| `IndexFlatL2(1024)` | 比较 1024 维向量，遍历得到精确 L2 近邻 | 返回平方 L2 距离；此索引不需要 `train()` |
| `IndexIDMap(base_index)` | 给基础索引加入显式整数 ID 映射 | ID 不要求与元数据列表位置相同；不改变基础搜索算法 |
| `add_with_ids(X, ids)` | 写入每一行向量及其标签 | 第 i 行 X 与第 i 个 ID 必须对应 |
| `search(Q, k)` | 为各查询返回前 k 项的距离和 ID | 课件一条查询返回两组 `1×k` 数组 |
| `index.ntotal` | 当前索引包含的向量数量 | 不是向量维度，也不是原文 token 数 |

[[向量近邻检索：精确搜索与近似搜索]] 解释不同搜索方法。FAISS 提供多种索引，不意味着本案例调用了 ANN。

## 数据形状和类型

对于课件四条文档、1024 维表示与一条查询：

```text
vectors_np      (4, 1024)   float32，每行一条文档向量
vector_ids_np   (4,)        int64，与行顺序对应
query_vector    (1, 1024)   float32，一条查询仍保持二维
distances       (1, 3)      平方欧氏距离
retrieved_ids   (1, 3)      IndexIDMap中的标签
```

上述形状是四条都成功编码时的情况；失败后 N 可能小于 4。应验证向量长度、有限数值、ID 对应、空批次和维度兼容，再交给索引。模型生成的数据类型转换不代表向量空间变成另一种语义表示。

查询或索引维度不同无法直接比较；模型不同但维度相同也可能不兼容。若不足 k 个邻居，返回标签中的 `-1` 表示缺失候选，应跳过，不能用它访问 Python 列表的最后一条。

## 平方 L2 与余弦如何对应

课件 `IndexFlatL2` 返回的数越小越近，不是“余弦相似度越大越好”的那种分数。详细公式与反例集中在 [[欧氏距离与平方欧氏距离]]。

若任务选用余弦比较非零向量，可把**库内向量和查询向量都做 L2 归一化**，再用内积索引 `IndexFlatIP`，此时较大点积表示较高余弦；也可以在同样归一化条件下用 L2，二者排序等价，返回数值的含义不同。

原课件代码没有显式归一化步骤。本次未得到实际 1024 维输出并测量长度，不能仅据模型名称断言截图分数可换算成余弦。

## FAISS 与外部记录的协作

搜索返回 ID 后，应用应按显式键找回原文和元数据。这个关系不是 FAISS 自行维护的业务表，见 [[向量检索中的ID与元数据]]。

FAISS 支持将索引写入文件并重新读取；外部正文与元数据需另外持久化并保持对应。课件只创建内存对象，未演示重启后的恢复。

“FAISS 不支持更新或删除”也是过度概括。操作支持取决于索引类型；例如文档说明 Flat、IVFFlat、IDMap 支持移除，而部分索引另有限制。改变记录后的 ID 语义和外部映射也需要处理，不能只盯着某个方法是否存在。

## 来源与核验

- 学习出处：[[AI大模型应用课件：Embedding与向量数据库]]，第 42、47–56 页；与本地 `2-embedding-faiss-元数据.py` 对照。
- [FAISS 官方仓库](https://github.com/facebookresearch/faiss)：检索／聚类库的定位，以及向量与度量作为输入的职责。
- [FAISS — Getting started](https://github.com/facebookresearch/faiss/wiki/Getting-started)：Float32 矩阵、行与查询形状、`add`／`search` 和 Flat 无需训练。
- [FAISS — Faiss indexes](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes)：Flat 精确搜索与 IDMap 包装。
- [FAISS — MetricType and distances](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)：平方 L2、归一化后内积与余弦关系。
- [FAISS — Special operations on indexes](https://github.com/facebookresearch/faiss/wiki/Special-operations-on-indexes)：删除支持与 ID 语义依索引而异。
- [FAISS — Index IO](https://github.com/facebookresearch/faiss/wiki/Index-IO,-cloning-and-hyper-parameter-tuning)：索引文件的写入与读取能力。
- 文档于 2026-10-03 查阅；本机当前使用的 Python 运行时未安装 FAISS，本轮仅核对材料与接口，没有执行索引程序或比较 CPU／GPU 性能。

## 关联

- [[向量数据库]]：库、数据库与关系扩展的职责区分。
- [[FAISS文本检索案例：向量、ID与元数据]]：完整输入、查询和结果解释。
