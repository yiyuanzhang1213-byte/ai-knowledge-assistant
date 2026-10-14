# 可溯源知识库问答助手

面向门店工作人员与会员的规则问答原型。从单文件全文提问示例扩展为文档分块、BM25 检索、依据筛选、原文引用、反馈导出与可选模型整理。

本仓库为 AI 产品经理求职作品集的开源二次开发原型，开发时间为 2026-10-14。演示样本均为自建合成数据，尚无真实用户或生产业务收益。

## 快速运行

在仓库根目录执行（Python 3.11+）：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r portfolio/requirements.txt
.venv\Scripts\python.exe -m streamlit run portfolio/app.py
```

无需 API Key 即可使用本地规则/检索模式。模型功能需在服务端自行配置 LLM_BASE_URL（包含 /v1 的基础地址）、LLM_MODEL、LLM_API_KEY；禁止提交真实凭据。可选模型适配器已实现，不把 mock 测试等同于真实模型验收。

```powershell
python -m portfolio.evaluate
python -m unittest portfolio.test_core -v
```

## 产品材料与验证

- [产品需求说明](portfolio/PRD.md)
- [可复现评测数据](portfolio/data/)
- [评测结果及逐条证据](portfolio/reports/evaluation.json)
- 验证范围：15 项核心与模型适配器测试，另见 UI 核验记录。

## 开源来源与本次贡献

- 上游：https://github.com/streamlit/llm-examples
- 基线提交：`7cf260745675e41f92e7436d3777aafdab9dad9f`
- 原许可证：Apache-2.0，完整保留 LICENSE。
- 原始介绍：[README.upstream.md](README.upstream.md)。
- 上游文件保持原样；本次新增功能全部位于 `portfolio/`。根 README 与忽略规则按作品集用途更新。
- 新增内容采用与上游相同许可证。原组件、示例和原提交作者不归属于本次开发者。

## 适用范围

本地演示、产品设计讨论和评测方法展示。发布到公网之前需要补齐认证、权限、存储策略和真实模型验证。当前合成数据结果不能用于宣称生产质量、真实用户规模或商业提效。
