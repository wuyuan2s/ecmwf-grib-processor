# 第三方数据与依赖声明

本文件用于说明项目源码许可证之外的数据和第三方组件权利。它不替代各权利方的完整许可条款。

## ECMWF 输入及派生数据

本仓库不包含 ECMWF 原始 GRIB2 文件，也不包含处理器生成的预报数据。处理器可读取使用者自行取得的 ECMWF 数据，并将其转换为 PNG、JSON、Int16 二进制网格等浏览器静态资源。

- 数据来源：[ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data)
- 数据使用条款：[ECMWF Terms of Use](https://apps.ecmwf.int/datasets/licences/general/)
- 许可证：[Creative Commons Attribution 4.0 International（CC BY 4.0）](https://creativecommons.org/licenses/by/4.0/)

发布由 ECMWF Open Data 生成的结果时，应在界面或随附文档中显著标出 ECMWF、数据来源、许可证链接和所做修改。可按实际数据年份使用以下中文声明：

> © ECMWF `<数据年份>`；来源：ECMWF Open Data；依据 CC BY 4.0 使用。原始 GRIB2 已由本项目转换为浏览器图层、查询网格和统计信息。

ECMWF 数据按原样提供，ECMWF 不对其准确性、完整性或特定用途适用性作保证。使用者应根据 ECMWF 最新条款核对署名和免责声明要求。

## 软件依赖

`eccodes`、NumPy、Pillow、contourpy、pytest 及其传递依赖分别适用各自许可证。安装包中的许可证文件和上游项目元数据是其完整条款的权威来源；本项目的 Apache-2.0 许可证不覆盖这些第三方组件。
