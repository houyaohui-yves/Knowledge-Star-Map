---
type: source
status: developing
source_type: mixed
topics: [股票投资, 周期, 正常化盈利]
domains: [Tides]
created: 2026-11-04
updated: 2026-11-04
---

# D类周期驱动型：研究方法与算例核验

对应 [[公司股票分类研究（四）：D类周期驱动型]]。按用户 D→C→E→A 的研究顺序首先完成；编号按 A～F 固定映射，未采用新交易纪律。

## 已读来源

2026-11-04 读取公开 HTML，未读取整本教材或验证图表底层数据：

| 来源 | 实际范围与用途 | 边界 |
| --- | --- | --- |
| [McKinsey：How to value cyclical companies](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/how-to-value-cyclical-companies) | 正常周期／新长期趋势、正常化盈利及价差建模的公开正文；前轮已读，本轮重新打开 | 未采用示例概率，不声称能预测拐点 |
| [Damodaran：Commodity companies—Value Drivers](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/commodityvaluedrivers.htm) | 正常化的利润均值、比率、同业方法及价格假设的正文 | 未采纳该页期货对冲建议；市场远期价格不当成确定未来现货价 |
| [Damodaran：More on normalizing earnings](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/normearn.htm) | 短文全文，规模变化和恢复时间问题 | 原文年数不移植为固定研究跨度；实际过渡期还需现金预测 |
| [Damodaran：Commodity company characteristics](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/littlebook/commoditycompanies.htm) | 价格接受、固定成本与债务放大波动、生存与资源寿命 | 特征须按公司验证，不能推断每个周期股都高债务 |

分类原义沿用 [[公司股票分类：林奇六类与分类边界核验记录]]；本文清单、操作流程和案例为助手教学适配，没有重新精读原书。

## 算术与假设

产品案例单位：销量万吨，价差元／吨，金额亿元，股数亿股。贡献=`销量×价差/10000`；固定现金费 2、折旧 1、利息 0.5；正税前利润乘 75%，亏损不计税收收益，再除 2.5 亿股。

- 低谷贡献 1.6，EBITDA -0.4，EBIT -1.4，净利 -1.9，EPS -0.76。
- 正常贡献 6，EBITDA 4，EBIT 3，净利 1.875，EPS 0.75。
- 高景气贡献 12.1，EBITDA 10.1，EBIT 9.1，净利 6.45，EPS 2.58。
- 现价 8 元，峰值 PE `8/2.58≈3.10`，正常 PE `8/0.75≈10.67`。
- 低谷现金：`3+(-0.4-0.5+0.4)-0.8-1.2=0.5`；第二年若经营消耗仍 0.5、必要投资 0.8、无到期本金，仍缺 1.3 才能维持最低现金 0.5。营运资金释放不能默认重复。
- 三年末财富 9.6／5／12.6，买价 8；CAGR 分别 6.265857%、-14.501203%、16.348339%。假设分红不生息、无费税、无增发且等待可融资；不代表由现金例已证明这些条件成立。
- 同样财富 9.6，2／4 年年化分别 9.544512%／4.663514%。

以上用程序复算，不是现实数据、统计概率或亏损下限。没有给实际持仓分类、改交易或证明用户已掌握；接续见 [[2026-10-23 股票投资入门学习记录]]。
