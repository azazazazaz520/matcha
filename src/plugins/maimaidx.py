import json
from nonebot import on_command, CommandSession
from maimai_py import MaimaiClient, MaimaiPlates, MaimaiScores, MaimaiSongs, PlayerIdentifier, LXNSProvider, DivingFishProvider
maimai = MaimaiClient()
divingfish = DivingFishProvider(developer_token="1df190806c37fa307c3a2c5330b920f9451aba7b06df625fba31a441ec0e1b9c773305b722ee1f3a74b23a22b2c560d4840fd0fb8b5f58e307b8b73c759af9ad")

@on_command('player_info' , aliases=('查询玩家信息'))
async def player_info(session: CommandSession) :
    player = await maimai.players(PlayerIdentifier(username="azaz114514"), provider=divingfish)
    await session.send(str(player.rating))
