# ══════════════════════════════════════════════════════════════════════
#  games.py  —  Oblivion Empire Games Cog
# ══════════════════════════════════════════════════════════════════════
#
#  GUESS GAMES — TIMER SYSTEM:
#    Each round has a 3-minute timer.
#    If nobody answers in time the round is auto-skipped.
#    After 3 consecutive timeouts the game auto-ends.
#    Correct answer cancels the timer and resets the timeout counter.
#
#  MAFIA — ADMIN SYSTEM:
#    Any server admin can control the lobby and every phase of the game.
#    Admins can also play as normal players simultaneously.
#    Admin controls: Open Voting · Tally Votes · Force Dawn
#                    View All Roles · Kick AFK Player · End Game
#    Night summary reveals: Doctor's target · Bodyguard's ward
#                           Detective's result (target + Mafia/Village)
#
#  MAFIA — ROLES (unlock at 14+ players):
#     7-13 players : 1 Mafia · Doctor · Detective · Villagers
#    14+   players : 2+ Mafia · Doctor · Detective · Bodyguard
#                    · Vigilante · Villagers
#
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio, random, unicodedata, re, os, io
from typing import Optional

from PIL import Image

from bot import (
    db, save_db, brand, empire_embed, logo_url, log_action, bot,
    bot_avatar, is_admin, _all_hero_names, HERO_IMAGES_DIR,
    GOLD, CRIMSON, VIOLET, TEAL, EMERALD, STEEL, AMBER,
    PHANTOM, OBSIDIAN, SEP, SEP2,
)

# ── Guess game timer settings ──────────────────────────────────────────
ROUND_TIMEOUT = 180   # seconds per round before auto-skip
MAX_TIMEOUTS  = 3     # consecutive timeouts before game auto-ends

# ══════════════════════════════════════════════════════════════════════
#  HERO ROSTER
# ══════════════════════════════════════════════════════════════════════

HOK_HEROES: dict[str, dict] = {
    "Agudo":          {"roles": ["Marksman"]},
    "Alessio":        {"roles": ["Marksman"]},
    "Allain":         {"roles": ["Fighter", "Tank"]},
    "Angela":         {"roles": ["Mage"]},
    "Ao'yin":         {"roles": ["Marksman"]},
    "Arke":           {"roles": ["Assassin"]},
    "Arli":           {"roles": ["Marksman"]},
    "Arthur":         {"roles": ["Fighter", "Tank"]},
    "Athena":         {"roles": ["Assassin", "Fighter"]},
    "Augran":         {"roles": ["Fighter"]},
    "Bai Qi":         {"roles": ["Tank"]},
    "Biron":          {"roles": ["Fighter", "Tank"]},
    "Cai Yan":        {"roles": ["Mage", "Support"]},
    "Cao Cao":        {"roles": ["Fighter"]},
    "Chang'e":        {"roles": ["Fighter", "Mage"]},
    "Chano":          {"roles": ["Marksman"]},
    "Charlotte":      {"roles": ["Fighter"]},
    "Cheng Yaojin":   {"roles": ["Tank"]},
    "Chicha":         {"roles": ["Fighter"]},
    "Cirrus":         {"roles": ["Assassin"]},
    "Consort Yu":     {"roles": ["Marksman"]},
    "Da Qiao":        {"roles": ["Mage", "Support"]},
    "Da Yu":          {"roles": ["Tank", "Support"]},
    "Daji":           {"roles": ["Mage"]},
    "Dharma":         {"roles": ["Fighter", "Tank"]},
    "Diaochan":       {"roles": ["Mage"]},
    "Dian Wei":       {"roles": ["Fighter"]},
    "Di Renjie":      {"roles": ["Marksman"]},
    "Dolia":          {"roles": ["Mage", "Support"]},
    "Donghuang":      {"roles": ["Mage", "Support"]},
    "Dr Bian":        {"roles": ["Mage"]},
    "Dun":            {"roles": ["Fighter", "Tank"]},
    "Dyadia":         {"roles": ["Support"]},
    "Erin":           {"roles": ["Marksman"]},
    "Fang":           {"roles": ["Marksman"]},
    "Feyd":           {"roles": ["Assassin"]},
    "Flowborn":       {"roles": ["Assassin", "Fighter", "Mage", "Marksman", "Tank", "Support"]},
    "Fuzi":           {"roles": ["Fighter"]},
    "Gan & Mo":       {"roles": ["Mage"]},
    "Gao":            {"roles": ["Mage"]},
    "Gao Changgong":  {"roles": ["Assassin"]},
    "Garo":           {"roles": ["Marksman"]},
    "Ge Ya":          {"roles": ["Marksman"]},
    "Guiguzi":        {"roles": ["Mage", "Support"]},
    "Guan Yu":        {"roles": ["Fighter", "Tank"]},
    "Han Xin":        {"roles": ["Assassin"]},
    "Haya":           {"roles": ["Mage"]},
    "Heino":          {"roles": ["Fighter", "Mage"]},
    "Hou Yi":         {"roles": ["Marksman"]},
    "Huang Zhong":    {"roles": ["Marksman"]},
    "Jin Chan":       {"roles": ["Mage"]},
    "Jing":           {"roles": ["Assassin"]},
    "Kaizer":         {"roles": ["Fighter", "Tank"]},
    "Kong Kong Er":   {"roles": ["Support"]},
    "Kongming":       {"roles": ["Mage"]},
    "Kui":            {"roles": ["Tank", "Support"]},
    "Lady Sun":       {"roles": ["Marksman"]},
    "Lady Zhen":      {"roles": ["Mage"]},
    "Lam":            {"roles": ["Assassin", "Fighter"]},
    "Li Bai":         {"roles": ["Assassin"]},
    "Li Xin":         {"roles": ["Fighter"]},
    "Lian Po":        {"roles": ["Tank"]},
    "Liang":          {"roles": ["Mage"]},
    "Liu Bang":       {"roles": ["Mage", "Tank"]},
    "Liu Bei":        {"roles": ["Fighter"]},
    "Liu Shan":       {"roles": ["Tank", "Support"]},
    "Loong":          {"roles": ["Fighter"]},
    "Lu Bu":          {"roles": ["Fighter", "Tank"]},
    "Luban No. 7":    {"roles": ["Marksman"]},
    "Luna":           {"roles": ["Assassin", "Mage"]},
    "Ma Chao":        {"roles": ["Fighter"]},
    "Mai Shiranui":   {"roles": ["Assassin", "Mage"]},
    "Marco Polo":     {"roles": ["Marksman"]},
    "Master Luban":   {"roles": ["Tank", "Support"]},
    "Mayene":         {"roles": ["Fighter"]},
    "Meng Tian":      {"roles": ["Tank"]},
    "Meng Ya":        {"roles": ["Marksman"]},
    "Menki":          {"roles": ["Mage", "Tank"]},
    "Mi Yue":         {"roles": ["Fighter", "Mage"]},
    "Milady":         {"roles": ["Mage"]},
    "Ming":           {"roles": ["Mage", "Support"]},
    "Mozi":           {"roles": ["Fighter", "Mage"]},
    "Mulan":          {"roles": ["Fighter"]},
    "Musashi":        {"roles": ["Assassin"]},
    "Nakoruru":       {"roles": ["Assassin"]},
    "Nezha":          {"roles": ["Fighter", "Tank"]},
    "Niumo":          {"roles": ["Tank", "Support"]},
    "Nu Wa":          {"roles": ["Mage"]},
    "Pangu":          {"roles": ["Fighter"]},
    "Pei":            {"roles": ["Assassin"]},
    "Sakeer":         {"roles": ["Mage", "Support"]},
    "Shangguan":      {"roles": ["Mage"]},
    "Shen Mengxi":    {"roles": ["Mage"]},
    "Shi":            {"roles": ["Mage"]},
    "Shieldun":       {"roles": ["Tank", "Support"]},
    "Shouyue":        {"roles": ["Assassin", "Marksman"]},
    "Sikong Zhen":    {"roles": ["Fighter", "Mage"]},
    "Sima Yi":        {"roles": ["Assassin", "Mage"]},
    "Su Lie":         {"roles": ["Tank", "Support"]},
    "Sun Bin":        {"roles": ["Mage", "Support"]},
    "Sun Ce":         {"roles": ["Fighter", "Tank"]},
    "Sun Quan":       {"roles": ["Marksman"]},
    "Taiyi Zhenren":  {"roles": ["Tank", "Support"]},
    "Ukyo Tachibana": {"roles": ["Assassin", "Fighter"]},
    "Umbrosa":        {"roles": ["Fighter"]},
    "Wang Zhaojun":   {"roles": ["Mage"]},
    "Wu Ze Tian":     {"roles": ["Mage"]},
    "Wukong":         {"roles": ["Assassin"]},
    "Wuyan":          {"roles": ["Fighter", "Tank"]},
    "Xiang Yu":       {"roles": ["Fighter", "Tank"]},
    "Xiao Qiao":      {"roles": ["Mage"]},
    "Xuance":         {"roles": ["Assassin"]},
    "Yang Jian":      {"roles": ["Fighter"]},
    "Yango":          {"roles": ["Assassin"]},
    "Yao":            {"roles": ["Assassin", "Fighter"]},
    "Yaria":          {"roles": ["Mage", "Support"]},
    "Ying":           {"roles": ["Assassin", "Fighter"]},
    "Ying Zheng":     {"roles": ["Mage"]},
    "Yixing":         {"roles": ["Fighter", "Mage"]},
    "Yuhuan":         {"roles": ["Mage"]},
    "Zhang Fei":      {"roles": ["Tank", "Support"]},
    "Zhao Huaizhen":  {"roles": ["Fighter"]},
    "Zhou Yu":        {"roles": ["Fighter", "Mage"]},
    "Zhu Bajie":      {"roles": ["Tank"]},
    "Zhuangzi":       {"roles": ["Tank", "Support"]},
    "Zilong":         {"roles": ["Assassin", "Fighter"]},
    "Ziya":           {"roles": ["Mage"]},
    # Add new heroes below:
    # "Hero Name": {"roles": ["Role1", "Role2"]},
}

