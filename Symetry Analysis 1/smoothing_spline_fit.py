from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_smoothing_spline


DEFAULT_DATA_FILE = Path("intersections.csv hand-editied base-removed.csv")


def load_points(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []

    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames:
            reader.fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]

        for row in reader:
            if not row:
                continue
            x_value = row.get("x")
            y_value = row.get("y")
            if x_value is None or y_value is None:
                continue
            try:
                x = float(x_value)
                y = float(y_value)
            except ValueError:
                continue
            if np.isfinite(x) and np.isfinite(y):
                xs.append(x)
                ys.append(y)

    if not xs:
        raise ValueError(f"No valid numeric point data was found in {path}.")

    x_array = np.asarray(xs, dtype=float)
    y_array = np.asarray(ys, dtype=float)

    order = np.argsort(x_array)
    x_array = x_array[order]
    y_array = y_array[order]

    unique_x, inverse, counts = np.unique(x_array, return_inverse=True, return_counts=True)
    if np.any(counts > 1):
        averaged_y = np.bincount(inverse, weights=y_array) / counts
        x_array = unique_x
        y_array = averaged_y

    return x_array, y_array


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fit a smoothing spline to CSV x,y data and display/save the plot."
    )
    parser.add_argument(
        "data_file",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="CSV file containing x,y data. Defaults to intersections.csv hand-editied base-removed.csv",
    )
    return parser.parse_args()


def make_fit_function(x: np.ndarray, y: np.ndarray):
    spline = make_smoothing_spline(x, y, lam=1.0)

    def fit_function(x_values):
        x_array = np.asarray(x_values, dtype=float)
        return spline(x_array)

    return fit_function


def write_sampled_csv(data_file: Path, x_orig: np.ndarray, y_orig: np.ndarray, fit_function) -> Path:
    sample_start = np.floor(x_orig.min() * 4) / 4.0
    sample_stop = np.ceil(x_orig.max() * 4) / 4.0
    sample_x = np.arange(sample_start, sample_stop + 0.25 / 2.0, 0.25)
    sample_y = fit_function(sample_x)

    output_path = data_file.with_name(f"{data_file.stem}_sampled_spline.csv")
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["original_x", "original_y", "sample_x", "sample_y"])
        max_len = max(len(x_orig), len(sample_x))
        for i in range(max_len):
            original_x = x_orig[i] if i < len(x_orig) else ""
            original_y = y_orig[i] if i < len(y_orig) else ""
            sample_x_value = sample_x[i] if i < len(sample_x) else ""
            sample_y_value = sample_y[i] if i < len(sample_y) else ""
            writer.writerow([original_x, original_y, sample_x_value, sample_y_value])

    return output_path


def write_python_function_file(data_file: Path, x_train: np.ndarray, y_train: np.ndarray) -> Path:
    output_path = data_file.with_name(f"{data_file.stem}_spline_function.py")

    x_list = ", ".join(f"{float(value):.15g}" for value in x_train)
    y_list = ", ".join(f"{float(value):.15g}" for value in y_train)

    function_source = f'''import numpy as np
from scipy.interpolate import make_smoothing_spline


def smoothing_spline_fit(x_values):
    x_train = np.array([{x_list}], dtype=float)
    y_train = np.array([{y_list}], dtype=float)
    spline = make_smoothing_spline(x_train, y_train, lam=1.0)
    x_array = np.asarray(x_values, dtype=float)
    return np.asarray(spline(x_array), dtype=float)
'''
    output_path.write_text(function_source, encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    data_file = args.data_file if args.data_file.is_absolute() else Path.cwd() / args.data_file

    x, y = load_points(data_file)

    if x.size < 3:
        raise ValueError("Need at least three points to fit a smoothing spline.")

    fit_function = make_fit_function(x, y)
    x_fit = np.linspace(x.min(), x.max(), 1000)
    y_fit = fit_function(x_fit)

    output_file = data_file.with_name(f"{data_file.stem}_smoothing_spline.png")
    title = f"Smoothing Spline Fit to {data_file.name}"

    plt.figure(figsize=(10, 6))
    plt.plot(x_fit, y_fit, color="tab:blue", linewidth=2, label="Smoothing spline fit")
    plt.scatter(x, y, color="tab:orange", s=18, label="Original points")
    plt.title(title)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=200)
    plt.show()

    sampled_csv_path = write_sampled_csv(data_file, x, y, fit_function)
    python_function_path = write_python_function_file(data_file, x, y)

    print(f"Fit complete. Plot saved to: {output_file}")
    print(f"Sampled data saved to: {sampled_csv_path}")
    print(f"Python spline function saved to: {python_function_path}")


if __name__ == "__main__":
    main()
