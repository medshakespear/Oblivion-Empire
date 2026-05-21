# ══════════════════════════════════════════════════════════════════════
#  games.py  —  Oblivion Empire Games Cog
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio, random, unicodedata, re, os, io
from typing import Optional

from PIL import Image

from bot import (db, save_db, brand, empire_embed, logo_url, log_action,
                 bot_avatar, _all_hero_names, HERO_IMAGES_DIR,
                 GOLD, CRIMSON, VIOLET, TEAL, EMERALD, STEEL, AMBER,
                 PHANTOM, OBSIDIAN, SEP, SEP2)

# ══════════════════════════════════════════════════════════════════════
#  COMPLETE HOK HERO ROSTER  — add new heroes at the bottom
# ══════════════════════════════════════════════════════════════════════

HOK_HEROES: dict[str, dict] = {
    # ── Clash Lane ─────────────────────────────────────────────────
    "Lian Po":           {"class":"Tank",    "lane":"Clash Lane"},
    "Arthur":            {"class":"Tank",    "lane":"Clash Lane"},
    "Dun":               {"class":"Tank",    "lane":"Clash Lane"},
    "Augran":            {"class":"Tank",    "lane":"Clash Lane"},
    "Kaizer":            {"class":"Fighter", "lane":"Clash Lane"},
    "Dolia":             {"class":"Tank",    "lane":"Clash Lane"},
    "Sun Ce":            {"class":"Tank",    "lane":"Clash Lane"},
    "Allain":            {"class":"Fighter", "lane":"Clash Lane"},
    "Biron":             {"class":"Fighter", "lane":"Clash Lane"},
    "Charlotte":         {"class":"Fighter", "lane":"Clash Lane"},
    "Mayene":            {"class":"Fighter", "lane":"Clash Lane"},
    "Li Xin":            {"class":"Fighter", "lane":"Clash Lane"},
    "Bai Qi":            {"class":"Fighter", "lane":"Clash Lane"},
    "Xiang Yu":          {"class":"Fighter", "lane":"Clash Lane"},
    "Loong":             {"class":"Fighter", "lane":"Clash Lane"},
    "Liu Bei":           {"class":"Fighter", "lane":"Clash Lane"},
    "Guan Yu":           {"class":"Fighter", "lane":"Clash Lane"},
    "Mulan":             {"class":"Fighter", "lane":"Clash Lane"},
    "Zilong":            {"class":"Fighter", "lane":"Clash Lane"},
    "Yang Jian":         {"class":"Fighter", "lane":"Clash Lane"},
    "Dian Wei":          {"class":"Fighter", "lane":"Clash Lane"},
    "Yixing":            {"class":"Fighter", "lane":"Clash Lane"},
    "Lu Bu":             {"class":"Fighter", "lane":"Clash Lane"},
    "Musashi":           {"class":"Fighter", "lane":"Clash Lane"},
    "Agudo":             {"class":"Fighter", "lane":"Clash Lane"},
    "Athena":            {"class":"Tank",    "lane":"Clash Lane"},
    "Wuyan":             {"class":"Fighter", "lane":"Clash Lane"},
    "Nezha":             {"class":"Fighter", "lane":"Clash Lane"},
    "Fatih":             {"class":"Fighter", "lane":"Clash Lane"},
    # ── Jungle ─────────────────────────────────────────────────────
    "Lam":               {"class":"Assassin","lane":"Jungle"},
    "Prince of Lanling": {"class":"Assassin","lane":"Jungle"},
    "Han Xin":           {"class":"Assassin","lane":"Jungle"},
    "Jing":              {"class":"Assassin","lane":"Jungle"},
    "Li Bai":            {"class":"Assassin","lane":"Jungle"},
    "Cao Cao":           {"class":"Assassin","lane":"Jungle"},
    "Milady":            {"class":"Assassin","lane":"Jungle"},
    "Consort Yu":        {"class":"Assassin","lane":"Jungle"},
    "Shangguan":         {"class":"Assassin","lane":"Jungle"},
    "Ying":              {"class":"Assassin","lane":"Jungle"},
    "Wukong":            {"class":"Fighter", "lane":"Jungle"},
    "Menki":             {"class":"Fighter", "lane":"Jungle"},
    "Gao":               {"class":"Assassin","lane":"Jungle"},
    "Gan & Mo":          {"class":"Assassin","lane":"Jungle"},
    "Ukyo Tachibana":    {"class":"Assassin","lane":"Jungle"},
    "Butterfly":         {"class":"Assassin","lane":"Jungle"},
    "Zhou Yu":           {"class":"Assassin","lane":"Jungle"},
    "Feyd":              {"class":"Assassin","lane":"Jungle"},
    # ── Mid Lane ───────────────────────────────────────────────────
    "Diaochan":          {"class":"Mage",    "lane":"Mid Lane"},
    "Angela":            {"class":"Mage",    "lane":"Mid Lane"},
    "Kongming":          {"class":"Mage",    "lane":"Mid Lane"},
    "Mi Yue":            {"class":"Mage",    "lane":"Mid Lane"},
    "Mai Shiranui":      {"class":"Mage",    "lane":"Mid Lane"},
    "Princess Frost":    {"class":"Mage",    "lane":"Mid Lane"},
    "Liang":             {"class":"Mage",    "lane":"Mid Lane"},
    "Sima Yi":           {"class":"Mage",    "lane":"Mid Lane"},
    "Lady Zhen":         {"class":"Mage",    "lane":"Mid Lane"},
    "Shouyue":           {"class":"Mage",    "lane":"Mid Lane"},
    "Donghuang":         {"class":"Mage",    "lane":"Mid Lane"},
    "Ming":              {"class":"Mage",    "lane":"Mid Lane"},
    "Ziya":              {"class":"Mage",    "lane":"Mid Lane"},
    "Yao":               {"class":"Mage",    "lane":"Mid Lane"},
    "Shi":               {"class":"Mage",    "lane":"Mid Lane"},
    "Heino":             {"class":"Mage",    "lane":"Mid Lane"},
    "Di Renjie":         {"class":"Mage",    "lane":"Mid Lane"},
    "Kui":               {"class":"Mage",    "lane":"Mid Lane"},
    "Xuance":            {"class":"Mage",    "lane":"Mid Lane"},
    "Cirrus":            {"class":"Mage",    "lane":"Mid Lane"},
    "Dharma":            {"class":"Mage",    "lane":"Mid Lane"},
    "Nu Wa":             {"class":"Mage",    "lane":"Mid Lane"},
    "Guiguzi":           {"class":"Mage",    "lane":"Mid Lane"},
    "Daji":              {"class":"Mage",    "lane":"Mid Lane"},
    "Meng Ya":           {"class":"Mage",    "lane":"Mid Lane"},
    # ── Farm Lane ──────────────────────────────────────────────────
    "Marco Polo":        {"class":"Marksman","lane":"Farm Lane"},
    "Hou Yi":            {"class":"Marksman","lane":"Farm Lane"},
    "Luban No. 7":       {"class":"Marksman","lane":"Farm Lane"},
    "Huang Zhong":       {"class":"Marksman","lane":"Farm Lane"},
    "Mozi":              {"class":"Marksman","lane":"Farm Lane"},
    "Nakoruru":          {"class":"Marksman","lane":"Farm Lane"},
    "Arli":              {"class":"Marksman","lane":"Farm Lane"},
    "Luara":             {"class":"Marksman","lane":"Farm Lane"},
    "Fang":              {"class":"Marksman","lane":"Farm Lane"},
    "Alessio":           {"class":"Marksman","lane":"Farm Lane"},
    "Erin":              {"class":"Marksman","lane":"Farm Lane"},
    "Garo":              {"class":"Marksman","lane":"Farm Lane"},
    "Arke":              {"class":"Marksman","lane":"Farm Lane"},
    "Chano":             {"class":"Marksman","lane":"Farm Lane"},
    "Chi Cha":           {"class":"Marksman","lane":"Farm Lane"},
    "Yuhuan":            {"class":"Marksman","lane":"Farm Lane"},
    # ── Roaming ────────────────────────────────────────────────────
    "Da Qiao":           {"class":"Support", "lane":"Roaming"},
    "Lady Sun":          {"class":"Support", "lane":"Roaming"},
    "Yaria":             {"class":"Support", "lane":"Roaming"},
    "Zhuangzi":          {"class":"Support", "lane":"Roaming"},
    "Sun Bin":           {"class":"Support", "lane":"Roaming"},
    "Liu Shan":          {"class":"Support", "lane":"Roaming"},
    "Xiao Qiao":         {"class":"Support", "lane":"Roaming"},
    "Cai Yan":           {"class":"Support", "lane":"Roaming"},
    "Fuzi":              {"class":"Support", "lane":"Roaming"},
    "Pei":               {"class":"Tank",    "lane":"Roaming"},
    "Zhang Fei":         {"class":"Tank",    "lane":"Roaming"},
    "Ata":               {"class":"Support", "lane":"Roaming"},
    "Luna":              {"class":"Support", "lane":"Roaming"},
    "Garuda":            {"class":"Support", "lane":"Roaming"},
    "Sakeer":            {"class":"Support", "lane":"Roaming"},
    "Haya":              {"class":"Support", "lane":"Roaming"},
    "DaYu":              {"class":"Support", "lane":"Roaming"},
    "Dr Bian":           {"class":"Support", "lane":"Roaming"},
    # ── Add new heroes below ───────────────────────────────────────
    # "Hero Name": {"class": "CLASS", "lane": "LANE"},
}

