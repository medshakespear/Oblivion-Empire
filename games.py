# ══════════════════════════════════════════════════════════════════════
#  games.py  —  Oblivion Empire Games Cog
# ══════════════════════════════════════════════════════════════════════
#
#  GUESS BY PICTURE — ZOOM SYSTEM:
#    When a round starts the bot randomly crops the hero image.
#    The crop size depends on difficulty:
#      🟢 Easy   — 55–75% of image visible (recognisable)
#      🟡 Medium — 25–55% visible (tricky)
#      🔴 Hard   — 6–25% visible (very hard)
#      🎲 Random — random difficulty every round
#    The crop is taken from a random position in the image,
#    then resized to 512×512 and sent as a file attachment.
#    Requires Pillow — listed in requirements.txt.
#
#  ADDING IMAGES:
#    /set_hero_image in Discord → pick hero → attach image file
#    Multiple images per hero are supported — picked randomly each round.
#
#  MAFIA — HOST-CONTROLLED:
#    No timers. Host decides when each phase advances:
#      Day discussion → host clicks "Open Voting" when ready
#      Voting         → host clicks "Tally Votes" when ready
#      Night          → host clicks "Dawn" after night actions
#    If host is eliminated another player takes control.
#
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio, random, unicodedata, re, os, io
from typing import Optional

from PIL import Image

from bot import db, save_db, brand, log_action, bot_avatar, _all_hero_names, HERO_IMAGES_DIR

EMPIRE_GOLD   = 0xc9a227
EMPIRE_RED    = 0x8b1a1a
EMPIRE_PURPLE = 0x5c0099
EMPIRE_GREEN  = 0x2ecc71
EMPIRE_CYAN   = 0x00b4d8

# ══════════════════════════════════════════════════════════════════════
#  COMPLETE HOK HERO ROSTER
#  Add new heroes at the bottom — the bot picks them up automatically.
# ══════════════════════════════════════════════════════════════════════

HOK_HEROES: dict[str, dict] = {
    # ── Tanks ──────────────────────────────────────────────────────
    "Lian Po":             {"class": "Tank",     "lane": "Baron Lane"},
    "Zhang Fei":           {"class": "Tank",     "lane": "Roam"},
    "Sun Ce":              {"class": "Tank",     "lane": "Roam"},
    "Dun":                 {"class": "Tank",     "lane": "Baron Lane"},
    "Pei":                 {"class": "Tank",     "lane": "Roam"},
    "Huang Gai":           {"class": "Tank",     "lane": "Roam"},
    "Mengchang":           {"class": "Tank",     "lane": "Baron Lane"},
    "Da Qiao":             {"class": "Tank",     "lane": "Roam"},     # also listed in support
    # ── Fighters ───────────────────────────────────────────────────
    "Arthur":              {"class": "Fighter",  "lane": "Baron Lane"},
    "Guan Yu":             {"class": "Fighter",  "lane": "Baron Lane"},
    "Liu Bei":             {"class": "Fighter",  "lane": "Baron Lane"},
    "Mulan":               {"class": "Fighter",  "lane": "Baron Lane"},
    "Xiang Yu":            {"class": "Fighter",  "lane": "Baron Lane"},
    "Loong":               {"class": "Fighter",  "lane": "Baron Lane"},
    "Wukong":              {"class": "Fighter",  "lane": "Jungle"},
    "Lam":                 {"class": "Fighter",  "lane": "Baron Lane"},
    "Zilong":              {"class": "Fighter",  "lane": "Baron Lane"},
    "Zhao Yun":            {"class": "Fighter",  "lane": "Baron Lane"},
    "Bai Qi":              {"class": "Fighter",  "lane": "Baron Lane"},
    "Yang Jian":           {"class": "Fighter",  "lane": "Baron Lane"},
    "Dian Wei":            {"class": "Fighter",  "lane": "Baron Lane"},
    "Sun Quan":            {"class": "Fighter",  "lane": "Baron Lane"},
    "Gao Changgong":       {"class": "Fighter",  "lane": "Jungle"},
    "Yue Buqun":           {"class": "Fighter",  "lane": "Baron Lane"},
    # ── Assassins ──────────────────────────────────────────────────
    "Li Bai":              {"class": "Assassin", "lane": "Jungle"},
    "Cao Cao":             {"class": "Assassin", "lane": "Jungle"},
    "Gan Jiang & Mo Ye":   {"class": "Assassin", "lane": "Jungle"},
    "Milady":              {"class": "Assassin", "lane": "Jungle"},
    "Consort Yu":          {"class": "Assassin", "lane": "Jungle"},
    "Han Xin":             {"class": "Assassin", "lane": "Jungle"},
    "Jing":                {"class": "Assassin", "lane": "Jungle"},
    "Gongsun Li":          {"class": "Assassin", "lane": "Dragon Lane"},
    "Hua Mulan":           {"class": "Assassin", "lane": "Jungle"},   # alternate version
    "Shangguan Wan'er":    {"class": "Assassin", "lane": "Jungle"},
    # ── Mages ──────────────────────────────────────────────────────
    "Diaochan":            {"class": "Mage",     "lane": "Mid Lane"},
    "Ying Zheng":          {"class": "Mage",     "lane": "Mid Lane"},
    "Zhong Kui":           {"class": "Mage",     "lane": "Mid Lane"},
    "Gao Jianli":          {"class": "Mage",     "lane": "Mid Lane"},
    "Zhuge Liang":         {"class": "Mage",     "lane": "Mid Lane"},
    "Luo Yi":              {"class": "Mage",     "lane": "Mid Lane"},
    "Nu Wa":               {"class": "Mage",     "lane": "Mid Lane"},
    "Di Renjie":           {"class": "Mage",     "lane": "Mid Lane"},
    "Su":                  {"class": "Mage",     "lane": "Mid Lane"},
    "Xun":                 {"class": "Mage",     "lane": "Mid Lane"},
    "Ming":                {"class": "Mage",     "lane": "Mid Lane"},
    "Voidcaller":          {"class": "Mage",     "lane": "Mid Lane"},
    "Wang Zhaojun":        {"class": "Mage",     "lane": "Mid Lane"},
    "Yun Zhongjun":        {"class": "Mage",     "lane": "Mid Lane"},
    "Pang Tong":           {"class": "Mage",     "lane": "Mid Lane"},
    "Sima Yi":             {"class": "Mage",     "lane": "Mid Lane"},
    # ── Marksmen ───────────────────────────────────────────────────
    "Sun Shangxiang":      {"class": "Marksman", "lane": "Dragon Lane"},
    "Hou Yi":              {"class": "Marksman", "lane": "Dragon Lane"},
    "Marco Polo":          {"class": "Marksman", "lane": "Dragon Lane"},
    "Luban No. 7":         {"class": "Marksman", "lane": "Dragon Lane"},
    "Huang Zhong":         {"class": "Marksman", "lane": "Dragon Lane"},
    "Mozi":                {"class": "Marksman", "lane": "Dragon Lane"},
    "Nakoruru":            {"class": "Marksman", "lane": "Dragon Lane"},
    "Kai":                 {"class": "Marksman", "lane": "Dragon Lane"},
    "Arash":               {"class": "Marksman", "lane": "Dragon Lane"},
    "Gan Ning":            {"class": "Marksman", "lane": "Dragon Lane"},
    # ── Supports ───────────────────────────────────────────────────
    "Lady Sun":            {"class": "Support",  "lane": "Roam"},
    "Mengmeng":            {"class": "Support",  "lane": "Roam"},
    "Luna":                {"class": "Support",  "lane": "Roam"},
    "Zhuangzi":            {"class": "Support",  "lane": "Roam"},
    "Fuzi":                {"class": "Support",  "lane": "Roam"},
    "Bian Que":            {"class": "Support",  "lane": "Roam"},
    "Cai Wenji":           {"class": "Support",  "lane": "Roam"},
    "Yaria":               {"class": "Support",  "lane": "Roam"},
    "Sun Bin":             {"class": "Support",  "lane": "Roam"},
    "Liu Shan":            {"class": "Support",  "lane": "Roam"},
    "Zhang Liang":         {"class": "Support",  "lane": "Roam"},
    # ── Add more heroes below this line ────────────────────────────
    # Format: "Hero Name": {"class": "CLASS", "lane": "LANE"},
}

