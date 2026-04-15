import httpx
from nonebot import CommandSession, on_command
from maimai_py import PlayerIdentifier
from maimai_py.exceptions import (
    InvalidDeveloperTokenError,
    InvalidPlayerIdentifierError,
    PrivacyLimitationError,
)

from .data_source import current_qq, load_bindings, lxns, maimai, parse_friend_code, save_bindings


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


def _format_best50_line(index: int, song, diff, score) -> str:
    title = _to_text(getattr(song, "title", "未知曲目"))
    diff_type = _to_text(getattr(diff, "type", getattr(diff, "name", "?")))
    rate = _to_text(getattr(score, "rate", "-"))
    achievements = _format_achievements(getattr(score, "achievements", None))

    dx_rating = None
    for attr_name in ("dx_rating", "ra", "rating"):
        if hasattr(score, attr_name):
            dx_rating = getattr(score, attr_name)
            break

    line = f"{index:02d}. {title} | {diff_type} | {rate} | {achievements}"
    if dx_rating is not None:
        line += f" | RA:{_to_text(dx_rating)}"
    return line


async def _query_player_with_handling(
    session: CommandSession,
    friend_code: int,
    *,
    invalid_player_msg: str,
    privacy_msg: str,
    request_error_msg: str,
    unknown_error_msg: str = None,
):
    try:
        return await maimai.players(PlayerIdentifier(friend_code=friend_code), provider=lxns)
    except InvalidPlayerIdentifierError:
        await session.send(invalid_player_msg)
        return None
    except InvalidDeveloperTokenError:
        await session.send("数据源开发者令牌无效或未配置，请联系管理员检查配置。")
        return None
    except PrivacyLimitationError:
        await session.send(privacy_msg)
        return None
    except httpx.RequestError:
        await session.send(request_error_msg)
        return None
    except Exception:
        if unknown_error_msg is not None:
            await session.send(unknown_error_msg)
            return None
        raise


async def _query_bests_mapping_with_handling(
    session: CommandSession,
    friend_code: int,
    *,
    invalid_player_msg: str,
    privacy_msg: str,
    request_error_msg: str,
    unknown_error_msg: str,
):
    try:
        best_scores = await maimai.bests(PlayerIdentifier(friend_code=friend_code), provider=lxns)
        return await best_scores.get_mapping()
    except InvalidPlayerIdentifierError:
        await session.send(invalid_player_msg)
        return None
    except InvalidDeveloperTokenError:
        await session.send("数据源开发者令牌无效或未配置，请联系管理员检查配置。")
        return None
    except PrivacyLimitationError:
        await session.send(privacy_msg)
        return None
    except httpx.RequestError:
        await session.send(request_error_msg)
        return None
    except Exception:
        await session.send(unknown_error_msg)
        return None

#一组文本按固定大小分批发送
async def _send_in_chunks(session: CommandSession, lines: list, chunk_size: int = 10) -> None:
    if not lines:
        return
    for idx in range(0, len(lines), chunk_size):
        await session.send("\n".join(lines[idx: idx + chunk_size]))


@on_command('bind_friend_code', aliases=('绑定好友码', '好友码绑定', '绑定fc'))
async def bind_friend_code(session: CommandSession):
    raw_code = session.current_arg_text.strip()
    if not raw_code:
        raw_code = (await session.aget(prompt='请发送你的好友码（纯数字）。')).strip()

    try:
        friend_code = parse_friend_code(raw_code)
        player = await _query_player_with_handling(
            session,
            friend_code,
            invalid_player_msg="该好友码无效或在 LXNS 中不存在，请确认后重试。",
            privacy_msg="该账号未授权第三方访问数据，暂时无法绑定。",
            request_error_msg="网络请求失败，暂时无法验证好友码，请稍后重试。",
        )
        if player is None:
            return
    except ValueError as e:
        await session.send(str(e))
        return

    qq = current_qq(session)
    if not qq:
        await session.send("无法识别你的 QQ，绑定失败。")
        return

    bindings = load_bindings()
    bindings[qq] = friend_code
    try:
        save_bindings(bindings)
    except OSError:
        await session.send("绑定信息保存失败，请联系管理员检查文件权限。")
        return

    await session.send(f"绑定成功，你的好友码已保存")


@on_command('player_info', aliases=('查询玩家信息',))
async def player_info(session: CommandSession):
    qq = current_qq(session)
    bindings = load_bindings()
    friend_code = bindings.get(qq)
    if not friend_code:
        await session.send("你还没有绑定好友码，请先发送：绑定好友码 你的好友码")
        return

    player = await _query_player_with_handling(
        session,
        int(friend_code),
        invalid_player_msg="当前绑定的好友码无效或未找到玩家，请重新绑定。",
        privacy_msg="该玩家未授权第三方访问数据，暂时无法查询。",
        request_error_msg="网络请求失败，请稍后重试。",
        unknown_error_msg="查询失败，发生未知错误，请稍后再试。",
    )
    if player is None:
        return

    await session.send(str(player.rating))

#查询b50
@on_command('best50', aliases=('b50', '查询b50', '查询best50', 'best50成绩'))
async def best50(session: CommandSession):
    qq = current_qq(session)
    bindings = load_bindings()
    friend_code = bindings.get(qq)
    if not friend_code:
        await session.send("你还没有绑定好友码，请先发送：绑定好友码 你的好友码")
        return

    mapping = await _query_bests_mapping_with_handling(
        session,
        int(friend_code),
        invalid_player_msg="当前绑定的好友码无效或未找到玩家，请重新绑定。",
        privacy_msg="该玩家未授权第三方访问数据，暂时无法查询。",
        request_error_msg="网络请求失败，请稍后重试。",
        unknown_error_msg="查询 BEST50 失败，发生未知错误，请稍后再试。",
    )
    if mapping is None:
        return

    if not mapping:
        await session.send("未查询到 BEST50 成绩。")
        return

    lines = [f"BEST50 成绩（共 {len(mapping)} 条）："]
    for index, (song, diff, score) in enumerate(mapping, start=1):
        lines.append(_format_best50_line(index, song, diff, score))

    await _send_in_chunks(session, lines, chunk_size=10)