# ══════════════════════════════════════════════════════════════════════
#  HERO QUOTES  (Guess by Quote game)
# ══════════════════════════════════════════════════════════════════════

HOK_QUOTES: dict[str, str] = {
    "Lian Po":           "I have broken armies with my body alone. You are no different.",
    "Arthur":            "A knight's strength means nothing without the honour that guides it.",
    "Dun":               "I gave my eye for loyalty. I would give the other without hesitation.",
    "Augran":            "The boundary between order and chaos is exactly where I stand.",
    "Kaizer":            "Speed, power, precision — I have mastered all three.",
    "Dolia":             "I was built to endure. Everything else is noise.",
    "Sun Ce":            "The south is mine. The rest is only a matter of time.",
    "Allain":            "I don't pick sides — I pick winners.",
    "Biron":             "The bigger the target, the more satisfying the hit.",
    "Charlotte":         "Strength without style is just noise.",
    "Mayene":            "Every wound I take makes me stronger. Keep trying.",
    "Li Xin":            "I close the gap before you even see me move.",
    "Bai Qi":            "I have buried kingdoms. What makes you think you are different?",
    "Xiang Yu":          "Heaven itself chose to end me. Even so, I do not regret a single battle.",
    "Loong":             "I am the will of the dragon — ancient, unbreakable, eternal.",
    "Liu Bei":           "A true ruler earns the hearts of the people, not just their obedience.",
    "Guan Yu":           "Loyalty above all — even above life itself.",
    "Mulan":             "They said I could not fight. I said nothing — and won.",
    "Zilong":            "Speed is my armour. Precision is my shield.",
    "Yang Jian":         "Heaven sees all things. And I see further than heaven.",
    "Dian Wei":          "Weapons are merely tools. My body is the weapon.",
    "Yixing":            "Every strike carries the weight of everything I have endured.",
    "Lu Bu":             "The heavens produced me. The earth cannot contain me.",
    "Musashi":           "I have won every duel not because I am lucky — but because I do not hesitate.",
    "Agudo":             "The jungle speaks, and I listen. They never hear it coming.",
    "Athena":            "Wisdom guides this shield. Courage guides this spear.",
    "Wuyan":             "They call me ugly. I call it armor against distraction.",
    "Nezha":             "I burn bright enough for everyone — and I do not care who gets scorched.",
    "Fatih":             "Conquest is not a destination. It is a way of life.",
    "Lam":               "The way of the blade has no shortcuts.",
    "Prince of Lanling": "Behind this mask is the last face you will ever see.",
    "Han Xin":           "Strike from where they least expect. That is the only rule I follow.",
    "Jing":              "I do not miss. I never have.",
    "Li Bai":            "Wine in one hand, sword in the other — the road ahead is mine.",
    "Cao Cao":           "Heroes rise and fall, but I alone will shape this age.",
    "Milady":            "Elegance and lethality — why choose only one?",
    "Consort Yu":        "For him I would bring down the stars themselves.",
    "Shangguan":         "Words are my blade. And my blade never misses.",
    "Ying":              "Silence is my greatest weapon. You will not hear me coming.",
    "Wukong":            "No cage in heaven or earth can hold the Great Sage Equal to Heaven!",
    "Menki":             "The jungle is mine. Everything in it answers to me.",
    "Gao":               "My melody ends where your heartbeat does.",
    "Gan & Mo":          "Two blades. One soul. Neither of us fights alone.",
    "Ukyo Tachibana":    "Cherry blossoms fall. So do my enemies. Both are beautiful.",
    "Butterfly":         "I flutter between worlds. You will never pin me down.",
    "Zhou Yu":           "Music and war — both require perfect timing.",
    "Feyd":              "Power is not taken. It is simply… remembered.",
    "Diaochan":          "Every man who looks upon me sees only what he wishes to see.",
    "Angela":            "Love is the most powerful force in the universe. Believe me.",
    "Kongming":          "The battle is won long before the first blade is ever drawn.",
    "Mi Yue":            "A woman who survives the palace learns to strike first.",
    "Mai Shiranui":      "My flames dance. My enemies do not.",
    "Princess Frost":    "Everything I touch turns cold. Everything cold stays that way.",
    "Liang":             "An unmovable wall is just as deadly as a sharpened blade.",
    "Sima Yi":           "I do not rush. Time is the only weapon I need.",
    "Lady Zhen":         "I am the poem they never got to finish writing.",
    "Shouyue":           "The moon remembers every battle fought beneath it.",
    "Donghuang":         "I am the first emperor. I will also be the last.",
    "Ming":              "Light and shadow are two sides of the same truth.",
    "Ziya":              "The stars have already written the outcome. I merely read it.",
    "Yao":               "Balance is not given. It must be enforced.",
    "Shi":               "Every note I play is a step closer to your end.",
    "Heino":             "My ice does not melt. My will does not either.",
    "Di Renjie":         "Every crime leaves a trace. Every criminal leaves a story.",
    "Kui":               "The thunder speaks. I translate.",
    "Xuance":            "Between worlds, between truths — I walk where no one else can.",
    "Cirrus":            "The wind does not ask permission. Neither do I.",
    "Dharma":            "All things are illusion. All illusions can be shattered.",
    "Nu Wa":             "I shaped this world with my own hands. I can reshape it again.",
    "Guiguzi":           "The greatest battles are fought in the mind, not on the field.",
    "Daji":              "They call it a curse. I call it a gift.",
    "Meng Ya":           "I dream of a world without war. Until then, I fight.",
    "Marco Polo":        "Every map has an edge — I have yet to find mine.",
    "Hou Yi":            "I once shot nine suns from the sky. You are but one more target.",
    "Luban No. 7":       "Model seven, online. All systems… exceeding expectations.",
    "Huang Zhong":       "Age is just a number. My aim has never been sharper.",
    "Mozi":              "Engineering is the truest form of warfare.",
    "Nakoruru":          "Nature speaks to those who learn to listen.",
    "Arli":              "The further the distance, the more I enjoy it.",
    "Luara":             "Every arrow is a promise. I always keep my promises.",
    "Fang":              "Fast, precise, lethal. In that order.",
    "Alessio":           "Style is strategy. I have both.",
    "Erin":              "I see the future in my arrows. They always find their mark.",
    "Garo":              "The darkness is not my enemy. It is my home.",
    "Arke":              "I was born in starlight. I will return you to dust.",
    "Chano":             "I carry the hopes of my tribe on every arrow I fire.",
    "Chi Cha":           "Quick and deadly. That is all you need to know about me.",
    "Yuhuan":            "Beauty is the most devastating weapon ever crafted.",
    "Da Qiao":           "A gentle hand can still turn the tide of war.",
    "Lady Sun":          "Do not mistake my smile for weakness.",
    "Yaria":             "The spirits answer when I call.",
    "Zhuangzi":          "Am I a man dreaming of a butterfly, or a butterfly dreaming of a man?",
    "Sun Bin":           "A broken leg taught me to see farther than any general on horseback.",
    "Liu Shan":          "I know what others think of me. I choose my own path anyway.",
    "Xiao Qiao":         "My hands carry music. My heart carries war.",
    "Cai Yan":           "My songs have crossed a thousand miles of sorrow.",
    "Fuzi":              "True strength lies not in power, but in lifting others.",
    "Pei":               "Stand behind me. Nothing gets through.",
    "Zhang Fei":         "Come then! All of you at once — it will save time!",
    "Ata":               "My path was written in the stars. I simply follow it.",
    "Luna":              "The moonlight guides those who are truly lost.",
    "Garuda":            "I descend from the heavens. Few rise back up to meet me.",
    "Sakeer":            "Every shield I raise protects a story worth saving.",
    "Haya":              "The forest does not fear the storm. Neither do I.",
    "DaYu":              "The floodwaters once obeyed me. So will you.",
    "Dr Bian":           "Life and death rest in my hands. I choose life — for now.",
}