# ══════════════════════════════════════════════════════════════════════
#  HERO QUOTES  (Guess by Quote game — bot shows these, players guess)
# ══════════════════════════════════════════════════════════════════════

HOK_QUOTES: dict[str, str] = {
    "Lian Po":           "I have broken armies with my body alone. You are no different.",
    "Zhang Fei":         "Come then! All of you at once — it will save time!",
    "Sun Ce":            "The south is mine. The rest is only a matter of time.",
    "Dun":               "I gave my eye for loyalty. I would give the other without hesitation.",
    "Pei":               "Stand behind me. Nothing gets through.",
    "Huang Gai":         "Old bones? My fists still hit harder than your best day.",
    "Mengchang":         "I open my doors to all — talent needs no invitation.",
    "Da Qiao":           "A gentle hand can still turn the tide of war.",
    "Arthur":            "A knight's strength means nothing without the honour that guides it.",
    "Guan Yu":           "Loyalty above all — even above life itself.",
    "Liu Bei":           "A true ruler earns the hearts of the people, not just their obedience.",
    "Mulan":             "They said I could not fight. I said nothing — and won.",
    "Xiang Yu":          "Heaven itself chose to end me. Even so, I do not regret a single battle.",
    "Loong":             "I am the will of the dragon — ancient, unbreakable, eternal.",
    "Wukong":            "No cage in heaven or earth can hold the Great Sage Equal to Heaven!",
    "Lam":               "The way of the blade has no shortcuts.",
    "Zilong":            "Speed is my armour. Precision is my shield.",
    "Zhao Yun":          "My spear has never tasted defeat.",
    "Bai Qi":            "I have buried kingdoms. What makes you think you are different?",
    "Yang Jian":         "Heaven sees all things. And I see further than heaven.",
    "Dian Wei":          "Weapons are merely tools. My body is the weapon.",
    "Sun Quan":          "To hold what you have is as great as to conquer new ground.",
    "Gao Changgong":     "Behind this mask hides a face that has never known defeat.",
    "Yue Buqun":         "With enough patience, even the sword fears the scabbard.",
    "Li Bai":            "Wine in one hand, sword in the other — the road ahead is mine.",
    "Cao Cao":           "Heroes rise and fall, but I alone will shape this age.",
    "Gan Jiang & Mo Ye": "Two blades. One soul. Neither of us fights alone.",
    "Milady":            "Elegance and lethality — why choose only one?",
    "Consort Yu":        "For him I would bring down the stars themselves.",
    "Han Xin":           "Strike from where they least expect. That is the only rule I follow.",
    "Jing":              "I do not miss. I never have.",
    "Gongsun Li":        "Dance and death look very similar from a distance.",
    "Hua Mulan":         "Every scar is a lesson the enemy paid to teach me.",
    "Shangguan Wan'er":  "Words are my blade. And my blade never misses.",
    "Diaochan":          "Every man who looks upon me sees only what he wishes to see.",
    "Ying Zheng":        "I unified the world. One more obstacle means nothing.",
    "Zhong Kui":         "Every demon I devour makes me stronger. Every single one.",
    "Gao Jianli":        "My music carries the weight of a nation's grief.",
    "Zhuge Liang":       "The battle is won long before the first blade is ever drawn.",
    "Luo Yi":            "Balance must be maintained — even at the cost of everything.",
    "Nu Wa":             "I shaped this world with my own hands. I can reshape it again.",
    "Di Renjie":         "Every crime leaves a trace. Every criminal leaves a story.",
    "Su":                "The pen and the sword both draw blood in the end.",
    "Xun":               "Music is the language of what words cannot say.",
    "Ming":              "Light and shadow are two sides of the same truth.",
    "Voidcaller":        "From the void I came. To the void all things return.",
    "Wang Zhaojun":      "I crossed a thousand miles of ice to forge peace. I can endure a little more.",
    "Yun Zhongjun":      "The storm above is mine to command. Stand back.",
    "Pang Tong":         "Behind this ugly face is a mind sharper than any sword.",
    "Sima Yi":           "I do not rush. Time is the only weapon I need.",
    "Sun Shangxiang":    "I was raised among warriors. Did you expect anything less?",
    "Hou Yi":            "I once shot nine suns from the sky. You are but one more target.",
    "Marco Polo":        "Every map has an edge — I have yet to find mine.",
    "Luban No. 7":       "Model seven, online. All systems… exceeding expectations.",
    "Huang Zhong":       "Age is just a number. My aim has never been sharper.",
    "Mozi":              "Engineering is the truest form of warfare.",
    "Nakoruru":          "Nature speaks to those who learn to listen.",
    "Kai":               "I was built for this moment. Every single moment.",
    "Arash":             "My arrow carries the sun's blessing. It will find you.",
    "Gan Ning":          "The sea does not ask permission. Neither do I.",
    "Lady Sun":          "Do not mistake my smile for weakness.",
    "Mengmeng":          "Every dream I weave is a world of its own.",
    "Luna":              "The moonlight guides those who are truly lost.",
    "Zhuangzi":          "Am I a man dreaming of a butterfly, or a butterfly dreaming of a man?",
    "Fuzi":              "True strength lies not in power, but in lifting others.",
    "Bian Que":          "Life and death rest in my hands. I choose life — for now.",
    "Cai Wenji":         "My songs have crossed a thousand miles of sorrow.",
    "Yaria":             "The spirits answer when I call.",
    "Sun Bin":           "A broken leg taught me to see farther than any general on horseback.",
    "Liu Shan":          "I know what others think of me. I choose my own path anyway.",
    "Zhang Liang":       "The revolution does not end. It only changes form.",
}

