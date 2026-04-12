import json
import httpx
from nonebot import on_command, CommandSession
from maimai_py import MaimaiClient, MaimaiPlates, MaimaiScores, MaimaiSongs, PlayerIdentifier, LXNSProvider, DivingFishProvider
from maimai_py.exceptions import (
    InvalidDeveloperTokenError,
    InvalidPlayerIdentifierError,
    PrivacyLimitationError,
)
maimai = MaimaiClient()
divingfish = DivingFishProvider(developer_token="1df190806c37fa307c3a2c5330b920f9451aba7b06df625fba31a441ec0e1b9c773305b722ee1f3a74b23a22b2c560d4840fd0fb8b5f58e307b8b73c759af9ad")
lxns = LXNSProvider(developer_token="ppcjoh-EUfaCjxk875CEsAhiwXJPXDnCmt5JpjmeZ0M=")
@on_command('player_info' , aliases=('查询玩家信息'))
async def player_info(session: CommandSession) :
    try:
        player = await maimai.players(PlayerIdentifier(friend_code=148267199516545), provider=lxns)
        await session.send(str(player.rating))
    except InvalidPlayerIdentifierError:
        await session.send("未找到玩家，请检查绑定信息或玩家标识是否正确。")
    except InvalidDeveloperTokenError:
        await session.send("数据源开发者令牌无效或未配置，请联系管理员检查配置。")
    except PrivacyLimitationError:
        await session.send("该玩家未授权第三方访问数据，暂时无法查询。")
    except httpx.RequestError:
        await session.send("网络请求失败，请稍后重试。")
    except Exception:
        await session.send("查询失败，发生未知错误，请稍后再试。")
