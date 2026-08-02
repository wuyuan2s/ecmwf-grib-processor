# ECMWF GRIB 数据处理器

本项目把 ECMWF 的 GRIB2 基础数据转换成浏览器容易加载的静态资源：全球等经纬度 PNG 图层、用于点选查询的低分辨率 JSON 网格、中国及邻近海域 0.25° 精细查询网格，以及描述全部时次、要素、单位、色带和统计值的 `manifest.json`。

这里把需求中的“更方便、更高效地在前端展示”落实为一次离线预处理：浏览器不解析 GRIB2，也不在用户设备上做百万格点的单位换算或配色。

## 安装

推荐在仓库根目录创建虚拟环境并安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e '.[test]'
```

依赖中的 `eccodes` PyPI 包通常会自动安装 ecCodes 运行库。若所在平台无法加载它，可先用系统包管理器安装 ecCodes，再重装 Python 依赖。

## 运行

```bash
ecmwf-process \
  /path/to/ifs-latest.grib2 \
  --output output \
  --sample-degrees 2 \
  --clean
```

`--clean` 会删除指定输出目录后重新生成，请勿把输出指向含有其他文件的目录。

## 处理规则

| 输出要素 | 输入字段 | 换算/派生 |
| --- | --- | --- |
| 2 米气温 | `2t` | K − 273.15 → °C |
| 2 米露点 | `2d` | K − 273.15 → °C |
| 2 米相对湿度 | `2t`, `2d` | Magnus 公式诊断，限制为 0–100% |
| 海平面气压 | `msl` | Pa ÷ 100 → hPa |
| 10 米风速 | `10u`, `10v` | `sqrt(u² + v²)` → m/s |
| 10 米最大阵风 | `10fg` | m/s |
| 累计总降水 | `tp` | m × 1000 → mm |
| 时段降水 | 相邻时次 `tp` | 当前累计 − 上一时次累计，负值归零 |
| 瞬时降水率 | `tprate` | kg m⁻² s⁻¹ × 3600 → mm/h |
| 降水相态 | `ptype` | 按 ECMWF 类别码离散着色 |
| 总云量 | `tcc` | 0–1 × 100 → % |
| 整层可降水量 | `tcwv` | kg/m² |
| 最大不稳定 CAPE | `mucape` | J/kg |
| 850 hPa 温度/风 | `t`, `u`, `v` @ 850 hPa | °C 底图 + 风场采样 |
| 700 hPa 相对湿度 | `r` @ 700 hPa | 0–100% |
| 500 hPa 涡度/高度 | `vo`, `z` @ 500 hPa | 涡度 × 10⁵ + 60 gpm 等高线 |
| 200 hPa 风速 | `u`, `v` @ 200 hPa | 风速底图 + 风场采样 |

每个时效还会由海平面气压生成 4 hPa 间隔的平滑等压线透明图层，并由 500 hPa 位势高度生成 60 gpm 等高线。等值线使用格点间连续插值，以双倍像素尺寸输出并在四倍画布上抗锯齿渲染；20 hPa 主等压线和 300 gpm 主等高线略微加强，并带有低透明度外描边，放大后不会出现格点阶梯。区域统计使用中国及邻近海域范围，不再以南极等全球极值代表当前业务区域。

处理器会检查网格类型，当前明确支持 ECMWF Open Data 使用的 `regular_ll` 规则经纬网格；经度从原始的 0–360 重排为 -180–180，纬度按北到南排列，使 PNG 可以直接贴到 Cesium 全球矩形上。

## 输出结构

```text
output/
├── manifest.json
├── layers/
│   ├── 20260801T1800Z-f006-temperature.png
│   └── 20260801T1800Z-f006-height-500.png
├── samples/
│   └── 20260801T1800Z-f006.json
├── query/
│   └── china-grid.i16
└── wind/
    ├── 20260801T1800Z-f006.json
    ├── 20260801T1800Z-f006-850.json
    └── 20260801T1800Z-f006-200.json
```

- `layers/*.png`：与全球矩形对应的 RGBA 单图层；
- `samples/*.json`：默认约 2° 的展示要素抽样值，供点击地图后快速查询；
- `query/china-grid.i16`：中国及邻近海域 0.25° Int16 量化格点，按需加载后可查询一个位置的全部时效；
- `wind/*.json`：地面、850 hPa 和 200 hPa 的 `wind_speed`、`wind_u`、`wind_v` 专用网格，供风羽和流场粒子使用；
- `manifest.json`：前端的唯一入口，添加时效不需要修改前端代码。

图片保留完整源网格分辨率；`--sample-degrees` 只影响点选查询 JSON 的体积，不影响地图图层清晰度。

## 扩展新要素

1. 在下载器参数中加入 ECMWF `shortName`；
2. 在 `pipeline.py` 中定义单位换算及字段映射；
3. 在 `palettes.py` 中增加中文名称、单位和色带；
4. 重新运行处理器。前端会从 manifest 自动生成要素选项和图例。

## 测试

```bash
pytest
```

单元测试覆盖单位换算与配色；使用真实 GRIB2 运行命令是端到端验收。