# ══════════════════════════════════════════════════════════════════════
#  HERO ALIASES  (shortcuts players can type and still get credit)
# ══════════════════════════════════════════════════════════════════════

HERO_ALIASES: dict[str, str] = {
    "gan jiang and mo ye": "Gan Jiang & Mo Ye",
    "gan mo":              "Gan Jiang & Mo Ye",
    "gm":                  "Gan Jiang & Mo Ye",
    "ganduo":              "Gan Jiang & Mo Ye",
    "gan":                 "Gan Jiang & Mo Ye",
    "luban":               "Luban No. 7",
    "luban7":              "Luban No. 7",
    "lu ban":              "Luban No. 7",
    "luban no 7":          "Luban No. 7",
    "lu ban no 7":         "Luban No. 7",
    "sun shang":           "Sun Shangxiang",
    "sun ss":              "Sun Shangxiang",
    "sss":                 "Sun Shangxiang",
    "sunshangxiang":       "Sun Shangxiang",
    "marco":               "Marco Polo",
    "consort":             "Consort Yu",
    "ying":                "Ying Zheng",
    "zhuge":               "Zhuge Liang",
    "cai":                 "Cai Wenji",
    "bian":                "Bian Que",
    "void":                "Voidcaller",
    "voidc":               "Voidcaller",
    "gongsun":             "Gongsun Li",
    "nuwa":                "Nu Wa",
    "nu wu":               "Nu Wa",
    "monkey":              "Wukong",
    "monkey king":         "Wukong",
    "sun wukong":          "Wukong",
    "lianpo":              "Lian Po",
    "zhangfei":            "Zhang Fei",
    "guanyu":              "Guan Yu",
    "libai":               "Li Bai",
    "caocao":              "Cao Cao",
    "liubei":              "Liu Bei",
    "zhaoyun":             "Zhao Yun",
    "baiqi":               "Bai Qi",
    "xiangyu":             "Xiang Yu",
    "hanxin":              "Han Xin",
    "diaochan":            "Diaochan",
    "zhongkui":            "Zhong Kui",
    "gaojianli":           "Gao Jianli",
    "luoyi":               "Luo Yi",
    "direnjie":            "Di Renjie",
    "huangzhong":          "Huang Zhong",
    "gongsunli":           "Gongsun Li",
    "ladysun":             "Lady Sun",
    "caiwenji":            "Cai Wenji",
    "bianque":             "Bian Que",
    "sunce":               "Sun Ce",
    "yangjian":            "Yang Jian",
    "dianwei":             "Dian Wei",
    "sunquan":             "Sun Quan",
    "gaochanggong":        "Gao Changgong",
    "wan er":              "Shangguan Wan'er",
    "waner":               "Shangguan Wan'er",
    "shangguan":           "Shangguan Wan'er",
    "wangzhaojun":         "Wang Zhaojun",
    "pangtong":            "Pang Tong",
    "simayi":              "Sima Yi",
    "ganning":             "Gan Ning",
    "sunbin":              "Sun Bin",
    "liushan":             "Liu Shan",
    "zhangliang":          "Zhang Liang",
    "arash":               "Arash",
    "lam":                 "Lam",
    "loong":               "Loong",
}

# ─── Answer checker ───────────────────────────────────────────────────

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
#
#  Loads a hero image from the local Railway volume,
#  crops a random region based on difficulty, resizes to 512×512.
#  Returns a discord.File ready to send.
#
#  Difficulty → fraction of image shown (smaller = harder):
#    easy:   55–75%
#    medium: 25–55%
#    hard:    6–25%
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


def _zoom_image_sync(filepath: str, difficulty: str) -> Optional[bytes]:
    """
    Synchronous Pillow processing — run in a thread via asyncio.to_thread().
    Returns PNG bytes or None on failure.
    """
    try:
        img = Image.open(filepath).convert("RGB")
        w, h = img.size

        actual_diff = difficulty if difficulty != "random" else random.choice(["easy","medium","hard"])
        min_f, max_f = ZOOM_RANGES.get(actual_diff, (0.25, 0.75))
        frac  = random.uniform(min_f, max_f)

        crop_w = max(int(w * frac), 32)
        crop_h = max(int(h * frac), 32)
        x = random.randint(0, max(w - crop_w, 0))
        y = random.randint(0, max(h - crop_h, 0))

        cropped = img.crop((x, y, x + crop_w, y + crop_h))
        resized = cropped.resize((512, 512), Image.LANCZOS)

        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


async def zoom_hero_image(filepath: str, difficulty: str) -> Optional[discord.File]:
    """Returns a discord.File with the cropped image, or None if processing fails."""
    if not os.path.exists(filepath):
        return None
    data = await asyncio.to_thread(_zoom_image_sync, filepath, difficulty)
    if data is None:
        return None
    return discord.File(io.BytesIO(data), filename="hero_clue.png")


def get_random_hero_image(hero: str) -> Optional[str]:
    """Return a random local image path for a hero, or None."""
    images = db.get("hero_images", {}).get(hero, [])
    if isinstance(images, str): images = [images] if images else []
    valid = [p for p in images if os.path.exists(p)]
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
#  GAME 1 — GUESS BY PICTURE  (with difficulty + zoom)
# ══════════════════════════════════════════════════════════════════════

