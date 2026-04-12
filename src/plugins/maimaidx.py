import json
import httpx
from pathlib import Path
from nonebot import on_command, CommandSession
from maimai_py import MaimaiClient, MaimaiPlates, MaimaiScores, MaimaiSongs, PlayerIdentifier, LXNSProvider, DivingFishProvider
from maimai_py.exceptions import (
    InvalidDeveloperTokenError,
    InvalidPlayerIdentifierError,
    PrivacyLimitationError,
)
maimai = MaimaiClient()
# 目前不使用水鱼
# divingfish = DivingFishProvider(developer_token="1df190806c37fa307c3a2c5330b920f9451aba7b06df625fba31a441ec0e1b9c773305b722ee1f3a74b23a22b2c560d4840fd0fb8b5f58e307b8b73c759af9ad")
lxns = LXNSProvider(developer_token="ppcjoh-EUfaCjxk875CEsAhiwXJPXDnCmt5JpjmeZ0M=")

DATA_DIR = Path(__file__).resolve().parent / "data"
BINDINGS_FILE = DATA_DIR / "lxns_bindings.json"


def _load_bindings() -> dict:
    if not BINDINGS_FILE.exists():
        return {}
    try:
        with BINDINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        return {}
    return {}


def _save_bindings(bindings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with BINDINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(bindings, f, ensure_ascii=False, indent=2)


def _current_qq(session: CommandSession) -> str:
    return str(session.ctx.get("user_id", ""))


def _parse_friend_code(raw: str) -> int:
    code = raw.strip()
    if not code.isdigit():
        raise ValueError("好友码必须是纯数字。")
    if len(code) < 8:
        raise ValueError("好友码长度不正确，请检查后重试。")
    return int(code)

#绑定落雪好友码
@on_command('bind_friend_code', aliases=('绑定好友码', '绑定friend_code', '绑定fc'))
async def bind_friend_code(session: CommandSession):
    raw_code = session.current_arg_text.strip()
    if not raw_code:
        raw_code = (await session.aget(prompt='请发送你的好友码（纯数字）。')).strip()

    try:
        friend_code = _parse_friend_code(raw_code)
        # 绑定前先用 LXNS 校验一次，避免写入无效好友码
        await maimai.players(PlayerIdentifier(friend_code=friend_code), provider=lxns)
    except ValueError as e:
        await session.send(str(e))
        return
    except InvalidPlayerIdentifierError:
        await session.send("该好友码无效或在 LXNS 中不存在，请确认后重试。")
        return
    except InvalidDeveloperTokenError:
        await session.send("数据源开发者令牌无效或未配置，请联系管理员检查配置。")
        return
    except PrivacyLimitationError:
        await session.send("该账号未授权第三方访问数据，暂时无法绑定。")
        return
    except httpx.RequestError:
        await session.send("网络请求失败，暂时无法验证好友码，请稍后重试。")
        return

    qq = _current_qq(session)
    if not qq:
        await session.send("无法识别你的 QQ，绑定失败。")
        return

    bindings = _load_bindings()
    bindings[qq] = friend_code
    try:
        _save_bindings(bindings)
    except OSError:
        await session.send("绑定信息保存失败，请联系管理员检查文件权限。")
        return

    await session.send(f"绑定成功，你的好友码已保存：{friend_code}")


@on_command('player_info' , aliases=('查询玩家信息'))
async def player_info(session: CommandSession) :
    qq = _current_qq(session)
    bindings = _load_bindings()
    friend_code = bindings.get(qq)
    if not friend_code:
        await session.send("你还没有绑定好友码，请先发送：绑定好友码 你的好友码")
        return

    try:
        player = await maimai.players(PlayerIdentifier(friend_code=int(friend_code)), provider=lxns)
        await session.send(str(player.rating))
    except InvalidPlayerIdentifierError:
        await session.send("当前绑定的好友码无效或未找到玩家，请重新绑定。")
    except InvalidDeveloperTokenError:
        await session.send("数据源开发者令牌无效或未配置，请联系管理员检查配置。")
    except PrivacyLimitationError:
        await session.send("该玩家未授权第三方访问数据，暂时无法查询。")
    except httpx.RequestError:
        await session.send("网络请求失败，请稍后重试。")
    except Exception:
        await session.send("查询失败，发生未知错误，请稍后再试。")
