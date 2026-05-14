from __future__ import annotations

import argparse
import asyncio
import io
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Response
from PIL import Image, ImageDraw, ImageFont

from . import _dither


@dataclass(frozen=True)
class DashboardConfig:
    latitude: float = 51.7559
    longitude: float = 19.4629
    timezone: str = "Europe/Warsaw"
    width: int = 1024
    height: int = 768
    grayscale_levels: int = 16

    @property
    def forecast_url(self) -> str:
        return (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={self.latitude}&longitude={self.longitude}"
            "&current=temperature_2m,apparent_temperature,precipitation,weather_code"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone={self.timezone}&forecast_days=2"
        )

    @property
    def air_quality_url(self) -> str:
        return (
            "https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={self.latitude}&longitude={self.longitude}"
            "&current=european_aqi,pm10,pm2_5"
            f"&timezone={self.timezone}"
        )

    @property
    def quote_url(self) -> str:
        return "https://api.viewbits.com/v1/zenquotes/?mode=today"


async def fetch_dashboard_data(config: DashboardConfig) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        forecast_req = client.get(config.forecast_url)
        air_req = client.get(config.air_quality_url)
        quote_req = client.get(config.quote_url)
        forecast, air, quote = await asyncio.gather(forecast_req, air_req, quote_req)

    forecast.raise_for_status()
    air.raise_for_status()
    quote.raise_for_status()

    quote_payload = quote.json()
    if isinstance(quote_payload, dict) and "data" in quote_payload:
        quote_item = quote_payload["data"][0]
    elif isinstance(quote_payload, list):
        quote_item = quote_payload[0]
    else:
        quote_item = {"q": "Stay awhile and observe.", "a": "Kindle Dashboard"}

    return {"forecast": forecast.json(), "air": air.json(), "quote": quote_item}


def weather_condition(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in {1, 2, 3}:
        return "Clouds"
    if code in {45, 48}:
        return "Fog"
    if code in {51, 53, 55, 56, 57}:
        return "Drizzle"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if code in {95, 96, 99}:
        return "Storm"
    return "Weather"


def air_quality_label(eaqi: int) -> str:
    if eaqi <= 20:
        return "Good"
    if eaqi <= 40:
        return "Fair"
    if eaqi <= 60:
        return "Moderate"
    if eaqi <= 80:
        return "Poor"
    return "Bad"


def load_font(
    size: int,
    bold: bool = False,
    italic: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        name = "OldStandardTT-Bold.ttf"
    elif italic:
        name = "OldStandardTT-Italic.ttf"
    else:
        name = "OldStandardTT-Regular.ttf"

    font = resources.files("kindle_dashboard").joinpath("fonts", name)
    with resources.as_file(font) as path:
        return ImageFont.truetype(str(path), size)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.ImageFont) -> None:
    w, h = text_size(draw, text, font)
    x1, y1, x2, y2 = box
    draw.text((x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2), text, fill=0, font=font)


def tracking_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, spacing: int) -> int:
    if not text:
        return 0
    return sum(text_size(draw, ch, font)[0] for ch in text) + spacing * (len(text) - 1)


def draw_tracking(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    spacing: int,
    fill: int = 0,
) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, fill=fill, font=font)
        x += text_size(draw, ch, font)[0] + spacing


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if text_size(draw, test, font)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_forecast_block(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    low: float,
    high: float,
    rain: float,
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
) -> None:
    x1, y1, x2, y2 = box
    pad_x = 22
    label_y = y1 + int((y2 - y1) * 0.28)
    row_y = label_y + 38
    col_gap = int((x2 - x1) * 0.10)
    col_w = int(((x2 - x1) - pad_x * 2 - col_gap * 2) / 3)
    starts = [x1 + pad_x, x1 + pad_x + col_w + col_gap, x1 + pad_x + (col_w + col_gap) * 2]

    draw_tracking(draw, (x1 + pad_x, label_y), label.upper(), label_font, 3, fill=35)
    for start, small_label, value, font in [
        (starts[0], "LOW", f"{round(low)}°", value_font),
        (starts[1], "HIGH", f"{round(high)}°", value_font),
        (starts[2], "RAIN", f"{rain} mm", small_font),
    ]:
        draw_tracking(draw, (start, row_y), small_label, label_font, 2, fill=70)
        draw.text((start, row_y + 24), value, fill=0 if small_label != "RAIN" else 55, font=font)


