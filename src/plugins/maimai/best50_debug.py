from __future__ import annotations

import base64
import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Sequence, Union

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Best50DebugItem:
    index: int #序号
    title: str #曲名
    difficulty: str #难度
    rate: str #评级
    achievements: str #达成率
    ra: str = "-" 
    note: str = ""

#图片的参数
@dataclass(frozen=True)
class Best50DebugTheme:
    width: int = 2000             #宽度
    padding: int = 40             #边距
    header_height: int = 220
    summary_height: int = 120
    section_header_height: int = 70
    section_gap: int = 40
    section_card_gap: int = 24
    card_height: int = 140
    card_gap: int = 18
    columns: int = 3

    background_color: tuple[int, int, int, int] = (15, 18, 28, 255)   #背景色
    panel_color: tuple[int, int, int, int] = (24, 29, 42, 255)
    card_color: tuple[int, int, int, int] = (33, 39, 58, 255)
    card_edge_color: tuple[int, int, int, int] = (90, 102, 140, 255)
    grid_color: tuple[int, int, int, int] = (71, 82, 112, 120)
    guide_color: tuple[int, int, int, int] = (255, 190, 92, 170)
    text_color: tuple[int, int, int, int] = (242, 245, 255, 255)
    muted_color: tuple[int, int, int, int] = (165, 173, 203, 255)
    accent_color: tuple[int, int, int, int] = (124, 129, 255, 255)
    pill_color: tuple[int, int, int, int] = (60, 71, 110, 255)

    font_candidates: tuple[str, ...] = (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    )


def _stringify(value: Any) -> str:
    if value is None:
        return "-"
    if hasattr(value, "value"):
        return str(value.value)
    if hasattr(value, "name"):
        return str(value.name)
    return str(value)


def _format_achievements(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.4f}%"
    return _stringify(value)


def build_items_from_mapping(mapping: Sequence[tuple[Any, Any, Any]]) -> list[Best50DebugItem]:
    items: list[Best50DebugItem] = []
    for index, (song, diff, score) in enumerate(mapping, start=1):
        title = _stringify(getattr(song, "title", "未知曲目"))
        difficulty = _stringify(getattr(diff, "type", getattr(diff, "name", "?")))
        rate = _stringify(getattr(score, "rate", "-"))
        achievements = _format_achievements(getattr(score, "achievements", None))

        ra_value = None
        for attr_name in ("ra", "rating", "dx_rating"):
            if hasattr(score, attr_name):
                ra_value = getattr(score, attr_name)
                break

        note = _stringify(getattr(score, "ds", ""))
        if ra_value is not None:
            note = f"{note} -> {_stringify(ra_value)}" if note else _stringify(ra_value)
        #封装成一个对象并返回
        items.append(
            Best50DebugItem(
                index=index,
                title=title,
                difficulty=difficulty,
                rate=rate,
                achievements=achievements,
                ra=_stringify(ra_value) if ra_value is not None else "-",
                note=note,
            )
        )
    return items


def build_demo_items(count: int = 10) -> list[Best50DebugItem]:
    demo_items: list[Best50DebugItem] = []
    difficulties = ["Basic", "Advanced", "Expert", "Master", "Re:Master"]
    for index in range(1, count + 1):
        difficulty = difficulties[(index - 1) % len(difficulties)]
        demo_items.append(
            Best50DebugItem(
                index=index,
                title=f"Demo Song {index:02d}",
                difficulty=difficulty,
                rate="SSS" if index % 3 == 0 else "SS",
                achievements=f"{99.0 + (index % 10) * 0.1:.4f}%",
                ra=str(1200 + index * 35),
                note=f"ds {12.0 + index * 0.1:.1f}",
            )
        )
    return demo_items


