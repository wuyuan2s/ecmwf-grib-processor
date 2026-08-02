"""Colour palettes shared by the image renderer and the web manifest."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


VARIABLES: Dict[str, dict] = {
    "temperature": {
        "source": "2t",
        "label": "2 米气温",
        "shortLabel": "气温",
        "unit": "°C",
        "description": "距地面 2 米处的空气温度",
        "group": "surface",
        "palette": [
            (-50, "#3f007d"),
            (-30, "#2c7fb8"),
            (-10, "#7fcdbb"),
            (0, "#edf8b1"),
            (15, "#fef0a9"),
            (25, "#fdae61"),
            (35, "#f46d43"),
            (50, "#a50026"),
        ],
    },
    "dewpoint": {
        "source": "2d",
        "label": "2 米露点温度",
        "shortLabel": "露点",
        "unit": "°C",
        "description": "反映近地层空气水汽含量的露点温度",
        "group": "surface",
        "palette": [
            (-50, "#4b1d73"),
            (-20, "#315da8"),
            (0, "#60b7aa"),
            (10, "#b8df72"),
            (20, "#ffd166"),
            (30, "#ef476f"),
        ],
    },
    "relative_humidity_2m": {
        "source": "2t + 2d",
        "label": "2 米相对湿度",
        "shortLabel": "湿度",
        "unit": "%",
        "description": "由 2 米气温和露点温度诊断的相对湿度",
        "group": "surface",
        "palette": [
            (0, "#8c510a"),
            (20, "#d8b365"),
            (40, "#f6e8c3"),
            (60, "#c7eae5"),
            (80, "#5ab4ac"),
            (100, "#01665e"),
        ],
    },
    "pressure": {
        "source": "msl",
        "label": "海平面气压",
        "shortLabel": "气压",
        "unit": "hPa",
        "description": "折算到平均海平面的气压",
        "group": "surface",
        "palette": [
            (940, "#5e3c99"),
            (970, "#3288bd"),
            (990, "#66c2a5"),
            (1010, "#e6f598"),
            (1020, "#fee08b"),
            (1040, "#f46d43"),
            (1060, "#9e0142"),
        ],
    },
    "wind_speed": {
        "source": "10u + 10v",
        "label": "10 米风速",
        "shortLabel": "风速",
        "unit": "m/s",
        "description": "由 10 米 U、V 风分量合成的风速",
        "group": "surface",
        "palette": [
            (0, "#10243b20"),
            (2, "#64d8cb90"),
            (5, "#39d353d0"),
            (10, "#f9e547e8"),
            (15, "#ff9f43f0"),
            (25, "#ff4d6df5"),
            (40, "#b5179eff"),
            (60, "#5a189aff"),
        ],
    },
    "wind_gust": {
        "source": "10fg",
        "label": "10 米最大阵风",
        "shortLabel": "阵风",
        "unit": "m/s",
        "description": "上一后处理时段内的 10 米最大阵风",
        "group": "surface",
        "palette": [
            (0, "#10243b20"),
            (5, "#64d8cb90"),
            (10, "#39d353d0"),
            (15, "#f9e547e8"),
            (20, "#ff9f43f0"),
            (30, "#ff4d6df5"),
            (40, "#b5179eff"),
            (60, "#5a189aff"),
        ],
    },
    "precipitation_period": {
        "source": "tp difference",
        "label": "时段降水",
        "shortLabel": "时段雨",
        "unit": "mm",
        "description": "上一预报时次至当前时次的累计降水",
        "group": "surface",
        "palette": [
            (0, "#00000000"),
            (0.1, "#d8f3dc40"),
            (1, "#74c69db0"),
            (5, "#52b788dd"),
            (10, "#168aadf0"),
            (25, "#4361eef5"),
            (50, "#7209b7fa"),
            (100, "#f72585ff"),
        ],
    },
    "precipitation": {
        "source": "tp",
        "label": "起报累计降水",
        "shortLabel": "累计雨",
        "unit": "mm",
        "description": "从起报时刻累计到当前时效的总降水",
        "group": "surface",
        "palette": [
            (0, "#00000000"),
            (0.1, "#d8f3dc40"),
            (1, "#74c69db0"),
            (5, "#52b788dd"),
            (10, "#168aadf0"),
            (25, "#4361eef5"),
            (50, "#7209b7fa"),
            (100, "#f72585ff"),
        ],
    },
    "precipitation_rate": {
        "source": "tprate",
        "label": "瞬时降水率",
        "shortLabel": "降水率",
        "unit": "mm/h",
        "description": "有效时刻附近的模式瞬时降水强度",
        "group": "surface",
        "palette": [
            (0, "#00000000"),
            (0.1, "#d8f3dc40"),
            (1, "#74c69db0"),
            (2.5, "#52b788dd"),
            (5, "#168aadf0"),
            (10, "#4361eef5"),
            (25, "#7209b7fa"),
            (50, "#f72585ff"),
        ],
    },
    "precipitation_type": {
        "source": "ptype",
        "label": "降水相态",
        "shortLabel": "雨雪相态",
        "unit": "类型",
        "description": "结合降水率使用的地面雨、雪、冻雨等相态",
        "group": "surface",
        "categories": [
            (0, "无降水", "#00000000"),
            (1, "雨", "#39b86bde"),
            (3, "冻雨", "#f72585f2"),
            (5, "雪", "#e7f6fff2"),
            (6, "湿雪", "#9ad9fff2"),
            (7, "雨夹雪", "#8f75d6f2"),
            (8, "冰粒", "#ffb347f2"),
            (12, "冻毛毛雨", "#ff6f91f2"),
        ],
        "palette": [
            (0, "#00000000"),
            (1, "#39b86bde"),
            (3, "#f72585f2"),
            (5, "#e7f6fff2"),
            (6, "#9ad9fff2"),
            (7, "#8f75d6f2"),
            (8, "#ffb347f2"),
            (12, "#ff6f91f2"),
        ],
    },
    "cloud_cover": {
        "source": "tcc",
        "label": "总云量",
        "shortLabel": "云量",
        "unit": "%",
        "description": "天空被云覆盖的比例",
        "group": "surface",
        "palette": [
            (0, "#d9f0ff10"),
            (20, "#c9e8f850"),
            (40, "#b8d8e880"),
            (60, "#a7c4d4a8"),
            (80, "#e3e9efcf"),
            (100, "#ffffffff"),
        ],
    },
    "total_column_water_vapour": {
        "source": "tcwv",
        "label": "整层水汽含量",
        "shortLabel": "整层水汽",
        "unit": "kg/m²",
        "description": "单位面积大气柱内的总水汽质量",
        "group": "surface",
        "palette": [
            (0, "#2b1055"),
            (10, "#3c4ba8"),
            (20, "#2d8fbd"),
            (30, "#3bc4a3"),
            (40, "#a8db70"),
            (55, "#ffd166"),
            (70, "#ef476f"),
            (85, "#9b1d67"),
        ],
    },
    "mucape": {
        "source": "mucape",
        "label": "最不稳定 CAPE",
        "shortLabel": "MUCAPE",
        "unit": "J/kg",
        "description": "最不稳定气块的对流有效位能，仅作为强对流环境指标之一",
        "group": "surface",
        "palette": [
            (0, "#00000000"),
            (100, "#c7e9c080"),
            (500, "#74c476c0"),
            (1000, "#fdd835dd"),
            (2000, "#fb8c00ee"),
            (3000, "#e53935f2"),
            (5000, "#8e24aaf8"),
        ],
    },
    "temperature_850": {
        "source": "t@850",
        "label": "850 hPa 温度与风",
        "shortLabel": "850 温风",
        "unit": "°C",
        "description": "低层冷暖平流与暖湿输送诊断，叠加 850 hPa 风场",
        "group": "upper",
        "level": 850,
        "vectorLevel": 850,
        "palette": [
            (-35, "#313695"),
            (-20, "#4575b4"),
            (-5, "#74add1"),
            (0, "#e0f3f8"),
            (10, "#fee090"),
            (20, "#fdae61"),
            (30, "#d73027"),
            (40, "#7f0000"),
        ],
    },
    "relative_humidity_700": {
        "source": "r@700",
        "label": "700 hPa 相对湿度",
        "shortLabel": "700 湿度",
        "unit": "%",
        "description": "中低层湿区与干侵入诊断",
        "group": "upper",
        "level": 700,
        "palette": [
            (0, "#8c510a"),
            (20, "#d8b365"),
            (40, "#f6e8c3"),
            (60, "#c7eae5"),
            (80, "#5ab4ac"),
            (100, "#01665e"),
        ],
    },
    "vorticity_500": {
        "source": "vo@500",
        "label": "500 hPa 高度与涡度",
        "shortLabel": "500 高涡",
        "unit": "10⁻⁵ s⁻¹",
        "description": "中层槽脊和正涡度扰动，叠加 60 gpm 等高线",
        "group": "upper",
        "level": 500,
        "palette": [
            (-30, "#2166ac"),
            (-15, "#67a9cf"),
            (-5, "#d1e5f0"),
            (0, "#ffffff20"),
            (5, "#fddbc7"),
            (15, "#ef8a62"),
            (30, "#b2182b"),
        ],
    },
    "wind_speed_200": {
        "source": "u@200 + v@200",
        "label": "200 hPa 高空急流",
        "shortLabel": "200 急流",
        "unit": "m/s",
        "description": "对流层上部急流轴和高空辐散背景诊断",
        "group": "upper",
        "level": 200,
        "vectorLevel": 200,
        "palette": [
            (0, "#10243b20"),
            (15, "#64d8cb80"),
            (25, "#39d353c0"),
            (35, "#f9e547e8"),
            (45, "#ff9f43f0"),
            (60, "#ff4d6df5"),
            (80, "#7b2cbfff"),
        ],
    },
}


def hex_to_rgba(value: str) -> Tuple[int, int, int, int]:
    """Parse #RRGGBB or #RRGGBBAA colours."""
    raw = value.lstrip("#")
    if len(raw) == 6:
        raw += "ff"
    if len(raw) != 8:
        raise ValueError(f"无效颜色：{value}")
    return tuple(int(raw[index : index + 2], 16) for index in range(0, 8, 2))  # type: ignore[return-value]


