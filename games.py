# ══════════════════════════════════════════════════════════════════════
#  games.py  —  Oblivion Empire Games Cog
# ══════════════════════════════════════════════════════════════════════
#
#  MAFIA FLOW (fully automatic — host only controls discussion/voting):
#    Game starts → Night 1 begins immediately
#    Night: special roles get DMs. When ALL have submitted → Dawn auto-triggers.
#    Day discussion: host clicks "Open Voting" when ready.
#    Voting: host clicks "Tally Votes". Night begins automatically after.
#    Repeat until win condition.
#    "Force Dawn" button available as fallback if someone goes AFK.
#
#  HERO DATA: roles = list (a hero can have multiple roles). No lanes.
#
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio, random, unicodedata, re, os, io
from typing import Optional

from PIL import Image

from bot import (db, save_db, brand, empire_embed, logo_url, log_action, bot,
                 bot_avatar, _all_hero_names, HERO_IMAGES_DIR,
                 GOLD, CRIMSON, VIOLET, TEAL, EMERALD, STEEL, AMBER,
                 PHANTOM, OBSIDIAN, SEP, SEP2)

# ══════════════════════════════════════════════════════════════════════
#  COMPLETE HOK HERO ROSTER
#  Each hero has a "roles" list — heroes can belong to multiple roles.
#  Add new heroes at the bottom.
# ══════════════════════════════════════════════════════════════════════

HOK_HEROES: dict[str, dict] = {
    # ── A ─────────────────────────────────────────────────────────
    "Agudo":             {"roles": ["Marksman"]},
    "Alessio":           {"roles": ["Marksman"]},
    "Allain":            {"roles": ["Fighter", "Tank"]},
    "Angela":            {"roles": ["Mage"]},
    "Ao'yin":            {"roles": ["Marksman"]},
    "Arke":              {"roles": ["Assassin"]},
    "Arli":              {"roles": ["Marksman"]},
    "Arthur":            {"roles": ["Fighter", "Tank"]},
    "Athena":            {"roles": ["Assassin", "Fighter"]},
    "Augran":            {"roles": ["Fighter"]},
    # ── B ─────────────────────────────────────────────────────────
    "Bai Qi":            {"roles": ["Tank"]},
    "Biron":             {"roles": ["Fighter", "Tank"]},
    # ── C ─────────────────────────────────────────────────────────
    "Cai Yan":           {"roles": ["Mage", "Support"]},
    "Cao Cao":           {"roles": ["Fighter"]},
    "Chang'e":           {"roles": ["Fighter", "Mage"]},
    "Chano":             {"roles": ["Marksman"]},
    "Charlotte":         {"roles": ["Fighter"]},
    "Cheng Yaojin":      {"roles": ["Tank"]},
    "Chicha":            {"roles": ["Fighter"]},
    "Cirrus":            {"roles": ["Assassin"]},
    "Consort Yu":        {"roles": ["Marksman"]},
    # ── D ─────────────────────────────────────────────────────────
    "Da Qiao":           {"roles": ["Mage", "Support"]},
    "Da Yu":             {"roles": ["Tank", "Support"]},
    "Daji":              {"roles": ["Mage"]},
    "Dharma":            {"roles": ["Fighter", "Tank"]},
    "Diaochan":          {"roles": ["Mage"]},
    "Dian Wei":          {"roles": ["Fighter"]},
    "Di Renjie":         {"roles": ["Marksman"]},
    "Dolia":             {"roles": ["Mage", "Support"]},
    "Donghuang":         {"roles": ["Mage", "Support"]},
    "Dr Bian":           {"roles": ["Mage"]},
    "Dun":               {"roles": ["Fighter", "Tank"]},
    "Dyadia":            {"roles": ["Support"]},
    # ── E ─────────────────────────────────────────────────────────
    "Erin":              {"roles": ["Marksman"]},
    # ── F ─────────────────────────────────────────────────────────
    "Fang":              {"roles": ["Marksman"]},
    "Feyd":              {"roles": ["Assassin"]},
    "Flowborn":          {"roles": ["Assassin", "Fighter", "Mage", "Marksman", "Tank", "Support"]},
    "Fuzi":              {"roles": ["Fighter"]},
    # ── G ─────────────────────────────────────────────────────────
    "Gan & Mo":          {"roles": ["Mage"]},
    "Gao":               {"roles": ["Mage"]},
    "Gao Changgong":     {"roles": ["Assassin"]},
    "Garo":              {"roles": ["Marksman"]},
    "Ge Ya":             {"roles": ["Marksman"]},
    "Guiguzi":           {"roles": ["Mage", "Support"]},
    "Guan Yu":           {"roles": ["Fighter", "Tank"]},
    # ── H ─────────────────────────────────────────────────────────
    "Han Xin":           {"roles": ["Assassin"]},
    "Haya":              {"roles": ["Mage"]},
    "Heino":             {"roles": ["Fighter", "Mage"]},
    "Hou Yi":            {"roles": ["Marksman"]},
    "Huang Zhong":       {"roles": ["Marksman"]},
    # ── J ─────────────────────────────────────────────────────────
    "Jin Chan":          {"roles": ["Mage"]},
    "Jing":              {"roles": ["Assassin"]},
    # ── K ─────────────────────────────────────────────────────────
    "Kaizer":            {"roles": ["Fighter", "Tank"]},
    "Kong Kong Er":      {"roles": ["Support"]},
    "Kongming":          {"roles": ["Mage"]},
    "Kui":               {"roles": ["Tank", "Support"]},
    # ── L ─────────────────────────────────────────────────────────
    "Lady Sun":          {"roles": ["Marksman"]},
    "Lady Zhen":         {"roles": ["Mage"]},
    "Lam":               {"roles": ["Assassin", "Fighter"]},
    "Li Bai":            {"roles": ["Assassin"]},
    "Li Xin":            {"roles": ["Fighter"]},
    "Lian Po":           {"roles": ["Tank"]},
    "Liang":             {"roles": ["Mage"]},
    "Liu Bang":          {"roles": ["Mage", "Tank"]},
    "Liu Bei":           {"roles": ["Fighter"]},
    "Liu Shan":          {"roles": ["Tank", "Support"]},
    "Loong":             {"roles": ["Fighter"]},
    "Lu Bu":             {"roles": ["Fighter", "Tank"]},
    "Luban No. 7":       {"roles": ["Marksman"]},
    "Luna":              {"roles": ["Assassin", "Mage"]},
    # ── M ─────────────────────────────────────────────────────────
    "Ma Chao":           {"roles": ["Fighter"]},
    "Mai Shiranui":      {"roles": ["Assassin", "Mage"]},
    "Marco Polo":        {"roles": ["Marksman"]},
    "Master Luban":      {"roles": ["Tank", "Support"]},
    "Mayene":            {"roles": ["Fighter"]},
    "Meng Tian":         {"roles": ["Tank"]},
    "Meng Ya":           {"roles": ["Marksman"]},
    "Menki":             {"roles": ["Mage", "Tank"]},
    "Mi Yue":            {"roles": ["Fighter", "Mage"]},
    "Milady":            {"roles": ["Mage"]},
    "Ming":              {"roles": ["Mage", "Support"]},
    "Mozi":              {"roles": ["Fighter", "Mage"]},
    "Mulan":             {"roles": ["Fighter"]},
    "Musashi":           {"roles": ["Assassin"]},
    # ── N ─────────────────────────────────────────────────────────
    "Nakoruru":          {"roles": ["Assassin"]},
    "Nezha":             {"roles": ["Fighter", "Tank"]},
    "Niumo":             {"roles": ["Tank", "Support"]},
    "Nu Wa":             {"roles": ["Mage"]},
    # ── P ─────────────────────────────────────────────────────────
    "Pangu":             {"roles": ["Fighter"]},
    "Pei":               {"roles": ["Assassin"]},
    # ── S ─────────────────────────────────────────────────────────
    "Sakeer":            {"roles": ["Mage", "Support"]},
    "Shangguan":         {"roles": ["Mage"]},
    "Shen Mengxi":       {"roles": ["Mage"]},
    "Shi":               {"roles": ["Mage"]},
    "Shieldun":          {"roles": ["Tank", "Support"]},
    "Shouyue":           {"roles": ["Assassin", "Marksman"]},
    "Sikong Zhen":       {"roles": ["Fighter", "Mage"]},
    "Sima Yi":           {"roles": ["Assassin", "Mage"]},
    "Su Lie":            {"roles": ["Tank", "Support"]},
    "Sun Bin":           {"roles": ["Mage", "Support"]},
    "Sun Ce":            {"roles": ["Fighter", "Tank"]},
    "Sun Quan":          {"roles": ["Marksman"]},
    # ── T ─────────────────────────────────────────────────────────
    "Taiyi Zhenren":     {"roles": ["Tank", "Support"]},
    # ── U ─────────────────────────────────────────────────────────
    "Ukyo Tachibana":    {"roles": ["Assassin", "Fighter"]},
    "Umbrosa":           {"roles": ["Fighter"]},
    # ── W ─────────────────────────────────────────────────────────
    "Wang Zhaojun":      {"roles": ["Mage"]},
    "Wu Ze Tian":        {"roles": ["Mage"]},
    "Wukong":            {"roles": ["Assassin"]},
    "Wuyan":             {"roles": ["Fighter", "Tank"]},
    # ── X ─────────────────────────────────────────────────────────
    "Xiang Yu":          {"roles": ["Fighter", "Tank"]},
    "Xiao Qiao":         {"roles": ["Mage"]},
    "Xuance":            {"roles": ["Assassin"]},
    # ── Y ─────────────────────────────────────────────────────────
    "Yang Jian":         {"roles": ["Fighter"]},
    "Yango":             {"roles": ["Assassin"]},
    "Yao":               {"roles": ["Assassin", "Fighter"]},
    "Yaria":             {"roles": ["Mage", "Support"]},
    "Ying":              {"roles": ["Assassin", "Fighter"]},
    "Ying Zheng":        {"roles": ["Mage"]},
    "Yixing":            {"roles": ["Fighter", "Mage"]},
    "Yuhuan":            {"roles": ["Mage"]},
    # ── Z ─────────────────────────────────────────────────────────
    "Zhang Fei":         {"roles": ["Tank", "Support"]},
    "Zhao Huaizhen":     {"roles": ["Fighter"]},
    "Zhou Yu":           {"roles": ["Fighter", "Mage"]},
    "Zhu Bajie":         {"roles": ["Tank"]},
    "Zhuangzi":          {"roles": ["Tank", "Support"]},
    "Zilong":            {"roles": ["Assassin", "Fighter"]},
    "Ziya":              {"roles": ["Mage"]},
    # ── Add new heroes below ───────────────────────────────────────
    # "Hero Name": {"roles": ["Role1", "Role2"]},
}