class DifficultySelectView(View):
    """Host picks difficulty before the game starts."""
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=120)
        self.channel_id, self.host_id = channel_id, host_id

    async def _start(self, interaction: discord.Interaction, difficulty: str):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("❌ Only the host can pick difficulty.", ephemeral=True); return
        images   = db.get("hero_images", {})
        hero_cnt = sum(1 for h in images if images[h])
        active_picture[self.channel_id] = {
            "host_id":    self.host_id,
            "difficulty": difficulty,
            "hero":       None,
            "used":       [],
            "scores":     {},
            "revealed":   True,
        }
        label = DIFFICULTY_LABELS.get(difficulty, difficulty)
        e = discord.Embed(
            title=f"🖼️ Guess by Picture — {label}",
            description=(f"*Hosted by **{interaction.user.display_name}***\n\n"
                         "A cropped hero image will appear.\n"
                         "**Type the hero's name in this channel** to win a point!\n\n"
                         f"🎮 **{hero_cnt}** heroes in the pool · Difficulty: **{label}**"),
            color=EMPIRE_GOLD)
        brand(e)
        await interaction.response.edit_message(embed=e, view=None)
        await asyncio.sleep(2)
        await _picture_round(interaction.channel, self.channel_id)

    @discord.ui.button(label="Easy",   style=discord.ButtonStyle.success,   emoji="🟢", row=0)
    async def easy(self, i, _):   await self._start(i, "easy")

    @discord.ui.button(label="Medium", style=discord.ButtonStyle.primary,   emoji="🟡", row=0)
    async def medium(self, i, _): await self._start(i, "medium")

    @discord.ui.button(label="Hard",   style=discord.ButtonStyle.danger,    emoji="🔴", row=0)
    async def hard(self, i, _):   await self._start(i, "hard")

    @discord.ui.button(label="Random", style=discord.ButtonStyle.secondary, emoji="🎲", row=0)
    async def random_diff(self, i, _): await self._start(i, "random")


