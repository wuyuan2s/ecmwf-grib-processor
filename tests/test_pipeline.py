import numpy as np
import pytest
from PIL import Image

from ecmwf_processor.palettes import colourise, hex_to_rgba
from ecmwf_processor.pipeline import (
    GridTransform,
    Frame,
    convert_units,
    field_identifier,
    period_precipitation,
    prepare_render_fields,
    process_grib,
    quantise_query_values,
    regional_slice,
    smooth_field,
    write_contours_png,
)


def test_temperature_converts_kelvin_to_celsius():
    values = np.array([273.15, 300.15], dtype=np.float32)
    assert np.allclose(convert_units("2t", values), [0, 27], atol=1e-4)


def test_pressure_converts_pa_to_hpa():
    assert np.allclose(
        convert_units("msl", np.array([101325], dtype=np.float32)), [1013.25]
    )


def test_upper_air_and_rate_units_are_forecaster_friendly():
    assert np.allclose(convert_units("t", np.array([273.15])), [0.0], atol=1e-4)
    assert np.allclose(convert_units("tprate", np.array([0.001])), [3.6])
    assert np.allclose(convert_units("z", np.array([9806.65])), [1000.0])
    assert np.allclose(convert_units("vo", np.array([0.0001])), [10.0])


def test_pressure_field_identifier_keeps_levels_distinct():
    assert field_identifier("t", "isobaricInhPa", 850) == "t@850"
    assert field_identifier("2t", "heightAboveGround", 2) == "2t"


def test_surface_relative_humidity_is_derived_from_temperature_and_dewpoint():
    frame = Frame(valid_time=None, run_time=None, forecast_hour=0)  # type: ignore[arg-type]
    frame.fields = {
        "2t": np.array([[20.0]], dtype=np.float32),
        "2d": np.array([[20.0]], dtype=np.float32),
    }
    fields = prepare_render_fields(frame, None)
    assert np.allclose(fields["relative_humidity_2m"], [[100.0]])


def test_hex_colour_supports_optional_alpha():
    assert hex_to_rgba("#ffffff") == (255, 255, 255, 255)
    assert hex_to_rgba("#00000000") == (0, 0, 0, 0)


def test_colourise_makes_nan_transparent():
    image = colourise(np.array([[0.0, np.nan]], dtype=np.float32), "temperature")
    assert image.shape == (1, 2, 4)
    assert image[0, 1].tolist() == [0, 0, 0, 0]


def test_period_precipitation_differences_accumulations_and_clips_roundoff():
    previous = np.array([[1.0, 2.0]], dtype=np.float32)
    current = np.array([[3.5, 1.999]], dtype=np.float32)
    result = period_precipitation(current, previous)
    assert np.allclose(result, [[2.5, 0.0]])
    assert np.allclose(period_precipitation(current, None), np.zeros_like(current))


def test_regional_slice_uses_inclusive_regular_grid_bounds():
    transform = GridTransform(
        width=5,
        height=3,
        column_order=np.arange(5),
        flip_rows=False,
        longitude_step=90.0,
        latitude_step=90.0,
    )
    values = np.arange(15, dtype=np.float32).reshape(3, 5)
    subset, bounds = regional_slice(
        values,
        transform,
        {"west": -90.0, "south": 0.0, "east": 90.0, "north": 90.0},
    )
    assert subset.tolist() == [[1.0, 2.0, 3.0], [6.0, 7.0, 8.0]]
    assert bounds["width"] == 3
    assert bounds["height"] == 2


def test_query_quantisation_preserves_scale_offset_and_missing_values():
    values = np.array([[800.0, 1013.25, np.nan]], dtype=np.float32)
    encoded = quantise_query_values(values, scale=0.01, offset=800.0)
    assert encoded.tolist() == [[0, 21325, -32768]]


def test_contour_renderer_interpolates_to_antialiased_high_resolution(tmp_path):
    values = np.add.outer(
        np.arange(8, dtype=np.float32), np.arange(12, dtype=np.float32)
    )
    path = tmp_path / "contours.png"
    write_contours_png(values, path, interval=4.0, radius=0, output_scale=2)

    image = np.asarray(Image.open(path))
    assert image.shape == (16, 24, 4)
    assert np.count_nonzero(image[..., 3]) > 0
    assert np.any((image[..., 3] > 0) & (image[..., 3] < 232))


def test_smooth_field_wraps_longitude_and_preserves_missing_values():
    values = np.array([[10.0, np.nan, 0.0, 0.0]], dtype=np.float32)
    smoothed = smooth_field(values, radius=1)
    assert np.isfinite(smoothed).all()
    assert smoothed[0, -1] > 0.0


def test_clean_refuses_to_delete_unrelated_output(tmp_path):
    output = tmp_path / "data"
    output.mkdir()
    unrelated = output / "keep-me.txt"
    unrelated.write_text("user data")

    with pytest.raises(ValueError, match="拒绝清理"):
        process_grib(tmp_path / "missing.grib2", output, clean=True)

    assert unrelated.read_text() == "user data"