class Best50DebugRenderer:
    def __init__(self, theme: Optional[Best50DebugTheme] = None) -> None:
        self.theme = theme or Best50DebugTheme()
        self._font_cache: dict[tuple[int, bool], Any] = {}

    def _load_font(self, size: int, bold: bool = False):
        cache_key = (size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        candidates = list(self.theme.font_candidates)
        if bold:
            candidates = candidates[1:2] + candidates[:1] + candidates[2:]

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                try:
                    font = ImageFont.truetype(candidate, size=size)
                    self._font_cache[cache_key] = font
                    return font
                except OSError:
                    continue

        font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font

    @staticmethod
    def _measure_text(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    def _fit_text(self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
        if not text:
            return ""

        if draw.textlength(text, font=font) <= max_width:
            return text

        ellipsis = "..."
        if draw.textlength(ellipsis, font=font) >= max_width:
            return ellipsis

        left = 0
        right = len(text)
        while left < right:
            mid = (left + right) // 2
            candidate = text[:mid] + ellipsis
            if draw.textlength(candidate, font=font) <= max_width:
                left = mid + 1
            else:
                right = mid

        candidate = text[: max(0, left - 1)] + ellipsis
        while draw.textlength(candidate, font=font) > max_width and candidate != ellipsis:
            candidate = candidate[:-4] + ellipsis if len(candidate) > 4 else ellipsis
        return candidate

    def _draw_labeled_box(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        label: str,
        value: str,
        *,
        label_font,
        value_font,
        fill: tuple[int, int, int, int],
        outline: tuple[int, int, int, int],
        accent: Any = None,
    ) -> None:
        draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=2)
        x1, y1, x2, y2 = box
        if accent is not None:
            draw.rounded_rectangle((x1 + 12, y1 + 12, x1 + 20, y2 - 12), radius=4, fill=accent)
        draw.text((x1 + 30, y1 + 18), label, font=label_font, fill=self.theme.muted_color)
        draw.text((x1 + 30, y1 + 50), value, font=value_font, fill=self.theme.text_color)

    def _draw_grid(self, draw: ImageDraw.ImageDraw, image: Image.Image, step: int = 50) -> None:
        width, height = image.size
        small_font = self._load_font(16)

        for x in range(0, width + 1, step):
            color = self.theme.guide_color if x % (step * 2) == 0 else self.theme.grid_color
            draw.line((x, 0, x, height), fill=color, width=1)
            if x % (step * 2) == 0:
                draw.text((x + 4, 4), str(x), font=small_font, fill=self.theme.muted_color)

        for y in range(0, height + 1, step):
            color = self.theme.guide_color if y % (step * 2) == 0 else self.theme.grid_color
            draw.line((0, y, width, y), fill=color, width=1)
            if y % (step * 2) == 0:
                draw.text((4, y + 2), str(y), font=small_font, fill=self.theme.muted_color)

    def _draw_header(self, draw: ImageDraw.ImageDraw, image: Image.Image, item_count: int) -> None:
        theme = self.theme
        x0 = theme.padding
        y0 = theme.padding
        x1 = theme.width - theme.padding
        header_box = (x0, y0, x1, y0 + theme.header_height)
        draw.rounded_rectangle(header_box, radius=28, fill=theme.panel_color, outline=theme.card_edge_color, width=2)

        title_font = self._load_font(40, bold=True)
        subtitle_font = self._load_font(22)
        info_font = self._load_font(20)

        draw.text((x0 + 28, y0 + 22), "BEST50 Debug Preview", font=title_font, fill=theme.text_color)
        draw.text(
            (x0 + 30, y0 + 80),
            "用于调试布局、字体、留白和卡片层级",
            font=subtitle_font,
            fill=theme.muted_color,
        )
        draw.text(
            (x0 + 30, y0 + 124),
            f"items: {item_count}    columns: {theme.columns}    card: {self.card_width} x {theme.card_height}",
            font=info_font,
            fill=theme.text_color,
        )
        draw.text(
            (x0 + 30, y0 + 156),
            "开启网格后，可以直接看对齐、边界、标题与信息区域是否合理。",
            font=info_font,
            fill=theme.muted_color,
        )

        if self.show_labels:
            self._draw_labeled_box(
                draw,
                (x1 - 330, y0 + 28, x1 - 30, y0 + 108),
                "HEADER",
                "标题 / 玩家信息 / 总览",
                label_font=self._load_font(18),
                value_font=self._load_font(22, bold=True),
                fill=theme.card_color,
                outline=theme.card_edge_color,
                accent=theme.accent_color,
            )
            self._draw_labeled_box(
                draw,
                (x1 - 330, y0 + 118, x1 - 30, y0 + 198),
                "DEBUG",
                "网格 / 边框 / 行高 / 字体",
                label_font=self._load_font(18),
                value_font=self._load_font(22, bold=True),
                fill=theme.card_color,
                outline=theme.card_edge_color,
                accent=theme.guide_color,
            )

    def _draw_summary(self, draw: ImageDraw.ImageDraw, start_y: int) -> int:
        theme = self.theme
        box = (theme.padding, start_y, theme.width - theme.padding, start_y + theme.summary_height)
        draw.rounded_rectangle(box, radius=22, fill=theme.panel_color, outline=theme.card_edge_color, width=2)

        inner_top = start_y + 12
        box_width = (theme.width - theme.padding * 2 - 24) // 3
        gap = 12
        x = theme.padding + 12

        summary_items = [
            ("SUMMARY", "这里放玩家昵称、Rating、牌子、头像等信息"),
            ("STRUCTURE", "建议分成头部、汇总、成绩卡片三个区域"),
            ("STYLE", "先定层级，再定颜色，最后调文字密度"),
        ]
        for label, value in summary_items:
            self._draw_labeled_box(
                draw,
                (x, inner_top, x + box_width, inner_top + 96),
                label,
                value,
                label_font=self._load_font(18),
                value_font=self._load_font(20, bold=True),
                fill=theme.card_color,
                outline=theme.card_edge_color,
                accent=theme.accent_color,
            )
            x += box_width + gap

        return start_y + theme.summary_height + 18

    def _draw_section_header(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        title: str,
        subtitle: str,
        *,
        accent: tuple[int, int, int, int],
        border: tuple[int, int, int, int],
    ) -> None:
        x1, y1, x2, y2 = box
        draw.rounded_rectangle(box, radius=20, fill=self.theme.panel_color, outline=border, width=3)
        draw.rounded_rectangle((x1 + 16, y1 + 14, x1 + 26, y2 - 14), radius=5, fill=accent)
        title_font = self._load_font(26, bold=True)
        subtitle_font = self._load_font(19)
        draw.text((x1 + 50, y1 + 16), title, font=title_font, fill=self.theme.text_color)
        draw.text((x1 + 50, y1 + 45), subtitle, font=subtitle_font, fill=self.theme.muted_color)

    def _draw_card(self, draw: ImageDraw.ImageDraw, item: Best50DebugItem, box: tuple[int, int, int, int]) -> None:
        theme = self.theme
        x1, y1, x2, y2 = box
        draw.rounded_rectangle(box, radius=22, fill=theme.card_color, outline=theme.card_edge_color, width=2)

        accent_color = theme.accent_color if item.index % 2 else theme.guide_color
        draw.rounded_rectangle((x1 + 14, y1 + 14, x1 + 24, y2 - 14), radius=4, fill=accent_color)

        index_font = self._load_font(20, bold=True)
        title_font = self._load_font(26, bold=True)
        meta_font = self._load_font(20)
        small_font = self._load_font(18)

        draw.text((x1 + 38, y1 + 18), f"{item.index:02d}", font=index_font, fill=theme.text_color)
        draw.text((x1 + 84, y1 + 18), item.difficulty, font=meta_font, fill=theme.muted_color)

        title_max_width = (x2 - x1) - 120
        title = self._fit_text(draw, item.title, title_font, title_max_width)
        draw.text((x1 + 38, y1 + 52), title, font=title_font, fill=theme.text_color)

        draw.text((x1 + 38, y1 + 94), f"rate: {item.rate}", font=meta_font, fill=theme.muted_color)
        draw.text((x1 + 230, y1 + 94), f"achievements: {item.achievements}", font=meta_font, fill=theme.muted_color)
        draw.text((x1 + 38, y1 + 126), f"RA: {item.ra}", font=small_font, fill=theme.text_color)

        if item.note:
            note = self._fit_text(draw, item.note, small_font, (x2 - x1) - 150)
            draw.text((x2 - 260, y2 - 34), note, font=small_font, fill=theme.muted_color)

    @property
    def card_width(self) -> int:
        theme = self.theme
        available_width = theme.width - theme.padding * 2 - (theme.columns - 1) * theme.card_gap
        return available_width // theme.columns

    def render(self, items: Sequence[Best50DebugItem], *, title: str = "BEST50 Debug Preview") -> Image.Image:
        theme = self.theme
        card_width = self.card_width
        content_top = theme.padding + theme.header_height + 18 + theme.summary_height + 18
        raw_sections = [
            ("旧版本 BEST35", "", list(items[:35]), theme.accent_color, theme.card_edge_color),
            ("新版本 BEST15", "", list(items[35:50]), theme.guide_color, theme.guide_color),
        ]
        section_items = [section for section in raw_sections if section[2]]

        section_heights: list[int] = []
        for _, _, section_list, _, _ in section_items:
            rows = max(1, math.ceil(len(section_list) / theme.columns))
            cards_height = rows * theme.card_height + (rows - 1) * theme.card_gap
            section_heights.append(theme.section_header_height + theme.section_card_gap + cards_height + 20)

        total_height = content_top + sum(section_heights) + theme.section_gap * max(0, len(section_items) - 1) + theme.padding + 90

        image = Image.new("RGBA", (theme.width, total_height), theme.background_color)
        draw = ImageDraw.Draw(image)

        if self.show_grid:
            self._draw_grid(draw, image)

        self._draw_header(draw, image, len(items))
        content_top = self._draw_summary(draw, theme.padding + theme.header_height + 18)

        if items:
            section_top = content_top
            for section_title, section_subtitle, section_list, accent, border in section_items:
                rows = max(1, math.ceil(len(section_list) / theme.columns))
                cards_height = rows * theme.card_height + (rows - 1) * theme.card_gap
                section_height = theme.section_header_height + theme.section_card_gap + cards_height + 20

                self._draw_section_header(
                    draw,
                    (theme.padding, section_top, theme.width - theme.padding, section_top + theme.section_header_height),
                    section_title,
                    section_subtitle,
                    accent=accent,
                    border=border,
                )

                cards_top = section_top + theme.section_header_height + theme.section_card_gap
                for index, item in enumerate(section_list):
                    row = index // theme.columns
                    col = index % theme.columns
                    x1 = theme.padding + col * (card_width + theme.card_gap)
                    y1 = cards_top + row * (theme.card_height + theme.card_gap)
                    self._draw_card(draw, item, (x1, y1, x1 + card_width, y1 + theme.card_height))

                section_top += section_height + theme.section_gap
        else:
            empty_box = (theme.padding, content_top, theme.width - theme.padding, content_top + 220)
            draw.rounded_rectangle(empty_box, radius=22, fill=theme.card_color, outline=theme.card_edge_color, width=2)
            title_font = self._load_font(28, bold=True)
            #body_font = self._load_font(22)
            draw.text((theme.padding + 28, content_top + 34), "No items to preview", font=title_font, fill=theme.text_color)
            

        footer_font = self._load_font(18)
        footer_y = total_height - 56
        draw.text(
            (theme.padding, footer_y),
            title,
            font=footer_font,
            fill=theme.muted_color,
        )
        draw.text(
            (theme.width - theme.padding, footer_y),
            "debug preview",
            font=footer_font,
            fill=theme.muted_color,
            anchor="ra",
        )

        return image

    @property
    def show_grid(self) -> bool:
        return getattr(self, "_show_grid", True)

    @show_grid.setter
    def show_grid(self, value: bool) -> None:
        self._show_grid = bool(value)

    @property
    def show_labels(self) -> bool:
        return getattr(self, "_show_labels", True)

    @show_labels.setter
    def show_labels(self, value: bool) -> None:
        self._show_labels = bool(value)


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    buffer = BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def save_preview(image: Image.Image, file_path: Union[str, Path]) -> Path:
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target


def render_best50_debug_preview(
    items: Sequence[Best50DebugItem],
    *,
    title: str = "BEST50 Debug Preview",
    show_grid: bool = True,
    show_labels: bool = True,
) -> Image.Image:
    renderer = Best50DebugRenderer()
    renderer.show_grid = show_grid
    renderer.show_labels = show_labels
    return renderer.render(items, title=title)