class PictureRoundView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=None)
        self.channel_id, self.host_id = channel_id, host_id

    @discord.ui.button(label="Reveal & Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, interaction: discord.Interaction, _: Button):
        game = active_picture.get(self.channel_id)
        if not game or game.get("revealed"):
            await interaction.response.send_message("No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        info = HOK_HEROES.get(hero, {})
        await interaction.response.send_message(embed=discord.Embed(
            title="⏭️ Skipped!",
            description=f"The hero was **{hero}**\n{info.get('class','?')} · {info.get('lane','?')}",
            color=EMPIRE_PURPLE))
        await _picture_next(interaction.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("❌ Only the host can end the game.", ephemeral=True); return
        game = active_picture.get(self.channel_id)
        if game: game["revealed"] = True
        await _picture_end(interaction.channel, self.channel_id)
        await interaction.response.send_message("🛑 Game ended.", ephemeral=True)


async def _picture_round(channel: discord.TextChannel, channel_id: int):
    game = active_picture.get(channel_id)
    if not game: return

    images = db.get("hero_images", {})
    used   = game.get("used", [])
    pool   = [h for h in images if images[h] and h not in used]

    if not pool:
        msg = ("Every hero with images has been shown. Game over!" if used
               else "No hero images found.\nUse `/set_hero_image` to add images.")
        await channel.send(embed=discord.Embed(
            title="✅ All Heroes Done!" if used else "⚠️ No Images",
            description=msg, color=EMPIRE_GOLD if used else EMPIRE_RED))
        await _picture_end(channel, channel_id); return

    hero       = random.choice(pool)
    filepath   = get_random_hero_image(hero)
    if not filepath:
        # image path missing — skip this hero
        game["used"].append(hero)
        await _picture_round(channel, channel_id); return

    difficulty = game["difficulty"]
    if difficulty == "random":
        actual_diff = random.choice(["easy","medium","hard"])
    else:
        actual_diff = difficulty

    file = await zoom_hero_image(filepath, actual_diff)

    game.update({"hero": hero, "revealed": False})
    game["used"].append(hero)

    info      = HOK_HEROES.get(hero, {})
    round_num = len(game["used"])
    diff_label = DIFFICULTY_LABELS.get(actual_diff, actual_diff)
    total     = len(pool) + len(used)

    e = discord.Embed(
        title=f"🖼️ Guess by Picture — Round {round_num}/{total}",
        description=(
            f"*Which Honor of Kings hero is this?*\n\n"
            "**Type the hero's name in this channel.**\n"
            f"First correct answer wins a point!\n\n"
            f"Difficulty: **{diff_label}**  |  {info.get('class','?')} · {info.get('lane','?')}"
        ), color=EMPIRE_GOLD)

    if file:
        e.set_image(url="attachment://hero_clue.png")
        e.set_footer(text="⚜ Oblivion Empire | Guess by Picture")
        await channel.send(embed=e, file=file, view=PictureRoundView(channel_id, game["host_id"]))
    else:
        # Pillow failed — send unmodified embed note
        e.description += "\n\n*(Image processing failed — hero skipped)*"
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
    scores = game.get("scores", {})
    e = discord.Embed(
        title="🏁 Guess by Picture — Game Over!",
        description=f"*{len(game.get('used',[]))} heroes shown.*",
        color=EMPIRE_GOLD)
    _add_score_field(e, scores, channel.guild)
    _persist_scores(scores)
    brand(e)
    await channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════
#  GAME 2 — GUESS BY QUOTE
# ══════════════════════════════════════════════════════════════════════

class QuoteRoundView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=None)
        self.channel_id, self.host_id = channel_id, host_id

    @discord.ui.button(label="Reveal & Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, interaction: discord.Interaction, _: Button):
        game = active_quote.get(self.channel_id)
        if not game or game.get("revealed"):
            await interaction.response.send_message("No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        info = HOK_HEROES.get(hero, {})
        await interaction.response.send_message(embed=discord.Embed(
            title="⏭️ Skipped!",
            description=f"That was **{hero}**\n{info.get('class','?')} · {info.get('lane','?')}",
            color=EMPIRE_PURPLE))
        await _quote_next(interaction.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message("❌ Only the host can end the game.", ephemeral=True); return
        game = active_quote.get(self.channel_id)
        if game: game["revealed"] = True
        await _quote_end(interaction.channel, self.channel_id)
        await interaction.response.send_message("🛑 Game ended.", ephemeral=True)


async def _quote_round(channel, channel_id):
    game = active_quote.get(channel_id)
    if not game: return
    used = game.get("used", [])
    pool = [h for h in HOK_QUOTES if h not in used]
    if not pool:
        await channel.send(embed=discord.Embed(
            title="✅ All Quotes Used!",
            description="Every hero has spoken. Game over!", color=EMPIRE_GOLD))
        await _quote_end(channel, channel_id); return
    hero  = random.choice(pool)
    quote = HOK_QUOTES[hero]
    info  = HOK_HEROES.get(hero, {})
    game.update({"hero": hero, "revealed": False})
    game["used"].append(hero)
    round_num = len(game["used"]); total = len(HOK_QUOTES)
    e = discord.Embed(
        title=f"💬 Guess by Quote — Round {round_num}/{total}",
        description=(f"*Which Honor of Kings hero said this?*\n\n"
                     f"**❝ {quote} ❞**\n\n"
                     "Type the hero's name in this channel.\n"
                     "First correct answer wins a point!"),
        color=EMPIRE_CYAN)
    e.set_footer(text=f"⚜ Oblivion Empire | {info.get('class','?')} · {info.get('lane','?')}")
    await channel.send(embed=e, view=QuoteRoundView(channel_id, game["host_id"]))


async def _quote_next(channel, channel_id):
    if not active_quote.get(channel_id): return
    await asyncio.sleep(3)
    await _quote_round(channel, channel_id)


async def _quote_end(channel, channel_id):
    game = active_quote.pop(channel_id, None)
    if not game: return
    scores = game.get("scores", {})
    e = discord.Embed(title="🏁 Guess by Quote — Game Over!",
                      description=f"*{len(game.get('used',[]))} quotes shown.*",
                      color=EMPIRE_GOLD)
    _add_score_field(e, scores, channel.guild)
    _persist_scores(scores)
    brand(e); await channel.send(embed=e)

# ─── Shared score helpers ─────────────────────────────────────────────

def _add_score_field(embed, scores, guild):
    if not scores:
        embed.add_field(name="📊 Scores", value="No points scored.", inline=False); return
    medals = ["🥇","🥈","🥉"]; lines = []
    for i, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x:-x[1])[:10], 1):
        mem   = guild.get_member(int(uid))
        name  = mem.display_name if mem else f"ID:{uid}"
        medal = medals[i-1] if i <= 3 else f"`{i}.`"
        lines.append(f"{medal} **{name}** — {pts} pt{'s' if pts!=1 else ''}")
    embed.add_field(name="📊 Final Scores", value="\n".join(lines), inline=False)


def _persist_scores(scores):
    for uid, pts in scores.items():
        db["game_scores"][uid] = db["game_scores"].get(uid, 0) + pts
    save_db(db)

# ══════════════════════════════════════════════════════════════════════
#  GAME 3 — MAFIA  (host-controlled, no timers)
#
#  Flow:
#    Lobby → Start → Day Discussion (no timer)
#       → host clicks "Open Voting" → Voting (no timer)
#       → host clicks "Tally Votes" → elimination announced
#       → Night (no timer, DMs sent)
#       → host clicks "Dawn" → night resolved, next Day begins
#
#  If host is eliminated → first remaining player becomes new host.
# ══════════════════════════════════════════════════════════════════════

MAFIA_ROLES: dict[str, dict] = {
    "Mafia":     {"emoji": "🗡️", "team": "mafia",   "desc": "Eliminate a villager each night. Blend in during the day."},
    "Detective": {"emoji": "🔍", "team": "village", "desc": "Investigate one player per night — learn if they are Mafia."},
    "Doctor":    {"emoji": "💊", "team": "village", "desc": "Protect one player from elimination each night."},
    "Villager":  {"emoji": "🏡", "team": "village", "desc": "Vote out the Mafia during the day. Trust no one."},
}


def assign_roles(n: int) -> list[str]:
    roles: list[str] = ["Mafia"] * max(1, n // 3)
    if n >= 5: roles.append("Doctor")
    if n >= 7: roles.append("Detective")
    roles += ["Villager"] * (n - len(roles))
    random.shuffle(roles); return roles


class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel   = channel
        self.host      = host
        self.players:  list[discord.Member] = [host]
        self.roles:    dict[int, str]       = {}
        self.alive:    list[discord.Member] = []
        self.phase     = "lobby"
        self.day       = 0
        self.votes:    dict[int, int]       = {}
        self.night_actions: dict[str, Optional[int]] = {
            "Mafia": None, "Doctor": None, "Detective": None}
        self.lobby_msg: Optional[discord.Message] = None

    def get_role(self, m: discord.Member) -> str:
        return self.roles.get(m.id, "Villager")

    def is_mafia(self, m: discord.Member) -> bool:
        return MAFIA_ROLES[self.get_role(m)]["team"] == "mafia"

    def mafia_alive(self)   -> list[discord.Member]: return [m for m in self.alive if self.is_mafia(m)]
    def village_alive(self) -> list[discord.Member]: return [m for m in self.alive if not self.is_mafia(m)]

    def check_win(self) -> Optional[str]:
        if not self.mafia_alive(): return "village"
        if len(self.mafia_alive()) >= len(self.village_alive()): return "mafia"
        return None

    def transfer_host_if_needed(self):
        """If host is dead, give control to first living player."""
        if self.host not in self.alive and self.alive:
            self.host = self.alive[0]


def _lobby_embed(game: MafiaGame) -> discord.Embed:
    e = discord.Embed(
        title="🎭 Mafia — Lobby",
        description=(
            f"*Host: **{game.host.display_name}***\n"
            "Need at least **4 players** to start.\n\n"
            "🗡️ **Mafia** — 1 per 3 players · eliminate villagers at night\n"
            "🏡 **Villagers** — vote out Mafia during the day\n"
            "💊 **Doctor** — protect someone per night *(5+ players)*\n"
            "🔍 **Detective** — investigate someone per night *(7+ players)*"
        ), color=EMPIRE_PURPLE)
    e.add_field(name=f"👥 Players ({len(game.players)})",
                value="\n".join(f"• {m.display_name}" for m in game.players) or "—", inline=False)
    e.set_footer(text="⚜ Oblivion Empire | Mafia — click Join!")
    return e


class MafiaLobbyView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="Join",   style=discord.ButtonStyle.success, emoji="✋")
    async def join_btn(self, interaction: discord.Interaction, _: Button):
        if self.game.phase != "lobby":
            await interaction.response.send_message("❌ Already started.", ephemeral=True); return
        if interaction.user in self.game.players:
            await interaction.response.send_message("❌ Already joined.", ephemeral=True); return
        self.game.players.append(interaction.user)
        await interaction.response.send_message(f"✅ **{interaction.user.display_name}** joined!")
        if self.game.lobby_msg:
            try: await self.game.lobby_msg.edit(embed=_lobby_embed(self.game), view=self)
            except Exception: pass

    @discord.ui.button(label="Start",  style=discord.ButtonStyle.primary,  emoji="▶️")
    async def start_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message("❌ Only the host can start.", ephemeral=True); return
        if len(self.game.players) < 4:
            await interaction.response.send_message("❌ Need at least 4 players.", ephemeral=True); return
        await interaction.response.defer()
        await _mafia_start(self.game)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger,   emoji="❌")
    async def cancel_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message("❌ Only the host can cancel.", ephemeral=True); return
        active_mafia.pop(self.game.channel.id, None)
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Mafia Game Cancelled", color=EMPIRE_RED))
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
        e = discord.Embed(title=f"🃏 Your Role — {role_info['emoji']} {role}",
                          description=role_info["desc"],
                          color=EMPIRE_RED if role == "Mafia" else EMPIRE_CYAN)
        e.add_field(name="Team", value=role_info["team"].capitalize(), inline=True)
        if role == "Mafia":
            team = ", ".join(m.display_name for m in game.players if game.is_mafia(m))
            e.add_field(name="🗡️ Your team", value=team, inline=False)
        e.set_footer(text="⚜ Oblivion Empire | Keep your role secret!")
        try:    await member.send(embed=e)
        except: dm_fails.append(member.display_name)

    names = "\n".join(f"• {m.display_name}" for m in game.players)
    e = discord.Embed(title="🎭 The Game Begins!",
                      description=(f"*{len(game.players)} players enter the darkness…*\n\n{names}\n\n"
                                   "✉️ Check your **DMs** for your secret role!"
                                   + (f"\n⚠️ DMs failed for: {', '.join(dm_fails)}" if dm_fails else "")),
                      color=EMPIRE_PURPLE)
    brand(e)
    await game.channel.send(embed=e)
    await asyncio.sleep(3)
    await _mafia_day(game)


# ── Day phase ─────────────────────────────────────────────────────────

class DayDiscussionView(View):
    """Host presses 'Open Voting' when discussion is over."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="📊 Open Voting", style=discord.ButtonStyle.primary, emoji="🗳️")
    async def open_voting(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message(
                "❌ Only **the host** can open voting.", ephemeral=True); return
        self.stop()
        names  = " · ".join(m.display_name for m in self.game.alive)
        e = discord.Embed(
            title=f"🗳️ Day {self.game.day} — Voting Open",
            description=(f"*{len(self.game.alive)} players alive.*\n\n"
                         f"**Alive:** {names}\n\n"
                         "Use the dropdown to vote who to eliminate.\n"
                         "When everyone has voted, the host tallies the results."),
            color=EMPIRE_GOLD)
        brand(e)
        view = DayVotingView(self.game)
        await interaction.response.send_message(embed=e, view=view)
        self.game._voting_view = view


class DayVotingView(View):
    """Voting dropdown + host's Tally button."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game
        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in game.alive]
        sel = Select(placeholder="🗳️ Vote to eliminate...", options=opts)
        sel.callback = self._on_vote; self.add_item(sel)

    async def _on_vote(self, interaction: discord.Interaction):
        if interaction.user not in self.game.alive:
            await interaction.response.send_message("❌ You are eliminated.", ephemeral=True); return
        tid = int(interaction.data["values"][0])
        if tid == interaction.user.id:
            await interaction.response.send_message("❌ Can't vote yourself.", ephemeral=True); return
        self.game.votes[interaction.user.id] = tid
        target = interaction.guild.get_member(tid)
        vote_count = len(self.game.votes)
        alive_count = len(self.game.alive)
        await interaction.response.send_message(
            f"🗳️ Vote cast for **{target.display_name if target else '?'}**.\n"
            f"*{vote_count}/{alive_count} players have voted.*", ephemeral=True)

    @discord.ui.button(label="⚖️ Tally Votes", style=discord.ButtonStyle.danger, emoji="⚖️", row=1)
    async def tally_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message(
                "❌ Only **the host** can tally votes.", ephemeral=True); return
        self.stop()
        await interaction.response.defer()
        await _mafia_resolve_votes(self.game)


async def _mafia_day(game: MafiaGame):
    game.phase = "day"
    game.day  += 1
    game.votes = {}
    game.transfer_host_if_needed()

    if w := game.check_win():
        await _mafia_end(game, w); return

    names = " · ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"☀️ Day {game.day} — Discussion",
        description=(f"*{len(game.alive)} players remain.*\n\n"
                     f"**Alive:** {names}\n\n"
                     "Discuss freely. When ready, **the host** opens voting."),
        color=EMPIRE_GOLD)
    e.set_footer(text=f"⚜ Oblivion Empire | Host: {game.host.display_name}")
    brand(e)
    await game.channel.send(embed=e, view=DayDiscussionView(game))


