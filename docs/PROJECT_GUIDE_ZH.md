# Group 33 项目说明

当前正式源码位于 `paper/`，来自用户提供的 `DSA5205_Project2_Group33_Overleaf`。原始 31 个文件保持不变，成员、分工、标题与 AI 辅助声明均以 `metadata.tex` 和最新正文为准。编译报告为 `output/pdf/Group_33_Report.pdf`，共 21 页。

## 编译与复现

- Overleaf：导入 `DSA5205_Project2_Group33_Overleaf.zip`，主文件选 `main.tex`，编译器选 XeLaTeX。
- 本地 LaTeX：进入 `paper/`，运行 `latexmk -xelatex main.tex`。
- 仓库校验编译：安装 Python 依赖及 Tectonic 后，在仓库根目录运行 `python -m project2.report`。
- 分析复现：`python -m project2.pipeline all --workspace runs/reproduction`。该命令与报告编译分开；详细环境配置见 README。

报告中的分析 commit `2e2e265ba9d007c94279225febaa15a054dff7cf` 对应原始研究实现；当前发布版本另包含整理后的 Group 33 文稿。新下载数据如被供应商修订，可能与原快照不同，不能未经更新就将冻结报告当成新运行的结果。

## 核心研究结论

用五个技术特征和 Ridge 回归，对 SPY 做日频择时。收盘出信号，次日开盘成交，预测之后开盘到开盘收益。每月用最新 1,260 个已实现标签重训，只在验证期选择四组 alpha。最终 alpha=1。

2022-2025 年，单边成本 5 bps 下，策略 CAGR 6.54%、Sharpe 0.481，低于买入持有的 11.18%、0.670。最大回撤约 -22.20%，基准约 -26.28%。策略股市暴露约 69.36%，总单边交易单位 246；费用与错过的正收益共同解释净表现落后。

原来的视频日志和合成语音讲解属于历史演示材料，不代表当前团队已经完成最终视频。提交前应由成员确认报告、真实贡献、AI 声明和视频，并检查 Canvas 分组与访问权限。