def palette_for_manifest(variable: str) -> List[dict]:
    return [
        {"value": value, "color": colour}
        for value, colour in VARIABLES[variable]["palette"]
    ]


def categories_for_manifest(variable: str) -> List[dict]:
    return [
        {"value": value, "label": label, "color": colour}
        for value, label, colour in VARIABLES[variable].get("categories", [])
    ]


def colourise(values: np.ndarray, variable: str) -> np.ndarray:
    """Linearly map a two-dimensional value array to RGBA pixels."""
    categories = VARIABLES[variable].get("categories")
    if categories:
        rgba = np.zeros((*values.shape, 4), dtype=np.uint8)
        for value, _, colour in categories:
            rgba[np.isclose(values, value)] = hex_to_rgba(colour)
        rgba[~np.isfinite(values)] = (0, 0, 0, 0)
        return rgba
    stops = VARIABLES[variable]["palette"]
    stop_values = np.asarray([stop[0] for stop in stops], dtype=np.float64)
    colours = np.asarray([hex_to_rgba(stop[1]) for stop in stops], dtype=np.float64)
    finite = np.isfinite(values)
    safe_values = np.where(finite, values, stop_values[0])
    rgba = np.empty((*values.shape, 4), dtype=np.uint8)
    for channel in range(4):
        rgba[..., channel] = np.interp(
            safe_values, stop_values, colours[:, channel]
        ).astype(np.uint8)
    rgba[~finite] = (0, 0, 0, 0)
    return rgba