async def _mafia_resolve_votes(game: MafiaGame):
    if not game.votes:
        await game.channel.send(embed=discord.Embed(
            title="🗳️ No Votes Cast",
            description="Nobody voted. Moving to night…", color=EMPIRE_PURPLE))
    else:
        tally: dict[int, int] = {}
        for tid in game.votes.values(): tally[tid] = tally.get(tid, 0) + 1
        max_votes = max(tally.values())
        leaders   = [tid for tid, v in tally.items() if v == max_votes]

        if len(leaders) > 1:
            # Tie — no elimination
            names_tied = ", ".join(
                g.display_name if (g := game.channel.guild.get_member(tid)) else "?" for tid in leaders)
            await game.channel.send(embed=discord.Embed(
                title="⚖️ It's a Tie!",
                description=f"**{names_tied}** each received **{max_votes}** votes.\nNo one is eliminated.",
                color=EMPIRE_PURPLE))
        else:
            elim_id = leaders[0]
            elim    = game.channel.guild.get_member(elim_id)
            if elim and elim in game.alive:
                game.alive.remove(elim)
                ri = MAFIA_ROLES[game.get_role(elim)]
                await game.channel.send(embed=discord.Embed(
                    title="⚖️ Eliminated!",
                    description=(f"**{elim.display_name}** was voted out.\n"
                                 f"They were: {ri['emoji']} **{game.get_role(elim)}**"),
                    color=EMPIRE_RED))

    if w := game.check_win():
        await _mafia_end(game, w); return

    await asyncio.sleep(2)
    await _mafia_night(game)


# ── Night phase ───────────────────────────────────────────────────────