# ══════════════════════════════════════════════════════════════════════
#  HERO ALIASES  —  shortcuts players can type
# ══════════════════════════════════════════════════════════════════════

HERO_ALIASES: dict[str, str] = {
    "gan jiang and mo ye":"Gan & Mo", "gan jiang mo ye":"Gan & Mo",
    "gan mo":"Gan & Mo", "ganmo":"Gan & Mo", "gan":"Gan & Mo",
    "luban":"Luban No. 7", "luban7":"Luban No. 7",
    "lu ban":"Luban No. 7", "luban no 7":"Luban No. 7",
    "lanling":"Prince of Lanling", "prince lanling":"Prince of Lanling",
    "zhuge liang":"Kongming", "zhuge":"Kongming",
    "bian que":"Dr Bian", "bian":"Dr Bian",
    "shangguan waner":"Shangguan", "wan er":"Shangguan", "waner":"Shangguan",
    "marco":"Marco Polo",
    "consort":"Consort Yu",
    "nuwa":"Nu Wa", "nu wu":"Nu Wa",
    "monkey":"Wukong", "monkey king":"Wukong", "sun wukong":"Wukong",
    "lianpo":"Lian Po", "zhangfei":"Zhang Fei", "guanyu":"Guan Yu",
    "libai":"Li Bai", "caocao":"Cao Cao", "liubei":"Liu Bei",
    "baiqi":"Bai Qi", "xiangyu":"Xiang Yu", "hanxin":"Han Xin",
    "diaochan":"Diaochan", "direnjie":"Di Renjie", "huangzhong":"Huang Zhong",
    "ladysun":"Lady Sun", "caiyan":"Cai Yan", "sunbin":"Sun Bin",
    "liushan":"Liu Shan", "sunce":"Sun Ce", "yangjian":"Yang Jian",
    "dianwei":"Dian Wei", "daqiao":"Da Qiao", "da qiao":"Da Qiao",
    "xiaoqiao":"Xiao Qiao", "xiao qiao":"Xiao Qiao",
    "ukyo":"Ukyo Tachibana",
    "frost":"Princess Frost", "princessfrost":"Princess Frost",
    "zhuangzi":"Zhuangzi", "mai":"Mai Shiranui",
    "zhou yu":"Zhou Yu", "zhouyu":"Zhou Yu",
    "simayi":"Sima Yi", "ladyzhen":"Lady Zhen", "lady zhen":"Lady Zhen",
    "miye":"Mi Yue", "mi yue":"Mi Yue",
    "arke":"Arke", "feyd":"Feyd", "daji":"Daji", "yaria":"Yaria",
    "nakoruru":"Nakoruru", "mozi":"Mozi", "loong":"Loong", "lam":"Lam",
    "luara":"Luara", "arli":"Arli", "chano":"Chano", "garo":"Garo",
    "butterfly":"Butterfly", "garuda":"Garuda", "dayu":"DaYu",
    "haya":"Haya", "sakeer":"Sakeer", "angela":"Angela",
    "augran":"Augran", "kaizer":"Kaizer",
}

# ─── Answer checker ────────────────────────────────────────────────────

def _norm(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9 &]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def check_guess(answer: str, correct_hero: str) -> bool:
    a   = _norm(answer)
    cor = _norm(correct_hero)
    if HERO_ALIASES.get(a) == correct_hero: return True
    for k, v in HERO_ALIASES.items():
        if v == correct_hero and a == _norm(k): return True
    if a == cor: return True
    if a.replace(" ","") == cor.replace(" ",""): return True
    if len(a) >= 4 and cor.startswith(a): return True
    return False

# ══════════════════════════════════════════════════════════════════════
#  IMAGE ZOOM PROCESSOR
# ══════════════════════════════════════════════════════════════════════

ZOOM_RANGES: dict[str, tuple[float,float]] = {
    "easy":   (0.55, 0.75),
    "medium": (0.25, 0.55),
    "hard":   (0.06, 0.25),
}
DIFFICULTY_LABELS = {
    "easy":"🟢 Easy", "medium":"🟡 Medium",
    "hard":"🔴 Hard", "random":"🎲 Random",
}

