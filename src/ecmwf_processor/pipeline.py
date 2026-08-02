"""Read regular-latitude/longitude GRIB2 fields and emit web assets."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
from contourpy import contour_generator
from eccodes import (
    codes_get,
    codes_get_array,
    codes_grib_new_from_file,
    codes_release,
)
from PIL import Image, ImageDraw

from .palettes import (
    VARIABLES,
    categories_for_manifest,
    colourise,
    palette_for_manifest,
)


SOURCE_TO_VARIABLE = {
    "2t": "temperature",
    "2d": "dewpoint",
    "msl": "pressure",
    "10fg": "wind_gust",
    "tp": "precipitation",
    "tprate": "precipitation_rate",
    "ptype": "precipitation_type",
    "tcc": "cloud_cover",
    "tcwv": "total_column_water_vapour",
    "mucape": "mucape",
}
WIND_COMPONENTS = {"10u", "10v"}
PRESSURE_LEVEL_FIELDS = {
    "t@850",
    "u@850",
    "v@850",
    "r@850",
    "r@700",
    "w@700",
    "z@500",
    "vo@500",
    "u@200",
    "v@200",
}
MISSING_VALUE = -9999.0
QUERY_MISSING_VALUE = -32768
ANALYSIS_BOUNDS = {"west": 70.0, "south": 0.0, "east": 145.0, "north": 60.0}
QUERY_VARIABLES = {
    "temperature": {"scale": 0.01, "offset": 0.0},
    "dewpoint": {"scale": 0.01, "offset": 0.0},
    "relative_humidity_2m": {"scale": 0.1, "offset": 0.0},
    "pressure": {"scale": 0.01, "offset": 800.0},
    "wind_speed": {"scale": 0.01, "offset": 0.0},
    "wind_gust": {"scale": 0.01, "offset": 0.0},
    "precipitation_period": {"scale": 0.1, "offset": 0.0},
    "precipitation": {"scale": 0.1, "offset": 0.0},
    "precipitation_rate": {"scale": 0.01, "offset": 0.0},
    "precipitation_type": {"scale": 1.0, "offset": 0.0},
    "cloud_cover": {"scale": 0.1, "offset": 0.0},
    "total_column_water_vapour": {"scale": 0.01, "offset": 0.0},
    "mucape": {"scale": 0.5, "offset": 0.0},
}


@dataclass
class Frame:
    valid_time: datetime
    run_time: datetime
    forecast_hour: int
    fields: Dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class GridTransform:
    width: int
    height: int
    column_order: np.ndarray
    flip_rows: bool
    longitude_step: float
    latitude_step: float

    def apply(self, values: np.ndarray) -> np.ndarray:
        grid = values.reshape(self.height, self.width)
        if self.flip_rows:
            grid = np.flip(grid, axis=0)
        return grid[:, self.column_order]


def parse_grib_datetime(date_value: int, time_value: int) -> datetime:
    date_text = str(int(date_value))
    time_text = f"{int(time_value):04d}"
    return datetime.strptime(date_text + time_text, "%Y%m%d%H%M").replace(
        tzinfo=timezone.utc
    )


def convert_units(short_name: str, values: np.ndarray) -> np.ndarray:
    converted = values.astype(np.float32, copy=False)
    if short_name in {"2t", "2d", "t"}:
        return converted - np.float32(273.15)
    if short_name == "msl":
        return converted / np.float32(100.0)
    if short_name == "tp":
        return converted * np.float32(1000.0)
    if short_name == "tcc":
        return converted * np.float32(100.0)
    if short_name == "tprate":
        return converted * np.float32(3600.0)
    if short_name == "z":
        return converted / np.float32(9.80665)
    if short_name == "vo":
        return converted * np.float32(100000.0)
    return converted


def field_identifier(short_name: str, type_of_level: str, level: int) -> str:
    if type_of_level in {"isobaricInhPa", "isobaricInPa"}:
        pressure_level = level if type_of_level == "isobaricInhPa" else level // 100
        return f"{short_name}@{pressure_level}"
    return short_name


def build_transform(handle: int) -> GridTransform:
    grid_type = str(codes_get(handle, "gridType"))
    if grid_type != "regular_ll":
        raise ValueError(
            f"目前只支持 regular_ll 规则经纬网格，当前数据为 {grid_type}"
        )
    width = int(codes_get(handle, "Ni"))
    height = int(codes_get(handle, "Nj"))
    latitudes = np.asarray(codes_get_array(handle, "latitudes")).reshape(
        height, width
    )
    longitudes = np.asarray(codes_get_array(handle, "longitudes")).reshape(
        height, width
    )
    flip_rows = bool(latitudes[0, 0] < latitudes[-1, 0])
    first_row_lons = longitudes[-1 if flip_rows else 0]
    normalised_lons = (first_row_lons + 180.0) % 360.0 - 180.0
    column_order = np.argsort(normalised_lons)
    sorted_lons = normalised_lons[column_order]
    sorted_lats = latitudes[::-1, 0] if flip_rows else latitudes[:, 0]
    longitude_step = float(np.median(np.diff(sorted_lons)))
    latitude_step = float(abs(np.median(np.diff(sorted_lats))))
    return GridTransform(
        width=width,
        height=height,
        column_order=column_order,
        flip_rows=flip_rows,
        longitude_step=longitude_step,
        latitude_step=latitude_step,
    )


def read_grib(path: Path) -> Tuple[Dict[str, Frame], GridTransform]:
    frames: Dict[str, Frame] = {}
    transform: Optional[GridTransform] = None
    message_count = 0
    with path.open("rb") as stream:
        while True:
            handle = codes_grib_new_from_file(stream)
            if handle is None:
                break
            try:
                short_name = str(codes_get(handle, "shortName"))
                type_of_level = str(codes_get(handle, "typeOfLevel"))
                level = int(codes_get(handle, "level"))
                field_name = field_identifier(short_name, type_of_level, level)
                if (
                    short_name not in SOURCE_TO_VARIABLE
                    and short_name not in WIND_COMPONENTS
                    and field_name not in PRESSURE_LEVEL_FIELDS
                ):
                    continue
                if transform is None:
                    transform = build_transform(handle)
                run_time = parse_grib_datetime(
                    int(codes_get(handle, "dataDate")),
                    int(codes_get(handle, "dataTime")),
                )
                valid_time = parse_grib_datetime(
                    int(codes_get(handle, "validityDate")),
                    int(codes_get(handle, "validityTime")),
                )
                forecast_hour = int(
                    round((valid_time - run_time).total_seconds() / 3600.0)
                )
                key = valid_time.isoformat()
                frame = frames.setdefault(
                    key,
                    Frame(
                        valid_time=valid_time,
                        run_time=run_time,
                        forecast_hour=forecast_hour,
                    ),
                )
                raw_values = np.asarray(codes_get_array(handle, "values"))
                values = transform.apply(raw_values)
                frame.fields[field_name] = convert_units(short_name, values)
                message_count += 1
            finally:
                codes_release(handle)

    if transform is None or message_count == 0:
        raise ValueError("文件中没有找到支持的 ECMWF 要素")
    return frames, transform


def finite_stats(values: np.ndarray) -> dict:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"min": None, "max": None, "mean": None}
    return {
        "min": round(float(np.min(finite)), 2),
        "max": round(float(np.max(finite)), 2),
        "mean": round(float(np.mean(finite)), 2),
    }


def timestamp_slug(frame: Frame) -> str:
    return f"{frame.valid_time:%Y%m%dT%H%MZ}-f{frame.forecast_hour:03d}"


def write_png(values: np.ndarray, variable: str, path: Path) -> None:
    rgba = colourise(values, variable)
    Image.fromarray(rgba, mode="RGBA").save(path, format="PNG", optimize=True)


def period_precipitation(
    current: np.ndarray, previous: Optional[np.ndarray]
) -> np.ndarray:
    """Return non-negative precipitation accumulated since the previous frame."""
    if previous is None:
        return np.zeros_like(current, dtype=np.float32)
    difference = current.astype(np.float32, copy=False) - previous.astype(
        np.float32, copy=False
    )
    return np.maximum(difference, np.float32(0.0)).astype(np.float32)


def regional_slice(
    values: np.ndarray, transform: GridTransform, bounds: dict = ANALYSIS_BOUNDS
) -> Tuple[np.ndarray, dict]:
    """Extract an inclusive regular-grid subset for China and nearby seas."""
    x0 = max(0, int(round((bounds["west"] + 180.0) / transform.longitude_step)))
    x1 = min(
        transform.width - 1,
        int(round((bounds["east"] + 180.0) / transform.longitude_step)),
    )
    y0 = max(0, int(round((90.0 - bounds["north"]) / transform.latitude_step)))
    y1 = min(
        transform.height - 1,
        int(round((90.0 - bounds["south"]) / transform.latitude_step)),
    )
    subset = values[y0 : y1 + 1, x0 : x1 + 1]
    actual_bounds = {
        "west": round(-180.0 + x0 * transform.longitude_step, 6),
        "south": round(90.0 - y1 * transform.latitude_step, 6),
        "east": round(-180.0 + x1 * transform.longitude_step, 6),
        "north": round(90.0 - y0 * transform.latitude_step, 6),
        "width": int(subset.shape[1]),
        "height": int(subset.shape[0]),
        "longitudeStep": round(transform.longitude_step, 6),
        "latitudeStep": round(transform.latitude_step, 6),
    }
    return subset, actual_bounds


def quantise_query_values(values: np.ndarray, scale: float, offset: float) -> np.ndarray:
    """Quantise a field to compact signed 16-bit values for browser queries."""
    encoded = np.rint((values.astype(np.float64) - offset) / scale)
    finite = np.isfinite(values)
    encoded = np.clip(encoded, -32767, 32767)
    encoded = np.where(finite, encoded, QUERY_MISSING_VALUE)
    return encoded.astype("<i2")


def write_isobars_png(
    pressure: np.ndarray, path: Path, interval: float = 4.0
) -> None:
    """Render smooth, antialiased pressure contours with subtle major lines."""
    write_contours_png(
        pressure,
        path,
        interval=interval,
        radius=2,
        major_interval=20.0,
    )


def smooth_field(values: np.ndarray, radius: int) -> np.ndarray:
    """Apply a missing-aware box filter, wrapping across the date line."""
    source = values.astype(np.float64, copy=False)
    if radius <= 0:
        return source.copy()
    finite = np.isfinite(source)

    def window_sum(array: np.ndarray) -> np.ndarray:
        padded = np.pad(array, ((radius, radius), (0, 0)), mode="edge")
        padded = np.pad(padded, ((0, 0), (radius, radius)), mode="wrap")
        integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant")
        integral = integral.cumsum(0).cumsum(1)
        window = radius * 2 + 1
        return (
            integral[window:, window:]
            - integral[:-window, window:]
            - integral[window:, :-window]
            + integral[:-window, :-window]
        )

    totals = window_sum(np.where(finite, source, 0.0))
    counts = window_sum(finite.astype(np.float64))
    return np.divide(
        totals,
        counts,
        out=np.full(source.shape, np.nan, dtype=np.float64),
        where=counts > 0,
    )


def write_contours_png(
    values: np.ndarray,
    path: Path,
    interval: float,
    radius: int = 3,
    colour: tuple = (230, 255, 252, 232),
    halo_colour: tuple = (18, 42, 52, 112),
    major_interval: Optional[float] = None,
    output_scale: int = 2,
) -> None:
    """Render interpolated vector contours to a high-resolution RGBA overlay."""
    if interval <= 0:
        raise ValueError("等值线间隔必须大于 0")
    if output_scale < 1:
        raise ValueError("等值线输出倍率必须至少为 1")

    smoothed = smooth_field(values, radius)
    finite_values = smoothed[np.isfinite(smoothed)]
    if finite_values.size == 0:
        Image.new(
            "RGBA",
            (values.shape[1] * output_scale, values.shape[0] * output_scale),
        ).save(path, format="PNG", optimize=True)
        return

    first_level = np.ceil(np.min(finite_values) / interval) * interval
    last_level = np.floor(np.max(finite_values) / interval) * interval
    levels = np.arange(first_level, last_level + interval * 0.5, interval)
    generator = contour_generator(
        z=np.ma.masked_invalid(smoothed),
        name="serial",
        line_type="Separate",
        corner_mask=True,
    )

    antialias_scale = output_scale * 2
    render_size = (
        values.shape[1] * antialias_scale,
        values.shape[0] * antialias_scale,
    )
    x_scale = (render_size[0] - 1) / max(values.shape[1] - 1, 1)
    y_scale = (render_size[1] - 1) / max(values.shape[0] - 1, 1)
    paths = []
    for level in levels:
        is_major = bool(
            major_interval
            and np.isclose(level / major_interval, round(level / major_interval))
        )
        for line in generator.lines(float(level)):
            if line.shape[0] < 2:
                continue
            points = [
                (float(point[0]) * x_scale, float(point[1]) * y_scale)
                for point in line
            ]
            paths.append((points, is_major))

    image = Image.new("RGBA", render_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width_ratio = antialias_scale / output_scale
    for points, is_major in paths:
        width = round((7 if is_major else 5) * width_ratio)
        draw.line(points, fill=halo_colour, width=width, joint="curve")
    for points, is_major in paths:
        width = round((3 if is_major else 2) * width_ratio)
        draw.line(points, fill=colour, width=width, joint="curve")

    output_size = (
        values.shape[1] * output_scale,
        values.shape[0] * output_scale,
    )
    image = image.resize(output_size, resample=Image.Resampling.LANCZOS)
    image.save(path, format="PNG", optimize=True)


def prepare_render_fields(
    frame: Frame, previous_precipitation: Optional[np.ndarray]
) -> Dict[str, np.ndarray]:
    render_fields: Dict[str, np.ndarray] = {}
    for source_name, variable in SOURCE_TO_VARIABLE.items():
        if source_name in frame.fields:
            render_fields[variable] = frame.fields[source_name]
    if "10u" in frame.fields and "10v" in frame.fields:
        render_fields["wind_speed"] = np.hypot(
            frame.fields["10u"], frame.fields["10v"]
        ).astype(np.float32)
    if "temperature" in render_fields and "dewpoint" in render_fields:
        temperature = render_fields["temperature"]
        dewpoint = render_fields["dewpoint"]
        numerator = np.exp((17.625 * dewpoint) / (243.04 + dewpoint))
        denominator = np.exp((17.625 * temperature) / (243.04 + temperature))
        render_fields["relative_humidity_2m"] = np.clip(
            100.0 * numerator / denominator, 0.0, 100.0
        ).astype(np.float32)
    if "precipitation" in render_fields:
        render_fields["precipitation_period"] = period_precipitation(
            render_fields["precipitation"], previous_precipitation
        )
    if "t@850" in frame.fields:
        render_fields["temperature_850"] = frame.fields["t@850"]
    if "r@700" in frame.fields:
        render_fields["relative_humidity_700"] = np.clip(
            frame.fields["r@700"], 0.0, 100.0
        ).astype(np.float32)
    if "vo@500" in frame.fields:
        render_fields["vorticity_500"] = frame.fields["vo@500"]
    if "u@200" in frame.fields and "v@200" in frame.fields:
        render_fields["wind_speed_200"] = np.hypot(
            frame.fields["u@200"], frame.fields["v@200"]
        ).astype(np.float32)
    return render_fields


def write_regional_query_grid(
    prepared_frames: list,
    transform: GridTransform,
    query_dir: Path,
) -> dict:
    """Write one compact, full-resolution regional grid for point time series."""
    query_dir.mkdir(parents=True, exist_ok=True)
    field_order = [
        name
        for name in QUERY_VARIABLES
        if any(name in render_fields for _, render_fields, _ in prepared_frames)
    ]
    blocks = []
    actual_bounds = None
    for _, render_fields, _ in prepared_frames:
        reference = next(iter(render_fields.values()))
        for name in field_order:
            values = render_fields.get(name)
            if values is None:
                values = np.full(reference.shape, np.nan, dtype=np.float32)
            subset, bounds = regional_slice(values, transform)
            actual_bounds = bounds
            encoding = QUERY_VARIABLES[name]
            blocks.append(
                quantise_query_values(
                    subset, encoding["scale"], encoding["offset"]
                ).tobytes(order="C")
            )
    binary_name = "china-grid.i16"
    (query_dir / binary_name).write_bytes(b"".join(blocks))
    assert actual_bounds is not None
    return {
        **actual_bounds,
        "resolution": f"{transform.longitude_step:g}°",
        "binary": f"query/{binary_name}",
        "layout": "frame-major-field-major-row-major-int16le",
        "missing": QUERY_MISSING_VALUE,
        "fieldOrder": field_order,
        "encoding": {
            name: {
                "scale": QUERY_VARIABLES[name]["scale"],
                "offset": QUERY_VARIABLES[name]["offset"],
            }
            for name in field_order
        },
    }


def sample_fields(
    fields: Dict[str, np.ndarray], transform: GridTransform, degrees: float
) -> dict:
    stride = max(1, int(round(degrees / transform.longitude_step)))
    sampled_fields = {}
    sample_height = 0
    sample_width = 0
    for name, values in fields.items():
        sampled = values[::stride, ::stride]
        sample_height, sample_width = sampled.shape
        cleaned = np.where(np.isfinite(sampled), np.round(sampled, 2), MISSING_VALUE)
        sampled_fields[name] = cleaned.astype(float).ravel().tolist()
    return {
        "west": -180.0,
        "east": 180.0,
        "north": 90.0,
        "south": -90.0,
        "width": sample_width,
        "height": sample_height,
        "longitudeStep": round(transform.longitude_step * stride, 6),
        "latitudeStep": round(transform.latitude_step * stride, 6),
        "missing": MISSING_VALUE,
        "fields": sampled_fields,
    }


def manifest_variable(name: str) -> dict:
    metadata = VARIABLES[name]
    result = {
        "label": metadata["label"],
        "shortLabel": metadata["shortLabel"],
        "unit": metadata["unit"],
        "description": metadata["description"],
        "source": metadata["source"],
        "palette": palette_for_manifest(name),
        "group": metadata.get("group", "surface"),
    }
    if metadata.get("level"):
        result["level"] = metadata["level"]
    if metadata.get("vectorLevel"):
        result["vectorLevel"] = metadata["vectorLevel"]
    categories = categories_for_manifest(name)
    if categories:
        result["categories"] = categories
    if name == "precipitation":
        result["stepType"] = "accumulation-from-run"
    elif name == "precipitation_period":
        result["stepType"] = "interval-accumulation"
    else:
        result["stepType"] = "instant"
    return result


def process_grib(
    input_path: Path,
    output_dir: Path,
    sample_degrees: float = 2.0,
    clean: bool = False,
) -> Path:
    if sample_degrees <= 0:
        raise ValueError("sample-degrees 必须大于 0")
    if clean and output_dir.exists():
        generated_names = {
            ".DS_Store",
            "manifest.json",
            "layers",
            "samples",
            "wind",
            "query",
        }
        existing_names = {item.name for item in output_dir.iterdir()}
        resolved_output = output_dir.resolve()
        if resolved_output == Path(resolved_output.anchor) or resolved_output == Path.home():
            raise ValueError(f"拒绝清理高风险目录：{resolved_output}")
        if existing_names - generated_names:
            extras = ", ".join(sorted(existing_names - generated_names))
            raise ValueError(f"输出目录包含非处理器文件，拒绝清理：{extras}")
        shutil.rmtree(output_dir)
    layers_dir = output_dir / "layers"
    samples_dir = output_dir / "samples"
    wind_dir = output_dir / "wind"
    query_dir = output_dir / "query"
    layers_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)
    wind_dir.mkdir(parents=True, exist_ok=True)
    query_dir.mkdir(parents=True, exist_ok=True)

    frames, transform = read_grib(input_path)
    manifest_frames = []
    available_variables = set()
    prepared_frames = []
    previous_precipitation = None
    previous_forecast_hour = None

    for frame in sorted(frames.values(), key=lambda item: item.valid_time):
        render_fields = prepare_render_fields(frame, previous_precipitation)
        period_hours = (
            0
            if previous_forecast_hour is None
            else frame.forecast_hour - previous_forecast_hour
        )
        prepared_frames.append((frame, render_fields, period_hours))
        if "precipitation" in render_fields:
            previous_precipitation = render_fields["precipitation"]
        previous_forecast_hour = frame.forecast_hour

    for frame, render_fields, period_hours in prepared_frames:

        slug = timestamp_slug(frame)
        layers = {}
        for variable, values in render_fields.items():
            image_name = f"{slug}-{variable}.png"
            write_png(values, variable, layers_dir / image_name)
            layers[variable] = {
                "image": f"layers/{image_name}",
                "stats": finite_stats(values),
                "regionalStats": finite_stats(regional_slice(values, transform)[0]),
            }
            if variable == "precipitation_period":
                layers[variable]["periodHours"] = period_hours
            available_variables.add(variable)

        overlays = {}
        if "pressure" in render_fields:
            isobar_name = f"{slug}-isobars.png"
            write_isobars_png(render_fields["pressure"], layers_dir / isobar_name)
            overlays["pressureContours"] = {
                "image": f"layers/{isobar_name}",
                "interval": 4,
                "unit": "hPa",
                "label": "4 hPa 等压线",
            }

        if "vorticity_500" in layers and "z@500" in frame.fields:
            height_name = f"{slug}-height-500.png"
            write_contours_png(
                frame.fields["z@500"],
                layers_dir / height_name,
                interval=60.0,
                radius=2,
                colour=(255, 244, 196, 232),
                halo_colour=(43, 32, 17, 112),
                major_interval=300.0,
            )
            layers["vorticity_500"]["overlay"] = {
                "image": f"layers/{height_name}",
                "interval": 60,
                "unit": "gpm",
                "label": "60 gpm 等高线",
            }

        sample_name = f"{slug}.json"
        query_fields = {
            name: values
            for name, values in render_fields.items()
            if VARIABLES[name].get("group", "surface") == "surface"
        }
        sample_payload = sample_fields(query_fields, transform, sample_degrees)
        (samples_dir / sample_name).write_text(
            json.dumps(sample_payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        wind_sample_path = None
        if "10u" in frame.fields and "10v" in frame.fields:
            wind_name = f"{slug}.json"
            wind_payload = sample_fields(
                {
                    "wind_speed": render_fields["wind_speed"],
                    "wind_u": frame.fields["10u"],
                    "wind_v": frame.fields["10v"],
                },
                transform,
                min(1.0, sample_degrees),
            )
            (wind_dir / wind_name).write_text(
                json.dumps(wind_payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            wind_sample_path = f"wind/{wind_name}"

        vector_samples = {}
        for level in (850, 200):
            u_name = f"u@{level}"
            v_name = f"v@{level}"
            if u_name not in frame.fields or v_name not in frame.fields:
                continue
            vector_name = f"{slug}-{level}.json"
            vector_payload = sample_fields(
                {
                    "wind_speed": np.hypot(
                        frame.fields[u_name], frame.fields[v_name]
                    ).astype(np.float32),
                    "wind_u": frame.fields[u_name],
                    "wind_v": frame.fields[v_name],
                },
                transform,
                min(1.0, sample_degrees),
            )
            (wind_dir / vector_name).write_text(
                json.dumps(vector_payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            vector_samples[level] = f"wind/{vector_name}"

        for variable, layer in layers.items():
            vector_level = VARIABLES[variable].get("vectorLevel")
            if vector_level in vector_samples:
                layer["vectorSample"] = vector_samples[vector_level]

        frame_manifest = {
            "validTime": frame.valid_time.isoformat().replace("+00:00", "Z"),
            "forecastHour": frame.forecast_hour,
            "sample": f"samples/{sample_name}",
            "layers": layers,
            "overlays": overlays,
        }
        if wind_sample_path:
            frame_manifest["windSample"] = wind_sample_path
        manifest_frames.append(frame_manifest)

    if not manifest_frames:
        raise ValueError("没有生成任何可视化帧")

    query_grid = write_regional_query_grid(prepared_frames, transform, query_dir)

    first_frame = min(frames.values(), key=lambda item: item.valid_time)
    sidecar_path = input_path.with_suffix(input_path.suffix + ".json")
    source_metadata = {}
    if sidecar_path.exists():
        try:
            source_metadata = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            source_metadata = {}

    manifest = {
        "schemaVersion": 2,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dataset": {
            "title": "ECMWF IFS 全球预报",
            "model": source_metadata.get("model", "ifs").upper(),
            "runTime": first_frame.run_time.isoformat().replace("+00:00", "Z"),
            "resolution": f"{transform.longitude_step:g}°",
            "forecastRangeHours": max(
                item.forecast_hour for item in frames.values()
            ),
            "frameIntervalHours": (
                manifest_frames[1]["forecastHour"] - manifest_frames[0]["forecastHour"]
                if len(manifest_frames) > 1
                else 0
            ),
            "attribution": "© ECMWF",
            "sourceUrl": "https://www.ecmwf.int/en/forecasts/datasets/open-data",
            "license": "CC BY 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
        },
        "bounds": {"west": -180, "south": -90, "east": 180, "north": 90},
        "analysisArea": {
            "label": "中国及邻近海域",
            **ANALYSIS_BOUNDS,
        },
        "queryGrid": query_grid,
        "variables": {
            name: manifest_variable(name)
            for name in VARIABLES
            if name in available_variables
        },
        "frames": manifest_frames,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest_path
