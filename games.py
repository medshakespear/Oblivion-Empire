# ══════════════════════════════════════════════════════════════════════
#  games.py  —  Oblivion Empire Games Cog
# ══════════════════════════════════════════════════════════════════════
#
#  HOW GUESS THE HERO WORKS — READ THIS:
#
#  The bot does NOT do image recognition or AI detection.
#  It works like a pub quiz:
#    1. Bot picks a hero from its own list  (it already knows the answer)
#    2. Bot posts the hero's image          (you supply the image URLs below)
#    3. Players type the hero name in chat
#    4. Bot checks if the text matches the  hero name it already knows
#    5. First correct answer gets the point
#
#  To add images:
#    Find the hero in HOK_HEROES below and paste its image URL.
#    Heroes with an empty "image" field are skipped until you add one.
#    The image should be a cropped / zoomed screenshot to make it harder.
#
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio, random, unicodedata, re
from typing import Optional

from bot import db, save_db, brand, log_action, bot_avatar

EMPIRE_GOLD   = 0xc9a227
EMPIRE_RED    = 0x8b1a1a
EMPIRE_PURPLE = 0x5c0099
EMPIRE_GREEN  = 0x2ecc71
EMPIRE_CYAN   = 0x00b4d8

# ══════════════════════════════════════════════════════════════════════
#  COMPLETE HONOR OF KINGS HERO ROSTER
#  Add image URLs to the "image" field.  Empty = hero is skipped.
# ══════════════════════════════════════════════════════════════════════