def _zoom_sync(filepath: str, difficulty: str) -> Optional[bytes]:
    try:
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        actual = difficulty if difficulty != "random" else random.choice(["easy","medium","hard"])
        min_f, max_f = ZOOM_RANGES.get(actual,(0.25,0.75))
        frac  = random.uniform(min_f, max_f)
        cw    = max(int(w*frac), 32)
        ch    = max(int(h*frac), 32)
        x     = random.randint(0, max(w-cw, 0))
        y     = random.randint(0, max(h-ch, 0))
        buf   = io.BytesIO()
        img.crop((x,y,x+cw,y+ch)).resize((512,512),Image.LANCZOS).save(buf,format="PNG")
        return buf.getvalue()
    except Exception:
        return None

async def zoom_image(filepath: str, difficulty: str) -> Optional[discord.File]:
    if not os.path.exists(filepath): return None
    data = await asyncio.to_thread(_zoom_sync, filepath, difficulty)
    if data is None: return None
    return discord.File(io.BytesIO(data), filename="hero_clue.png")

def pick_image(hero: str) -> Optional[str]:
    images = db.get("hero_images",{}).get(hero,[])
    if isinstance(images, str): images = [images] if images else []
    valid  = [p for p in images if os.path.exists(p)]
    return random.choice(valid) if valid else None

# ══════════════════════════════════════════════════════════════════════
#  ACTIVE GAME STATE
# ══════════════════════════════════════════════════════════════════════

active_picture: dict[int, dict]        = {}
active_quote:   dict[int, dict]        = {}
active_mafia:   dict[int, "MafiaGame"] = {}

def channel_busy(cid: int) -> Optional[str]:
    if cid in active_picture: return "Guess by Picture"
    if cid in active_quote:   return "Guess by Quote"
    if cid in active_mafia:   return "Mafia"
    return None

# ══════════════════════════════════════════════════════════════════════
#  GAME 1 — GUESS BY PICTURE
# ══════════════════════════════════════════════════════════════════════

class DifficultyView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=120)
        self.channel_id, self.host_id = channel_id, host_id

    async def _start(self, i: discord.Interaction, diff: str):
        if i.user.id != self.host_id:
            await i.response.send_message("❌ Only the host can pick difficulty.", ephemeral=True); return
        images   = db.get("hero_images",{})
        hero_cnt = sum(1 for h in images if images[h])
        active_picture[self.channel_id] = {
            "host_id":i.host_id if hasattr(i,"host_id") else self.host_id,
            "difficulty":diff,"hero":None,"used":[],"scores":{},"revealed":True,
        }
        # store host_id properly
        active_picture[self.channel_id]["host_id"] = self.host_id
        label = DIFFICULTY_LABELS.get(diff, diff)
        e = discord.Embed(
            title=f"🖼️  Guess by Picture  —  {label}",
            description=(
                f"{SEP}\n"
                f"*Hosted by **{i.user.display_name}***\n\n"
                f"A **cropped** hero image will appear.\n"
                "**Type the hero's name in this channel** to win a point!\n\n"
                f"🎮 **{hero_cnt}** heroes in the pool\n"
                f"Difficulty: **{label}**\n"
                f"{SEP}"
            ), color=AMBER,
        )
        brand(e)
        await i.response.edit_message(embed=e, view=None)
        await asyncio.sleep(2)
        await _picture_round(i.channel, self.channel_id)

    @discord.ui.button(label="Easy",   style=discord.ButtonStyle.success,   emoji="🟢", row=0)
    async def easy(self, i, _):   await self._start(i,"easy")
    @discord.ui.button(label="Medium", style=discord.ButtonStyle.primary,   emoji="🟡", row=0)
    async def medium(self, i, _): await self._start(i,"medium")
    @discord.ui.button(label="Hard",   style=discord.ButtonStyle.danger,    emoji="🔴", row=0)
    async def hard(self, i, _):   await self._start(i,"hard")
    @discord.ui.button(label="Random", style=discord.ButtonStyle.secondary, emoji="🎲", row=0)
    async def rnd(self, i, _):    await self._start(i,"random")


