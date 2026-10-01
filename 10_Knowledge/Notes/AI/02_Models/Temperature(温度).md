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
source: "https://huggingface.co/docs/transformers/internal/generation_utils"
---

# Temperature（温度）

## 核心认识

Temperature 是生成阶段调整候选 Token 概率分布的参数。它改变采样的集中程度，不修改模型权重，也不是“知识水平”或“正确率”的开关。

常见定义是在 softmax 前用正温度 T 缩放模型给出的分数（logits）：

$$
p_i(T)=\frac{\exp(z_i/T)}{\sum_j\exp(z_j/T)},\qquad T>0
$$

| 温度 | 对同一组 logits 的影响 |
| --- | --- |
| 0 < T < 1 | 分布更集中，高分候选获得更大概率 |
| T = 1 | 保持原 softmax 分布 |
| T > 1 | 分布更平缓，低分候选相对更容易被抽中 |

## 一个数值例子

仅有 A、B 两个候选，在 T=1 时概率为 0.8、0.2。按上式计算，T=0.5 时约为 0.941、0.059；T=2 时约为 0.667、0.333。温度改变概率差距，不交换这两个候选的高低顺序。数字是教学计算，不是模型实测。

## 使用边界

- 公式不能直接代入 T=0；趋近于零时概率集中到最高分候选。某些接口用零表示贪心解码，另一些只接受正数，应查看实际实现。
- 低温不保证事实正确：模型可能稳定选择错误内容。也不能仅凭温度设置承诺整个服务逐次输出完全一致。
- 效果取决于解码方式；没有启用采样时，温度参数可能不生效。
- [[Top P(核采样)]]控制候选集合，温度调整概率分布。比较效果时可先固定其他条件，一次改变一个参数；这是实验建议，不是所有任务的最优配置。

## 来源与核验

- 2026-10-01 补全原空白概念；原始提及出处未知。
- [Hugging Face：TemperatureLogitsWarper](https://huggingface.co/docs/transformers/internal/generation_utils#transformers.TemperatureLogitsWarper)：查阅温度缩放、正值要求及与采样的关系。数学例子按标准温度缩放计算；未测评具体服务。

## 关联

- [[模型与训练]]、[[Token(词元)]]、[[Top P(核采样)]]、[[提示词工程]]。