# ══════════════════════════════════════════════════════════════════════
#  HERO QUOTES  (used in Guess by Quote game)
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
    "Taiyi Zhenren":  "The heavens gave me power to heal and power to harm. Today I choose harm.",
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
#  HERO ALIASES  —  shortcuts players can type
# ══════════════════════════════════════════════════════════════════════

HERO_ALIASES: dict[str, str] = {
    # Gan & Mo
    "gan jiang and mo ye": "Gan & Mo", "gan mo": "Gan & Mo",
    "ganmo": "Gan & Mo", "gan": "Gan & Mo",
    # Luban
    "luban": "Luban No. 7", "luban7": "Luban No. 7",
    "lu ban": "Luban No. 7", "luban no 7": "Luban No. 7",
    # Gao Changgong = Prince of Lanling
    "prince of lanling": "Gao Changgong", "lanling": "Gao Changgong",
    "prince lanling": "Gao Changgong",
    # Kongming = Zhuge Liang
    "zhuge liang": "Kongming", "zhuge": "Kongming",
    # Dr Bian = Bian Que
    "bian que": "Dr Bian", "bian": "Dr Bian",
    # Shangguan = Shangguan Wan'er
    "shangguan waner": "Shangguan", "wan er": "Shangguan", "waner": "Shangguan",
    # Nu Wa
    "nuwa": "Nu Wa", "nu wu": "Nu Wa",
    # Wukong
    "monkey": "Wukong", "monkey king": "Wukong", "sun wukong": "Wukong",
    # Common no-space
    "lianpo": "Lian Po", "zhangfei": "Zhang Fei", "guanyu": "Guan Yu",
    "libai": "Li Bai", "caocao": "Cao Cao", "liubei": "Liu Bei",
    "baiqi": "Bai Qi", "xiangyu": "Xiang Yu", "hanxin": "Han Xin",
    "diaochan": "Diaochan", "direnjie": "Di Renjie", "huangzhong": "Huang Zhong",
    "ladysun": "Lady Sun", "caiyan": "Cai Yan", "sunbin": "Sun Bin",
    "liushan": "Liu Shan", "sunce": "Sun Ce", "yangjian": "Yang Jian",
    "dianwei": "Dian Wei", "daqiao": "Da Qiao", "da qiao": "Da Qiao",
    "xiaoqiao": "Xiao Qiao", "xiao qiao": "Xiao Qiao",
    "ukyo": "Ukyo Tachibana",
    "frost": "Cirrus",           # old players may type this
    "zhuge": "Kongming",
    "simayi": "Sima Yi", "ladyzhen": "Lady Zhen", "lady zhen": "Lady Zhen",
    "miye": "Mi Yue", "mi yue": "Mi Yue",
    "zhouyu": "Zhou Yu", "zhou yu": "Zhou Yu",
    "yingzheng": "Ying Zheng", "ying zheng": "Ying Zheng",
    "wangzhaojun": "Wang Zhaojun", "wang zhaojun": "Wang Zhaojun",
    "donghuang": "Donghuang",
    "marco": "Marco Polo",
    "angela": "Angela", "daji": "Daji", "yaria": "Yaria",
    "nakoruru": "Nakoruru", "mozi": "Mozi", "loong": "Loong", "lam": "Lam",
    "arke": "Arke", "feyd": "Feyd", "shouyue": "Shouyue",
    "chicha": "Chicha", "cheng": "Cheng Yaojin",
    "pangu": "Pangu", "lubu": "Lu Bu", "lu bu": "Lu Bu",
    "machao": "Ma Chao", "ma chao": "Ma Chao",
    "shieldun": "Shieldun", "niumo": "Niumo",
    "suliei": "Su Lie", "su lie": "Su Lie",
    "taiyi": "Taiyi Zhenren", "zhu bajie": "Zhu Bajie", "zhubajie": "Zhu Bajie",
    "wuzetian": "Wu Ze Tian", "wu ze tian": "Wu Ze Tian",
    "masterluban": "Master Luban", "master luban": "Master Luban",
    "mengtian": "Meng Tian", "meng tian": "Meng Tian",
    "sikong": "Sikong Zhen", "shen": "Shen Mengxi",
    "liubang": "Liu Bang", "liu bang": "Liu Bang",
    "kongkonger": "Kong Kong Er", "kong kong er": "Kong Kong Er",
    "zhaoh": "Zhao Huaizhen", "zhao": "Zhao Huaizhen",
    "gao changgong": "Gao Changgong",
    "aoyin": "Ao'yin", "ao yin": "Ao'yin",
    "geya": "Ge Ya", "ge ya": "Ge Ya",
    "yixing": "Yixing", "umbrosa": "Umbrosa",
    "dyadia": "Dyadia", "yango": "Yango",
    "changie": "Chang'e", "change": "Chang'e",
}