class PictureRoundView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=None)
        self.channel_id, self.host_id = channel_id, host_id

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, i: discord.Interaction, _: Button):
        game = active_picture.get(self.channel_id)
        if not game or game.get("revealed"):
            await i.response.send_message("No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        info = HOK_HEROES.get(hero,{})
        await i.response.send_message(embed=discord.Embed(
            title="⏭️  Skipped!",
            description=f"The hero was **{hero}**\n*{info.get('class','?')} · {info.get('lane','?')}*",
            color=VIOLET))
        await _picture_next(i.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, i: discord.Interaction, _: Button):
        if i.user.id != self.host_id:
            await i.response.send_message("❌ Only the host can end the game.", ephemeral=True); return
        game = active_picture.get(self.channel_id)
        if game: game["revealed"] = True
        await _picture_end(i.channel, self.channel_id)
        await i.response.send_message("🛑 Game ended.", ephemeral=True)


async def _picture_round(channel: discord.TextChannel, channel_id: int):
    game = active_picture.get(channel_id)
    if not game: return
    images = db.get("hero_images",{})
    used   = game.get("used",[])
    pool   = [h for h in images if images[h] and h not in used]
    if not pool:
        msg = ("Every hero with images has been shown. Well played!" if used
               else "No hero images found.\nUse `/set_hero_image` to add some!")
        await channel.send(embed=empire_embed(
            "✅  All Heroes Shown!" if used else "⚠️  No Images",
            msg, GOLD if used else CRIMSON))
        await _picture_end(channel, channel_id); return

    hero     = random.choice(pool)
    filepath = pick_image(hero)
    if not filepath:
        game["used"].append(hero)
        await _picture_round(channel, channel_id); return

    difficulty  = game["difficulty"]
    actual_diff = difficulty if difficulty != "random" else random.choice(["easy","medium","hard"])
    file        = await zoom_image(filepath, actual_diff)

    game.update({"hero":hero,"revealed":False})
    game["used"].append(hero)

    info       = HOK_HEROES.get(hero,{})
    round_num  = len(game["used"])
    diff_label = DIFFICULTY_LABELS.get(actual_diff, actual_diff)
    total      = len(pool) + len(used)

    e = discord.Embed(
        title=f"🖼️  Guess by Picture  —  Round {round_num}/{total}",
        description=(
            f"{SEP}\n"
            "*Which Honor of Kings hero is this?*\n\n"
            "**Type the hero's name in this channel.**\n"
            f"First correct answer wins a point!\n\n"
            f"Difficulty: **{diff_label}**\n"
            f"{SEP}"
        ), color=AMBER,
    )
    if file:
        e.set_image(url="attachment://hero_clue.png")
        e.set_footer(text=f"⚜  Oblivion Empire  ·  {info.get('class','?')} · {info.get('lane','?')}",
                     icon_url=logo_url() or discord.utils.MISSING)
        await channel.send(embed=e, file=file, view=PictureRoundView(channel_id, game["host_id"]))
    else:
        game["revealed"] = True
        e.description += "\n\n*(Image error — hero skipped)*"
        await channel.send(embed=e)
        await asyncio.sleep(2)
        await _picture_next(channel, channel_id)


async def _picture_next(channel, channel_id):
    if not active_picture.get(channel_id): return
    await asyncio.sleep(3)
    await _picture_round(channel, channel_id)

async def _picture_end(channel, channel_id):
    game = active_picture.pop(channel_id, None)
    if not game: return
    scores = game.get("scores",{})
    e = discord.Embed(
        title="🏁  Guess by Picture  —  Game Over!",
        description=f"{SEP}\n*{len(game.get('used',[]))} heroes were shown.*\n{SEP}",
        color=GOLD,
    )
    _add_scores(e, scores, channel.guild)
    _save_scores(scores)
    brand(e); await channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════
#  GAME 2 — GUESS BY QUOTE
#
#  BUG FIX: The quote game now uses a dedicated channel_id-keyed
#  state dict.  The on_message handler processes picture game first
#  then quote game independently — no early return blocks the second.
#  Rounds are tracked via game["round_msg_id"] to avoid stale buttons.
# ══════════════════════════════════════════════════════════════════════

class QuoteRoundView(View):
    def __init__(self, channel_id: int, host_id: int, round_id: str):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.host_id    = host_id
        self.round_id   = round_id  # unique per round, prevents stale buttons acting

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, i: discord.Interaction, _: Button):
        game = active_quote.get(self.channel_id)
        # Only act if this button belongs to the current active round
        if not game or game.get("revealed") or game.get("round_id") != self.round_id:
            await i.response.send_message("No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        info = HOK_HEROES.get(hero,{})
        await i.response.send_message(embed=discord.Embed(
            title="⏭️  Skipped!",
            description=f"That was **{hero}**\n*{info.get('class','?')} · {info.get('lane','?')}*",
            color=VIOLET))
        await _quote_next(i.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, i: discord.Interaction, _: Button):
        if i.user.id != self.host_id:
            await i.response.send_message("❌ Only the host can end the game.", ephemeral=True); return
        game = active_quote.get(self.channel_id)
        if game: game["revealed"] = True
        await _quote_end(i.channel, self.channel_id)
        await i.response.send_message("🛑 Game ended.", ephemeral=True)


async def _quote_round(channel: discord.TextChannel, channel_id: int):
    game = active_quote.get(channel_id)
    if not game: return

    used = game.get("used", [])
    pool = [h for h in HOK_QUOTES if h not in used]

    if not pool:
        await channel.send(embed=empire_embed(
            "✅  All Quotes Used!", "Every hero has spoken. Game over!", GOLD))
        await _quote_end(channel, channel_id); return

    hero      = random.choice(pool)
    quote     = HOK_QUOTES[hero]
    info      = HOK_HEROES.get(hero,{})
    round_id  = str(random.randint(100000, 999999))  # unique per round

    game.update({"hero": hero, "revealed": False, "round_id": round_id})
    game["used"].append(hero)

    round_num = len(game["used"])
    total     = len(HOK_QUOTES)

    e = discord.Embed(
        title=f"💬  Guess by Quote  —  Round {round_num}/{total}",
        description=(
            f"{SEP}\n"
            "*Which Honor of Kings hero said this?*\n\n"
            f"**❝  {quote}  ❞**\n\n"
            "Type the hero's name in this channel.\n"
            f"First correct answer wins a point!\n"
            f"{SEP}"
        ), color=TEAL,
    )
    e.set_footer(text=f"⚜  Oblivion Empire  ·  {info.get('class','?')} · {info.get('lane','?')}",
                 icon_url=logo_url() or discord.utils.MISSING)
    await channel.send(embed=e, view=QuoteRoundView(channel_id, game["host_id"], round_id))


async def _quote_next(channel, channel_id):
    if not active_quote.get(channel_id): return
    await asyncio.sleep(3)
    await _quote_round(channel, channel_id)

async def _quote_end(channel, channel_id):
    game = active_quote.pop(channel_id, None)
    if not game: return
    scores = game.get("scores",{})
    e = discord.Embed(
        title="🏁  Guess by Quote  —  Game Over!",
        description=f"{SEP}\n*{len(game.get('used',[]))} quotes shown.*\n{SEP}",
        color=GOLD,
    )
    _add_scores(e, scores, channel.guild)
    _save_scores(scores)
    brand(e); await channel.send(embed=e)

# ─── Shared score helpers ──────────────────────────────────────────────

def _add_scores(embed: discord.Embed, scores: dict, guild: discord.Guild):
    if not scores:
        embed.add_field(name="📊 Scores", value="No points scored.", inline=False); return
    medals = ["🥇","🥈","🥉"]; lines = []
    for n, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x:-x[1])[:10], 1):
        mem   = guild.get_member(int(uid))
        name  = mem.display_name if mem else f"ID:{uid}"
        medal = medals[n-1] if n <= 3 else f"`{n}.`"
        lines.append(f"{medal}  **{name}**  —  {pts} pt{'s' if pts!=1 else ''}")
    embed.add_field(name="📊 Final Scores", value="\n".join(lines), inline=False)

def _save_scores(scores: dict):
    for uid, pts in scores.items():
        db["game_scores"][uid] = db["game_scores"].get(uid, 0) + pts
    save_db(db)

# ══════════════════════════════════════════════════════════════════════
#  GAME 3 — MAFIA  (host-controlled, no timers)
# ══════════════════════════════════════════════════════════════════════

MAFIA_ROLES: dict[str,dict] = {
    "Mafia":     {"emoji":"🗡️","team":"mafia",  "desc":"Eliminate a villager each night. Blend in during the day."},
    "Detective": {"emoji":"🔍","team":"village","desc":"Investigate one player per night — learn if they are Mafia."},
    "Doctor":    {"emoji":"💊","team":"village","desc":"Protect one player from elimination each night."},
    "Villager":  {"emoji":"🏡","team":"village","desc":"Vote out the Mafia during the day. Trust no one."},
}

