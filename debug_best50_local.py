#!/usr/bin/env python3
"""
本地调试脚本：快速生成 BEST50 图片用于测试
使用方式：
  python debug_best50_local.py demo          # 生成 demo 数据（50条）
  python debug_best50_local.py demo 20       # 生成 demo 数据（20条）
  python debug_best50_local.py real <fc>    # 使用真实好友码查询数据
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.plugins.maimai.best50_debug import (
    build_demo_items,
    Best50DebugItem,
    render_best50_debug_preview,
    save_preview,
    image_to_base64,
)
from src.plugins.maimai.data_source import lxns, maimai
from maimai_py import PlayerIdentifier


def _to_text(value) -> str:
    if value is None:
        return "-"
    if hasattr(value, "value"):
        return str(value.value)
    if hasattr(value, "name"):
        return str(value.name)
    return str(value)


def _format_achievements(value) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.4f}%"
    return _to_text(value)


def generate_demo_image(count: int = 50) -> Path:
    """生成 demo 图片"""
    print(f"[INFO] 生成 {count} 条 demo 数据...")
    items = build_demo_items(count)
    
    print(f"[INFO] 渲染图片...")
    image = render_best50_debug_preview(
        items,
        title=f"BEST50 Demo 预览（{count} 条）",
        show_grid=False,
        show_labels=False,
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(f"debug/best50_demo_{count}_{timestamp}.png")
    save_preview(image, output)
    
    print(f"[SUCCESS] 图片已保存: {output}")
    print(f"[INFO] 尺寸: {image.size}")
    return output


async def generate_real_image(friend_code: int) -> Path:
    """使用真实好友码生成图片"""
    print(f"[INFO] 查询好友码 {friend_code} 的数据...")
    
    try:
        best_scores = await maimai.bests(PlayerIdentifier(friend_code=friend_code), provider=lxns)
        mapping = await best_scores.get_mapping()
    except Exception as e:
        print(f"[ERROR] 查询失败: {e}")
        return None
    
    if not mapping:
        print("[WARNING] 未查询到成绩")
        return None
    
    print(f"[INFO] 获得 {len(mapping)} 条成绩，正在构建项目列表...")
    
    items = []
    for index, (song, diff, score) in enumerate(mapping, start=1):
        title = _to_text(getattr(song, "title", "未知曲目"))
        difficulty = _to_text(getattr(diff, "type", getattr(diff, "name", "?")))
        rate = _to_text(getattr(score, "rate", "-"))
        achievements = _format_achievements(getattr(score, "achievements", None))
        
        ra_value = None
        for attr_name in ("dx_rating", "ra", "rating"):
            if hasattr(score, attr_name):
                ra_value = getattr(score, attr_name)
                break
        
        note = _to_text(getattr(score, "ds", ""))
        if ra_value is not None:
            note = f"{note} -> {_to_text(ra_value)}" if note else _to_text(ra_value)
        
        items.append(
            Best50DebugItem(
                index=index,
                title=title,
                difficulty=difficulty,
                rate=rate,
                achievements=achievements,
                ra=_to_text(ra_value) if ra_value is not None else "-",
                note=note,
            )
        )
    
    print(f"[INFO] 渲染图片...")
    image = render_best50_debug_preview(
        items,
        title=f"BEST50 成绩预览（{len(items)} 条）",
        show_grid=False,
        show_labels=False,
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(f"debug/best50_real_{friend_code}_{timestamp}.png")
    save_preview(image, output)
    
    print(f"[SUCCESS] 图片已保存: {output}")
    print(f"[INFO] 尺寸: {image.size}")
    return output


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "demo":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        output = generate_demo_image(count)
        print(f"\n[TIP] 打开文件: {output.absolute()}")
    
    elif mode == "real":
        if len(sys.argv) < 3:
            print("[ERROR] 缺少好友码参数")
            print(__doc__)
            sys.exit(1)
        
        friend_code = int(sys.argv[2])
        asyncio.run(generate_real_image(friend_code))
    
    else:
        print(f"[ERROR] 未知模式: {mode}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