HOK_HEROES: dict[str, dict] = {
    # ── Tanks ────────────────────────────────────────────────────────
    "Lian Po":          {"image": "", "class": "Tank",      "lane": "Baron Lane"},
    "Zhang Fei":        {"image": "", "class": "Tank",      "lane": "Roam"},
    "Sun Ce":           {"image": "", "class": "Tank",      "lane": "Roam"},
    "Dun":              {"image": "", "class": "Tank",      "lane": "Baron Lane"},
    "Pei":              {"image": "", "class": "Tank",      "lane": "Roam"},
    "Ultimecia":        {"image": "", "class": "Tank",      "lane": "Roam"},
    # ── Fighters ─────────────────────────────────────────────────────
    "Arthur":           {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Guan Yu":          {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Liu Bei":          {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Mulan":            {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Xiang Yu":         {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Loong":            {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Wukong":           {"image": "", "class": "Fighter",   "lane": "Jungle"},
    "Lam":              {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Zilong":           {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Zhao Yun":         {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    "Bai Qi":           {"image": "", "class": "Fighter",   "lane": "Baron Lane"},
    # ── Assassins ────────────────────────────────────────────────────
    "Li Bai":           {"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Cao Cao":          {"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Gan Jiang & Mo Ye":{"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Milady":           {"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Consort Yu":       {"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Han Xin":          {"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Jing":             {"image": "", "class": "Assassin",  "lane": "Jungle"},
    "Gongsun Li":       {"image": "", "class": "Assassin",  "lane": "Dragon Lane"},
    # ── Mages ────────────────────────────────────────────────────────
    "Diaochan":         {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Ying Zheng":       {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Zhong Kui":        {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Gao Jianli":       {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Zhuge Liang":      {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Luo Yi":           {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Nu Wa":            {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Su":               {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Xun":              {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Ming":             {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Voidcaller":       {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    "Di Renjie":        {"image": "", "class": "Mage",      "lane": "Mid Lane"},
    # ── Marksmen ─────────────────────────────────────────────────────
    "Sun Shangxiang":   {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Hou Yi":           {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Marco Polo":       {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Luban No. 7":      {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Huang Zhong":      {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Mozi":             {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Nakoruru":         {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    "Kai":              {"image": "", "class": "Marksman",  "lane": "Dragon Lane"},
    # ── Supports ─────────────────────────────────────────────────────
    "Lady Sun":         {"image": "", "class": "Support",   "lane": "Roam"},
    "Mengmeng":         {"image": "", "class": "Support",   "lane": "Roam"},
    "Luna":             {"image": "", "class": "Support",   "lane": "Roam"},
    "Zhuangzi":         {"image": "", "class": "Support",   "lane": "Roam"},
    "Fuzi":             {"image": "", "class": "Support",   "lane": "Roam"},
    "Da Qiao":          {"image": "", "class": "Support",   "lane": "Roam"},
    "Bian Que":         {"image": "", "class": "Support",   "lane": "Roam"},
    "Cai Wenji":        {"image": "", "class": "Support",   "lane": "Roam"},
    "Yaria":            {"image": "", "class": "Support",   "lane": "Roam"},
}

# ── Hero name aliases ─────────────────────────────────────────────────
# Players can type any alias and the bot accepts it as correct.
HERO_ALIASES: dict[str, str] = {
    # Gan Jiang & Mo Ye shortcuts
    "gan jiang and mo ye": "Gan Jiang & Mo Ye",
    "gan mo":              "Gan Jiang & Mo Ye",
    "gm7":                 "Gan Jiang & Mo Ye",
    "gmye":                "Gan Jiang & Mo Ye",
    # Luban No.7 shortcuts
    "luban":               "Luban No. 7",
    "luban7":              "Luban No. 7",
    "luban no7":           "Luban No. 7",
    "lu ban":              "Luban No. 7",
    # Common abbreviations
    "ying":                "Ying Zheng",
    "marco":               "Marco Polo",
    "consort":             "Consort Yu",
    "sun ss":              "Sun Shangxiang",
    "sss":                 "Sun Shangxiang",
    "sun shang":           "Sun Shangxiang",
    "zhuge":               "Zhuge Liang",
    "da qiao":             "Da Qiao",
    "daqiao":              "Da Qiao",
    "cai":                 "Cai Wenji",
    "bian":                "Bian Que",
    "bian que":            "Bian Que",
    "void":                "Voidcaller",
    "voidc":               "Voidcaller",
    "di ren":              "Di Renjie",
    "huang":               "Huang Zhong",
    "gongsun":             "Gongsun Li",
    "han":                 "Han Xin",
    "gao":                 "Gao Jianli",
    "luo":                 "Luo Yi",
    "zhao":                "Zhao Yun",
    "xiang":               "Xiang Yu",
    "sun ce":              "Sun Ce",
    "zhang fei":           "Zhang Fei",
    "lian":                "Lian Po",
    "nuwu":                "Nu Wa",
    "nuwa":                "Nu Wa",
    "wukong":              "Wukong",
    "sun wukong":          "Wukong",
    "monkey":              "Wukong",
    "monkey king":         "Wukong",
    "milady":              "Milady",
    "lady":                "Lady Sun",
    "mengmeng":            "Mengmeng",
}


def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse spaces — for comparison only."""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    # Remove punctuation except spaces and alphanumerics
    text = re.sub(r"[^a-z0-9& ]", "", text)
    return text.strip()


def check_guess(answer: str, correct_hero: str) -> bool:
    """
    Returns True if the player's answer matches the correct hero name.
    Handles: aliases, case, accents, extra spaces, & vs and.
    """
    a = _normalise(answer)
    # Check alias table
    canonical = HERO_ALIASES.get(a)
    if canonical:
        return canonical == correct_hero

    # Check direct normalised match
    correct_norm = _normalise(correct_hero)
    if a == correct_norm:
        return True

    # Check all aliases that point to this hero
    for alias_key, alias_val in HERO_ALIASES.items():
        if alias_val == correct_hero and a == _normalise(alias_key):
            return True

    return False


def get_playable_heroes() -> dict[str, dict]:
    """Only heroes that have an image URL set."""
    return {k: v for k, v in HOK_HEROES.items() if v.get("image", "").strip()}

# ══════════════════════════════════════════════════════════════════════
#  ACTIVE GAME STATE
# ══════════════════════════════════════════════════════════════════════

active_guess: dict[int, dict] = {}   # channel_id → game state
active_mafia: dict[int, "MafiaGame"] = {}

# ══════════════════════════════════════════════════════════════════════
#  GUESS THE HERO
# ══════════════════════════════════════════════════════════════════════

class GuessHeroView(View):
    def __init__(self, channel_id: int, host_id: int):
        super().__init__(timeout=65)
        self.channel_id = channel_id
        self.host_id    = host_id

    @discord.ui.button(label="Reveal & Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, interaction: discord.Interaction, _: Button):
        game = active_guess.get(self.channel_id)
        if not game or game.get("revealed"):
            await interaction.response.send_message("❌ No active round.", ephemeral=True); return
        game["revealed"] = True
        hero = game["hero"]
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏭️ Skipped!",
                description=f"The hero was **{hero}**.",
                color=EMPIRE_PURPLE), ephemeral=False)
        await _next_round(interaction.channel, self.channel_id)

    @discord.ui.button(label="End Game", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user.id != self.host_id:
            await interaction.response.send_message(
                "❌ Only the host can end the game.", ephemeral=True); return
        game = active_guess.get(self.channel_id)
        if game: game["revealed"] = True
        await _end_guess_game(interaction.channel, self.channel_id)
        await interaction.response.send_message("🛑 Game ended.", ephemeral=True)


async def _post_round(channel: discord.TextChannel, channel_id: int):
    playable = get_playable_heroes()
    if not playable:
        await channel.send(embed=discord.Embed(
            title="⚠️ No Hero Images Added Yet",
            description=(
                "You need to add image URLs to `games.py` first.\n\n"
                "Open `games.py`, find the `HOK_HEROES` dictionary,\n"
                "and paste an image URL into the `\"image\"` field for each hero.\n\n"
                "Example:\n"
                "```\n\"Li Bai\": {\"image\": \"https://i.imgur.com/abc.png\", ...}\n```"
            ),
            color=EMPIRE_RED))
        active_guess.pop(channel_id, None)
        return

    game = active_guess.get(channel_id)
    if not game:
        return

    used = game.get("used", [])
    pool = [h for h in playable if h not in used]
    if not pool:
        await _end_guess_game(channel, channel_id)
        return

    hero      = random.choice(pool)
    hero_data = playable[hero]

    game["hero"]     = hero
    game["revealed"] = False
    game["used"].append(hero)

    round_num = len(game["used"])
    total     = len(playable)

    e = discord.Embed(
        title=f"🔎 Guess the Hero!  (Round {round_num}/{total})",
        description=(
            "*Which Honor of Kings hero is this?*\n\n"
            "**Type the hero's name in chat.**\n"
            "First correct answer earns a point!\n\n"
            "⏱ You have **60 seconds**."
        ),
        color=EMPIRE_GOLD,
    )
    e.set_image(url=hero_data["image"])
    e.set_footer(text="⚜ Oblivion Empire | Guess the Hero")
    await channel.send(embed=e, view=GuessHeroView(channel_id, game["host_id"]))

    # 60-second timeout
    await asyncio.sleep(60)
    game = active_guess.get(channel_id)
    if game and not game.get("revealed"):
        game["revealed"] = True
        await channel.send(embed=discord.Embed(
            title="⏰ Time's Up!",
            description=(f"Nobody guessed it!\n\n"
                         f"The hero was **{hero}** "
                         f"({hero_data['class']} • {hero_data['lane']})"),
            color=EMPIRE_RED))
        await _next_round(channel, channel_id)


async def _next_round(channel: discord.TextChannel, channel_id: int):
    game = active_guess.get(channel_id)
    if not game:
        return
    await asyncio.sleep(3)
    await _post_round(channel, channel_id)


async def _end_guess_game(channel: discord.TextChannel, channel_id: int):
    game = active_guess.pop(channel_id, None)
    if not game:
        return

    scores = game.get("scores", {})
    e = discord.Embed(
        title="🏁 Guess the Hero — Game Over!",
        description=f"*{len(game.get('used', []))} heroes were shown.*",
        color=EMPIRE_GOLD,
    )
    if scores:
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        medals = ["🥇", "🥈", "🥉"]
        lines  = []
        for i, (uid, pts) in enumerate(sorted_scores[:10], 1):
            mem   = channel.guild.get_member(int(uid))
            name  = mem.display_name if mem else f"ID:{uid}"
            medal = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(f"{medal} **{name}** — {pts} pt{'s' if pts != 1 else ''}")
        e.add_field(name="📊 Final Scores", value="\n".join(lines), inline=False)
        # Save to persistent db
        for uid, pts in scores.items():
            db["game_scores"][uid] = db["game_scores"].get(uid, 0) + pts
        save_db(db)
    else:
        e.add_field(name="📊 Scores", value="No points scored this round.", inline=False)
    brand(e)
    await channel.send(embed=e)

# ══════════════════════════════════════════════════════════════════════
#  MAFIA GAME
# ══════════════════════════════════════════════════════════════════════

MAFIA_ROLES = {
    "Mafia":     {"emoji": "🗡️", "team": "mafia",   "desc": "Eliminate villagers at night. Blend in during the day."},
    "Detective": {"emoji": "🔍", "team": "village", "desc": "Investigate one player each night to learn if they are Mafia."},
    "Doctor":    {"emoji": "💊", "team": "village", "desc": "Protect one player from elimination each night."},
    "Villager":  {"emoji": "🏡", "team": "village", "desc": "Vote out the Mafia during the day. Trust no one."},
}


def assign_roles(n: int) -> list[str]:
    roles = []
    mafia_count = max(1, n // 3)
    roles += ["Mafia"] * mafia_count
    if n >= 5:  roles.append("Doctor")
    if n >= 7:  roles.append("Detective")
    roles += ["Villager"] * (n - len(roles))
    random.shuffle(roles)
    return roles


class MafiaGame:
    def __init__(self, channel: discord.TextChannel, host: discord.Member):
        self.channel   = channel
        self.host      = host
        self.players:  list[discord.Member] = [host]
        self.roles:    dict[int, str]       = {}
        self.alive:    list[discord.Member] = []
        self.phase     = "lobby"
        self.day       = 0
        self.votes:    dict[int, int] = {}
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
        if not self.mafia_alive():  return "village"
        if len(self.mafia_alive()) >= len(self.village_alive()): return "mafia"
        return None


def _lobby_embed(game: MafiaGame) -> discord.Embed:
    e = discord.Embed(
        title="🎭 Mafia — Lobby",
        description=(
            f"*Host: **{game.host.display_name}***\n"
            "Minimum **4 players** to start.\n\n"
            "**Roles:**\n"
            "🗡️ **Mafia** — eliminate villagers at night\n"
            "🏡 **Villagers** — vote out Mafia during day\n"
            "💊 **Doctor** (5+ players) — save one player per night\n"
            "🔍 **Detective** (7+ players) — investigate one player per night"
        ),
        color=EMPIRE_PURPLE,
    )
    e.add_field(
        name=f"👥 Players ({len(game.players)})",
        value="\n".join(f"• {m.display_name}" for m in game.players) or "—",
        inline=False)
    e.set_footer(text="⚜ Oblivion Empire | Mafia Game")
    return e


class MafiaLobbyView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=300)
        self.game = game

    @discord.ui.button(label="Join",   style=discord.ButtonStyle.success, emoji="✋")
    async def join_btn(self, interaction: discord.Interaction, _: Button):
        if self.game.phase != "lobby":
            await interaction.response.send_message("❌ Game already started.", ephemeral=True); return
        if interaction.user in self.game.players:
            await interaction.response.send_message("❌ Already joined.", ephemeral=True); return
        self.game.players.append(interaction.user)
        await interaction.response.send_message(
            f"✅ **{interaction.user.display_name}** joined!", ephemeral=False)
        if self.game.lobby_msg:
            try:
                await self.game.lobby_msg.edit(embed=_lobby_embed(self.game), view=self)
            except Exception: pass

    @discord.ui.button(label="Start",  style=discord.ButtonStyle.primary, emoji="▶️")
    async def start_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message("❌ Only the host can start.", ephemeral=True); return
        if len(self.game.players) < 4:
            await interaction.response.send_message("❌ Need at least 4 players.", ephemeral=True); return
        await interaction.response.defer()
        await _start_mafia(self.game, interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger,  emoji="❌")
    async def cancel_btn(self, interaction: discord.Interaction, _: Button):
        if interaction.user != self.game.host:
            await interaction.response.send_message("❌ Only the host can cancel.", ephemeral=True); return
        active_mafia.pop(self.game.channel.id, None)
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Mafia Game Cancelled", color=EMPIRE_RED))
        self.stop()


async def _start_mafia(game: MafiaGame, interaction: discord.Interaction):
    role_list = assign_roles(len(game.players))
    for member, role in zip(game.players, role_list):
        game.roles[member.id] = role
    game.alive = list(game.players)
    game.phase = "starting"

    dm_failures = []
    for member in game.players:
        role      = game.get_role(member)
        role_info = MAFIA_ROLES[role]
        e = discord.Embed(
            title=f"🃏 Your Role — {role_info['emoji']} {role}",
            description=role_info["desc"],
            color=EMPIRE_RED if role == "Mafia" else EMPIRE_CYAN,
        )
        e.add_field(name="Team", value=role_info["team"].capitalize(), inline=True)
        if role == "Mafia":
            team_names = ", ".join(m.display_name for m in game.players if game.is_mafia(m))
            e.add_field(name="🗡️ Your Mafia team", value=team_names, inline=False)
        e.set_footer(text="⚜ Oblivion Empire | Mafia — keep your role secret!")
        try:
            await member.send(embed=e)
        except discord.Forbidden:
            dm_failures.append(member.display_name)

    names = "\n".join(f"• {m.display_name}" for m in game.players)
    e = discord.Embed(
        title="🎭 Mafia — The Game Begins!",
        description=(
            f"*{len(game.players)} players have entered the darkness...*\n\n"
            f"{names}\n\n"
            "✉️ Check your **DMs** for your secret role!"
            + (f"\n⚠️ DMs failed for: {', '.join(dm_failures)}" if dm_failures else "")
        ),
        color=EMPIRE_PURPLE,
    )
    brand(e)
    await game.channel.send(embed=e)
    await asyncio.sleep(3)
    await _day_phase(game)


class DayVoteView(View):
    def __init__(self, game: MafiaGame):
        super().__init__(timeout=120)
        self.game = game
        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in game.alive]
        sel = Select(placeholder="🗳️ Vote to eliminate...", options=opts)
        sel.callback = self._on_vote
        self.add_item(sel)

    async def _on_vote(self, interaction: discord.Interaction):
        if interaction.user not in self.game.alive:
            await interaction.response.send_message("❌ You are eliminated.", ephemeral=True); return
        tid = int(interaction.data["values"][0])
        if tid == interaction.user.id:
            await interaction.response.send_message("❌ Can't vote for yourself.", ephemeral=True); return
        self.game.votes[interaction.user.id] = tid
        target = interaction.guild.get_member(tid)
        await interaction.response.send_message(
            f"🗳️ Voted for **{target.display_name if target else '?'}**.", ephemeral=True)


class NightActionView(View):
    def __init__(self, game: MafiaGame, actor_role: str, user_id: int):
        super().__init__(timeout=90)
        self.game       = game
        self.actor_role = actor_role
        self.user_id    = user_id

        targets = game.alive if actor_role == "Doctor" else game.village_alive()
        opts    = [
            discord.SelectOption(label=m.display_name[:100], value=str(m.id))
            for m in targets if m.id != user_id
        ]
        if not opts: return
        labels  = {"Mafia": "🗡️ Eliminate...", "Doctor": "💊 Protect...", "Detective": "🔍 Investigate..."}
        sel     = Select(placeholder=labels.get(actor_role, "Select..."), options=opts)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not yours.", ephemeral=True); return
        tid = int(interaction.data["values"][0])
        self.game.night_actions[self.actor_role] = tid
        target = interaction.guild.get_member(tid)
        msgs   = {
            "Mafia":     f"🗡️ Target locked: **{target.display_name if target else '?'}**",
            "Doctor":    f"💊 Protecting **{target.display_name if target else '?'}** tonight.",
            "Detective": f"🔍 Investigating **{target.display_name if target else '?'}**...",
        }
        await interaction.response.send_message(msgs.get(self.actor_role, "✅ Done."), ephemeral=True)
        self.stop()


async def _day_phase(game: MafiaGame):
    game.phase = "day"
    game.day  += 1
    game.votes = {}

    winner = game.check_win()
    if winner:
        await _end_mafia(game, winner); return

    names = " • ".join(m.display_name for m in game.alive)
    e = discord.Embed(
        title=f"☀️ Day {game.day} — Discuss & Vote",
        description=(
            f"*{len(game.alive)} players remain.*\n\n"
            f"**Alive:** {names}\n\n"
            "Vote to eliminate a suspect.\n"
            "Voting closes in **2 minutes**."
        ),
        color=EMPIRE_GOLD,
    )
    brand(e)
    view = DayVoteView(game)
    await game.channel.send(embed=e, view=view)
    await asyncio.sleep(120)
    view.stop()

    if not game.votes:
        await game.channel.send(embed=discord.Embed(
            title="🗳️ No Votes Cast",
            description="Nobody eliminated. The night falls...",
            color=EMPIRE_PURPLE))
    else:
        tally: dict[int, int] = {}
        for tid in game.votes.values():
            tally[tid] = tally.get(tid, 0) + 1
        elim_id = max(tally, key=tally.get)
        elim    = game.channel.guild.get_member(elim_id)
        if elim and elim in game.alive:
            game.alive.remove(elim)
            role_info = MAFIA_ROLES[game.get_role(elim)]
            await game.channel.send(embed=discord.Embed(
                title="⚖️ The Community Has Spoken!",
                description=(f"**{elim.display_name}** is eliminated.\n\n"
                             f"They were: {role_info['emoji']} **{game.get_role(elim)}**"),
                color=EMPIRE_RED))

    winner = game.check_win()
    if winner:
        await _end_mafia(game, winner); return
    await asyncio.sleep(3)
    await _night_phase(game)


async def _night_phase(game: MafiaGame):
    game.phase        = "night"
    game.night_actions = {"Mafia": None, "Doctor": None, "Detective": None}

    e = discord.Embed(
        title=f"🌙 Night {game.day} — Darkness Falls",
        description="*Oblivion Empire sleeps. Special roles — check your DMs.*\n"
                    "**90 seconds** before dawn.",
        color=0x1a1a2e,
    )
    brand(e)
    await game.channel.send(embed=e)

    for member in game.alive:
        role = game.get_role(member)
        if role not in ("Mafia", "Doctor", "Detective"): continue
        action_e = discord.Embed(
            title=f"🌙 Night Action — {MAFIA_ROLES[role]['emoji']} {role}",
            description="Use the menu below.",
            color=EMPIRE_PURPLE)
        action_e.set_footer(text="⚜ Oblivion Empire | Mafia — Night Phase")
        try:
            await member.send(embed=action_e, view=NightActionView(game, role, member.id))
        except discord.Forbidden:
            pass

    await asyncio.sleep(90)

    elim_id  = game.night_actions.get("Mafia")
    prot_id  = game.night_actions.get("Doctor")
    invest_id= game.night_actions.get("Detective")

    # Detective result DM
    if invest_id:
        target = game.channel.guild.get_member(invest_id)
        det    = next((m for m in game.alive if game.get_role(m) == "Detective"), None)
        if target and det:
            is_maf  = game.get_role(target) == "Mafia"
            result_e = discord.Embed(
                title="🔍 Investigation Result",
                description=(f"**{target.display_name}** is "
                             f"{'🗡️ **Mafia**' if is_maf else '🏡 **Village**'}!"),
                color=EMPIRE_RED if is_maf else EMPIRE_GREEN)
            try:
                await det.send(embed=result_e)
            except Exception: pass

    # Resolve kill
    dawn_lines = []
    if elim_id and elim_id != prot_id:
        victim = game.channel.guild.get_member(elim_id)
        if victim and victim in game.alive:
            game.alive.remove(victim)
            role_info = MAFIA_ROLES[game.get_role(victim)]
            dawn_lines.append(
                f"💀 **{victim.display_name}** was eliminated during the night.\n"
                f"They were: {role_info['emoji']} **{game.get_role(victim)}**")
    elif elim_id and elim_id == prot_id:
        dawn_lines.append("💊 Someone was targeted but **survived** — the Doctor saved them!")
    else:
        dawn_lines.append("😴 A quiet night. Nobody was eliminated.")

    e = discord.Embed(
        title=f"🌅 Dawn of Day {game.day + 1}",
        description="\n".join(dawn_lines),
        color=EMPIRE_GOLD)
    brand(e)
    await game.channel.send(embed=e)

    winner = game.check_win()
    if winner:
        await _end_mafia(game, winner); return
    await asyncio.sleep(3)
    await _day_phase(game)


async def _end_mafia(game: MafiaGame, winner: str):
    game.phase = "ended"
    active_mafia.pop(game.channel.id, None)

    if winner == "village":
        title, desc, color = "🏡 Village Wins!", "The Mafia is eliminated. Oblivion Empire is safe!", EMPIRE_GREEN
    else:
        title, desc, color = "🗡️ Mafia Wins!", "The Mafia controls Oblivion Empire. Darkness reigns...", EMPIRE_RED

    reveal = "\n".join(
        f"{MAFIA_ROLES[game.get_role(m)]['emoji']} **{m.display_name}** — {game.get_role(m)}"
        for m in game.players)
    e = discord.Embed(title=title, description=desc, color=color)
    e.add_field(name="🃏 Role Reveal", value=reveal, inline=False)
    brand(e)
    await game.channel.send(embed=e)
    await log_action(game.channel.guild, "🎭 Mafia Ended",
        f"#{game.channel.name} — {winner} won | {len(game.players)} players")

# ══════════════════════════════════════════════════════════════════════
#  GAMES PANEL
# ══════════════════════════════════════════════════════════════════════

class GamesPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Guess the Hero", emoji="🔎",
                       style=discord.ButtonStyle.primary, row=0)
    async def guess_hero_btn(self, interaction: discord.Interaction, _: Button):
        cid = interaction.channel_id
        if cid in active_guess:
            await interaction.response.send_message(
                "❌ Guess the Hero is already running here!", ephemeral=True); return
        if cid in active_mafia:
            await interaction.response.send_message(
                "❌ Finish the Mafia game first.", ephemeral=True); return

        playable = get_playable_heroes()
        if not playable:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⚠️ No Hero Images Set Up Yet",
                    description=(
                        "To play Guess the Hero you need to add image URLs.\n\n"
                        "**Steps:**\n"
                        "1. Open `games.py`\n"
                        "2. Find the `HOK_HEROES` dictionary\n"
                        "3. Paste image URLs into the `\"image\"` field for each hero\n"
                        "4. Push to GitHub — Railway redeploys automatically\n\n"
                        "Use cropped screenshots for a harder challenge!"
                    ),
                    color=EMPIRE_RED), ephemeral=True); return

        active_guess[cid] = {
            "host_id": interaction.user.id,
            "hero":    None,
            "used":    [],
            "scores":  {},
            "revealed": True,
        }
        e = discord.Embed(
            title="🔎 Guess the Hero — Starting!",
            description=(
                f"*Hosted by **{interaction.user.display_name}***\n\n"
                "An HoK hero image will appear below.\n"
                "**Type the hero's name in this channel.** First correct answer gets a point!\n\n"
                f"🎮 **{len(playable)}** heroes in the pool."
            ),
            color=EMPIRE_GOLD,
        )
        brand(e)
        await interaction.response.send_message(embed=e)
        await asyncio.sleep(3)
        await _post_round(interaction.channel, cid)
        await log_action(interaction.guild, "🔎 Guess Hero Started",
            f"{interaction.user.mention} started Guess the Hero in #{interaction.channel.name}")

    @discord.ui.button(label="Mafia", emoji="🎭",
                       style=discord.ButtonStyle.danger, row=0)
    async def mafia_btn(self, interaction: discord.Interaction, _: Button):
        cid = interaction.channel_id
        if cid in active_mafia:
            await interaction.response.send_message(
                "❌ A Mafia game is already running here!", ephemeral=True); return
        if cid in active_guess:
            await interaction.response.send_message(
                "❌ Finish Guess the Hero first.", ephemeral=True); return

        game = MafiaGame(interaction.channel, interaction.user)
        active_mafia[cid] = game
        e    = _lobby_embed(game)
        view = MafiaLobbyView(game)
        await interaction.response.send_message(embed=e, view=view)
        msg = await interaction.original_response()
        game.lobby_msg = msg
        await log_action(interaction.guild, "🎭 Mafia Lobby",
            f"{interaction.user.mention} opened Mafia lobby in #{interaction.channel.name}")

    @discord.ui.button(label="Game Scores", emoji="🏅",
                       style=discord.ButtonStyle.secondary, row=1)
    async def scores_btn(self, interaction: discord.Interaction, _: Button):
        scores = db.get("game_scores", {})
        if not scores:
            await interaction.response.send_message(
                embed=discord.Embed(title="🏅 No Scores Yet",
                                    description="Play some games first!",
                                    color=EMPIRE_PURPLE), ephemeral=True); return
        sorted_s = sorted(scores.items(), key=lambda x: -x[1])
        medals   = ["🥇", "🥈", "🥉"]
        lines    = []
        for i, (uid, pts) in enumerate(sorted_s[:15], 1):
            mem   = interaction.guild.get_member(int(uid))
            name  = mem.display_name if mem else f"ID:{uid}"
            medal = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(f"{medal} **{name}** — {pts} pt{'s' if pts != 1 else ''}")
        e = discord.Embed(
            title="🏅 Guess the Hero — All-Time Scores",
            description="\n".join(lines),
            color=EMPIRE_GOLD)
        brand(e)
        await interaction.response.send_message(embed=e, ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════

class GamesCog(commands.Cog):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @app_commands.command(name="games",
                          description="🎮 Open the Oblivion Empire games panel")
    async def cmd_games(self, interaction: discord.Interaction):
        playable = get_playable_heroes()
        e = discord.Embed(
            title="🎮 Oblivion Empire — Games",
            description="*Welcome to the arena, warrior.*",
            color=EMPIRE_PURPLE,
        )
        e.add_field(name="🔎 Guess the Hero",
                    value=(f"Identify HoK heroes from images.\n"
                           f"*{len(playable)} hero{'es' if len(playable)!=1 else ''} "
                           f"ready to play!*"),
                    inline=False)
        e.add_field(name="🎭 Mafia",
                    value="Social deduction. Villagers vs Mafia. Trust no one.",
                    inline=False)
        e.add_field(name="🏅 Game Scores",
                    value="All-time Guess the Hero leaderboard.",
                    inline=False)
        av = bot_avatar()
        if av: e.set_thumbnail(url=av)
        e.set_footer(text="⚜ Oblivion Empire | Games Panel")
        await interaction.response.send_message(embed=e, view=GamesPanelView())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for Guess the Hero answers in active game channels."""
        if message.author.bot:
            return
        cid  = message.channel.id
        game = active_guess.get(cid)
        if not game or game.get("revealed"):
            return
        hero = game.get("hero")
        if not hero:
            return

        if check_guess(message.content, hero):
            game["revealed"] = True
            uid = str(message.author.id)
            game["scores"][uid] = game["scores"].get(uid, 0) + 1
            pts = game["scores"][uid]
            info = HOK_HEROES.get(hero, {})
            e = discord.Embed(
                title="✅ Correct!",
                description=(
                    f"🎉 **{message.author.display_name}** got it!\n\n"
                    f"The hero was **{hero}**\n"
                    f"Class: {info.get('class','?')} • Lane: {info.get('lane','?')}\n\n"
                    f"They now have **{pts}** point{'s' if pts != 1 else ''} this game."
                ),
                color=EMPIRE_GREEN,
            )
            e.set_footer(text="⚜ Oblivion Empire | Next hero coming up...")
            await message.channel.send(embed=e)
            await asyncio.sleep(3)
            await _next_round(message.channel, cid)


async def setup(bot_instance: commands.Bot):
    bot_instance.tree.remove_command("games")
    cog = GamesCog(bot_instance)
    await bot_instance.add_cog(cog)