def assign_roles(n: int) -> list[str]:
    roles: list[str] = ["Mafia"] * max(1, n//3)
    if n >= 5: roles.append("Doctor")
    if n >= 7: roles.append("Detective")
    roles += ["Villager"] * (n - len(roles))
    random.shuffle(roles); return roles

class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel = channel; self.host = host
        self.players: list[discord.Member] = [host]
        self.roles:   dict[int,str]        = {}
        self.alive:   list[discord.Member] = []
        self.phase    = "lobby"; self.day = 0
        self.votes:   dict[int,int]        = {}
        self.night_actions: dict[str,Optional[int]] = {
            "Mafia":None,"Doctor":None,"Detective":None}
        self.lobby_msg: Optional[discord.Message] = None

    def get_role(self, m: discord.Member) -> str: return self.roles.get(m.id,"Villager")
    def is_mafia(self, m: discord.Member) -> bool: return MAFIA_ROLES[self.get_role(m)]["team"]=="mafia"
    def mafia_alive(self)   -> list[discord.Member]: return [m for m in self.alive if self.is_mafia(m)]
    def village_alive(self) -> list[discord.Member]: return [m for m in self.alive if not self.is_mafia(m)]
    def check_win(self)     -> Optional[str]:
        if not self.mafia_alive(): return "village"
        if len(self.mafia_alive()) >= len(self.village_alive()): return "mafia"
        return None
    def transfer_host(self):
        if self.host not in self.alive and self.alive:
            self.host = self.alive[0]

def _lobby_embed(game: MafiaGame) -> discord.Embed:
    e = discord.Embed(
        title="🎭  Mafia  —  Lobby",
        description=(
            f"{SEP}\n"
            f"*Host: **{game.host.display_name}***\n\n"
            "Need at least **4 players** to start.\n\n"
            "🗡️ **Mafia** — 1 per 3 players · eliminate villagers at night\n"
            "🏡 **Villagers** — vote out Mafia during the day\n"
            "💊 **Doctor** — protect someone per night *(5+ players)*\n"
            "🔍 **Detective** — investigate someone per night *(7+ players)*\n"
            f"{SEP}"
        ), color=PHANTOM,
    )
    e.add_field(name=f"👥 Players  ({len(game.players)})",
                value="\n".join(f"• {m.display_name}" for m in game.players) or "—", inline=False)
    e.set_footer(text="⚜  Oblivion Empire  ·  Mafia")
    return e

class MafiaLobbyView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None); self.game = game

    @discord.ui.button(label="Join",   style=discord.ButtonStyle.success, emoji="✋")
    async def join_btn(self, i: discord.Interaction, _: Button):
        if self.game.phase != "lobby":
            await i.response.send_message("❌ Already started.", ephemeral=True); return
        if i.user in self.game.players:
            await i.response.send_message("❌ Already joined.", ephemeral=True); return
        self.game.players.append(i.user)
        await i.response.send_message(f"✅ **{i.user.display_name}** joined the game!")
        if self.game.lobby_msg:
            try: await self.game.lobby_msg.edit(embed=_lobby_embed(self.game), view=self)
            except Exception: pass

    @discord.ui.button(label="Start",  style=discord.ButtonStyle.primary,  emoji="▶️")
    async def start_btn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can start.", ephemeral=True); return
        if len(self.game.players) < 4:
            await i.response.send_message("❌ Need at least 4 players.", ephemeral=True); return
        await i.response.defer()
        await _mafia_start(self.game)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger,   emoji="❌")
    async def cancel_btn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can cancel.", ephemeral=True); return
        active_mafia.pop(self.game.channel.id, None)
        await i.response.send_message(embed=empire_embed("❌  Mafia Cancelled","The game has been cancelled.",CRIMSON))
        self.stop()

async def _mafia_start(game: MafiaGame):
    role_list = assign_roles(len(game.players))
    for member, role in zip(game.players, role_list):
        game.roles[member.id] = role
    game.alive = list(game.players); game.phase = "starting"

    dm_fails: list[str] = []
    for member in game.players:
        role      = game.get_role(member)
        role_info = MAFIA_ROLES[role]
        e = discord.Embed(
            title=f"🃏  Your Role  —  {role_info['emoji']} {role}",
            description=(
                f"{SEP}\n{role_info['desc']}\n{SEP}\n\n"
                f"**Team:** {role_info['team'].capitalize()}"
            ), color=CRIMSON if role=="Mafia" else TEAL,
        )
        if role == "Mafia":
            team = ", ".join(m.display_name for m in game.players if game.is_mafia(m))
            e.add_field(name="🗡️ Your Mafia", value=team, inline=False)
        e.set_footer(text="⚜  Oblivion Empire  ·  Keep your role secret!")
        try:    await member.send(embed=e)
        except: dm_fails.append(member.display_name)

    names = "\n".join(f"• {m.display_name}" for m in game.players)
    e = discord.Embed(
        title="🎭  The Game Begins!",
        description=(
            f"{SEP}\n"
            f"*{len(game.players)} players enter the darkness…*\n\n"
            f"{names}\n\n"
            "✉️ Check your **DMs** for your secret role!"
            + (f"\n⚠️ DMs failed for: {', '.join(dm_fails)}" if dm_fails else "")
            + f"\n{SEP}"
        ), color=PHANTOM,
    )
    brand(e); await game.channel.send(embed=e)
    await asyncio.sleep(3)
    await _mafia_day(game)

class DayDiscussionView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None); self.game = game

    @discord.ui.button(label="📊 Open Voting", style=discord.ButtonStyle.primary, emoji="🗳️")
    async def open_voting(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only **the host** can open voting.", ephemeral=True); return
        self.stop()
        names = " · ".join(m.display_name for m in self.game.alive)
        e = discord.Embed(
            title=f"🗳️  Day {self.game.day}  —  Voting Open",
            description=(
                f"{SEP}\n"
                f"*{len(self.game.alive)} players alive.*  **Alive:** {names}\n\n"
                "Vote below to eliminate a suspect.\n"
                "When ready, the **host** tallies the results.\n"
                f"{SEP}"
            ), color=GOLD,
        )
        brand(e)
        await i.response.send_message(embed=e, view=DayVotingView(self.game))

class DayVotingView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None); self.game = game
        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id)) for m in game.alive]
        sel  = Select(placeholder="🗳️  Vote to eliminate…", options=opts)
        sel.callback = self._on_vote; self.add_item(sel)

    async def _on_vote(self, i: discord.Interaction):
        if i.user not in self.game.alive:
            await i.response.send_message("❌ You are eliminated.", ephemeral=True); return
        tid = int(i.data["values"][0])
        if tid == i.user.id:
            await i.response.send_message("❌ Can't vote for yourself.", ephemeral=True); return
        self.game.votes[i.user.id] = tid
        target = i.guild.get_member(tid)
        await i.response.send_message(
            f"🗳️ Voted for **{target.display_name if target else '?'}**.\n"
            f"*{len(self.game.votes)}/{len(self.game.alive)} players voted.*", ephemeral=True)

    @discord.ui.button(label="⚖️ Tally Votes", style=discord.ButtonStyle.danger, emoji="⚖️", row=1)
    async def tally_btn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only **the host** can tally votes.", ephemeral=True); return
        self.stop(); await i.response.defer()
        await _mafia_resolve_votes(self.game)

async def _mafia_day(game: MafiaGame):
    game.phase = "day"; game.day += 1; game.votes = {}
    game.transfer_host()
    if w := game.check_win(): await _mafia_end(game,w); return
    names = " · ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"☀️  Day {game.day}  —  Discussion",
        description=(
            f"{SEP}\n"
            f"*{len(game.alive)} players remain.*\n\n"
            f"**Alive:** {names}\n\n"
            "Discuss freely. When ready, **the host** opens voting.\n"
            f"{SEP}"
        ), color=GOLD,
    )
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Host: {game.host.display_name}")
    brand(e); await game.channel.send(embed=e, view=DayDiscussionView(game))

async def _mafia_resolve_votes(game: MafiaGame):
    if not game.votes:
        await game.channel.send(embed=empire_embed(
            "🗳️  No Votes Cast","Nobody voted. Moving to night…", VIOLET)); 
    else:
        tally: dict[int,int] = {}
        for tid in game.votes.values(): tally[tid] = tally.get(tid,0)+1
        max_v   = max(tally.values())
        leaders = [tid for tid,v in tally.items() if v==max_v]
        if len(leaders) > 1:
            tied = ", ".join(
                (g.display_name if (g:=game.channel.guild.get_member(tid)) else "?") for tid in leaders)
            await game.channel.send(embed=empire_embed(
                "⚖️  Tie!",f"**{tied}** each received **{max_v}** votes. Nobody eliminated.",VIOLET))
        else:
            elim = game.channel.guild.get_member(leaders[0])
            if elim and elim in game.alive:
                game.alive.remove(elim)
                ri = MAFIA_ROLES[game.get_role(elim)]
                await game.channel.send(embed=discord.Embed(
                    title="⚖️  Eliminated!",
                    description=(f"**{elim.display_name}** was voted out.\n"
                                 f"They were: {ri['emoji']} **{game.get_role(elim)}**"),
                    color=CRIMSON))
    if w := game.check_win(): await _mafia_end(game,w); return
    await asyncio.sleep(2); await _mafia_night(game)

