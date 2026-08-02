"""CLI entry point for ECMWF GRIB processing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

from .pipeline import process_grib


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecmwf-process",
        description="把 ECMWF GRIB2 转为 Cesium 可直接加载的 PNG + JSON。",
    )
    parser.add_argument("input", type=Path, help="输入 GRIB2 文件")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="输出目录（默认：./output）",
    )
    parser.add_argument(
        "--sample-degrees",
        type=float,
        default=2.0,
        help="点选查询网格的近似分辨率（默认：2°）",
    )
    parser.add_argument("--clean", action="store_true", help="生成前清理输出目录")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not input_path.is_file():
        parser.exit(1, f"错误：找不到输入文件 {input_path}\n")
    try:
        manifest = process_grib(
            input_path,
            output_path,
            sample_degrees=args.sample_degrees,
            clean=args.clean,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"错误：{exc}\n")
    print(f"处理完成：{manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
