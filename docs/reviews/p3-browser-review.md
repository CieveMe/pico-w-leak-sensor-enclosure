# P3 浏览器与尺寸图复核

## 复核结论

初版复核未通过。独立复核发现爆炸位移向量错误地乘72、隐藏父节点下探头仍可拾取、部分尺寸图标签没有跟随输入参数。修正后针对三个问题的数字与真实浏览器回归均通过。

## 修正及回归

- 爆炸位移现在直接使用以毫米记录的manifest向量乘滑杆比例。真实浏览器中上盖Z位移在0%、50%、100%分别为0、17.5、35 mm，回零为0；六件重载后均可见。
- 拾取现在逐层检查命中mesh至装配根节点的有效可见性。对同一射线 `origin=(65,0,100)`、`direction=(0,0,-1)`，探头显示时命中`water_sensor`，隐藏部件父组后结果为`null`，恢复后再次命中`water_sensor`。
- SVG孔径、孔中心和外形尺寸文字由输入参数及与之匹配的manifest生成。非默认变体把盖板孔改为4.2 mm、中心改为X ±16 / Y ±28、壳宽改为46 mm；生成文字分别为“盖板 · 4 × Ø4.2 通孔”“盖板孔中心 X ±16 / Y ±28”“主机下壳 46 × 74”，圆半径为5.88 SVG单位。与变体不匹配的旧manifest会被拒绝。
- Python全套：20 passed。独立viewer副本Node测试：2 passed；Vite生产构建成功，单JS bundle为601.33 kB（gzip 154.39 kB），仍显示500 kB提示。
- 在本地隔离Vite viewer（http://127.0.0.1:4173/）通过现有Chrome的agent-browser连接复测：六个GLB加载，页面级error/unhandledrejection为0，真实报告176通过、0失败、1项待验证。浏览器重新请求并核对同版SVG的孔径、孔中心和尺寸文字。
- 修正后桌面和390×844窄屏截图为 `artifacts/p3/desktop-final.png`、`artifacts/p3/mobile-final.png`，已目视检查；机器检查结果及SHA-256见 `artifacts/p3/browser-acceptance.json`。

## 版本与指纹

当前CAD source revision为 `sha256:51ee0d54319a88e871f1ba0fe63c3fc858b7ee4dca68e9fd8133f528b981c6de`。截图记录的是P3修正后该版本的实际浏览器运行。公开机器记录中的SHA-256按Git暂存blob精确字节计算；检出时的行尾转换可能改变文本文件原始字节。P4审核保留了更新前的本地回执，本节不将历史浏览器观察冒充P4新开浏览器测试。

## 验证边界

唯一待验证项仍为独立CAD软件重开（`independent_cad_app.reopen`）。数字回归和网页查看不替代CAD软件重开、实物试装、打印、强度、射频或防水试验。P2几何验收结论保持。P3修正已关闭；P4公开仓库目标检查、Sol/High暂存与来源许可复核、公开推送和远端CI尚未完成。