def image_to_png(image: Image.Image, levels: int) -> bytes:
    image = image.convert("L")
    pixels = list(image.tobytes())
    dithered = _dither.floyd_steinberg(pixels, image.width, image.height, levels)
    out = Image.frombytes("L", image.size, bytes(dithered))
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def draw_dashboard(data: dict[str, Any], config: DashboardConfig) -> Image.Image:
    forecast = data["forecast"]
    air = data["air"]
    quote = data["quote"]
    current = forecast["current"]
    daily = forecast["daily"]
    eaqi = int(air["current"]["european_aqi"])

    image = Image.new("RGB", (config.width, config.height), "white")
    draw = ImageDraw.Draw(image)

    big = load_font(198, bold=True)
    title = load_font(31, bold=True)
    quote_font = load_font(22, italic=True)
    value_font = load_font(38)
    feels_font = load_font(22)
    rain_font = load_font(17)
    small = load_font(15)
    tiny = load_font(10, bold=True)

    w = config.width
    h = config.height
    top_h = 285
    right_x = int(w * 0.64)
    mid_y = top_h + (h - top_h) // 2

    draw.line((0, top_h, w, top_h), fill=0, width=2)
    draw.line((right_x, top_h, right_x, h), fill=0, width=2)
    draw.line((right_x, mid_y, w, mid_y), fill=42, width=1)

    temp = f"{round(current['temperature_2m'])}°"
    condition = weather_condition(int(current["weather_code"])).upper()
    sub_lines = [
        (condition, title, 0),
        (f"Feels like {round(current['apparent_temperature'])}°", feels_font, 0),
        (f"EAQI {eaqi} · {air_quality_label(eaqi)}", small, 34),
    ]
    temp_w, temp_h = text_size(draw, temp, big)
    sub_w = max(text_size(draw, text, font)[0] for text, font, _ in sub_lines)
    gap = 46
    start_x = (w - temp_w - gap - sub_w) / 2 - 15
    temp_y = (top_h - temp_h) / 2 - 28
    draw.text((start_x, temp_y), temp, fill=0, font=big)

    sub_x = start_x + temp_w + gap
    sub_total_h = sum(text_size(draw, text, font)[1] for text, font, _ in sub_lines) + 46
    sub_y = (top_h - sub_total_h) / 2 + 13
    for text, font, fill in sub_lines:
        tw, th = text_size(draw, text, font)
        draw.text((sub_x + (sub_w - tw) / 2, sub_y), text, fill=fill, font=font)
        sub_y += th + 23

    q_pad_x = int(right_x * 0.06)
    q_lines = wrap_text(draw, quote.get("q", ""), quote_font, right_x - q_pad_x * 2)
    line_h = 35
    quote_h = len(q_lines[:6]) * line_h + 38
    y = top_h + ((h - top_h) - quote_h) / 2
    for line in q_lines[:6]:
        draw.text((q_pad_x, y), line, fill=34, font=quote_font)
        y += line_h
    author = f"— {quote.get('a', 'Unknown')}".upper()
    author_w = tracking_size(draw, author, tiny, 4)
    draw_tracking(draw, (right_x - q_pad_x - author_w, int(y + 9)), author, tiny, 4, fill=102)

    draw_forecast_block(
        draw,
        (right_x, top_h, w, mid_y),
        "Today",
        daily["temperature_2m_min"][0],
        daily["temperature_2m_max"][0],
        daily["precipitation_sum"][0],
        tiny,
        value_font,
        rain_font,
    )
    draw_forecast_block(
        draw,
        (right_x, mid_y, w, h),
        "Tomorrow",
        daily["temperature_2m_min"][1],
        daily["temperature_2m_max"][1],
        daily["precipitation_sum"][1],
        tiny,
        value_font,
        rain_font,
    )

    return image


async def render_dashboard_png(data: dict[str, Any], config: DashboardConfig) -> bytes:
    return image_to_png(draw_dashboard(data, config), config.grayscale_levels)


app = FastAPI(title="Kindle Dashboard Renderer")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard.png")
async def dashboard_png() -> Response:
    config = DashboardConfig()
    data = await fetch_dashboard_data(config)
    png = await render_dashboard_png(data, config)
    return Response(content=png, media_type="image/png")


async def render_file(output: Path) -> None:
    config = DashboardConfig()
    data = await fetch_dashboard_data(config)
    output.write_bytes(await render_dashboard_png(data, config))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render or serve Kindle dashboard PNGs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="Render one PNG file")
    render_parser.add_argument("output", type=Path)

    serve_parser = subparsers.add_parser("serve", help="Run the HTTP server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    if args.command == "render":
        asyncio.run(render_file(args.output))
    else:
        uvicorn.run("kindle_dashboard.app:app", host=args.host, port=args.port)
