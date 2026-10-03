---
type: knowledge
status: developing
topics:
  - AI/Agent
  - AI/平台
ai_area: engineering
domains:
  - Engines
created: 2026-10-03
updated: 2026-10-03
source: "[[2026-10-01 Agent学习记录]]"
---

# Agent平台、框架与应用

## 核心认识

Agent 平台是为应用提供可复用构建、运行与管理能力的集成软件环境，帮助组合模型、指令、工具、数据与控制逻辑。具体产品覆盖范围不同，本文不设统一的必备功能清单。

| 生命周期 | 观察平台提供什么支持 |
| --- | --- |
| 构建 | 配置模型与指令，接入工具和资料，定义编排 |
| 运行 | 接收任务，调度调用，传递状态，处理异常 |
| 管理 | 查看记录，评估结果，控制访问并维护应用 |

LLM 提供模型能力；具体 Agent 应用面向一个任务；框架／SDK 提供代码组件与运行机制；平台提供集成环境。框架也可以有运行时、持久化与调试能力，产品边界可能重叠，不能用“框架不能运行”来区分。

Dify 的节点编排与日志、LangGraph 的框架／运行时及 LangSmith 的平台能力，是此前查阅的术语实例，不构成产品排名。平台可以呈现为画布，也可以主要通过 API 使用。

[[Glean Agent平台：介绍与分析]] 是独立产品案例：观察企业知识接入、Auto／Workflow、工具执行与应用治理如何组合。功能应按文章记录的文档版本理解；未进行租户实测，也不能直接将 Auto mode 等同于原论文的 ReAct。

## 一个分层例子

以退款资格查询为教学任务：LLM 提取诉求；应用规定查订单、取政策、核验资格与解释的业务逻辑；框架可以提供状态传递、调用和流程组件；平台可进一步集成接入配置、运行记录与管理界面。同一系统未必分别采用四个产品，这里区分的是职责。具体流程见 [[Workflow Agent的搭建原理]]，示例未运行。

## 来源与核验

2026-10-03 从 [[Agent入门：Workflow、ReAct与平台]] 提取，学习出处为 [[2026-10-01 Agent学习记录]]；原课程、视频与时间戳未提供。以下查阅记录沿用 2026-10-01 的核验范围，本次没有重新测试工具、平台或模型。

- [Dify：Workflow & Chatflow](https://docs.dify.ai/en/cloud/use-dify/build/workflow-chatflow)：作为画布节点编排与会话应用的平台实例；不据此推断所有平台都支持同样能力。
- [Dify：Orchestration Logic](https://docs.dify.ai/en/cloud/use-dify/build/orchestrate-node)：支持串行、并行、变量引用和循环的产品实例。
- [Dify：Logs](https://docs.dify.ai/en/cloud/use-dify/monitor/logs)：支持运行结果、节点记录、延迟和 Token 使用等观察能力的产品实例；本文不涵盖套餐价格或保留期。
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)：2026-10-01 查阅，支持框架／运行时也能提供状态与执行能力，以及 LangSmith 作为追踪、评估和部署平台的术语实例。平台定义、生命周期和层次对照为助手跨资料归纳，不是该文档给出的统一行业标准。
- 平台定义、生命周期与分层例子是跨资料的工程归纳，不是统一行业标准，也不构成当前产品选型结论。

## 关联

- [[Agent入门：Workflow、ReAct与平台]]：控制方式与平台的关系。
- [[AI工程系统]]：工程导航。
