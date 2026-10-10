# Pico W 漏水探头外壳

这是一个参数化机械学习原型：Pico W 主机安装在较干燥的高处，可拆卸 SEN0121 探头单独放到待检查位置。仓库包含四个面向原型制作的自定义结构件、简化硬件包络、STEP/STL/GLB、数字几何检查、浏览器装配查看器和由参数生成的尺寸图。

![浏览器装配评审](artifacts/p3/desktop-final.png)

## 复现

使用 Python 3.12 与 Node.js 22，在仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/prepare_viewer.py
.\.venv\Scripts\python.exe -m pytest -q
Set-Location viewer
npm ci
npm test
npm run build
npm run dev
```

打开 `npm run dev` 输出的本地地址。`prepare_viewer.py`会重建基线、按manifest将同版文件复制到查看器，并从同一参数及manifest生成SVG尺寸图，不依赖本机绝对路径。

## 检查结果与限制

当前基线报告为 **176项数字检查通过、0失败、1项待验证**。待验证项是尚未在独立桌面CAD软件中重开STEP。测试也会重建有意义的参数变体，并检查非法参数与人为几何侵入能否被检测。GitHub Actions工作流配置为在Windows上运行几何测试和查看器生产构建。

STEP数字回读和GLB坐标检查不代表实物适配或产品可靠性。尚未进行实物打印/试装、紧固强度、射频、电路报警、探测深度或防水测试。探头连接器不防水；这不是认证报警器或防水外壳。

## 文件

- `cad/`：可编辑Python几何、参数、导出与验证代码。
- `artifacts/baseline/`：当前revision对应的STEP、STL、GLB、manifest和检查报告。
- `viewer/`：Three.js评审页面与依赖锁。
- `artifacts/drawings/pico-w-dimensions.svg`：参数化尺寸图。
- `docs/sources-and-assumptions.md`：公开来源、设计假设、安装顺序和边界。
- `docs/bom.md`：零件清单。

详见[来源与假设](docs/sources-and-assumptions.md)、[BOM](docs/bom.md)和[贡献指南](CONTRIBUTING.md)。查看器支持选件、显隐、分解、外壳透明、适配/复位视角、真实检查状态和同版文件下载。

## 许可与署名

原创代码和设计文件以MIT License发布。厂商规格通过链接引用，不再分发厂商文件。Raspberry Pi与DFRobot名称仅用于识别兼容参考产品，其商标归各自所有者。详见[LICENSE](LICENSE)与[来源和假设](docs/sources-and-assumptions.md)。

分享构建后的查看器时，请保留[Three.js运行时许可声明](viewer/public/licenses/third-party-notices.txt)；其他依赖仍适用各自上游许可。