# ══════════════════════════════════════════════════════════════════════
#  HERO QUOTES
# ══════════════════════════════════════════════════════════════════════

HOK_QUOTES: dict[str, str] = {
    "Agudo":          "The further the distance, the more I enjoy it.",
    "Alessio":        "Style is strategy. I have both.",
    "Allain":         "I don't pick sides — I pick winners.",
    "Angela":         "Love is the most powerful force in the universe. Believe me.",
    "Ao'yin":         "I rise with the tide. Everything else sinks.",
    "Arke":           "I was born in starlight. I will return you to dust.",
    "Arli":           "Every arrow is a promise. I always keep my promises.",
    "Arthur":         "A knight's strength means nothing without the honour that guides it.",
    "Athena":         "Wisdom guides this shield. Courage guides this spear.",
    "Augran":         "The boundary between order and chaos is exactly where I stand.",
    "Bai Qi":         "I have buried kingdoms. What makes you think you are different?",
    "Biron":          "The bigger the target, the more satisfying the hit.",
    "Cai Yan":        "My songs have crossed a thousand miles of sorrow.",
    "Cao Cao":        "Heroes rise and fall, but I alone will shape this age.",
    "Chang'e":        "I flew to the moon for peace. I will bring war if I must.",
    "Chano":          "I carry the hopes of my tribe on every arrow I fire.",
    "Charlotte":      "Strength without style is just noise.",
    "Cheng Yaojin":   "I swung my axe first and asked questions never.",
    "Chicha":         "Quick and deadly. That is all you need to know about me.",
    "Cirrus":         "The wind does not ask permission. Neither do I.",
    "Consort Yu":     "For him I would bring down the stars themselves.",
    "Da Qiao":        "A gentle hand can still turn the tide of war.",
    "Da Yu":          "The floodwaters once obeyed me. So will you.",
    "Daji":           "They call it a curse. I call it a gift.",
    "Dharma":         "All things are illusion. All illusions can be shattered.",
    "Diaochan":       "Every man who looks upon me sees only what he wishes to see.",
    "Dian Wei":       "Weapons are merely tools. My body is the weapon.",
    "Di Renjie":      "Every crime leaves a trace. Every criminal leaves a story.",
    "Dolia":          "I was built to endure. Everything else is noise.",
    "Donghuang":      "I am the first emperor. I will also be the last.",
    "Dr Bian":        "Life and death rest in my hands. I choose life — for now.",
    "Dun":            "I gave my eye for loyalty. I would give the other without hesitation.",
    "Dyadia":         "Two hearts, one purpose. We cannot be divided.",
    "Erin":           "I see the future in my arrows. They always find their mark.",
    "Fang":           "Fast, precise, lethal. In that order.",
    "Feyd":           "Power is not taken. It is simply… remembered.",
    "Flowborn":       "I am every warrior and none of them. Choose your fate.",
    "Fuzi":           "True strength lies not in power, but in lifting others.",
    "Gan & Mo":       "Two blades. One soul. Neither of us fights alone.",
    "Gao":            "My melody ends where your heartbeat does.",
    "Gao Changgong":  "Behind this mask is the last face you will ever see.",
    "Garo":           "The darkness is not my enemy. It is my home.",
    "Ge Ya":          "I aim where you will be, not where you are.",
    "Guiguzi":        "The greatest battles are fought in the mind, not on the field.",
    "Guan Yu":        "Loyalty above all — even above life itself.",
    "Han Xin":        "Strike from where they least expect. That is the only rule I follow.",
    "Haya":           "The forest does not fear the storm. Neither do I.",
    "Heino":          "My ice does not melt. My will does not either.",
    "Hou Yi":         "I once shot nine suns from the sky. You are but one more target.",
    "Huang Zhong":    "Age is just a number. My aim has never been sharper.",
    "Jin Chan":       "Every coin has two sides. I have seen both.",
    "Jing":           "I do not miss. I never have.",
    "Kaizer":         "Speed, power, precision — I have mastered all three.",
    "Kong Kong Er":   "Small hands, big heart. Do not underestimate either.",
    "Kongming":       "The battle is won long before the first blade is ever drawn.",
    "Kui":            "The thunder speaks. I translate.",
    "Lady Sun":       "Do not mistake my smile for weakness.",
    "Lady Zhen":      "I am the poem they never got to finish writing.",
    "Lam":            "The way of the blade has no shortcuts.",
    "Li Bai":         "Wine in one hand, sword in the other — the road ahead is mine.",
    "Li Xin":         "I close the gap before you even see me move.",
    "Lian Po":        "I have broken armies with my body alone. You are no different.",
    "Liang":          "An unmovable wall is just as deadly as a sharpened blade.",
    "Liu Bang":       "From peasant to emperor — the road was paved with their doubt.",
    "Liu Bei":        "A true ruler earns the hearts of the people, not just their obedience.",
    "Liu Shan":       "I know what others think of me. I choose my own path anyway.",
    "Loong":          "I am the will of the dragon — ancient, unbreakable, eternal.",
    "Lu Bu":          "The heavens produced me. The earth cannot contain me.",
    "Luban No. 7":    "Model seven, online. All systems… exceeding expectations.",
    "Luna":           "The moonlight guides those who are truly lost.",
    "Ma Chao":        "My father's blood is on their hands. My blade will answer.",
    "Mai Shiranui":   "My flames dance. My enemies do not.",
    "Marco Polo":     "Every map has an edge — I have yet to find mine.",
    "Master Luban":   "I built the machines that built the world. A small army is nothing.",
    "Mayene":         "Every wound I take makes me stronger. Keep trying.",
    "Meng Tian":      "I built the Great Wall. I can build a wall around your future too.",
    "Meng Ya":        "I dream of a world without war. Until then, I fight.",
    "Menki":          "The jungle is mine. Everything in it answers to me.",
    "Mi Yue":         "A woman who survives the palace learns to strike first.",
    "Milady":         "Elegance and lethality — why choose only one?",
    "Ming":           "Light and shadow are two sides of the same truth.",
    "Mozi":           "Engineering is the truest form of warfare.",
    "Mulan":          "They said I could not fight. I said nothing — and won.",
    "Musashi":        "I have won every duel not because I am lucky — but because I do not hesitate.",
    "Nakoruru":       "Nature speaks to those who learn to listen.",
    "Nezha":          "I burn bright enough for everyone — and I do not care who gets scorched.",
    "Niumo":          "I am the bull that broke the mountain. You are the mountain.",
    "Nu Wa":          "I shaped this world with my own hands. I can reshape it again.",
    "Pangu":          "I split heaven from earth. This fight is beneath me — and I will still win.",
    "Pei":            "Stand behind me. Nothing gets through.",
    "Sakeer":         "Every shield I raise protects a story worth saving.",
    "Shangguan":      "Words are my blade. And my blade never misses.",
    "Shen Mengxi":    "Dreams are the only truth. Everything else is noise.",
    "Shi":            "Every note I play is a step closer to your end.",
    "Shieldun":       "I was forged for this. Your blows are just a warmup.",
    "Shouyue":        "The moon remembers every battle fought beneath it.",
    "Sikong Zhen":    "I speak two languages — reason and force. You will learn both.",
    "Sima Yi":        "I do not rush. Time is the only weapon I need.",
    "Su Lie":         "The mountain does not move for the storm. I am the mountain.",
    "Sun Bin":        "A broken leg taught me to see farther than any general on horseback.",
    "Sun Ce":         "The south is mine. The rest is only a matter of time.",
    "Sun Quan":       "To hold what you have is as great as to conquer new ground.",
    "Taiyi Zhenren":  "The heavens gave me power to heal and to harm. Today I choose harm.",
    "Ukyo Tachibana": "Cherry blossoms fall. So do my enemies. Both are beautiful.",
    "Umbrosa":        "I came from the shadow. I will drag you back into it.",
    "Wang Zhaojun":   "I crossed a thousand miles of ice to forge peace. I can endure a little more.",
    "Wu Ze Tian":     "I did not wait for a throne. I built one.",
    "Wukong":         "No cage in heaven or earth can hold the Great Sage Equal to Heaven!",
    "Wuyan":          "They call me ugly. I call it armor against distraction.",
    "Xiang Yu":       "Heaven itself chose to end me. Even so, I do not regret a single battle.",
    "Xiao Qiao":      "My hands carry music. My heart carries war.",
    "Xuance":         "Between worlds, between truths — I walk where no one else can.",
    "Yang Jian":      "Heaven sees all things. And I see further than heaven.",
    "Yango":          "I strike fast, I strike once. That is always enough.",
    "Yao":            "Balance is not given. It must be enforced.",
    "Yaria":          "The spirits answer when I call.",
    "Ying":           "Silence is my greatest weapon. You will not hear me coming.",
    "Ying Zheng":     "I unified the world. One more obstacle means nothing.",
    "Yixing":         "Every strike carries the weight of everything I have endured.",
    "Yuhuan":         "Beauty is the most devastating weapon ever crafted.",
    "Zhang Fei":      "Come then! All of you at once — it will save time!",
    "Zhao Huaizhen":  "I carry the sword of justice. It does not sleep.",
    "Zhou Yu":        "Music and war — both require perfect timing.",
    "Zhu Bajie":      "They say I am lazy. They say it with bruises.",
    "Zhuangzi":       "Am I a man dreaming of a butterfly, or a butterfly dreaming of a man?",
    "Zilong":         "Speed is my armour. Precision is my shield.",
    "Ziya":           "The stars have already written the outcome. I merely read it.",
}

