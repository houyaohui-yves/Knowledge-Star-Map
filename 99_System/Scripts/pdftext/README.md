# PDF 转文本样品 v0.1.2

本地提取 PDF 文字，扫描页使用 RapidOCR 中文 OCR。支持单页、左右双页及混合文件，输出 TXT / Markdown。不会上传 PDF，不调用大模型、不改写正文，不修改原 PDF。

当前电脑已安装环境和模型，可以直接测试。

## 立即测试

在终端进入知识库后执行：

```bash
cd /Users/houyaohui/Developer/Knowledge-Star-Map

./99_System/Scripts/pdftext/pdftext convert \
  "20_Sources/Files/PDFs/既往剧本杀/江寒A-1本.pdf" --format both
```

这条命令会复用已生成的结果。需要重新识别时加 `--force`。也可以直接让助手“用 pdftext 转换这份 PDF”，无需手动运行。

结果默认在 PDF 同级的 `_extracted/文件名-参数哈希/`：

- `document.md` / `document.txt`：阅读正文，不插入“PDF 第 N 页”或“左页／右页”等工具生成的标注；按原有阅读顺序以空行连接。
- `report.json`：处理页数、耗时、逐页告警、错误及版本。
- `pages.json`：文字框、置信度、页码分区、正文及被过滤的页眉页脚，用于核对和按页读取。

转换完成只打印摘要和结果路径，不把全文塞入 AI 上下文。`review` 表示有内容需要核对，并不等于转换失败；`partial` 表示部分页失败，`failed` 表示整个文件失败。OCR 即使无告警也不代表逐字准确。

## 常用命令

以下命令从仓库根目录执行；把 `资料.pdf` 换成真实路径。路径包含中文或空格时保留引号。

```bash
# 默认 Markdown；自动选择文字层提取或 OCR，逐页判断版式
./99_System/Scripts/pdftext/pdftext convert "资料.pdf"

# 纯文本；只处理指定页
./99_System/Scripts/pdftext/pdftext convert "资料.pdf" --format txt --pages 5-8

# 强制单页 / 左右双页
./99_System/Scripts/pdftext/pdftext convert "资料.pdf" --layout single
./99_System/Scripts/pdftext/pdftext convert "资料.pdf" --layout spread

# 混合文件：指定页覆盖自动判断，其余页继续自动处理
./99_System/Scripts/pdftext/pdftext convert "资料.pdf" \
  --single-pages 1-4 --spread-pages 5-15

# 文字层异常时强制 OCR；若不希望过滤页眉页脚，加 --keep-margins
./99_System/Scripts/pdftext/pdftext convert "资料.pdf" --ocr always --keep-margins

# 批量处理目录，默认不递归；加 --recursive 包含子目录
./99_System/Scripts/pdftext/pdftext convert "20_Sources/Files/PDFs/既往剧本杀/"

# 更换输出父目录；仍按文件名和参数创建独立子目录
./99_System/Scripts/pdftext/pdftext convert "资料.pdf" --output-dir "/tmp/pdftext-results"

# 按页读取转换后的结果；长度上限按字符计算
./99_System/Scripts/pdftext/pdftext read "结果目录" --pages 5-8 --max-chars 12000

# 检查依赖和模型
./99_System/Scripts/pdftext/pdftext doctor
```

页码参数及 JSON 内部记录全部使用从 1 开始的 PDF 物理页码，不是书上印刷页码；正文不再插入页码标注。`1-3,5` 表示第 1、2、3、5 页，仍可通过 `read --pages` 按页读取。读取被截断时会提示接续 `--offset`；保持相同页段继续读取即可。

自 v0.1.2 起采用上述无页码标注格式。既有转换文件不自动改写；新版转换使用新的缓存标识，避免复用旧版带标注的正文。

`--ocr never` 完全禁用 OCR，扫描文件会没有正文，仅适合诊断。`--dpi` 可调整扫描渲染分辨率，默认 260，允许 72–400。

## 如何测试单页与双页

1. 用默认 `auto` 转换一份普通单页文件，检查正文和段落。
2. 查看江寒样本第 5–14 页：应先输出整段左页，再输出右页。
3. 对特殊页使用 `--single-pages` / `--spread-pages` 重跑，比较结果。
4. 记录有问题的 PDF 名称、物理页码和具体错字或顺序，交给助手改进。

针对江寒样本，第 15 页左侧为文字拼贴、右侧文字很少，自动模式保守保留为单页并告警。可用 `--spread-pages 15` 改为左右分区，但无法消除拼贴文字本身的 OCR 错误。黑条遮挡的内容不会被恢复，也不能保证自动标记所有黑条。

## 样品的实际技术实现

- 用 pdfplumber 判断文字层及图像覆盖；文字层有效则按坐标提取，扫描或可疑页使用 OCR。
- 为稳妥处理裁剪和旋转，样品统一用 PDFium 渲染 OCR 页面；暂未实现原图直取优化，因此无需系统安装 Poppler。
- RapidOCR PP-OCRv6 small 检测与识别，ONNX Runtime CPU 推理。先得到整页文字框，再依据中缝和文字分布分区排序；不是先机械地切半图片。手动模式同样保留跨线文字框并告警。
- 自动双页要求横向比例、两侧正文和中间空白同时满足。双栏文章仍可能与双页相似，因此自动双页会提示核对；竖向多栏只告警，不承诺可靠阅读顺序。
- 重复边缘文字及页脚数字保守过滤，删除项保存在 `pages.json`；变形标志和与正文重叠的水印可能残留。可用 `--keep-margins` 关闭过滤。
- 缓存包含文件内容、参数、工具版本、依赖版本、模型哈希；输出被修改或部分失败时不命中缓存。
- 每次逐页处理，渲染上限 2400 万像素，单文件暂限 512 MiB。支持 Ctrl+C；样品未实现单页硬超时、断点续跑、并发转换锁和密码交互。
- 依赖、模型放在工具目录 `.venv/`、`.models/`，已在局部 `.gitignore` 排除。转换时使用已校验的本地模型路径，不自动下载。

这是可供试用的样品，并非正式方案所有验收项均已完成；特别是字级准确率、真实横向单页和复杂双栏资料仍需更多测试。当前不修改长期学习规则，避免试用工具成为未经确认的强制流程。

## 安装与维护

本机无需再次安装。重新安装或迁移电脑时，需要 Python 3.12（已验证版本）和网络：

```bash
./99_System/Scripts/pdftext/setup.sh

# 如默认 python3 版本较旧，指定 Python 3.12 路径：
PDFTEXT_PYTHON=/path/to/python3.12 ./99_System/Scripts/pdftext/setup.sh
```

依赖版本固定在 `requirements.txt`，模型校验值固定在 `models.lock.json`。当前实测环境约 349 MB，模型约 31 MB；不同系统可能不同。跨平台安装尚未验证。

执行自动化测试：

```bash
./99_System/Scripts/pdftext/.venv/bin/python -m unittest discover \
  -s 99_System/Scripts/pdftext -p 'test_*.py' -v
```

退出码：0 为成功、缓存命中或需核对；1 为失败或参数错误；2 为部分页失败；130 为用户中断。批处理发生错误仍处理后续文件，请同时查看各文件摘要。