class NightActionView(View):
    def __init__(self, game: MafiaGame, actor_role: str, user_id: int):
        super().__init__(timeout=None)
        self.game, self.actor_role, self.user_id = game, actor_role, user_id
        targets = game.alive if actor_role=="Doctor" else game.village_alive()
        opts    = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                   for m in targets if m.id!=user_id]
        if not opts: return
        labels  = {"Mafia":"🗡️ Eliminate…","Doctor":"💊 Protect…","Detective":"🔍 Investigate…"}
        sel     = Select(placeholder=labels.get(actor_role,"Select…"), options=opts)
        sel.callback = self._on_select; self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ Not yours.", ephemeral=True); return
        tid = int(i.data["values"][0])
        self.game.night_actions[self.actor_role] = tid
        target = i.guild.get_member(tid)
        msgs = {
            "Mafia":     f"🗡️ Target locked: **{target.display_name if target else '?'}**",
            "Doctor":    f"💊 Protecting **{target.display_name if target else '?'}** tonight.",
            "Detective": f"🔍 Investigating **{target.display_name if target else '?'}**…",
        }
        await i.response.send_message(msgs.get(self.actor_role,"✅ Done."), ephemeral=True)
        self.stop()

class NightHostView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None); self.game = game

    @discord.ui.button(label="🌅 Dawn — End Night", style=discord.ButtonStyle.success, emoji="☀️")
    async def dawn_btn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only **the host** can end the night.", ephemeral=True); return
        self.stop(); await i.response.defer()
        await _mafia_resolve_night(self.game)

async def _mafia_night(game: MafiaGame):
    game.phase = "night"
    game.night_actions = {"Mafia":None,"Doctor":None,"Detective":None}
    game.transfer_host()
    e = discord.Embed(
        title=f"🌙  Night {game.day}  —  Darkness Falls",
        description=(
            f"{SEP}\n"
            "Special roles — check your **DMs** for your action menu.\n\n"
            "When everyone is done, **the host** clicks Dawn to continue.\n"
            f"{SEP}"
        ), color=PHANTOM,
    )
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Host: {game.host.display_name}")
    brand(e); await game.channel.send(embed=e, view=NightHostView(game))
    for member in game.alive:
        role = game.get_role(member)
        if role not in ("Mafia","Doctor","Detective"): continue
        ae = discord.Embed(
            title=f"🌙  Night Action  —  {MAFIA_ROLES[role]['emoji']} {role}",
            description=f"{SEP}\nUse the dropdown below to take your action.\n{SEP}",
            color=PHANTOM,
        )
        ae.set_footer(text="⚜  Oblivion Empire  ·  Mafia Night Phase")
        try:    await member.send(embed=ae, view=NightActionView(game,role,member.id))
        except: pass

async def _mafia_resolve_night(game: MafiaGame):
    elim_id   = game.night_actions.get("Mafia")
    prot_id   = game.night_actions.get("Doctor")
    invest_id = game.night_actions.get("Detective")
    if invest_id:
        target = game.channel.guild.get_member(invest_id)
        det    = next((m for m in game.alive if game.get_role(m)=="Detective"), None)
        if target and det:
            is_maf = game.get_role(target)=="Mafia"
            try:
                await det.send(embed=discord.Embed(
                    title="🔍  Investigation Result",
                    description=f"**{target.display_name}** is {'🗡️ **Mafia**' if is_maf else '🏡 **Village**'}!",
                    color=CRIMSON if is_maf else EMERALD))
            except Exception: pass
    dawn: list[str] = []
    if elim_id and elim_id != prot_id:
        victim = game.channel.guild.get_member(elim_id)
        if victim and victim in game.alive:
            game.alive.remove(victim)
            ri = MAFIA_ROLES[game.get_role(victim)]
            dawn.append(f"💀 **{victim.display_name}** was eliminated overnight.\n"
                        f"They were: {ri['emoji']} **{game.get_role(victim)}**")
    elif elim_id and elim_id == prot_id:
        dawn.append("💊 Someone was targeted but **survived** — the Doctor saved them!")
    else:
        dawn.append("😴 A quiet night. Nobody was eliminated.")
    e = discord.Embed(
        title=f"🌅  Dawn  —  Day {game.day+1}",
        description=f"{SEP}\n" + "\n".join(dawn) + f"\n{SEP}",
        color=GOLD,
    )
    brand(e); await game.channel.send(embed=e)
    if w := game.check_win(): await _mafia_end(game,w); return
    await asyncio.sleep(2); await _mafia_day(game)

async def _mafia_end(game: MafiaGame, winner: str):
    game.phase = "ended"; active_mafia.pop(game.channel.id,None)
    if winner == "village":
        title, desc, color = "🏡  Village Wins!", "The Mafia is gone. Oblivion Empire is safe!", EMERALD
    else:
        title, desc, color = "🗡️  Mafia Wins!", "The Mafia controls Oblivion Empire. Darkness reigns…", CRIMSON
    reveal = "\n".join(
        f"{MAFIA_ROLES[game.get_role(m)]['emoji']} **{m.display_name}** — {game.get_role(m)}"
        for m in game.players)
    e = discord.Embed(
        title=title,
        description=f"{SEP}\n{desc}\n{SEP}",
        color=color,
    )
    e.add_field(name="🃏 Full Role Reveal", value=reveal, inline=False)
    brand(e); await game.channel.send(embed=e)
    await log_action(game.channel.guild,"🎭 Mafia Ended",
        f"#{game.channel.name} — {winner} won · {len(game.players)} players")

# ══════════════════════════════════════════════════════════════════════
#  GAMES PANEL
# ══════════════════════════════════════════════════════════════════════

class GamesPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Guess by Picture", emoji="🖼️", style=discord.ButtonStyle.primary,   row=0)
    async def picture_btn(self, i: discord.Interaction, _: Button):
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        images = db.get("hero_images",{})
        if not any(v for v in images.values()):
            await i.response.send_message(embed=empire_embed(
                "⚠️  No Hero Images Yet",
                "Use `/set_hero_image` to add images:\n\n"
                "1. Type `/set_hero_image` in Discord\n"
                "2. Pick the hero from the autocomplete list\n"
                "3. Attach the image file (.png/.jpg/.webp)\n\n"
                "Use `/hero_images` to track progress.", CRIMSON), ephemeral=True); return
        hero_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🖼️  Guess by Picture  —  Choose Difficulty",
            description=(
                f"{SEP}\n"
                f"*Host: **{i.user.display_name}***\n\n"
                f"**{hero_cnt}** heroes ready in the pool.\n\n"
                "🟢 **Easy** — 55–75% of image visible\n"
                "🟡 **Medium** — 25–55% visible\n"
                "🔴 **Hard** — 6–25% visible *(very hard!)*\n"
                "🎲 **Random** — different every round\n"
                f"{SEP}"
            ), color=AMBER,
        )
        brand(e)
        await i.response.send_message(embed=e, view=DifficultyView(cid, i.user.id))
        await log_action(i.guild,"🖼️ Picture Game",
            f"{i.user.mention} starting Guess by Picture in #{i.channel.name}")

    @discord.ui.button(label="Guess by Quote",   emoji="💬", style=discord.ButtonStyle.success,   row=0)
    async def quote_btn(self, i: discord.Interaction, _: Button):
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        active_quote[cid] = {
            "host_id":i.user.id, "hero":None, "round_id":None,
            "used":[], "scores":{}, "revealed":True,
        }
        e = discord.Embed(
            title="💬  Guess by Quote  —  Starting!",
            description=(
                f"{SEP}\n"
                f"*Hosted by **{i.user.display_name}***\n\n"
                "A hero quote will appear below.\n"
                "**Type who said it** to win a point!\n\n"
                f"💬 **{len(HOK_QUOTES)}** heroes in the pool.\n"
                f"{SEP}"
            ), color=TEAL,
        )
        brand(e)
        await i.response.send_message(embed=e)
        await asyncio.sleep(2)
        await _quote_round(i.channel, cid)
        await log_action(i.guild,"💬 Quote Game",
            f"{i.user.mention} started in #{i.channel.name}")

    @discord.ui.button(label="Mafia",            emoji="🎭", style=discord.ButtonStyle.danger,    row=0)
    async def mafia_btn(self, i: discord.Interaction, _: Button):
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        game = MafiaGame(i.channel, i.user)
        active_mafia[cid] = game
        view = MafiaLobbyView(game)
        await i.response.send_message(embed=_lobby_embed(game), view=view)
        game.lobby_msg = await i.original_response()
        await log_action(i.guild,"🎭 Mafia Lobby",
            f"{i.user.mention} opened in #{i.channel.name}")

    @discord.ui.button(label="All-Time Scores",  emoji="🏅", style=discord.ButtonStyle.secondary, row=1)
    async def scores_btn(self, i: discord.Interaction, _: Button):
        scores = db.get("game_scores",{})
        if not scores:
            await i.response.send_message(empire_embed("🏅  No Scores Yet","Play some games first!", VIOLET), ephemeral=True); return
        medals = ["🥇","🥈","🥉"]; lines = []
        for n, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x:-x[1])[:15], 1):
            mem   = i.guild.get_member(int(uid))
            name  = mem.display_name if mem else f"ID:{uid}"
            medal = medals[n-1] if n <= 3 else f"`{n}.`"
            lines.append(f"{medal}  **{name}**  —  {pts} pt{'s' if pts!=1 else ''}")
        e = discord.Embed(
            title="🏅  All-Time Scores",
            description=f"{SEP}\n" + "\n".join(lines) + f"\n{SEP}",
            color=GOLD,
        )
        brand(e); await i.response.send_message(embed=e, ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════

class GamesCog(commands.Cog):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        _all_hero_names.clear()
        _all_hero_names.extend(sorted(HOK_HEROES.keys()))

    @app_commands.command(name="games", description="🎮 Open the Oblivion Empire games panel")
    async def cmd_games(self, i: discord.Interaction):
        images  = db.get("hero_images",{})
        img_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🎮  Oblivion Empire  —  Games",
            description=(
                f"{SEP}\n"
                "*Welcome to the arena, warrior.*\n"
                f"{SEP}"
            ), color=VIOLET,
        )
        e.set_thumbnail(url=logo_url() or (bot_avatar() or discord.utils.MISSING))
        e.add_field(name="🖼️ Guess by Picture",
                    value=(f"A cropped hero image appears — type the name to win.\n"
                           f"*{img_cnt} hero{'es' if img_cnt!=1 else ''} ready · Easy / Medium / Hard / Random*"),
                    inline=False)
        e.add_field(name="💬 Guess by Quote",
                    value=(f"A hero quote appears — type who said it to win.\n"
                           f"*{len(HOK_QUOTES)} heroes · works immediately, no setup needed*"),
                    inline=False)
        e.add_field(name="🎭 Mafia",
                    value="Social deduction — Villagers vs Mafia.\n4+ players · host-controlled · no timers.",
                    inline=False)
        e.add_field(name="🏅 All-Time Scores", value="Combined leaderboard across both guess games.", inline=False)
        e.set_footer(text="⚜  Oblivion Empire  ·  Games Panel", icon_url=logo_url() or discord.utils.MISSING)
        await i.response.send_message(embed=e, view=GamesPanelView())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        BUG FIX: Both game checks run independently.
        The picture game no longer has a bare 'return' that blocks the quote game.
        Each game is checked only if a game is active AND the round is unrevealed.
        """
        if message.author.bot: return
        cid = message.channel.id

        # ── Picture game ───────────────────────────────────────────
        pg = active_picture.get(cid)
        if pg and not pg.get("revealed") and pg.get("hero"):
            if check_guess(message.content, pg["hero"]):
                pg["revealed"] = True
                uid = str(message.author.id)
                pg["scores"][uid] = pg["scores"].get(uid, 0) + 1
                pts  = pg["scores"][uid]
                info = HOK_HEROES.get(pg["hero"],{})
                e = discord.Embed(
                    title="✅  Correct!",
                    description=(
                        f"{SEP}\n"
                        f"🎉 **{message.author.display_name}** got it!\n\n"
                        f"The hero was **{pg['hero']}**\n"
                        f"*{info.get('class','?')} · {info.get('lane','?')}*\n\n"
                        f"They now have **{pts}** point{'s' if pts!=1 else ''} this game.\n"
                        f"{SEP}"
                    ), color=EMERALD,
                )
                e.set_footer(text="⚜  Oblivion Empire  ·  Next hero coming up…",
                             icon_url=logo_url() or discord.utils.MISSING)
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _picture_next(message.channel, cid)
            # NOTE: no return here — allow quote game to also check if needed
            # (in practice only one game runs per channel, but this is safer)

        # ── Quote game ─────────────────────────────────────────────
        qg = active_quote.get(cid)
        if qg and not qg.get("revealed") and qg.get("hero"):
            if check_guess(message.content, qg["hero"]):
                qg["revealed"] = True
                uid = str(message.author.id)
                qg["scores"][uid] = qg["scores"].get(uid, 0) + 1
                pts  = qg["scores"][uid]
                info = HOK_HEROES.get(qg["hero"],{})
                e = discord.Embed(
                    title="✅  Correct!",
                    description=(
                        f"{SEP}\n"
                        f"🎉 **{message.author.display_name}** got it!\n\n"
                        f"That was **{qg['hero']}**\n"
                        f"*{info.get('class','?')} · {info.get('lane','?')}*\n\n"
                        f"They now have **{pts}** point{'s' if pts!=1 else ''} this game.\n"
                        f"{SEP}"
                    ), color=EMERALD,
                )
                e.set_footer(text="⚜  Oblivion Empire  ·  Next quote coming up…",
                             icon_url=logo_url() or discord.utils.MISSING)
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _quote_next(message.channel, cid)


async def setup(bot_instance: commands.Bot):
    bot_instance.tree.remove_command("games")
    await bot_instance.add_cog(GamesCog(bot_instance))