# ══════════════════════════════════════════════════════════════════════
#  HERO ALIASES
# ══════════════════════════════════════════════════════════════════════

HERO_ALIASES: dict[str, str] = {
    "gan jiang and mo ye": "Gan & Mo", "gan mo": "Gan & Mo",
    "ganmo": "Gan & Mo",
    "luban": "Luban No. 7", "luban7": "Luban No. 7",
    "lu ban": "Luban No. 7", "luban no 7": "Luban No. 7",
    "prince of lanling": "Gao Changgong", "lanling": "Gao Changgong",
    "prince lanling": "Gao Changgong", "gao changgong": "Gao Changgong",
    "zhuge liang": "Kongming", "zhuge": "Kongming",
    "bian que": "Dr Bian", "bian": "Dr Bian",
    "shangguan waner": "Shangguan", "wan er": "Shangguan",
    "nuwa": "Nu Wa", "nu wu": "Nu Wa",
    "monkey": "Wukong", "monkey king": "Wukong", "sun wukong": "Wukong",
    "lianpo": "Lian Po", "zhangfei": "Zhang Fei", "guanyu": "Guan Yu",
    "libai": "Li Bai", "caocao": "Cao Cao", "liubei": "Liu Bei",
    "baiqi": "Bai Qi", "xiangyu": "Xiang Yu", "hanxin": "Han Xin",
    "diaochan": "Diaochan", "direnjie": "Di Renjie", "huangzhong": "Huang Zhong",
    "ladysun": "Lady Sun", "caiyan": "Cai Yan", "sunbin": "Sun Bin",
    "liushan": "Liu Shan", "sunce": "Sun Ce", "yangjian": "Yang Jian",
    "dianwei": "Dian Wei", "daqiao": "Da Qiao", "da qiao": "Da Qiao",
    "xiaoqiao": "Xiao Qiao", "xiao qiao": "Xiao Qiao",
    "ukyo": "Ukyo Tachibana",
    "simayi": "Sima Yi", "ladyzhen": "Lady Zhen", "lady zhen": "Lady Zhen",
    "miye": "Mi Yue", "mi yue": "Mi Yue",
    "zhouyu": "Zhou Yu", "zhou yu": "Zhou Yu",
    "yingzheng": "Ying Zheng", "ying zheng": "Ying Zheng",
    "marco": "Marco Polo", "angela": "Angela", "daji": "Daji",
    "yaria": "Yaria", "nakoruru": "Nakoruru", "mozi": "Mozi",
    "loong": "Loong", "lam": "Lam", "arke": "Arke", "feyd": "Feyd",
    "lubu": "Lu Bu", "lu bu": "Lu Bu", "machao": "Ma Chao",
    "taiyi": "Taiyi Zhenren", "zhubajie": "Zhu Bajie", "zhu bajie": "Zhu Bajie",
    "wuzetian": "Wu Ze Tian", "masterluban": "Master Luban",
    "mengtian": "Meng Tian", "sikong": "Sikong Zhen",
    "liubang": "Liu Bang", "aoyin": "Ao'yin", "geya": "Ge Ya",
    "changie": "Chang'e", "change": "Chang'e",
}

ROLE_EMOJIS = {
    "Tank": "🛡️", "Fighter": "⚔️", "Assassin": "🗡️",
    "Mage": "🔮", "Marksman": "🏹", "Support": "💚",
}

def hero_role_str(hero: str) -> str:
    roles = HOK_HEROES.get(hero, {}).get("roles", [])
    return " / ".join(f"{ROLE_EMOJIS.get(r, '')} {r}" for r in roles) or "?"

def _norm(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9 &]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def check_guess(answer: str, correct: str) -> bool:
    a   = _norm(answer)
    cor = _norm(correct)
    if HERO_ALIASES.get(a) == correct: return True
    for k, v in HERO_ALIASES.items():
        if v == correct and a == _norm(k): return True
    if a == cor: return True
    if a.replace(" ", "") == cor.replace(" ", ""): return True
    if len(a) >= 4 and cor.startswith(a): return True
    return False

# ══════════════════════════════════════════════════════════════════════
#  IMAGE ZOOM
# ══════════════════════════════════════════════════════════════════════

ZOOM_RANGES = {"easy": (0.55, 0.75), "medium": (0.25, 0.55), "hard": (0.06, 0.25)}
DIFFICULTY_LABELS = {
    "easy": "🟢 Easy", "medium": "🟡 Medium",
    "hard": "🔴 Hard", "random": "🎲 Random",
}

def _zoom_sync(filepath: str, difficulty: str) -> Optional[bytes]:
    try:
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        actual = difficulty if difficulty != "random" else random.choice(["easy", "medium", "hard"])
        min_f, max_f = ZOOM_RANGES.get(actual, (0.25, 0.75))
        frac = random.uniform(min_f, max_f)
        cw   = max(int(w * frac), 32)
        ch   = max(int(h * frac), 32)
        x    = random.randint(0, max(w - cw, 0))
        y    = random.randint(0, max(h - ch, 0))
        buf  = io.BytesIO()
        img.crop((x, y, x + cw, y + ch)).resize((512, 512), Image.LANCZOS).save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

async def zoom_image(filepath: str, difficulty: str) -> Optional[discord.File]:
    if not os.path.exists(filepath): return None
    data = await asyncio.to_thread(_zoom_sync, filepath, difficulty)
    if data is None: return None
    return discord.File(io.BytesIO(data), filename="hero_clue.png")

def pick_image(hero: str) -> Optional[str]:
    images = db.get("hero_images", {}).get(hero, [])
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
#  SHARED SCORE HELPERS
# ══════════════════════════════════════════════════════════════════════

def _add_scores(embed: discord.Embed, scores: dict, guild: discord.Guild):
    if not scores:
        embed.add_field(name="📊 Scores", value="No points scored.", inline=False)
        return
    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for n, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x: -x[1])[:10], 1):
        mem   = guild.get_member(int(uid))
        name  = mem.display_name if mem else f"ID:{uid}"
        medal = medals[n - 1] if n <= 3 else f"`{n}.`"
        lines.append(f"{medal}  **{name}**  —  {pts} pt{'s' if pts != 1 else ''}")
    embed.add_field(name="📊 Final Scores", value="\n".join(lines), inline=False)

def _save_scores(scores: dict):
    for uid, pts in scores.items():
        db["game_scores"][uid] = db["game_scores"].get(uid, 0) + pts
    save_db(db)

# ══════════════════════════════════════════════════════════════════════
#  GAME 1 — GUESS BY PICTURE  (3-minute timer per round)
# ══════════════════════════════════════════════════════════════════════

class DifficultyView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=120)
        self.channel_id, self.host_id = channel_id, host_id

    async def _start(self, i: discord.Interaction, diff: str):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        images   = db.get("hero_images", {})
        hero_cnt = sum(1 for h in images if images[h])
        active_picture[self.channel_id] = {
            "host_id":  self.host_id,
            "difficulty": diff,
            "hero":     None,
            "used":     [],
            "scores":   {},
            "revealed": True,
            "_timer":   None,
            "timeouts": 0,
        }
        label = DIFFICULTY_LABELS.get(diff, diff)
        e = discord.Embed(
            title=f"🖼️  Guess by Picture  —  {label}",
            description=(
                f"{SEP}\n"
                f"*Started by **{i.user.display_name}***\n\n"
                "A cropped hero image will appear below.\n"
                "**Type the hero's name** in this channel to win a point!\n\n"
                f"🎮 **{hero_cnt}** heroes ready  ·  Difficulty: **{label}**\n"
                f"⏱ **3 minutes** per round  ·  3 timeouts = game ends\n"
                f"{SEP}"
            ), color=AMBER)
        brand(e)
        await i.response.edit_message(embed=e, view=None)
        await asyncio.sleep(2)
        await _picture_round(i.channel, self.channel_id)

    @discord.ui.button(label="Easy",   style=discord.ButtonStyle.success,   emoji="🟢", row=0)
    async def easy(self, i, _):   await self._start(i, "easy")
    @discord.ui.button(label="Medium", style=discord.ButtonStyle.primary,   emoji="🟡", row=0)
    async def medium(self, i, _): await self._start(i, "medium")
    @discord.ui.button(label="Hard",   style=discord.ButtonStyle.danger,    emoji="🔴", row=0)
    async def hard(self, i, _):   await self._start(i, "hard")
    @discord.ui.button(label="Random", style=discord.ButtonStyle.secondary, emoji="🎲", row=0)
    async def rnd(self, i, _):    await self._start(i, "random")