# ─── Role emoji helper ─────────────────────────────────────────────────

ROLE_EMOJIS: dict[str, str] = {
    "Tank": "🛡️", "Fighter": "⚔️", "Assassin": "🗡️",
    "Mage": "🔮", "Marksman": "🏹", "Support": "💚",
}

def hero_role_str(hero: str) -> str:
    """Return formatted role string for a hero, e.g. '🗡️ Assassin / ⚔️ Fighter'"""
    info  = HOK_HEROES.get(hero, {})
    roles = info.get("roles", [])
    return " / ".join(f"{ROLE_EMOJIS.get(r, '')} {r}" for r in roles) or "?"

# ─── Answer checker ────────────────────────────────────────────────────

def _norm(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9 &']", "", text)
    return re.sub(r"\s+", " ", text).strip()

def check_guess(answer: str, correct_hero: str) -> bool:
    a   = _norm(answer)
    cor = _norm(correct_hero)
    if HERO_ALIASES.get(a) == correct_hero: return True
    for k, v in HERO_ALIASES.items():
        if v == correct_hero and a == _norm(k): return True
    if a == cor: return True
    if a.replace(" ", "") == cor.replace(" ", ""): return True
    if len(a) >= 4 and cor.startswith(a): return True
    return False

# ══════════════════════════════════════════════════════════════════════
#  IMAGE ZOOM PROCESSOR
# ══════════════════════════════════════════════════════════════════════

ZOOM_RANGES: dict[str, tuple[float, float]] = {
    "easy":   (0.55, 0.75),
    "medium": (0.25, 0.55),
    "hard":   (0.06, 0.25),
}
DIFFICULTY_LABELS = {
    "easy":   "🟢 Easy",
    "medium": "🟡 Medium",
    "hard":   "🔴 Hard",
    "random": "🎲 Random",
}

def _zoom_sync(filepath: str, difficulty: str) -> Optional[bytes]:
    try:
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        actual  = difficulty if difficulty != "random" else random.choice(["easy","medium","hard"])
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
#  GAME 1 — GUESS BY PICTURE
# ══════════════════════════════════════════════════════════════════════

class DifficultyView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=120)
        self.channel_id, self.host_id = channel_id, host_id

    async def _start(self, i: discord.Interaction, diff: str):
        if i.user.id != self.host_id:
            await i.response.send_message("❌ Only the host can pick difficulty.", ephemeral=True); return
        images   = db.get("hero_images", {})
        hero_cnt = sum(1 for h in images if images[h])
        active_picture[self.channel_id] = {
            "host_id": self.host_id, "difficulty": diff,
            "hero": None, "used": [], "scores": {}, "revealed": True,
        }
        label = DIFFICULTY_LABELS.get(diff, diff)
        e = discord.Embed(
            title=f"🖼️  Guess by Picture  —  {label}",
            description=(f"{SEP}\n*Hosted by **{i.user.display_name}***\n\n"
                         "A cropped hero image will appear below.\n"
                         "**Type the hero's name in this channel** to win a point!\n\n"
                         f"🎮 **{hero_cnt}** heroes in the pool  ·  Difficulty: **{label}**\n{SEP}"),
            color=AMBER)
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
        game = active_picture.get(self.channel_id)
        if not game or game.get("revealed"):
            await i.response.send_message("No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        await i.response.send_message(embed=discord.Embed(
            title="⏭️  Skipped!",
            description=f"The hero was **{hero}**\n*{hero_role_str(hero)}*",
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
    images = db.get("hero_images", {})
    used   = game.get("used", [])
    pool   = [h for h in images if images[h] and h not in used]
    if not pool:
        await channel.send(embed=empire_embed(
            "✅  All Heroes Shown!" if used else "⚠️  No Images",
            "Every hero with images has been shown. Well played!" if used
            else "Use `/set_hero_image` to add images!",
            GOLD if used else CRIMSON))
        await _picture_end(channel, channel_id); return
    hero     = random.choice(pool)
    filepath = pick_image(hero)
    if not filepath:
        game["used"].append(hero)
        await _picture_round(channel, channel_id); return
    difficulty  = game["difficulty"]
    actual_diff = difficulty if difficulty != "random" else random.choice(["easy","medium","hard"])
    file = await zoom_image(filepath, actual_diff)
    game.update({"hero": hero, "revealed": False})
    game["used"].append(hero)
    diff_label = DIFFICULTY_LABELS.get(actual_diff, actual_diff)
    round_num  = len(game["used"])
    total      = len(pool) + len(used)
    e = discord.Embed(
        title=f"🖼️  Guess by Picture  —  Round {round_num}/{total}",
        description=(f"{SEP}\n*Which Honor of Kings hero is this?*\n\n"
                     "**Type the hero's name in this channel.**\n"
                     f"First correct answer wins a point!\n\nDifficulty: **{diff_label}**\n{SEP}"),
        color=AMBER)
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


async def _picture_next(channel, channel_id):
    if not active_picture.get(channel_id): return
    await asyncio.sleep(3)
    await _picture_round(channel, channel_id)

async def _picture_end(channel, channel_id):
    game = active_picture.pop(channel_id, None)
    if not game: return
    e = discord.Embed(
        title="🏁  Guess by Picture  —  Game Over!",
        description=f"{SEP}\n*{len(game.get('used',[]))} heroes were shown.*\n{SEP}",
        color=GOLD)
    _add_scores(e, game.get("scores", {}), channel.guild)
    _save_scores(game.get("scores", {}))
    brand(e); await channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════
#  GAME 2 — GUESS BY QUOTE
# ══════════════════════════════════════════════════════════════════════

class QuoteRoundView(View):
    def __init__(self, channel_id: int, host_id: int, round_id: str):
        super().__init__(timeout=None)
        self.channel_id, self.host_id, self.round_id = channel_id, host_id, round_id

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, i: discord.Interaction, _: Button):
        game = active_quote.get(self.channel_id)
        if not game or game.get("revealed") or game.get("round_id") != self.round_id:
            await i.response.send_message("No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        await i.response.send_message(embed=discord.Embed(
            title="⏭️  Skipped!",
            description=f"That was **{hero}**\n*{hero_role_str(hero)}*",
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
        await channel.send(embed=empire_embed("✅  All Quotes Used!","Every hero has spoken. Game over!", GOLD))
        await _quote_end(channel, channel_id); return
    hero     = random.choice(pool)
    quote    = HOK_QUOTES[hero]
    round_id = str(random.randint(100000, 999999))
    game.update({"hero": hero, "revealed": False, "round_id": round_id})
    game["used"].append(hero)
    round_num = len(game["used"])
    total     = len(HOK_QUOTES)
    e = discord.Embed(
        title=f"💬  Guess by Quote  —  Round {round_num}/{total}",
        description=(f"{SEP}\n*Which Honor of Kings hero said this?*\n\n"
                     f"**❝  {quote}  ❞**\n\n"
                     f"Type the hero's name in this channel.\nFirst correct answer wins a point!\n{SEP}"),
        color=TEAL)
    e.set_footer(text=f"⚜  Oblivion Empire  ·  {hero_role_str(hero)}",
                 icon_url=logo_url() or discord.utils.MISSING)
    await channel.send(embed=e, view=QuoteRoundView(channel_id, game["host_id"], round_id))


async def _quote_next(channel, channel_id):
    if not active_quote.get(channel_id): return
    await asyncio.sleep(3)
    await _quote_round(channel, channel_id)

async def _quote_end(channel, channel_id):
    game = active_quote.pop(channel_id, None)
    if not game: return
    e = discord.Embed(
        title="🏁  Guess by Quote  —  Game Over!",
        description=f"{SEP}\n*{len(game.get('used',[]))} quotes shown.*\n{SEP}",
        color=GOLD)
    _add_scores(e, game.get("scores", {}), channel.guild)
    _save_scores(game.get("scores", {}))
    brand(e); await channel.send(embed=e)

# ─── Shared score helpers ──────────────────────────────────────────────

def _add_scores(embed: discord.Embed, scores: dict, guild: discord.Guild):
    if not scores:
        embed.add_field(name="📊 Scores", value="No points scored.", inline=False); return
    medals = ["🥇", "🥈", "🥉"]; lines = []
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
#  GAME 3 — MAFIA
#
#  Phase flow:
#    Start → Night 1 (auto)
#    Night: when ALL special roles submit → Dawn auto-triggers (3s delay)
#           "Force Dawn" button available as fallback for AFK players
#    Dawn  → Day discussion
#    Day   → host clicks "Open Voting"
#    Voting → host clicks "Tally Votes" → Night auto-starts
# ══════════════════════════════════════════════════════════════════════

MAFIA_ROLES: dict[str, dict] = {
    # ── Core roles ─────────────────────────────────────────────────
    "Mafia": {
        "emoji": "🗡️", "team": "mafia",
        "desc": (
            "You and your allies eliminate one villager every night.\n"
            "Blend in during the day — vote with the crowd, point fingers,\n"
            "and avoid suspicion at all costs.\n\n"
            "**Win condition:** equal or outnumber the Village."
        ),
    },
    "Villager": {
        "emoji": "🏡", "team": "village",
        "desc": (
            "You have no special ability — but your vote is your weapon.\n"
            "Pay attention, build cases, and trust your instincts.\n"
            "The Mafia is hiding among you right now.\n\n"
            "**Win condition:** eliminate all Mafia."
        ),
    },
    "Doctor": {
        "emoji": "💊", "team": "village",
        "desc": (
            "Each night, choose one player to protect.\n"
            "If the Mafia targets them, they survive — and you stay alive too.\n"
            "You can protect yourself, but don't rely on it.\n\n"
            "**Win condition:** eliminate all Mafia."
        ),
    },
    "Detective": {
        "emoji": "🔍", "team": "village",
        "desc": (
            "Each night, investigate one player.\n"
            "You will learn if they are **Mafia** or **Village** — but not their exact role.\n"
            "Use this information wisely; if Mafia identifies you, you're a priority target.\n\n"
            "**Win condition:** eliminate all Mafia."
        ),
    },
    # ── Unlocks at 14 players ──────────────────────────────────────
    "Bodyguard": {
        "emoji": "🛡️", "team": "village",
        "desc": (
            "Each night, choose one player to guard with your life.\n"
            "If the Mafia targets them — **you die instead, they live.**\n"
            "If the Mafia targets anyone else, you survive unharmed.\n"
            "Unlike the Doctor, saving someone costs you everything.\n\n"
            "**Win condition:** eliminate all Mafia."
        ),
    },
    # ── Unlocks at 20 players ──────────────────────────────────────
    "Vigilante": {
        "emoji": "⚡", "team": "village",
        "desc": (
            "You carry justice — and a burden.\n"
            "**Once per game**, you may execute a player at night.\n"
            "If your target is Mafia → you become a hero.\n"
            "If your target is innocent → **you die of guilt** the same dawn.\n"
            "Each other night you must choose to hold your power.\n\n"
            "**Win condition:** eliminate all Mafia."
        ),
    },
}

# ── How many Mafia per player count ───────────────────────────────
def _mafia_count(n: int) -> int:
    """1 Mafia per 7 players."""
    return max(1, n // 7)

def assign_roles(n: int) -> list[str]:
    """
    Role assignment rules:
      7–13  players : 1 Mafia · Doctor · Detective · Villagers
      14–20 players : 2 Mafia · Doctor · Detective · Bodyguard · Villagers
      21+   players : 3+ Mafia · Doctor · Detective · Bodyguard · Vigilante · Villagers
    Doctor and Detective are always present (minimum is 7).
    """
    roles: list[str] = ["Mafia"] * _mafia_count(n)
    roles += ["Doctor", "Detective"]
    if n >= 14: roles.append("Bodyguard")
    if n >= 20: roles.append("Vigilante")
    roles += ["Villager"] * (n - len(roles))
    random.shuffle(roles)
    return roles


def _all_night_done(game: "MafiaGame") -> bool:
    """True when every special role that is alive has submitted an action."""
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


class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel = channel
        self.host    = host
        self.players: list[discord.Member] = [host]
        self.roles:   dict[int, str]       = {}
        self.alive:   list[discord.Member] = []
        self.phase    = "lobby"
        self.day      = 0
        self.night    = 0
        self.votes:   dict[int, int] = {}
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

    def mafia_alive(self)    -> list[discord.Member]:
        return [m for m in self.alive if self.is_mafia(m)]

    def village_alive(self)  -> list[discord.Member]:
        return [m for m in self.alive if not self.is_mafia(m)]

    def check_win(self) -> Optional[str]:
        if not self.mafia_alive(): return "village"
        if len(self.mafia_alive()) >= len(self.village_alive()): return "mafia"
        return None

    def transfer_host(self):
        if self.host not in self.alive and self.alive:
            self.host = self.alive[0]


def _player_count_preview(n: int) -> str:
    mc    = _mafia_count(n)
    roles = [f"🗡️ ×{mc} Mafia", "💊 Doctor", "🔍 Detective"]
    if n >= 14: roles.append("🛡️ Bodyguard")
    if n >= 20: roles.append("⚡ Vigilante")
    vills = n - mc - 2 - (1 if n >= 14 else 0) - (1 if n >= 20 else 0)
    roles.append(f"🏡 ×{vills} Villagers")
    return "  ·  ".join(roles)


def _lobby_embed(game: MafiaGame) -> discord.Embed:
    n        = len(game.players)
    preview  = _player_count_preview(n) if n >= 7 else "*Need 7 players to preview roles*"
    e = discord.Embed(
        title="🎭  Mafia  —  Lobby",
        description=(
            f"{SEP}\n"
            f"*Host: **{game.host.display_name}***  ·  **{n}/7** minimum\n\n"
            "**Role roster unlocks:**\n"
            "👥 **7+** — 🗡️ Mafia · 💊 Doctor · 🔍 Detective · 🏡 Villagers\n"
            "👥 **14+** — adds 🛡️ **Bodyguard** *(guards a player; dies in their place)*\n"
            "👥 **20+** — adds ⚡ **Vigilante** *(one-time night execution; guilt kills if wrong)*\n"
            f"👥 **Mafia scaling** — 1 per 7 players\n\n"
            f"**Current roster preview:**\n{preview}\n"
            f"{SEP}"
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

    @discord.ui.button(label="Join",   style=discord.ButtonStyle.success, emoji="✋")
    async def join_btn(self, i: discord.Interaction, _: Button):
        if self.game.phase != "lobby":
            await i.response.send_message("❌ Already started.", ephemeral=True); return
        if i.user in self.game.players:
            await i.response.send_message("❌ Already joined.", ephemeral=True); return
        self.game.players.append(i.user)
        await i.response.send_message(f"✅ **{i.user.display_name}** joined the shadows!")
        if self.game.lobby_msg:
            try: await self.game.lobby_msg.edit(embed=_lobby_embed(self.game), view=self)
            except Exception: pass

    @discord.ui.button(label="Start",  style=discord.ButtonStyle.primary,  emoji="▶️")
    async def start_btn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can start.", ephemeral=True); return
        if len(self.game.players) < 7:
            await i.response.send_message(
                f"❌ Need at least **7 players** to start. "
                f"Currently **{len(self.game.players)}/7**.", ephemeral=True); return
        await i.response.defer()
        await _mafia_start(self.game)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger,   emoji="❌")
    async def cancel_btn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can cancel.", ephemeral=True); return
        active_mafia.pop(self.game.channel.id, None)
        await i.response.send_message(embed=empire_embed("❌  Cancelled","Mafia game cancelled.", CRIMSON))
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
        color = CRIMSON if role == "Mafia" else (
            0x8b5e00 if role == "Bodyguard" else
            0x5c3d99 if role == "Vigilante" else
            TEAL
        )
        e = discord.Embed(
            title=f"🃏  Your Role  —  {role_info['emoji']} {role}",
            description=f"{SEP}\n{role_info['desc']}\n{SEP}",
            color=color)
        e.add_field(name="⚔️ Team", value=role_info["team"].capitalize(), inline=True)
        if role == "Mafia":
            team = ", ".join(m.display_name for m in game.players if game.is_mafia(m))
            e.add_field(name="🗡️ Your Allies", value=team or "You're alone…", inline=False)
        e.set_footer(text="⚜  Oblivion Empire  ·  Keep your role secret!")
        try:    await member.send(embed=e)
        except: dm_fails.append(member.display_name)

    names  = "\n".join(f"• {m.display_name}" for m in game.players)
    roster = _player_count_preview(len(game.players))
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
    await asyncio.sleep(3)
    await _mafia_night(game)


# ══════════════════════════════════════════════════════════════════════
#  NIGHT PHASE
# ══════════════════════════════════════════════════════════════════════

class NightActionView(View):
    """
    Sent via DM — i.guild is None in this context.
    guild_id is stored so we can resolve members via bot.get_guild().
    """
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
        elif actor_role == "Bodyguard":
            candidates = [m for m in game.alive if m.id != user_id]
        elif actor_role == "Vigilante":
            candidates = [m for m in game.alive if m.id != user_id]
        else:
            candidates = []

        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in candidates if m.id != user_id]

        if actor_role == "Vigilante" and not game.vigilante_used:
            opts.insert(0, discord.SelectOption(
                label="🤝 Hold my power this night",
                value="0",
                description="Save the execution for a better moment"))

        if not opts: return

        placeholders = {
            "Mafia":      "🗡️  Choose tonight's target…",
            "Doctor":     "💊  Choose who to protect…",
            "Detective":  "🔍  Choose who to investigate…",
            "Bodyguard":  "🛡️  Choose who to guard with your life…",
            "Vigilante":  "⚡  Use your power or hold it…",
        }
        sel = Select(placeholder=placeholders.get(actor_role, "Select…"), options=opts[:25])
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ This isn't your action.", ephemeral=True); return

        raw = i.data["values"][0]
        tid = int(raw)

        guild  = bot.get_guild(self.guild_id)
        target = guild.get_member(tid) if (guild and tid != 0) else None

        self.game.night_actions[self.actor_role] = tid

        if self.actor_role == "Vigilante" and tid == 0:
            msg = "🤝 Power held. Waiting for a better moment…"
        else:
            msgs = {
                "Mafia":     f"🗡️ Target locked: **{target.display_name if target else '?'}**\n*They won't see it coming.*",
                "Doctor":    f"💊 Protecting **{target.display_name if target else '?'}** tonight.\n*Stay close.*",
                "Detective": f"🔍 Investigating **{target.display_name if target else '?'}**…\n*Results at dawn.*",
                "Bodyguard": f"🛡️ Guarding **{target.display_name if target else '?'}** with your life.\n*You will die for them if needed.*",
                "Vigilante": f"⚡ Executing **{target.display_name if target else '?'}** tonight.\n*Justice — or guilt — awaits at dawn.*",
            }
            msg = msgs.get(self.actor_role, "✅ Action submitted.")

        await i.response.send_message(msg, ephemeral=True)
        self.stop()

        if _all_night_done(self.game) and not self.game._dawn_scheduled:
            self.game._dawn_scheduled = True
            asyncio.create_task(_auto_dawn(self.game))


class NightForceView(View):
    """Fallback — lets host force dawn if someone goes AFK."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="Force Dawn  (AFK fallback)", style=discord.ButtonStyle.secondary, emoji="🌅")
    async def force_dawn(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can force dawn.", ephemeral=True); return
        if self.game._dawn_scheduled:
            await i.response.send_message("Dawn is already triggering.", ephemeral=True); return
        self.game._dawn_scheduled = True
        self.stop()
        await i.response.defer()
        await _mafia_resolve_night(self.game)


async def _auto_dawn(game: MafiaGame):
    """Triggered automatically once all night actions are submitted."""
    await asyncio.sleep(4)
    if game.phase == "night" and game.channel.id in active_mafia:
        await game.channel.send(embed=discord.Embed(
            title="🌅  All actions submitted — Dawn breaks!",
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
    game.transfer_host()

    special_alive = [r for r in ("Mafia","Doctor","Detective","Bodyguard","Vigilante")
                     if any(game.get_role(m) == r for m in game.alive)]
    active_roles  = [r for r in special_alive
                     if not (r == "Vigilante" and game.vigilante_used)]

    role_icons = {"Mafia":"🗡️","Doctor":"💊","Detective":"🔍","Bodyguard":"🛡️","Vigilante":"⚡"}
    acting_str = "  ".join(f"{role_icons[r]}{r}" for r in active_roles) or "*(no special roles)*"

    e = discord.Embed(
        title=f"🌙  Night {game.night}  —  Darkness Falls",
        description=(
            f"{SEP}\n"
            "Special roles — check your **DMs** for your action menu.\n\n"
            f"**Acting tonight:** {acting_str}\n\n"
            "Dawn triggers automatically once all actions are submitted.\n"
            f"*(Host can force dawn if someone goes AFK)*\n"
            f"{SEP}"
        ), color=PHANTOM)
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Host: {game.host.display_name}")
    brand(e)
    await game.channel.send(embed=e, view=NightForceView(game))

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
    """
    Night resolution order:
      1. Detective → private DM result
      2. Vigilante → executes target (or holds); if innocent, dies of guilt
      3. Doctor    → saves target from Mafia
      4. Bodyguard → if Mafia targets their ward (and Doctor didn't save), Bodyguard dies instead
      5. Mafia     → kills target (unless Doctor saved or Bodyguard sacrificed)
    """
    guild     = game.channel.guild
    elim_id   = game.night_actions.get("Mafia")     or 0
    prot_id   = game.night_actions.get("Doctor")    or 0
    guard_id  = game.night_actions.get("Bodyguard") or 0
    invest_id = game.night_actions.get("Detective") or 0
    vig_id    = game.night_actions.get("Vigilante") or 0

    dawn: list[str] = []

    # ── 1. Detective DM ───────────────────────────────────────────
    if invest_id:
        target = guild.get_member(invest_id)
        det    = next((m for m in game.alive if game.get_role(m) == "Detective"), None)
        if target and det:
            is_maf = game.get_role(target) == "Mafia"
            try:
                await det.send(embed=discord.Embed(
                    title="🔍  Investigation Result",
                    description=(
                        f"Your investigation is complete.\n\n"
                        f"**{target.display_name}** is "
                        f"{'🗡️ **Mafia** — they are your enemy.' if is_maf else '🏡 **Village** — they appear innocent.'}"
                    ),
                    color=CRIMSON if is_maf else EMERALD))
            except Exception:
                pass

    # ── 2. Vigilante execution ────────────────────────────────────
    if vig_id and vig_id != 0:
        game.vigilante_used = True
        vig_target = guild.get_member(vig_id)
        if vig_target and vig_target in game.alive:
            is_mafia_target = game.get_role(vig_target) == "Mafia"
            game.alive.remove(vig_target)
            if is_mafia_target:
                dawn.append(
                    f"⚡ **Justice was served in the night!**\n"
                    f"An unknown force eliminated **{vig_target.display_name}**.\n"
                    f"They were: 🗡️ **Mafia** — a hero walks among you.")
            else:
                ri         = MAFIA_ROLES[game.get_role(vig_target)]
                vig_member = next((m for m in game.alive if game.get_role(m) == "Vigilante"), None)
                dawn.append(
                    f"⚡ **A Vigilante struck — and paid the price.**\n"
                    f"**{vig_target.display_name}** was executed.\n"
                    f"They were: {ri['emoji']} **{game.get_role(vig_target)}** — innocent.\n"
                    f"*Consumed by guilt, the Vigilante also fell.*")
                if vig_member and vig_member in game.alive:
                    game.alive.remove(vig_member)

    # ── 3–5. Mafia kill, Doctor save, Bodyguard sacrifice ─────────
    if elim_id:
        victim = guild.get_member(elim_id)

        if elim_id == prot_id:
            dawn.append("💊 The Mafia struck — but **someone survived** the night.\n*The Doctor's protection held.*")

        elif elim_id == guard_id:
            guard_member = next((m for m in game.alive if game.get_role(m) == "Bodyguard"), None)
            if guard_member and guard_member in game.alive:
                game.alive.remove(guard_member)
                dawn.append(
                    f"🛡️ **A guardian fell in the night.**\n"
                    f"The Mafia targeted **{victim.display_name if victim else '?'}** — "
                    f"but the **Bodyguard** stepped in front and paid with their life.\n"
                    f"**{victim.display_name if victim else '?'}** survived.")
            else:
                if victim and victim in game.alive:
                    game.alive.remove(victim)
                    ri = MAFIA_ROLES[game.get_role(victim)]
                    dawn.append(
                        f"💀 **{victim.display_name}** was eliminated by the Mafia.\n"
                        f"They were: {ri['emoji']} **{game.get_role(victim)}**")
        else:
            if victim and victim in game.alive:
                game.alive.remove(victim)
                ri = MAFIA_ROLES[game.get_role(victim)]
                dawn.append(
                    f"💀 **{victim.display_name}** was eliminated by the Mafia.\n"
                    f"They were: {ri['emoji']} **{game.get_role(victim)}**")
    else:
        if not any("Vigilante" in line for line in dawn):
            dawn.append("😴 A quiet night — the Mafia held back. Nobody was eliminated.")

    alive_names = "  ·  ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"🌅  Dawn  —  Day {game.day + 1} begins",
        description=(
            f"{SEP}\n"
            + "\n\n".join(dawn)
            + f"\n\n**Alive ({len(game.alive)}):** {alive_names}\n"
            + f"{SEP}"
        ), color=GOLD)
    brand(e)
    await game.channel.send(embed=e)

    if w := game.check_win():
        await _mafia_end(game, w); return
    await asyncio.sleep(2)
    await _mafia_day(game)


# ══════════════════════════════════════════════════════════════════════
#  DAY PHASE
# ══════════════════════════════════════════════════════════════════════

class DayControlView(View):
    """Host-only button to open voting after discussion."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="Open Voting", style=discord.ButtonStyle.primary, emoji="🗳️")
    async def open_voting(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can open voting.", ephemeral=True)
            return
        if self.game.phase != "day":
            await i.response.send_message("❌ Not in the day phase.", ephemeral=True)
            return
        self.stop()
        await i.response.defer()
        await _mafia_voting(self.game)


async def _mafia_day(game: MafiaGame):
    game.phase  = "day"
    game.day   += 1
    game.votes  = {}
    game.transfer_host()

    alive_names = "  ·  ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"☀️  Day {game.day}  —  Town Discussion",
        description=(
            f"{SEP}\n"
            "The town gathers. Discuss, debate, and find the Mafia.\n\n"
            f"**Alive ({len(game.alive)}):** {alive_names}\n\n"
            f"*When ready, the host opens voting.*\n"
            f"{SEP}"
        ),
        color=GOLD,
    )
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Host: {game.host.display_name}")
    brand(e)
    await game.channel.send(embed=e, view=DayControlView(game))


# ══════════════════════════════════════════════════════════════════════
#  VOTING PHASE
# ══════════════════════════════════════════════════════════════════════

class VotingView(View):
    """Each alive player votes once; host tallies when ready."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

        opts = [
            discord.SelectOption(label=m.display_name[:100], value=str(m.id))
            for m in game.alive
        ]
        sel = Select(placeholder="🗳️  Vote to eliminate…", options=opts[:25])
        sel.callback = self._on_vote
        self.add_item(sel)

    async def _on_vote(self, i: discord.Interaction):
        if self.game.phase != "voting":
            await i.response.send_message("❌ Voting is closed.", ephemeral=True)
            return
        voter = i.user
        if voter not in self.game.alive:
            await i.response.send_message("❌ Only alive players can vote.", ephemeral=True)
            return
        target_id = int(i.data["values"][0])
        if target_id == voter.id:
            await i.response.send_message("❌ You can't vote for yourself.", ephemeral=True)
            return
        already_voted = voter.id in self.game.votes
        self.game.votes[voter.id] = target_id
        target = self.game.channel.guild.get_member(target_id)
        action = "changed their vote to" if already_voted else "voted against"
        await i.response.send_message(
            f"✅ **{voter.display_name}** {action} **{target.display_name if target else '?'}**."
        )


class TallyView(View):
    """Host-only tally button."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="Tally Votes", style=discord.ButtonStyle.danger, emoji="⚖️")
    async def tally(self, i: discord.Interaction, _: Button):
        if i.user != self.game.host:
            await i.response.send_message("❌ Only the host can tally votes.", ephemeral=True)
            return
        if self.game.phase != "voting":
            await i.response.send_message("❌ Not in voting phase.", ephemeral=True)
            return
        self.stop()
        await i.response.defer()
        await _mafia_tally(self.game)


async def _mafia_voting(game: MafiaGame):
    game.phase = "voting"
    game.votes = {}

    alive_names = "  ·  ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"🗳️  Day {game.day}  —  Voting Opens",
        description=(
            f"{SEP}\n"
            "Cast your vote using the menu below.\n"
            "You may change your vote before the host tallies.\n\n"
            f"**Alive ({len(game.alive)}):** {alive_names}\n"
            f"{SEP}"
        ),
        color=CRIMSON,
    )
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Host tallies when ready")
    brand(e)
    await game.channel.send(embed=e, view=VotingView(game))
    await game.channel.send(
        embed=discord.Embed(
            description="*Host: click **Tally Votes** when discussion is done.*",
            color=PHANTOM,
        ),
        view=TallyView(game),
    )


async def _mafia_tally(game: MafiaGame):
    """Count votes, eliminate the plurality leader, then start night."""
    guild = game.channel.guild

    if not game.votes:
        await game.channel.send(embed=discord.Embed(
            title="⚖️  No Votes Cast",
            description="Nobody voted. The town lets the day slip by.\n*Night falls…*",
            color=PHANTOM,
        ))
        await asyncio.sleep(2)
        await _mafia_night(game)
        return

    tally: dict[int, int] = {}
    for target_id in game.votes.values():
        tally[target_id] = tally.get(target_id, 0) + 1

    lines = []
    for tid, count in sorted(tally.items(), key=lambda x: -x[1]):
        member = guild.get_member(tid)
        name   = member.display_name if member else f"<{tid}>"
        bar    = "█" * count
        lines.append(f"**{name}** — {bar} ({count})")

    max_votes   = max(tally.values())
    top_targets = [tid for tid, c in tally.items() if c == max_votes]

    if len(top_targets) > 1:
        tied_names  = ", ".join(
            (guild.get_member(tid).display_name if guild.get_member(tid) else str(tid))
            for tid in top_targets
        )
        result_text = f"**Tie between {tied_names}** — no one is eliminated.\n*The Mafia breathes easy.*"
    else:
        eliminated = guild.get_member(top_targets[0])
        if eliminated and eliminated in game.alive:
            game.alive.remove(eliminated)
        ri          = MAFIA_ROLES[game.get_role(eliminated)] if eliminated else None
        result_text = (
            f"**{eliminated.display_name if eliminated else '?'}** is eliminated by the town.\n"
            f"They were: {ri['emoji']} **{game.get_role(eliminated)}**"
        ) if eliminated and ri else "The eliminated player could not be found."

    alive_names = "  ·  ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"⚖️  Day {game.day}  —  Verdict",
        description=(
            f"{SEP}\n"
            + "\n".join(lines)
            + f"\n\n{result_text}\n\n"
            + f"**Alive ({len(game.alive)}):** {alive_names}\n"
            + f"{SEP}"
        ),
        color=CRIMSON,
    )
    brand(e)
    await game.channel.send(embed=e)

    if w := game.check_win():
        await _mafia_end(game, w)
        return

    await asyncio.sleep(3)
    await _mafia_night(game)


async def _mafia_end(game: MafiaGame, winner: str):
    game.phase = "ended"; active_mafia.pop(game.channel.id, None)
    if winner == "village":
        title, desc, color = "🏡  Village Wins!", "The Mafia is gone. Oblivion Empire is safe!", EMERALD
    else:
        title, desc, color = "🗡️  Mafia Wins!", "The Mafia controls Oblivion Empire. Darkness reigns…", CRIMSON
    reveal = "\n".join(
        f"{MAFIA_ROLES[game.get_role(m)]['emoji']} **{m.display_name}** — {game.get_role(m)}"
        for m in game.players)
    e = discord.Embed(title=title,
                      description=f"{SEP}\n{desc}\n{SEP}", color=color)
    e.add_field(name="🃏 Full Role Reveal", value=reveal, inline=False)
    brand(e); await game.channel.send(embed=e)
    await log_action(game.channel.guild, "🎭 Mafia Ended",
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
        images = db.get("hero_images", {})
        if not any(v for v in images.values()):
            await i.response.send_message(embed=empire_embed(
                "⚠️  No Hero Images Yet",
                "Use `/set_hero_image` to add images:\n\n"
                "1. Type `/set_hero_image` in Discord\n"
                "2. Pick the hero from the autocomplete list\n"
                "3. Attach the image file (.png/.jpg)\n\n"
                "Use `/hero_images` to track progress.", CRIMSON), ephemeral=True); return
        hero_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🖼️  Guess by Picture  —  Choose Difficulty",
            description=(f"{SEP}\n*Host: **{i.user.display_name}***\n\n"
                         f"**{hero_cnt}** heroes ready in the pool.\n\n"
                         "🟢 **Easy** — 55–75% of image visible\n"
                         "🟡 **Medium** — 25–55% visible\n"
                         "🔴 **Hard** — 6–25% visible\n"
                         f"🎲 **Random** — different every round\n{SEP}"),
            color=AMBER)
        brand(e)
        await i.response.send_message(embed=e, view=DifficultyView(cid, i.user.id))

    @discord.ui.button(label="Guess by Quote",   emoji="💬", style=discord.ButtonStyle.success,   row=0)
    async def quote_btn(self, i: discord.Interaction, _: Button):
        cid  = i.channel_id
        busy = channel_busy(cid)
        if busy:
            await i.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        active_quote[cid] = {
            "host_id": i.user.id, "hero": None, "round_id": None,
            "used": [], "scores": {}, "revealed": True,
        }
        e = discord.Embed(
            title="💬  Guess by Quote  —  Starting!",
            description=(f"{SEP}\n*Hosted by **{i.user.display_name}***\n\n"
                         "A hero quote will appear below.\n"
                         f"**Type who said it** to win a point!\n\n"
                         f"💬 **{len(HOK_QUOTES)}** heroes in the pool.\n{SEP}"),
            color=TEAL)
        brand(e)
        await i.response.send_message(embed=e)
        await asyncio.sleep(2)
        await _quote_round(i.channel, cid)

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
        await log_action(i.guild, "🎭 Mafia Lobby",
            f"{i.user.mention} opened in #{i.channel.name}")

    @discord.ui.button(label="All-Time Scores",  emoji="🏅", style=discord.ButtonStyle.secondary, row=1)
    async def scores_btn(self, i: discord.Interaction, _: Button):
        scores = db.get("game_scores", {})
        if not scores:
            await i.response.send_message(empire_embed("🏅  No Scores Yet","Play some games first!", VIOLET), ephemeral=True); return
        medals = ["🥇", "🥈", "🥉"]; lines = []
        for n, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x: -x[1])[:15], 1):
            mem   = i.guild.get_member(int(uid))
            name  = mem.display_name if mem else f"ID:{uid}"
            medal = medals[n - 1] if n <= 3 else f"`{n}.`"
            lines.append(f"{medal}  **{name}**  —  {pts} pt{'s' if pts != 1 else ''}")
        e = discord.Embed(title="🏅  All-Time Scores",
                          description=f"{SEP}\n" + "\n".join(lines) + f"\n{SEP}",
                          color=GOLD)
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
        images  = db.get("hero_images", {})
        img_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🎮  Oblivion Empire  —  Games",
            description=f"{SEP}\n*Welcome to the arena, warrior.*\n{SEP}",
            color=VIOLET)
        e.set_thumbnail(url=logo_url() or (bot_avatar() or discord.utils.MISSING))
        e.add_field(name="🖼️ Guess by Picture",
                    value=(f"A cropped hero image appears — type the name to win.\n"
                           f"*{img_cnt} hero{'es' if img_cnt != 1 else ''} ready · Easy / Medium / Hard / Random*"),
                    inline=False)
        e.add_field(name="💬 Guess by Quote",
                    value=(f"A hero quote appears — type who said it.\n"
                           f"*{len(HOK_QUOTES)} heroes · works immediately*"),
                    inline=False)
        e.add_field(name="🎭 Mafia",
                    value="Social deduction — **7+ players** required.\nNight → Day → Vote → Night → repeat.\nAuto-advances · host controls pacing.",
                    inline=False)
        e.add_field(name="🏅 All-Time Scores", value="Combined leaderboard.", inline=False)
        e.set_footer(text="⚜  Oblivion Empire  ·  Games Panel", icon_url=logo_url() or discord.utils.MISSING)
        await i.response.send_message(embed=e, view=GamesPanelView())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        cid = message.channel.id

        pg = active_picture.get(cid)
        if pg and not pg.get("revealed") and pg.get("hero"):
            if check_guess(message.content, pg["hero"]):
                pg["revealed"] = True
                uid = str(message.author.id)
                pg["scores"][uid] = pg["scores"].get(uid, 0) + 1
                pts = pg["scores"][uid]
                e = discord.Embed(
                    title="✅  Correct!",
                    description=(f"{SEP}\n🎉 **{message.author.display_name}** got it!\n\n"
                                 f"The hero was **{pg['hero']}**\n*{hero_role_str(pg['hero'])}*\n\n"
                                 f"They now have **{pts}** point{'s' if pts != 1 else ''} this game.\n{SEP}"),
                    color=EMERALD)
                e.set_footer(text="⚜  Oblivion Empire  ·  Next hero coming up…",
                             icon_url=logo_url() or discord.utils.MISSING)
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _picture_next(message.channel, cid)

        qg = active_quote.get(cid)
        if qg and not qg.get("revealed") and qg.get("hero"):
            if check_guess(message.content, qg["hero"]):
                qg["revealed"] = True
                uid = str(message.author.id)
                qg["scores"][uid] = qg["scores"].get(uid, 0) + 1
                pts = qg["scores"][uid]
                e = discord.Embed(
                    title="✅  Correct!",
                    description=(f"{SEP}\n🎉 **{message.author.display_name}** got it!\n\n"
                                 f"That was **{qg['hero']}**\n*{hero_role_str(qg['hero'])}*\n\n"
                                 f"They now have **{pts}** point{'s' if pts != 1 else ''} this game.\n{SEP}"),
                    color=EMERALD)
                e.set_footer(text="⚜  Oblivion Empire  ·  Next quote coming up…",
                             icon_url=logo_url() or discord.utils.MISSING)
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _quote_next(message.channel, cid)


async def setup(bot_instance: commands.Bot):
    # NOTE: do NOT call tree.sync() here.
    # setup() runs before bot.start() so the HTTP client isn't connected yet.
    # Syncing happens in on_ready() once the bot is fully connected.
    bot_instance.tree.remove_command("games")
    await bot_instance.add_cog(GamesCog(bot_instance))