class NightActionView(View):
    def __init__(self, game: MafiaGame, actor_role: str, user_id: int):
        super().__init__(timeout=None)
        self.game, self.actor_role, self.user_id = game, actor_role, user_id
        targets = game.alive if actor_role == "Doctor" else game.village_alive()
        opts    = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                   for m in targets if m.id != user_id]
        if not opts: return
        labels  = {"Mafia": "🗡️ Eliminate…", "Doctor": "💊 Protect…", "Detective": "🔍 Investigate…"}
        sel     = Select(placeholder=labels.get(actor_role, "Select…"), options=opts)
        sel.callback = self._on_select; self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not yours.", ephemeral=True); return
        tid = int(interaction.data["values"][0])
        self.game.night_actions[self.actor_role] = tid
        target = interaction.guild.get_member(tid)
        msgs = {
            "Mafia":     f"🗡️ Target locked: **{target.display_name if target else '?'}**",
            "Doctor":    f"💊 Protecting **{target.display_name if target else '?'}** tonight.",
            "Detective": f"🔍 Investigating **{target.display_name if target else '?'}**…",
        }
        await interaction.response.send_message(msgs.get(self.actor_role, "✅ Done."), ephemeral=True)
        self.stop()


class NightHostView(View):
    """Host presses 'Dawn' to end the night and resolve actions."""
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="🌅 Dawn — End Night", style=discord.ButtonStyle.success, emoji="☀️")
    async def dawn_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message(
                "❌ Only **the host** can end the night.", ephemeral=True); return
        self.stop()
        await interaction.response.defer()
        await _mafia_resolve_night(self.game)


async def _mafia_night(game: MafiaGame):
    game.phase        = "night"
    game.night_actions = {"Mafia": None, "Doctor": None, "Detective": None}
    game.transfer_host_if_needed()

    e = discord.Embed(
        title=f"🌙 Night {game.day} — Darkness Falls",
        description=("Special roles — check your **DMs** for your action menu.\n\n"
                     "When everyone is done, **the host** clicks Dawn to continue."),
        color=0x1a1a2e)
    e.set_footer(text=f"⚜ Oblivion Empire | Host: {game.host.display_name}")
    brand(e)
    await game.channel.send(embed=e, view=NightHostView(game))

    # Send DMs to special roles
    for member in game.alive:
        role = game.get_role(member)
        if role not in ("Mafia", "Doctor", "Detective"): continue
        ae = discord.Embed(
            title=f"🌙 Night Action — {MAFIA_ROLES[role]['emoji']} {role}",
            description="Use the dropdown below to take your action.",
            color=EMPIRE_PURPLE)
        ae.set_footer(text="⚜ Oblivion Empire | Mafia Night Phase")
        try:    await member.send(embed=ae, view=NightActionView(game, role, member.id))
        except: pass


async def _mafia_resolve_night(game: MafiaGame):
    elim_id   = game.night_actions.get("Mafia")
    prot_id   = game.night_actions.get("Doctor")
    invest_id = game.night_actions.get("Detective")

    # Detective DM
    if invest_id:
        target = game.channel.guild.get_member(invest_id)
        det    = next((m for m in game.alive if game.get_role(m) == "Detective"), None)
        if target and det:
            is_maf = game.get_role(target) == "Mafia"
            try:
                await det.send(embed=discord.Embed(
                    title="🔍 Investigation Result",
                    description=f"**{target.display_name}** is {'🗡️ **Mafia**' if is_maf else '🏡 **Village**'}!",
                    color=EMPIRE_RED if is_maf else EMPIRE_GREEN))
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

    e = discord.Embed(title=f"🌅 Dawn — Day {game.day + 1}",
                      description="\n".join(dawn), color=EMPIRE_GOLD)
    brand(e)
    await game.channel.send(embed=e)

    if w := game.check_win():
        await _mafia_end(game, w); return
    await asyncio.sleep(2)
    await _mafia_day(game)


async def _mafia_end(game: MafiaGame, winner: str):
    game.phase = "ended"
    active_mafia.pop(game.channel.id, None)
    if winner == "village":
        title, desc, color = "🏡 Village Wins!", "The Mafia is eliminated. Oblivion Empire is safe!", EMPIRE_GREEN
    else:
        title, desc, color = "🗡️ Mafia Wins!", "The Mafia controls Oblivion Empire. Darkness reigns…", EMPIRE_RED
    reveal = "\n".join(
        f"{MAFIA_ROLES[game.get_role(m)]['emoji']} **{m.display_name}** — {game.get_role(m)}"
        for m in game.players)
    e = discord.Embed(title=title, description=desc, color=color)
    e.add_field(name="🃏 Full Role Reveal", value=reveal, inline=False)
    brand(e)
    await game.channel.send(embed=e)
    await log_action(game.channel.guild, "🎭 Mafia Ended",
        f"#{game.channel.name} — {winner} won · {len(game.players)} players")

# ══════════════════════════════════════════════════════════════════════
#  GAMES PANEL
# ══════════════════════════════════════════════════════════════════════

class GamesPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Guess by Picture", emoji="🖼️",
                       style=discord.ButtonStyle.primary, row=0)
    async def picture_btn(self, interaction: discord.Interaction, _: Button):
        cid  = interaction.channel_id
        busy = channel_busy(cid)
        if busy:
            await interaction.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        images = db.get("hero_images", {})
        if not any(v for v in images.values()):
            await interaction.response.send_message(embed=discord.Embed(
                title="⚠️ No Hero Images Yet",
                description=("Use `/set_hero_image` to add images:\n\n"
                             "1. Type `/set_hero_image` in Discord\n"
                             "2. Pick the hero from the autocomplete list\n"
                             "3. Attach the image file (.png/.jpg/.webp)\n"
                             "4. Done!\n\nUse `/hero_images` to see progress."),
                color=EMPIRE_RED), ephemeral=True); return
        hero_cnt = sum(1 for h in images if images[h])
        e = discord.Embed(
            title="🖼️ Guess by Picture — Choose Difficulty",
            description=(f"*Host: **{interaction.user.display_name}***\n\n"
                         f"**{hero_cnt}** heroes ready.\n\n"
                         "Pick the difficulty level — it controls how much of the image is shown:\n"
                         "🟢 **Easy** — 55–75% visible\n"
                         "🟡 **Medium** — 25–55% visible\n"
                         "🔴 **Hard** — 6–25% visible (very hard!)\n"
                         "🎲 **Random** — different every round"),
            color=EMPIRE_GOLD)
        brand(e)
        await interaction.response.send_message(
            embed=e, view=DifficultySelectView(cid, interaction.user.id))
        await log_action(interaction.guild, "🖼️ Picture Game",
            f"{interaction.user.mention} starting Guess by Picture in #{interaction.channel.name}")

    @discord.ui.button(label="Guess by Quote", emoji="💬",
                       style=discord.ButtonStyle.success, row=0)
    async def quote_btn(self, interaction: discord.Interaction, _: Button):
        cid  = interaction.channel_id
        busy = channel_busy(cid)
        if busy:
            await interaction.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        active_quote[cid] = {"host_id": interaction.user.id,
                             "hero": None, "used": [], "scores": {}, "revealed": True}
        e = discord.Embed(
            title="💬 Guess by Quote — Starting!",
            description=(f"*Hosted by **{interaction.user.display_name}***\n\n"
                         "A hero quote will appear. **Type who said it** to win a point!\n\n"
                         f"💬 **{len(HOK_QUOTES)}** heroes in the pool."),
            color=EMPIRE_CYAN)
        brand(e)
        await interaction.response.send_message(embed=e)
        await asyncio.sleep(2)
        await _quote_round(interaction.channel, cid)
        await log_action(interaction.guild, "💬 Quote Game",
            f"{interaction.user.mention} started in #{interaction.channel.name}")

    @discord.ui.button(label="Mafia", emoji="🎭",
                       style=discord.ButtonStyle.danger, row=0)
    async def mafia_btn(self, interaction: discord.Interaction, _: Button):
        cid  = interaction.channel_id
        busy = channel_busy(cid)
        if busy:
            await interaction.response.send_message(f"❌ **{busy}** is already running here!", ephemeral=True); return
        game = MafiaGame(interaction.channel, interaction.user)
        active_mafia[cid] = game
        view = MafiaLobbyView(game)
        await interaction.response.send_message(embed=_lobby_embed(game), view=view)
        game.lobby_msg = await interaction.original_response()
        await log_action(interaction.guild, "🎭 Mafia Lobby",
            f"{interaction.user.mention} opened in #{interaction.channel.name}")

    @discord.ui.button(label="All-Time Scores", emoji="🏅",
                       style=discord.ButtonStyle.secondary, row=1)
    async def scores_btn(self, interaction: discord.Interaction, _: Button):
        scores = db.get("game_scores", {})
        if not scores:
            await interaction.response.send_message(
                embed=discord.Embed(title="🏅 No Scores Yet",
                                    description="Play some games first!", color=EMPIRE_PURPLE), ephemeral=True); return
        medals = ["🥇","🥈","🥉"]; lines = []
        for i, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x:-x[1])[:15], 1):
            mem   = interaction.guild.get_member(int(uid))
            name  = mem.display_name if mem else f"ID:{uid}"
            medal = medals[i-1] if i <= 3 else f"`{i}.`"
            lines.append(f"{medal} **{name}** — {pts} pt{'s' if pts!=1 else ''}")
        e = discord.Embed(title="🏅 All-Time Scores", description="\n".join(lines), color=EMPIRE_GOLD)
        brand(e)
        await interaction.response.send_message(embed=e, ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════

class GamesCog(commands.Cog):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        # Populate hero name list for /set_hero_image autocomplete
        _all_hero_names.clear()
        _all_hero_names.extend(sorted(HOK_HEROES.keys()))

    @app_commands.command(name="games", description="🎮 Open the Oblivion Empire games panel")
    async def cmd_games(self, interaction: discord.Interaction):
        images   = db.get("hero_images", {})
        img_cnt  = sum(1 for h in images if images[h])
        e = discord.Embed(title="🎮 Oblivion Empire — Games",
                          description="*Welcome to the arena, warrior.*", color=EMPIRE_PURPLE)
        e.add_field(name="🖼️ Guess by Picture",
                    value=(f"A cropped hero image appears — type the name to win.\n"
                           f"*{img_cnt} hero{'es' if img_cnt!=1 else ''} ready · 3 difficulty levels*\n"
                           f"*(Admins: `/set_hero_image` to add images)*"), inline=False)
        e.add_field(name="💬 Guess by Quote",
                    value=(f"A hero quote appears — type who said it to win.\n"
                           f"*{len(HOK_QUOTES)} heroes · no setup needed*"), inline=False)
        e.add_field(name="🎭 Mafia",
                    value="Social deduction — Villagers vs Mafia.\n4+ players · host-controlled · no timers.", inline=False)
        e.add_field(name="🏅 All-Time Scores", value="Combined leaderboard.", inline=False)
        av = bot_avatar()
        if av: e.set_thumbnail(url=av)
        e.set_footer(text="⚜ Oblivion Empire | Games Panel")
        await interaction.response.send_message(embed=e, view=GamesPanelView())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        cid = message.channel.id

        # Picture game
        pg = active_picture.get(cid)
        if pg and not pg.get("revealed") and pg.get("hero"):
            if check_guess(message.content, pg["hero"]):
                pg["revealed"] = True
                uid = str(message.author.id)
                pg["scores"][uid] = pg["scores"].get(uid, 0) + 1
                pts  = pg["scores"][uid]
                info = HOK_HEROES.get(pg["hero"], {})
                e = discord.Embed(
                    title="✅ Correct!",
                    description=(f"🎉 **{message.author.display_name}** got it!\n\n"
                                 f"The hero was **{pg['hero']}**\n"
                                 f"{info.get('class','?')} · {info.get('lane','?')}\n\n"
                                 f"They now have **{pts}** point{'s' if pts!=1 else ''} this game."),
                    color=EMPIRE_GREEN)
                e.set_footer(text="⚜ Oblivion Empire | Next hero coming up…")
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _picture_next(message.channel, cid)
            return

        # Quote game
        qg = active_quote.get(cid)
        if qg and not qg.get("revealed") and qg.get("hero"):
            if check_guess(message.content, qg["hero"]):
                qg["revealed"] = True
                uid = str(message.author.id)
                qg["scores"][uid] = qg["scores"].get(uid, 0) + 1
                pts  = qg["scores"][uid]
                info = HOK_HEROES.get(qg["hero"], {})
                e = discord.Embed(
                    title="✅ Correct!",
                    description=(f"🎉 **{message.author.display_name}** got it!\n\n"
                                 f"That was **{qg['hero']}**\n"
                                 f"{info.get('class','?')} · {info.get('lane','?')}\n\n"
                                 f"They now have **{pts}** point{'s' if pts!=1 else ''} this game."),
                    color=EMPIRE_GREEN)
                e.set_footer(text="⚜ Oblivion Empire | Next quote coming up…")
                await message.channel.send(embed=e)
                await asyncio.sleep(3)
                await _quote_next(message.channel, cid)


async def setup(bot_instance: commands.Bot):
    bot_instance.tree.remove_command("games")
    await bot_instance.add_cog(GamesCog(bot_instance))