class PictureRoundView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=None)
        self.channel_id, self.host_id = channel_id, host_id

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        game = active_picture.get(self.channel_id)
        if not game or game.get("revealed"):
            await i.response.send_message("No active round.", ephemeral=True)
            return
        _cancel_timer(game)
        game["revealed"] = True
        hero = game["hero"]
        await i.response.send_message(embed=discord.Embed(
            title="⏭️  Skipped!",
            description=f"The hero was **{hero}**\n*{hero_role_str(hero)}*",
            color=VIOLET))
        await _picture_next(i.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        game = active_picture.get(self.channel_id)
        if game:
            _cancel_timer(game)
            game["revealed"] = True
        await _picture_end(i.channel, self.channel_id)
        await i.response.send_message("🛑 Game ended.", ephemeral=True)


def _cancel_timer(game: dict):
    task = game.get("_timer")
    if task and not task.done():
        task.cancel()
    game["_timer"] = None


async def _picture_round(channel: discord.TextChannel, channel_id: int):
    game = active_picture.get(channel_id)
    if not game: return

    images = db.get("hero_images", {})
    used   = game.get("used", [])
    pool   = [h for h in images if images[h] and h not in used]

    if not pool:
        msg = "Every hero with images has been shown. Game over!" if used else "Use `/set_hero_image` to add images."
        title = "✅  All Heroes Shown!" if used else "⚠️  No Images"
        await channel.send(embed=empire_embed(title, msg, GOLD if used else CRIMSON))
        await _picture_end(channel, channel_id)
        return

    hero     = random.choice(pool)
    filepath = pick_image(hero)
    if not filepath:
        game["used"].append(hero)
        await _picture_round(channel, channel_id)
        return

    difficulty  = game["difficulty"]
    actual_diff = difficulty if difficulty != "random" else random.choice(["easy", "medium", "hard"])
    file = await zoom_image(filepath, actual_diff)

    game.update({"hero": hero, "revealed": False})
    game["used"].append(hero)

    diff_label = DIFFICULTY_LABELS.get(actual_diff, actual_diff)
    round_num  = len(game["used"])
    total      = len(pool) + len(used)
    timeouts   = game.get("timeouts", 0)

    e = discord.Embed(
        title=f"🖼️  Guess by Picture  —  Round {round_num}/{total}",
        description=(
            f"{SEP}\n"
            "*Which Honor of Kings hero is this?*\n\n"
            "**Type the hero's name in this channel.**\n"
            f"First correct answer wins a point!\n\n"
            f"Difficulty: **{diff_label}**  ·  ⏱ **3 minutes**"
            + (f"  ·  ⚠️ {timeouts}/{MAX_TIMEOUTS} timeouts" if timeouts > 0 else "")
            + f"\n{SEP}"
        ), color=AMBER)
    if file:
        e.set_image(url="attachment://hero_clue.png")
        e.set_footer(text="⚜  Oblivion Empire  ·  Guess by Picture",
                     icon_url=logo_url() or discord.utils.MISSING)
        await channel.send(embed=e, file=file, view=PictureRoundView(channel_id, game["host_id"]))
    else:
        game["revealed"] = True
        await channel.send(embed=e)
        await asyncio.sleep(2)
        await _picture_next(channel, channel_id)
        return

    # Start the round timer
    async def _picture_timeout():
        await asyncio.sleep(ROUND_TIMEOUT)
        g = active_picture.get(channel_id)
        if not g or g.get("revealed"): return
        g["revealed"] = True
        g["timeouts"] = g.get("timeouts", 0) + 1
        touts = g["timeouts"]
        await channel.send(embed=discord.Embed(
            title="⏰  Time's Up!",
            description=(
                f"Nobody guessed in time!\n"
                f"The answer was **{hero}**  ·  *{hero_role_str(hero)}*\n\n"
                f"Timeouts: **{touts}/{MAX_TIMEOUTS}**"
                + (" — Game ending due to inactivity!" if touts >= MAX_TIMEOUTS else "")
            ), color=CRIMSON))
        if touts >= MAX_TIMEOUTS:
            await _picture_end(channel, channel_id)
        else:
            await _picture_next(channel, channel_id)

    _cancel_timer(game)
    game["_timer"] = asyncio.create_task(_picture_timeout())


async def _picture_next(channel, channel_id):
    if not active_picture.get(channel_id): return
    await asyncio.sleep(3)
    await _picture_round(channel, channel_id)

async def _picture_end(channel, channel_id):
    game = active_picture.pop(channel_id, None)
    if not game: return
    _cancel_timer(game)
    scores = game.get("scores", {})
    e = discord.Embed(
        title="🏁  Guess by Picture  —  Game Over!",
        description=f"{SEP}\n*{len(game.get('used', []))} heroes were shown.*\n{SEP}",
        color=GOLD)
    _add_scores(e, scores, channel.guild)
    _save_scores(scores)
    brand(e)
    await channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════
#  GAME 2 — GUESS BY QUOTE  (3-minute timer per round)
# ══════════════════════════════════════════════════════════════════════

class QuoteRoundView(View):
    def __init__(self, channel_id: int, host_id: int, round_id: str):
        super().__init__(timeout=None)
        self.channel_id, self.host_id, self.round_id = channel_id, host_id, round_id

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        game = active_quote.get(self.channel_id)
        if not game or game.get("revealed") or game.get("round_id") != self.round_id:
            await i.response.send_message("No active round.", ephemeral=True)
            return
        _cancel_timer(game)
        game["revealed"] = True
        hero = game["hero"]
        await i.response.send_message(embed=discord.Embed(
            title="⏭️  Skipped!",
            description=f"That was **{hero}**\n*{hero_role_str(hero)}*",
            color=VIOLET))
        await _quote_next(i.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        game = active_quote.get(self.channel_id)
        if game:
            _cancel_timer(game)
            game["revealed"] = True
        await _quote_end(i.channel, self.channel_id)
        await i.response.send_message("🛑 Game ended.", ephemeral=True)


async def _quote_round(channel: discord.TextChannel, channel_id: int):
    game = active_quote.get(channel_id)
    if not game: return

    used = game.get("used", [])
    pool = [h for h in HOK_QUOTES if h not in used]

    if not pool:
        await channel.send(embed=empire_embed("✅  All Quotes Used!", "Every hero has spoken. Game over!", GOLD))
        await _quote_end(channel, channel_id)
        return

    hero     = random.choice(pool)
    quote    = HOK_QUOTES[hero]
    round_id = str(random.randint(100000, 999999))

    game.update({"hero": hero, "revealed": False, "round_id": round_id})
    game["used"].append(hero)

    round_num = len(game["used"])
    total     = len(HOK_QUOTES)
    timeouts  = game.get("timeouts", 0)

    e = discord.Embed(
        title=f"💬  Guess by Quote  —  Round {round_num}/{total}",
        description=(
            f"{SEP}\n"
            "*Which Honor of Kings hero said this?*\n\n"
            f"**❝  {quote}  ❞**\n\n"
            "Type the hero's name in this channel.\n"
            f"First correct answer wins a point!  ·  ⏱ **3 minutes**"
            + (f"  ·  ⚠️ {timeouts}/{MAX_TIMEOUTS} timeouts" if timeouts > 0 else "")
            + f"\n{SEP}"
        ), color=TEAL)
    e.set_footer(text=f"⚜  Oblivion Empire  ·  {hero_role_str(hero)}",
                 icon_url=logo_url() or discord.utils.MISSING)
    await channel.send(embed=e, view=QuoteRoundView(channel_id, game["host_id"], round_id))

    async def _quote_timeout():
        await asyncio.sleep(ROUND_TIMEOUT)
        g = active_quote.get(channel_id)
        if not g or g.get("revealed") or g.get("round_id") != round_id: return
        g["revealed"] = True
        g["timeouts"] = g.get("timeouts", 0) + 1
        touts = g["timeouts"]
        await channel.send(embed=discord.Embed(
            title="⏰  Time's Up!",
            description=(
                f"Nobody guessed in time!\n"
                f"That was **{hero}**  ·  *{hero_role_str(hero)}*\n\n"
                f"Timeouts: **{touts}/{MAX_TIMEOUTS}**"
                + (" — Game ending due to inactivity!" if touts >= MAX_TIMEOUTS else "")
            ), color=CRIMSON))
        if touts >= MAX_TIMEOUTS:
            await _quote_end(channel, channel_id)
        else:
            await _quote_next(channel, channel_id)

    _cancel_timer(game)
    game["_timer"] = asyncio.create_task(_quote_timeout())


async def _quote_next(channel, channel_id):
    if not active_quote.get(channel_id): return
    await asyncio.sleep(3)
    await _quote_round(channel, channel_id)

async def _quote_end(channel, channel_id):
    game = active_quote.pop(channel_id, None)
    if not game: return
    _cancel_timer(game)
    scores = game.get("scores", {})
    e = discord.Embed(
        title="🏁  Guess by Quote  —  Game Over!",
        description=f"{SEP}\n*{len(game.get('used', []))} quotes shown.*\n{SEP}",
        color=GOLD)
    _add_scores(e, scores, channel.guild)
    _save_scores(scores)
    brand(e)
    await channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════
#  GAME 3 — MAFIA
# ══════════════════════════════════════════════════════════════════════

MAFIA_ROLES: dict[str, dict] = {
    "Mafia": {
        "emoji": "🗡️", "team": "mafia",
        "desc": (
            "You and your allies eliminate one villager every night.\n"
            "Blend in during the day — vote with the crowd and avoid suspicion.\n\n"
            "**Win:** equal or outnumber the Village."
        ),
    },
    "Villager": {
        "emoji": "🏡", "team": "village",
        "desc": (
            "No special power — but your vote is your weapon.\n"
            "Pay attention, build cases, and trust your instincts.\n\n"
            "**Win:** eliminate all Mafia."
        ),
    },
    "Doctor": {
        "emoji": "💊", "team": "village",
        "desc": (
            "Each night, protect one player from Mafia elimination.\n"
            "You can protect yourself, but don't rely on it.\n\n"
            "**Win:** eliminate all Mafia."
        ),
    },
    "Detective": {
        "emoji": "🔍", "team": "village",
        "desc": (
            "Each night, investigate one player.\n"
            "You learn if they are Mafia or Village.\n"
            "The investigation result is revealed publicly at dawn.\n\n"
            "**Win:** eliminate all Mafia."
        ),
    },
    "Bodyguard": {
        "emoji": "🛡️", "team": "village",
        "desc": (
            "Each night, guard one player with your life.\n"
            "If Mafia targets them — **you die instead, they survive.**\n"
            "Unlocks at 14 players.\n\n"
            "**Win:** eliminate all Mafia."
        ),
    },
    "Vigilante": {
        "emoji": "⚡", "team": "village",
        "desc": (
            "Once per game, execute a player at night.\n"
            "If they are Mafia → hero. If innocent → **you also die of guilt.**\n"
            "Each other night choose to hold your power.\n"
            "Unlocks at 14 players.\n\n"
            "**Win:** eliminate all Mafia."
        ),
    },
}


def _mafia_count(n: int) -> int:
    return max(1, n // 7)


def assign_roles(n: int) -> list[str]:
    """
    7–13  players: Mafia · Doctor · Detective · Villagers
    14+   players: adds Bodyguard + Vigilante
    Mafia count: 1 per 7 players
    """
    roles: list[str] = ["Mafia"] * _mafia_count(n)
    roles += ["Doctor", "Detective"]
    if n >= 14:
        roles += ["Bodyguard", "Vigilante"]
    roles += ["Villager"] * (n - len(roles))
    random.shuffle(roles)
    return roles


def _all_night_done(game: "MafiaGame") -> bool:
    for role in ("Mafia", "Doctor", "Detective"):
        has_role = any(game.get_role(m) == role for m in game.alive)
        if has_role and game.night_actions.get(role) is None:
            return False
    has_bg = any(game.get_role(m) == "Bodyguard" for m in game.alive)
    if has_bg and game.night_actions.get("Bodyguard") is None:
        return False
    has_vig = any(game.get_role(m) == "Vigilante" for m in game.alive)
    if has_vig and not game.vigilante_used and game.night_actions.get("Vigilante") is None:
        return False
    return True


def _player_count_preview(n: int) -> str:
    mc    = _mafia_count(n)
    roles = [f"🗡️ ×{mc} Mafia", "💊 Doctor", "🔍 Detective"]
    if n >= 14:
        roles += ["🛡️ Bodyguard", "⚡ Vigilante"]
    vills = n - mc - 2 - (2 if n >= 14 else 0)
    roles.append(f"🏡 ×{max(vills, 0)} Villagers")
    return "  ·  ".join(roles)


class MafiaGame:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.players: list[discord.Member] = []
        self.roles:   dict[int, str]       = {}
        self.alive:   list[discord.Member] = []
        self.phase    = "lobby"
        self.day      = 0
        self.night    = 0
        self.votes:   dict[int, int]       = {}
        self.night_actions: dict[str, Optional[int]] = {
            "Mafia": None, "Doctor": None, "Detective": None,
            "Bodyguard": None, "Vigilante": None,
        }
        self.vigilante_used  = False
        self.lobby_msg:  Optional[discord.Message] = None
        self._dawn_scheduled = False

    def get_role(self, m: discord.Member) -> str:
        return self.roles.get(m.id, "Villager")

    def is_mafia(self, m: discord.Member) -> bool:
        return MAFIA_ROLES[self.get_role(m)]["team"] == "mafia"

    def mafia_alive(self)   -> list[discord.Member]:
        return [m for m in self.alive if self.is_mafia(m)]

    def village_alive(self) -> list[discord.Member]:
        return [m for m in self.alive if not self.is_mafia(m)]

    def check_win(self) -> Optional[str]:
        if not self.mafia_alive(): return "village"
        if len(self.mafia_alive()) >= len(self.village_alive()): return "mafia"
        return None


def _lobby_embed(game: MafiaGame) -> discord.Embed:
    n       = len(game.players)
    preview = _player_count_preview(n) if n >= 7 else "*Need 7 players to preview roles*"
    e = discord.Embed(
        title="🎭  Mafia  —  Lobby",
        description=(
            f"{SEP}\n"
            f"**{n}/7** players joined\n\n"
            "**Role roster unlocks:**\n"
            "👥 **7+**   — 🗡️ Mafia · 💊 Doctor · 🔍 Detective · 🏡 Villagers\n"
            "👥 **14+**  — adds 🛡️ **Bodyguard** + ⚡ **Vigilante** automatically\n"
            "📊 **Mafia scaling** — 1 Mafia per 7 players\n\n"
            f"**Current preview:** {preview}\n"
            f"{SEP}\n"
            "🛡️ *Only admins can start and manage the lobby.*"
        ), color=PHANTOM)
    e.add_field(
        name=f"👥 Players  ({n})",
        value="\n".join(f"• {m.display_name}" for m in game.players) or "—",
        inline=False)
    e.set_footer(text="⚜  Oblivion Empire  ·  Mafia — click Join!")
    return e


class MafiaLobbyView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    def _admin(self, i: discord.Interaction) -> bool:
        m = i.guild.get_member(i.user.id)
        return m is not None and is_admin(m)

    @discord.ui.button(label="Join",   style=discord.ButtonStyle.success, emoji="✋")
    async def join_btn(self, i: discord.Interaction, _: Button):
        if self.game.phase != "lobby":
            await i.response.send_message("❌ Already started.", ephemeral=True)
            return
        if i.user in self.game.players:
            await i.response.send_message("❌ Already joined.", ephemeral=True)
            return
        self.game.players.append(i.user)
        await i.response.send_message(f"✅ **{i.user.display_name}** joined the shadows!")
        if self.game.lobby_msg:
            try:
                await self.game.lobby_msg.edit(embed=_lobby_embed(self.game), view=self)
            except Exception:
                pass

    @discord.ui.button(label="Start",  style=discord.ButtonStyle.primary, emoji="▶️")
    async def start_btn(self, i: discord.Interaction, _: Button):
        if not self._admin(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        if len(self.game.players) < 7:
            await i.response.send_message(
                f"❌ Need at least **7 players**. Currently **{len(self.game.players)}/7**.",
                ephemeral=True)
            return
        await i.response.defer()
        await _mafia_start(self.game)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_btn(self, i: discord.Interaction, _: Button):
        if not self._admin(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        active_mafia.pop(self.game.channel.id, None)
        await i.response.send_message(
            embed=empire_embed("❌  Cancelled", "Mafia game cancelled.", CRIMSON))
        self.stop()


async def _mafia_start(game: MafiaGame):
    role_list = assign_roles(len(game.players))
    for member, role in zip(game.players, role_list):
        game.roles[member.id] = role
    game.alive = list(game.players)
    game.phase = "starting"

    dm_fails: list[str] = []
    for member in game.players:
        role      = game.get_role(member)
        role_info = MAFIA_ROLES[role]
        color = (CRIMSON   if role == "Mafia"     else
                 0x8b5e00  if role == "Bodyguard"  else
                 0x5c3d99  if role == "Vigilante"  else TEAL)
        e = discord.Embed(
            title=f"🃏  Your Role  —  {role_info['emoji']} {role}",
            description=f"{SEP}\n{role_info['desc']}\n{SEP}",
            color=color)
        e.add_field(name="⚔️ Team", value=role_info["team"].capitalize(), inline=True)
        if role == "Mafia":
            allies = ", ".join(m.display_name for m in game.players if game.is_mafia(m))
            e.add_field(name="🗡️ Your Allies", value=allies or "You're alone…", inline=False)
        e.set_footer(text="⚜  Oblivion Empire  ·  Keep your role secret!")
        try:
            await member.send(embed=e)
        except Exception:
            dm_fails.append(member.display_name)

    roster = _player_count_preview(len(game.players))
    names  = "\n".join(f"• {m.display_name}" for m in game.players)
    e = discord.Embed(
        title="🎭  The Game Begins!",
        description=(
            f"{SEP}\n"
            f"*{len(game.players)} souls enter the darkness…*\n\n"
            f"{names}\n\n"
            f"**Tonight's roster:** {roster}\n\n"
            "✉️ Check your **DMs** for your secret role!"
            + (f"\n⚠️ DMs failed for: {', '.join(dm_fails)}" if dm_fails else "")
            + f"\n{SEP}"
        ), color=PHANTOM)
    brand(e)
    await game.channel.send(embed=e)

    # Post persistent admin control panel
    await _post_admin_panel(game, "starting")

    await asyncio.sleep(3)
    await _mafia_night(game)


async def _post_admin_panel(game: MafiaGame, phase: str):
    """Post a persistent admin-only control panel in the game channel."""
    e = discord.Embed(
        title="🛡️  Admin Control Panel",
        description=(
            f"{SEP}\n"
            "These controls are visible to everyone but **only admins can use them**.\n\n"
            "👁️ **View All Roles** — see every player's role\n"
            "🚫 **Kick Player** — remove an AFK player from the game\n"
            "⚡ **Force Next Phase** — skip waiting and advance immediately\n"
            "🛑 **End Game** — terminate the game and reveal all roles\n"
            f"{SEP}"
        ), color=STEEL)
    e.set_footer(text="⚜  Oblivion Empire  ·  Admin Panel  ·  Mafia")
    await game.channel.send(embed=e, view=MafiaAdminView(game))

# ══════════════════════════════════════════════════════════════════════
#  ADMIN CONTROL PANEL
# ══════════════════════════════════════════════════════════════════════

class MafiaAdminView(View):
    """Persistent admin control panel. Any admin can use all buttons."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    def _guard(self, i: discord.Interaction) -> bool:
        m = i.guild.get_member(i.user.id)
        return m is not None and is_admin(m)

    @discord.ui.button(label="👁️ View All Roles", style=discord.ButtonStyle.secondary, row=0)
    async def view_roles(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        lines = []
        for m in self.game.players:
            role = self.game.get_role(m)
            ri   = MAFIA_ROLES[role]
            alive_str = "✅" if m in self.game.alive else "💀"
            lines.append(f"{alive_str} {ri['emoji']} **{m.display_name}** — {role}")
        e = discord.Embed(
            title="🔍  All Roles  (Admin Only)",
            description="\n".join(lines) or "No players yet.",
            color=CRIMSON)
        e.set_footer(text="⚜  Visible only to you")
        await i.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="🚫 Kick Player", style=discord.ButtonStyle.danger, row=0)
    async def kick_player(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        if not self.game.alive:
            await i.response.send_message("❌ No alive players.", ephemeral=True)
            return
        e = discord.Embed(
            title="🚫  Kick AFK Player",
            description="Select the player to remove from the game.",
            color=CRIMSON)
        await i.response.send_message(embed=e, view=KickPlayerView(self.game), ephemeral=True)

    @discord.ui.button(label="⚡ Force Next Phase", style=discord.ButtonStyle.primary, row=1)
    async def force_phase(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        if self.game.phase == "night":
            if self.game._dawn_scheduled:
                await i.response.send_message("Dawn is already triggering.", ephemeral=True)
                return
            self.game._dawn_scheduled = True
            await i.response.send_message("⚡ Forcing dawn…", ephemeral=True)
            await self.game.channel.send(embed=discord.Embed(
                title="⚡  Admin forced dawn — night phase skipped!",
                color=GOLD))
            await _mafia_resolve_night(self.game)
        elif self.game.phase in ("day", "voting"):
            await i.response.send_message(
                "⚠️ Use the **Open Voting** or **Tally Votes** buttons in the game message.",
                ephemeral=True)
        else:
            await i.response.send_message("Nothing to force right now.", ephemeral=True)

    @discord.ui.button(label="🛑 End Game", style=discord.ButtonStyle.danger, row=1)
    async def end_game(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        if self.game.channel.id not in active_mafia:
            await i.response.send_message("❌ Game already ended.", ephemeral=True)
            return
        await i.response.send_message("🛑 Ending game…", ephemeral=True)
        await _mafia_end(self.game, "admin")
        self.stop()


class KickPlayerView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=60)
        self.game = game
        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in game.alive]
        sel = Select(placeholder="🚫  Select player to remove (AFK)…", options=opts)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        tid    = int(i.data["values"][0])
        member = i.guild.get_member(tid)
        if member and member in self.game.alive:
            self.game.alive.remove(member)
            ri = MAFIA_ROLES[self.game.get_role(member)]
            await i.response.edit_message(
                content=f"🚫 **{member.display_name}** removed.",
                embed=None, view=None)
            await self.game.channel.send(embed=discord.Embed(
                title="🚫  Player Removed by Admin",
                description=(
                    f"**{member.display_name}** was removed from the game (AFK).\n"
                    f"Their role: {ri['emoji']} **{self.game.get_role(member)}**\n\n"
                    f"**Alive:** {len(self.game.alive)} players remain."
                ), color=CRIMSON))
            # Check win condition after removal
            if w := self.game.check_win():
                await _mafia_end(self.game, w)
        else:
            await i.response.edit_message(content="❌ Player not found.", embed=None, view=None)

# ══════════════════════════════════════════════════════════════════════
#  NIGHT PHASE
# ══════════════════════════════════════════════════════════════════════

class NightActionView(View):
    """Sent by DM — i.guild is None. Uses guild_id to resolve members."""
    def __init__(self, game: MafiaGame, actor_role: str, user_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.game       = game
        self.actor_role = actor_role
        self.user_id    = user_id
        self.guild_id   = guild_id

        if actor_role == "Mafia":
            candidates = game.village_alive()
        elif actor_role == "Doctor":
            candidates = game.alive
        elif actor_role == "Detective":
            candidates = game.village_alive()
        else:  # Bodyguard, Vigilante
            candidates = [m for m in game.alive if m.id != user_id]

        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in candidates if m.id != user_id]

        if actor_role == "Vigilante" and not game.vigilante_used:
            opts.insert(0, discord.SelectOption(
                label="🤝 Hold my power this night",
                value="0",
                description="Save the execution for a better moment"))

        if not opts:
            return

        placeholders = {
            "Mafia":     "🗡️  Choose tonight's target…",
            "Doctor":    "💊  Choose who to protect…",
            "Detective": "🔍  Choose who to investigate…",
            "Bodyguard": "🛡️  Choose who to guard with your life…",
            "Vigilante": "⚡  Use your power or hold it…",
        }
        sel = Select(placeholder=placeholders.get(actor_role, "Select…"), options=opts[:25])
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ This isn't your action.", ephemeral=True)
            return

        tid    = int(i.data["values"][0])
        guild  = bot.get_guild(self.guild_id)
        target = guild.get_member(tid) if (guild and tid != 0) else None
        tname  = target.display_name if target else "?"

        # Save BEFORE responding to ensure action is recorded
        self.game.night_actions[self.actor_role] = tid

        if self.actor_role == "Vigilante" and tid == 0:
            msg = "🤝 Power held. Choose your moment wisely…"
        else:
            msgs = {
                "Mafia":     f"🗡️ Target locked: **{tname}**\n*They won't see it coming.*",
                "Doctor":    f"💊 Protecting **{tname}** tonight.\n*Stay close.*",
                "Detective": f"🔍 Investigating **{tname}**…\n*Results revealed at dawn.*",
                "Bodyguard": f"🛡️ Guarding **{tname}** with your life.\n*You will die for them if needed.*",
                "Vigilante": f"⚡ Executing **{tname}** tonight.\n*Justice — or guilt — awaits at dawn.*",
            }
            msg = msgs.get(self.actor_role, "✅ Action submitted.")

        await i.response.send_message(msg, ephemeral=True)
        self.stop()

        if _all_night_done(self.game) and not self.game._dawn_scheduled:
            self.game._dawn_scheduled = True
            asyncio.create_task(_auto_dawn(self.game))


async def _auto_dawn(game: MafiaGame):
    await asyncio.sleep(4)
    if game.phase == "night" and game.channel.id in active_mafia:
        await game.channel.send(embed=discord.Embed(
            title="🌅  All actions submitted — Dawn breaks automatically!",
            color=GOLD))
        await _mafia_resolve_night(game)


async def _mafia_night(game: MafiaGame):
    game.phase           = "night"
    game.night          += 1
    game._dawn_scheduled = False
    game.night_actions   = {
        "Mafia": None, "Doctor": None, "Detective": None,
        "Bodyguard": None, "Vigilante": None,
    }

    special_alive = [r for r in ("Mafia", "Doctor", "Detective", "Bodyguard", "Vigilante")
                     if any(game.get_role(m) == r for m in game.alive)]
    active_roles  = [r for r in special_alive
                     if not (r == "Vigilante" and game.vigilante_used)]

    role_icons = {"Mafia": "🗡️", "Doctor": "💊", "Detective": "🔍",
                  "Bodyguard": "🛡️", "Vigilante": "⚡"}
    acting_str = "  ".join(f"{role_icons[r]} {r}" for r in active_roles) or "*(no special roles)*"

    e = discord.Embed(
        title=f"🌙  Night {game.night}  —  Darkness Falls",
        description=(
            f"{SEP}\n"
            "Special roles — check your **DMs** for your action menu.\n\n"
            f"**Acting tonight:** {acting_str}\n\n"
            "Dawn triggers automatically once all actions are submitted.\n"
            "*(Admins can force dawn via the admin panel)*\n"
            f"{SEP}"
        ), color=PHANTOM)
    e.set_footer(text="⚜  Oblivion Empire  ·  Night Phase")
    brand(e)
    await game.channel.send(embed=e)

    guild_id = game.channel.guild.id
    for member in game.alive:
        role = game.get_role(member)
        if role not in active_roles:
            continue
        if role == "Vigilante" and game.vigilante_used:
            continue
        ae = discord.Embed(
            title=f"🌙  Night {game.night}  —  {MAFIA_ROLES[role]['emoji']} {role}",
            description=f"{SEP}\nUse the menu below to take your action.\n{SEP}",
            color=PHANTOM)
        ae.set_footer(text="⚜  Oblivion Empire  ·  Night Phase")
        try:
            await member.send(embed=ae, view=NightActionView(game, role, member.id, guild_id))
        except Exception:
            pass

    if _all_night_done(game) and not game._dawn_scheduled:
        game._dawn_scheduled = True
        asyncio.create_task(_auto_dawn(game))


async def _mafia_resolve_night(game: MafiaGame):
    guild     = game.channel.guild
    elim_id   = game.night_actions.get("Mafia")     or 0
    prot_id   = game.night_actions.get("Doctor")    or 0
    guard_id  = game.night_actions.get("Bodyguard") or 0
    invest_id = game.night_actions.get("Detective") or 0
    vig_id    = game.night_actions.get("Vigilante") or 0

    summary: list[str] = []   # night action summary (always shown)
    results: list[str] = []   # what actually happened

    # ── 1. Detective reveal ────────────────────────────────────────
    if invest_id:
        invest_target = guild.get_member(invest_id)
        det           = next((m for m in game.alive if game.get_role(m) == "Detective"), None)
        if invest_target:
            is_maf = game.get_role(invest_target) == "Mafia"
            result_str = "🗡️ **Mafia!**" if is_maf else "🏡 Village."
            summary.append(
                f"🔍 Detective investigated **{invest_target.display_name}** — {result_str}")
            # Also send private DM to detective
            if det:
                try:
                    await det.send(embed=discord.Embed(
                        title="🔍  Investigation Result",
                        description=(
                            f"Your target: **{invest_target.display_name}**\n\n"
                            f"They are {'🗡️ **Mafia** — your enemy!' if is_maf else '🏡 **Village** — appears innocent.'}"
                        ), color=CRIMSON if is_maf else EMERALD))
                except Exception:
                    pass

    # ── 2. Doctor reveal ───────────────────────────────────────────
    if prot_id:
        prot_target = guild.get_member(prot_id)
        if prot_target:
            summary.append(f"💊 Doctor shielded **{prot_target.display_name}** tonight.")

    # ── 3. Bodyguard reveal ────────────────────────────────────────
    if guard_id:
        guard_target = guild.get_member(guard_id)
        if guard_target:
            summary.append(f"🛡️ Bodyguard stood guard over **{guard_target.display_name}**.")

    # ── 4. Vigilante execution ─────────────────────────────────────
    if vig_id and vig_id != 0:
        game.vigilante_used = True
        vig_target  = guild.get_member(vig_id)
        if vig_target and vig_target in game.alive:
            is_maf_target = game.get_role(vig_target) == "Mafia"
            game.alive.remove(vig_target)
            if is_maf_target:
                results.append(
                    f"⚡ **Justice in the night!** An unknown force eliminated **{vig_target.display_name}**.\n"
                    f"They were: 🗡️ **Mafia** — a hero walks among you.")
            else:
                ri         = MAFIA_ROLES[game.get_role(vig_target)]
                vig_member = next((m for m in game.alive if game.get_role(m) == "Vigilante"), None)
                results.append(
                    f"⚡ **A Vigilante struck — and paid the price.**\n"
                    f"**{vig_target.display_name}** was executed. They were: {ri['emoji']} **{game.get_role(vig_target)}** — innocent.\n"
                    f"*Consumed by guilt, the Vigilante also perished.*")
                if vig_member and vig_member in game.alive:
                    game.alive.remove(vig_member)

    # ── 5. Mafia kill (with Doctor save + Bodyguard sacrifice) ─────
    if elim_id:
        victim = guild.get_member(elim_id)
        if elim_id == prot_id:
            results.append(
                "💊 The Mafia struck — but **someone survived the night.**\n"
                "*The Doctor's protection held.*")
        elif elim_id == guard_id:
            guard_member = next((m for m in game.alive if game.get_role(m) == "Bodyguard"), None)
            vname = victim.display_name if victim else "?"
            if guard_member and guard_member in game.alive:
                game.alive.remove(guard_member)
                results.append(
                    f"🛡️ **A guardian fell in the night.**\n"
                    f"The Mafia targeted **{vname}** — but the Bodyguard stepped in front and paid with their life.\n"
                    f"**{vname}** survived.")
            else:
                if victim and victim in game.alive:
                    game.alive.remove(victim)
                    ri = MAFIA_ROLES[game.get_role(victim)]
                    results.append(
                        f"💀 **{victim.display_name}** was eliminated by the Mafia.\n"
                        f"They were: {ri['emoji']} **{game.get_role(victim)}**")
        else:
            if victim and victim in game.alive:
                game.alive.remove(victim)
                ri = MAFIA_ROLES[game.get_role(victim)]
                results.append(
                    f"💀 **{victim.display_name}** was eliminated by the Mafia.\n"
                    f"They were: {ri['emoji']} **{game.get_role(victim)}**")
    else:
        if not any("Vigilante" in line for line in results):
            results.append("😴 A quiet night — the Mafia held back. Nobody was eliminated.")

    alive_names = "  ·  ".join(m.display_name for m in game.alive)

    summary_text = "\n".join(summary) if summary else "*No actions to reveal.*"
    results_text = "\n\n".join(results)

    e = discord.Embed(
        title=f"🌅  Dawn  —  Day {game.day + 1} begins",
        description=(
            f"{SEP}\n"
            f"**Night {game.night} Summary:**\n"
            f"{summary_text}\n\n"
            f"**What happened:**\n"
            f"{results_text}\n\n"
            f"**Alive ({len(game.alive)}):** {alive_names}\n"
            f"{SEP}"
        ), color=GOLD)
    brand(e)
    await game.channel.send(embed=e)

    if w := game.check_win():
        await _mafia_end(game, w)
        return
    await asyncio.sleep(2)
    await _mafia_day(game)

# ══════════════════════════════════════════════════════════════════════
#  DAY PHASE
# ══════════════════════════════════════════════════════════════════════

class DayDiscussionView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    def _guard(self, i: discord.Interaction) -> bool:
        m = i.guild.get_member(i.user.id)
        return m is not None and is_admin(m)

    @discord.ui.button(label="📊 Open Voting", style=discord.ButtonStyle.primary, emoji="🗳️")
    async def open_voting(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        self.stop()
        names = " · ".join(m.display_name for m in self.game.alive)
        e = discord.Embed(
            title=f"🗳️  Day {self.game.day}  —  Voting Open",
            description=(
                f"{SEP}\n"
                f"*{len(self.game.alive)} players alive.*\n\n"
                f"**Alive:** {names}\n\n"
                "Use the dropdown below to vote.\n"
                "When everyone has voted, an admin tallies the results.\n"
                f"{SEP}"
            ), color=GOLD)
        e.set_footer(text="⚜  Oblivion Empire  ·  Day Phase")
        brand(e)
        await i.response.send_message(embed=e, view=DayVotingView(self.game))


class DayVotingView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game
        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in game.alive]
        sel = Select(placeholder="🗳️  Vote to eliminate…", options=opts)
        sel.callback = self._on_vote
        self.add_item(sel)

    async def _on_vote(self, i: discord.Interaction):
        if i.user not in self.game.alive:
            await i.response.send_message("❌ You are eliminated.", ephemeral=True)
            return
        tid = int(i.data["values"][0])
        if tid == i.user.id:
            await i.response.send_message("❌ You can't vote for yourself.", ephemeral=True)
            return
        self.game.votes[i.user.id] = tid
        target = i.guild.get_member(tid)
        tname  = target.display_name if target else "?"
        await i.response.send_message(
            f"🗳️ Voted for **{tname}**.\n"
            f"*{len(self.game.votes)}/{len(self.game.alive)} players have voted.*",
            ephemeral=True)

    @discord.ui.button(label="⚖️ Tally Votes", style=discord.ButtonStyle.danger, emoji="⚖️", row=1)
    async def tally_btn(self, i: discord.Interaction, _: Button):
        m = i.guild.get_member(i.user.id)
        if m is None or not is_admin(m):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        self.stop()
        await i.response.defer()
        await _mafia_resolve_votes(self.game)


async def _mafia_day(game: MafiaGame):
    game.phase = "day"
    game.day  += 1
    game.votes = {}

    if w := game.check_win():
        await _mafia_end(game, w)
        return

    names = " · ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"☀️  Day {game.day}  —  Discussion",
        description=(
            f"{SEP}\n"
            f"*{len(game.alive)} players remain.*\n\n"
            f"**Alive:** {names}\n\n"
            "Discuss freely. When ready, an **admin** opens voting.\n"
            f"{SEP}"
        ), color=GOLD)
    e.set_footer(text="⚜  Oblivion Empire  ·  Day Phase")
    brand(e)
    await game.channel.send(embed=e, view=DayDiscussionView(game))


async def _mafia_resolve_votes(game: MafiaGame):
    guild = game.channel.guild

    if game.votes:
        lines = []
        for voter_id, target_id in game.votes.items():
            voter  = guild.get_member(voter_id)
            target = guild.get_member(target_id)
            vname  = voter.display_name  if voter  else f"ID:{voter_id}"
            tname  = target.display_name if target else f"ID:{target_id}"
            lines.append(f"**{vname}** → {tname}")
        breakdown = "\n".join(lines)
    else:
        breakdown = "*No votes cast*"

    if not game.votes:
        e = discord.Embed(
            title="🗳️  Vote Results  —  No Votes",
            description=f"{SEP}\n{breakdown}\n\nNobody voted. Night begins…\n{SEP}",
            color=VIOLET)
        brand(e)
        await game.channel.send(embed=e)
    else:
        tally: dict[int, int] = {}
        for tid in game.votes.values():
            tally[tid] = tally.get(tid, 0) + 1
        max_v   = max(tally.values())
        leaders = [tid for tid, v in tally.items() if v == max_v]

        if len(leaders) > 1:
            tied_names = ", ".join(
                (m.display_name if (m := guild.get_member(tid)) else f"ID:{tid}")
                for tid in leaders)
            plural = "s" if max_v != 1 else ""
            e = discord.Embed(
                title="⚖️  Vote Results  —  Tie!",
                description=(
                    f"{SEP}\n**Vote Breakdown:**\n{breakdown}\n\n"
                    f"**{tied_names}** tied with **{max_v}** vote{plural}.\n"
                    f"Nobody eliminated. Night begins…\n{SEP}"
                ), color=VIOLET)
            brand(e)
            await game.channel.send(embed=e)
        else:
            elim = guild.get_member(leaders[0])
            if elim and elim in game.alive:
                game.alive.remove(elim)
                ri = MAFIA_ROLES[game.get_role(elim)]
                e = discord.Embed(
                    title="⚖️  Vote Results  —  Eliminated!",
                    description=(
                        f"{SEP}\n**Vote Breakdown:**\n{breakdown}\n\n"
                        f"💀 **{elim.display_name}** has been voted out.\n"
                        f"They were: {ri['emoji']} **{game.get_role(elim)}**\n{SEP}"
                    ), color=CRIMSON)
                brand(e)
                await game.channel.send(embed=e)

    if w := game.check_win():
        await _mafia_end(game, w)
        return
    await asyncio.sleep(2)
    await _mafia_night(game)


async def _mafia_end(game: MafiaGame, winner: str):
    game.phase = "ended"
    active_mafia.pop(game.channel.id, None)

    if winner == "admin":
        title  = "🛑  Game Ended by Admin"
        desc   = "The game was terminated by an admin."
        color  = STEEL
    elif winner == "village":
        title  = "🏡  Village Wins!"
        desc   = "The Mafia is eliminated. Oblivion Empire is safe!"
        color  = EMERALD
    else:
        title  = "🗡️  Mafia Wins!"
        desc   = "The Mafia controls Oblivion Empire. Darkness reigns…"
        color  = CRIMSON

    reveal = "\n".join(
        f"{MAFIA_ROLES[game.get_role(m)]['emoji']} **{m.display_name}** — {game.get_role(m)}"
        for m in game.players)
    e = discord.Embed(
        title=title,
        description=f"{SEP}\n{desc}\n{SEP}",
        color=color)
    e.add_field(name="🃏 Full Role Reveal", value=reveal or "—", inline=False)
    brand(e)
    await game.channel.send(embed=e)
    await log_action(
        game.channel.guild, "🎭 Mafia Ended",
        f"#{game.channel.name} — {winner} | {len(game.players)} players")

# ══════════════════════════════════════════════════════════════════════
#  GAMES PANEL
# ══════════════════════════════════════════════════════════════════════

class GamesPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Guess by Picture", emoji="🖼️",
                       style=discord.ButtonStyle.primary, row=0)
    async def picture_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True)
            return
        images = db.get("hero_images", {})
        if not any(v for v in images.values()):
            await i.response.send_message(embed=empire_embed(
                "⚠️  No Hero Images Yet",
                "Use `/set_hero_image` to add images first.\nThen try starting the game again.",
                CRIMSON), ephemeral=True)
            return
        hero_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🖼️  Guess by Picture  —  Choose Difficulty",
            description=(
                f"{SEP}\n"
                f"*Started by **{i.user.display_name}***\n\n"
                f"**{hero_cnt}** heroes ready.\n\n"
                "🟢 **Easy** — 55–75% of image visible\n"
                "🟡 **Medium** — 25–55% visible\n"
                "🔴 **Hard** — 6–25% visible\n"
                f"🎲 **Random** — different every round\n"
                f"⏱ **3 minutes** per round  ·  3 timeouts = auto-end\n"
                f"{SEP}"
            ), color=AMBER)
        brand(e)
        await i.response.send_message(embed=e, view=DifficultyView(cid, i.user.id))

    @discord.ui.button(label="Guess by Quote", emoji="💬",
                       style=discord.ButtonStyle.success, row=0)
    async def quote_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True)
            return
        active_quote[cid] = {
            "host_id":  i.user.id,
            "hero":     None,
            "round_id": None,
            "used":     [],
            "scores":   {},
            "revealed": True,
            "_timer":   None,
            "timeouts": 0,
        }
        e = discord.Embed(
            title="💬  Guess by Quote  —  Starting!",
            description=(
                f"{SEP}\n"
                f"*Started by **{i.user.display_name}***\n\n"
                "A hero quote will appear below.\n"
                f"**Type who said it** to win a point!\n\n"
                f"💬 **{len(HOK_QUOTES)}** heroes  ·  ⏱ **3 minutes** per round\n"
                f"{SEP}"
            ), color=TEAL)
        brand(e)
        await i.response.send_message(embed=e)
        await asyncio.sleep(2)
        await _quote_round(i.channel, cid)

    @discord.ui.button(label="Mafia", emoji="🎭",
                       style=discord.ButtonStyle.danger, row=0)
    async def mafia_btn(self, i: discord.Interaction, _: Button):
        if not is_admin(i.guild.get_member(i.user.id)):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True)
            return
        game = MafiaGame(i.channel)
        active_mafia[cid] = game
        view = MafiaLobbyView(game)
        await i.response.send_message(embed=_lobby_embed(game), view=view)
        game.lobby_msg = await i.original_response()
        await log_action(i.guild, "🎭 Mafia Lobby",
            f"{i.user.mention} opened lobby in #{i.channel.name}")

    @discord.ui.button(label="All-Time Scores", emoji="🏅",
                       style=discord.ButtonStyle.secondary, row=1)
    async def scores_btn(self, i: discord.Interaction, _: Button):
        scores = db.get("game_scores", {})
        if not scores:
            await i.response.send_message(
                empire_embed("🏅  No Scores Yet", "Play some games first!", VIOLET),
                ephemeral=True)
            return
        medals = ["🥇", "🥈", "🥉"]
        lines  = []
        for n, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x: -x[1])[:15], 1):
            mem   = i.guild.get_member(int(uid))
            name  = mem.display_name if mem else f"ID:{uid}"
            medal = medals[n - 1] if n <= 3 else f"`{n}.`"
            lines.append(f"{medal}  **{name}**  —  {pts} pt{'s' if pts != 1 else ''}")
        e = discord.Embed(
            title="🏅  All-Time Scores",
            description=f"{SEP}\n" + "\n".join(lines) + f"\n{SEP}",
            color=GOLD)
        brand(e)
        await i.response.send_message(embed=e, ephemeral=True)

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
        images  = db.get("hero_images", {})
        img_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🎮  Oblivion Empire  —  Games",
            description=f"{SEP}\n*Welcome to the arena, warrior.*\n{SEP}",
            color=VIOLET)
        e.set_thumbnail(url=logo_url() or (bot_avatar() or discord.utils.MISSING))
        e.add_field(
            name="🖼️ Guess by Picture",
            value=(
                f"Cropped hero image — type the name to score.\n"
                f"*{img_cnt} hero{'es' if img_cnt != 1 else ''} ready · Easy / Medium / Hard / Random · 3-min timer*"
            ), inline=False)
        e.add_field(
            name="💬 Guess by Quote",
            value=(
                f"Hero quote appears — type who said it.\n"
                f"*{len(HOK_QUOTES)} heroes · works immediately · 3-min timer*"
            ), inline=False)
        e.add_field(
            name="🎭 Mafia",
            value=(
                "Social deduction — **7+ players**.\n"
                "🛡️ Bodyguard + ⚡ Vigilante unlock at **14 players**.\n"
                "Night first · auto-advances · admin-controlled."
            ), inline=False)
        e.add_field(
            name="🏅 All-Time Scores",
            value="Combined leaderboard across both guess games.",
            inline=False)
        e.add_field(
            name="🔒 Admin Note",
            value="Only admins can start and manage games.\nAdmins can also play as normal players.",
            inline=False)
        e.set_footer(text="⚜  Oblivion Empire  ·  Games Panel",
                     icon_url=logo_url() or discord.utils.MISSING)
        await i.response.send_message(embed=e, view=GamesPanelView())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        cid = message.channel.id

        # Picture game
        pg = active_picture.get(cid)
        if pg and not pg.get("revealed") and pg.get("hero"):
            if check_guess(message.content, pg["hero"]):
                _cancel_timer(pg)
                pg["revealed"] = True
                pg["timeouts"] = 0  # reset consecutive timeouts
                uid = str(message.author.id)
                pg["scores"][uid] = pg["scores"].get(uid, 0) + 1
                pts = pg["scores"][uid]
                e = discord.Embed(
                    title="✅  Correct!",
                    description=(
                        f"{SEP}\n"
                        f"🎉 **{message.author.display_name}** got it!\n\n"
                        f"The hero was **{pg['hero']}**\n"
                        f"*{hero_role_str(pg['hero'])}*\n\n"
                        f"They now have **{pts}** point{'s' if pts != 1 else ''} this game.\n"
                        f"{SEP}"
                    ), color=EMERALD)
                e.set_footer(text="⚜  Oblivion Empire  ·  Next hero in 3 seconds…",
                             icon_url=logo_url() or discord.utils.MISSING)
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _picture_next(message.channel, cid)

        # Quote game
        qg = active_quote.get(cid)
        if qg and not qg.get("revealed") and qg.get("hero"):
            if check_guess(message.content, qg["hero"]):
                _cancel_timer(qg)
                qg["revealed"] = True
                qg["timeouts"] = 0  # reset consecutive timeouts
                uid = str(message.author.id)
                qg["scores"][uid] = qg["scores"].get(uid, 0) + 1
                pts = qg["scores"][uid]
                e = discord.Embed(
                    title="✅  Correct!",
                    description=(
                        f"{SEP}\n"
                        f"🎉 **{message.author.display_name}** got it!\n\n"
                        f"That was **{qg['hero']}**\n"
                        f"*{hero_role_str(qg['hero'])}*\n\n"
                        f"They now have **{pts}** point{'s' if pts != 1 else ''} this game.\n"
                        f"{SEP}"
                    ), color=EMERALD)
                e.set_footer(text="⚜  Oblivion Empire  ·  Next quote in 3 seconds…",
                             icon_url=logo_url() or discord.utils.MISSING)
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _quote_next(message.channel, cid)


async def setup(bot_instance: commands.Bot):
    # NOTE: do NOT call tree.sync() here.
    # setup() runs before bot.start() so HTTP isn't connected yet.
    # Syncing happens in on_ready() once the bot is fully connected.
    bot_instance.tree.remove_command("games")
    await bot_instance.add_cog(GamesCog(bot_instance))
