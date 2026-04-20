import json
from pathlib import Path

from nonebot import CommandSession
from maimai_py import LXNSProvider, MaimaiClient


maimai = MaimaiClient()
# 目前不使用水鱼
# divingfish = DivingFishProvider(developer_token="1df190806c37fa307c3a2c5330b920f9451aba7b06df625fba31a441ec0e1b9c773305b722ee1f3a74b23a22b2c560d4840fd0fb8b5f58e307b8b73c759af9ad")
lxns = LXNSProvider(developer_token="ppcjoh-EUfaCjxk875CEsAhiwXJPXDnCmt5JpjmeZ0M=")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BINDINGS_FILE = DATA_DIR / "lxns_bindings.json"


def load_bindings() -> dict:
    if not BINDINGS_FILE.exists():
        return {}
    try:
        with BINDINGS_FILE.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        return {}
    return {}

#保存好友码
def save_bindings(bindings: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with BINDINGS_FILE.open("w", encoding="utf-8") as file_handle:
        json.dump(bindings, file_handle, ensure_ascii=False, indent=2)

#获取qq号
def current_qq(session: CommandSession) -> str:
    return str(session.ctx.get("user_id", ""))

#检查好友码
def parse_friend_code(raw: str) -> int:
    code = raw.strip()
    if not code.isdigit():
        raise ValueError("好友码必须是纯数字。")
    if len(code) < 8:
        raise ValueError("好友码长度不正确，请检查后重试。")
    return int(code)