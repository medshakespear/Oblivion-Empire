# ══════════════════════════════════════════════════════════════════════
#  bot.py  —  Oblivion Empire Bot  (Honor of Kings Community)
# ══════════════════════════════════════════════════════════════════════
#
#  HOK RANK SYSTEM — 7 Main Tiers:
#    🥉 Bronze      (3 sub-tiers I-III)   — no star loss on defeat
#    🥈 Silver      (3 sub-tiers I-III)
#    🥇 Gold        (4 sub-tiers I-IV)
#    💠 Platinum    (4 sub-tiers I-IV)
#    💎 Diamond     (5 sub-tiers I-V)     — draft & ban phase begins
#    ⚡ Master      (5 sub-tiers I-V)
#    👑 Grandmaster — star-count ladder (no sub-tiers)
#       Milestones by accumulated stars:
#         👑 King     0  stars
#         🔮 Mythic  25  stars
#         🌟 Epic    50  stars
#         🏆 Legend 100  stars
#
#  RAILWAY ENV VARIABLES:
#    DISCORD_TOKEN   — bot token
#    ADMIN_ROLE_IDS  — comma-separated role IDs  e.g. "123,456"
#    DATA_DIR        — /data  (Railway persistent volume)
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
from discord import app_commands
import os, json, asyncio, uuid
from datetime import datetime
from typing import Optional

# ─── INTENTS ──────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members        = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── ENV / CONFIG ─────────────────────────────────────────────────────
ADMIN_ROLE_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_ROLE_IDS", "").split(",")
    if x.strip().isdigit()
]
DATA_DIR  = os.getenv("DATA_DIR", "/data")
DATA_FILE = os.path.join(DATA_DIR, "oblivion_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

LOG_CHANNEL_NAME = "oblivion-logs"   # change to match your server

# ─── COLOURS ──────────────────────────────────────────────────────────
EMPIRE_GOLD   = 0xc9a227
EMPIRE_RED    = 0x8b1a1a
EMPIRE_PURPLE = 0x5c0099
EMPIRE_CYAN   = 0x00b4d8
EMPIRE_GREEN  = 0x2ecc71

# ══════════════════════════════════════════════════════════════════════
#  HONOR OF KINGS — RANK DATA
# ══════════════════════════════════════════════════════════════════════

HOK_MAIN_RANKS = [
    "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster"
]
HOK_RANK_ORDER = {r: i for i, r in enumerate(HOK_MAIN_RANKS)}   # 0–6

# Sub-tiers per tier (Grandmaster has none — uses stars instead)
HOK_SUBTIERS: dict[str, list[str]] = {
    "Bronze":      ["I", "II", "III"],
    "Silver":      ["I", "II", "III"],
    "Gold":        ["I", "II", "III", "IV"],
    "Platinum":    ["I", "II", "III", "IV"],
    "Diamond":     ["I", "II", "III", "IV", "V"],
    "Master":      ["I", "II", "III", "IV", "V"],
    "Grandmaster": [],
}

HOK_RANK_EMOJIS: dict[str, str] = {
    "Bronze":      "🥉",
    "Silver":      "🥈",
    "Gold":        "🥇",
    "Platinum":    "💠",
    "Diamond":     "💎",
    "Master":      "⚡",
    "Grandmaster": "👑",
}

# Grandmaster milestones — (minimum_stars, display_name, emoji)
HOK_GM_MILESTONES: list[tuple[int, str, str]] = [
    (100, "Legend", "🏆"),
    ( 50, "Epic",   "🌟"),
    ( 25, "Mythic", "🔮"),
    (  0, "King",   "👑"),
]

# HoK lanes (proper HoK naming — not MLBB)
HOK_LANES = ["Baron Lane", "Jungle", "Mid Lane", "Dragon Lane", "Roam"]
HOK_LANE_EMOJIS: dict[str, str] = {
    "Baron Lane":  "🗡️",
    "Jungle":      "🌿",
    "Mid Lane":    "⚡",
    "Dragon Lane": "🐉",
    "Roam":        "🌀",
}

HOK_CLASSES = ["Tank", "Fighter", "Assassin", "Mage", "Marksman", "Support"]
HOK_CLASS_EMOJIS: dict[str, str] = {
    "Tank":      "🛡️",
    "Fighter":   "⚔️",
    "Assassin":  "🗡️",
    "Mage":      "🔮",
    "Marksman":  "🏹",
    "Support":   "💚",
}

# ─── RANK HELPERS ─────────────────────────────────────────────────────

def gm_milestone(stars: int) -> tuple[str, str]:
    """Return (name, emoji) for a Grandmaster star count."""
    for min_s, name, emoji in HOK_GM_MILESTONES:
        if stars >= min_s:
            return name, emoji
    return "King", "👑"


def format_rank(rank_str: str, stars: int = 0) -> str:
    """Human-readable rank line with emoji.
       e.g. '💎 Diamond V'  or  '👑 Grandmaster · 🔮 Mythic (38 ⭐)'
    """
    if not rank_str:
        return "—"
    main  = rank_str.split()[0]
    emoji = HOK_RANK_EMOJIS.get(main, "🎮")
    if main == "Grandmaster":
        ms_name, ms_emoji = gm_milestone(stars)
        return f"{emoji} Grandmaster · {ms_emoji} {ms_name}  ({stars} ⭐)"
    return f"{emoji} {rank_str}"


def sub_tier_index(sub: str) -> int:
    order = ["I", "II", "III", "IV", "V"]
    return order.index(sub) if sub in order else 0


def rank_sort_key(md: dict) -> tuple[int, int]:
    """
    Primary sort = tier index (Bronze=0 … Grandmaster=6).
    Secondary sort = sub-tier index  OR  star count for Grandmaster.
    Higher = better, so we negate for ascending-only sorts.
    """
    peak = md.get("peak_rank", "")
    main = peak.split()[0] if peak else ""
    tier = HOK_RANK_ORDER.get(main, -1)
    if main == "Grandmaster":
        return (tier, md.get("peak_stars", 0))
    sub = peak.split()[-1] if " " in peak else "I"
    return (tier, sub_tier_index(sub))

# ══════════════════════════════════════════════════════════════════════
#  DATA LAYER
# ══════════════════════════════════════════════════════════════════════

def _blank_db() -> dict:
    return {
        "members":     {},
        "events":      {},
        "game_scores": {},
        "config":      {"admin_role_ids": ADMIN_ROLE_IDS},
    }


def load_db() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in _blank_db().items():
            data.setdefault(k, v)
        return data
    fresh = _blank_db()
    save_db(fresh)
    return fresh


def save_db(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def new_member(discord_id: int) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "discord_id":    discord_id,
        "ign":           "",
        "current_rank":  "",     # e.g. "Gold III" or "Grandmaster"
        "current_stars": 0,      # only used when current_rank = "Grandmaster"
        "peak_rank":     "",     # e.g. "Diamond V" or "Grandmaster"
        "peak_stars":    0,      # only used when peak_rank = "Grandmaster"
        "main_lane":     "",
        "hero_class":    "",
        "region":        "",
        "registered_at": now,
        "updated_at":    now,
    }


# Global in-memory db — imported by games.py
db = load_db()

# ─── GENERIC HELPERS ──────────────────────────────────────────────────

def bot_avatar() -> Optional[str]:
    return bot.user.display_avatar.url if bot.user else None


def brand(embed: discord.Embed, thumb: bool = True) -> discord.Embed:
    av = bot_avatar()
    if av and thumb:
        embed.set_thumbnail(url=av)
    embed.set_footer(text="⚜ Oblivion Empire", icon_url=av or discord.utils.MISSING)
    return embed


async def log_action(guild: discord.Guild, title: str, desc: str) -> None:
    ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if not ch:
        return
    e = discord.Embed(title=title, description=desc,
                      color=EMPIRE_PURPLE, timestamp=datetime.utcnow())
    brand(e, thumb=False)
    try:
        await ch.send(embed=e)
    except Exception:
        pass


def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    admin_ids = set(db["config"].get("admin_role_ids", ADMIN_ROLE_IDS))
    return any(r.id in admin_ids for r in member.roles)


def fuzzy_search(guild: discord.Guild, query: str) -> list[discord.Member]:
    q = query.strip()
    if q.isdigit():
        m = guild.get_member(int(q))
        return [m] if m else []
    if q.startswith("<@") and q.endswith(">"):
        try:
            m = guild.get_member(int(q.strip("<@!>")))
            return [m] if m else []
        except Exception:
            pass
    ql = q.lower()
    return [
        m for m in guild.members if not m.bot and (
            ql in m.display_name.lower()
            or ql in m.name.lower()
            or (m.global_name and ql in m.global_name.lower())
        )
    ][:25]

# ══════════════════════════════════════════════════════════════════════
#  PROFILE SETUP FLOW
#
#  Step 1 — Lane (dropdown)
#  Step 2 — Hero Class (dropdown)
#  Step 3 — Current Rank TIER (dropdown, 7 options)
#  Step 4 — Current Rank SUB-TIER (dropdown) or skip if Grandmaster
#  Step 5 — Peak Rank TIER (dropdown, 7 options)
#  Step 6 — Peak Rank SUB-TIER (dropdown) or skip if Grandmaster
#  Step 7 — Final Modal: IGN + GM stars (if any) + Region
# ══════════════════════════════════════════════════════════════════════

# ── Step 1 ────────────────────────────────────────────────────────────
class SetupLaneView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        opts = [
            discord.SelectOption(label=lane, emoji=HOK_LANE_EMOJIS[lane])
            for lane in HOK_LANES
        ]
        sel = Select(placeholder="🗺️ Step 1 — Choose your main lane...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        lane     = interaction.data["values"][0]
        existing = db["members"].get(str(interaction.user.id))
        e = discord.Embed(
            title="⚙️ Profile Setup — Step 2 of 7",
            description=f"✅ Lane: **{HOK_LANE_EMOJIS[lane]} {lane}**\n\nPick your **hero class**:",
            color=EMPIRE_PURPLE)
        brand(e)
        await interaction.response.edit_message(
            embed=e, view=SetupClassView(self.user_id, lane, existing))


# ── Step 2 ────────────────────────────────────────────────────────────
class SetupClassView(View):
    def __init__(self, user_id: int, lane: str, existing: Optional[dict]):
        super().__init__(timeout=180)
        self.user_id  = user_id
        self.lane     = lane
        self.existing = existing
        opts = [
            discord.SelectOption(label=c, emoji=HOK_CLASS_EMOJIS[c])
            for c in HOK_CLASSES
        ]
        sel = Select(placeholder="🎮 Step 2 — Choose your hero class...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        cls = interaction.data["values"][0]
        e = discord.Embed(
            title="⚙️ Profile Setup — Step 3 of 7",
            description=(f"✅ Lane: **{HOK_LANE_EMOJIS[self.lane]} {self.lane}**\n"
                         f"✅ Class: **{HOK_CLASS_EMOJIS[cls]} {cls}**\n\n"
                         "Select your **current rank tier**:"),
            color=EMPIRE_PURPLE)
        brand(e)
        await interaction.response.edit_message(
            embed=e,
            view=RankTierView(self.user_id, self.lane, cls, self.existing,
                              purpose="current", progress=3))


# ── Reusable: Tier picker ──────────────────────────────────────────────
class RankTierView(View):
    """
    purpose = "current" or "peak"
    After picking tier, routes to SubTierView (non-GM) or straight to
    ProfileFinalModal (if both ranks confirmed as GM).
    """
    def __init__(self, user_id: int, lane: str, cls: str,
                 existing: Optional[dict], purpose: str,
                 current_rank: str = "", current_stars: int = 0,
                 progress: int = 3):
        super().__init__(timeout=180)
        self.user_id      = user_id
        self.lane         = lane
        self.cls          = cls
        self.existing     = existing
        self.purpose      = purpose
        self.current_rank = current_rank      # filled only when purpose="peak"
        self.current_stars = current_stars
        self.progress     = progress

        label = ("current rank" if purpose == "current" else "peak / highest rank")
        step  = f"Step {progress} of 7"

        opts = []
        for tier in HOK_MAIN_RANKS:
            subs = HOK_SUBTIERS[tier]
            desc = (f"{len(subs)} sub-tiers (I–{subs[-1]})" if subs
                    else "Star-count ladder  (King → Mythic → Epic → Legend)")
            opts.append(discord.SelectOption(
                label=tier, emoji=HOK_RANK_EMOJIS[tier], description=desc))

        sel = Select(placeholder=f"📊 {step} — Select your {label} tier...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        tier = interaction.data["values"][0]

        if tier == "Grandmaster":
            # No sub-tiers — go straight to next stage
            if self.purpose == "current":
                # current = GM, now pick peak tier
                e = discord.Embed(
                    title="⚙️ Profile Setup — Step 5 of 7",
                    description=(f"✅ Lane: **{HOK_LANE_EMOJIS[self.lane]} {self.lane}**\n"
                                 f"✅ Class: **{HOK_CLASS_EMOJIS[self.cls]} {self.cls}**\n"
                                 f"✅ Current: **👑 Grandmaster** *(stars recorded in final step)*\n\n"
                                 "Now select your **peak rank tier**:"),
                    color=EMPIRE_PURPLE)
                brand(e)
                await interaction.response.edit_message(
                    embed=e,
                    view=RankTierView(self.user_id, self.lane, self.cls, self.existing,
                                      purpose="peak", current_rank="Grandmaster",
                                      current_stars=0, progress=5))
            else:
                # peak = GM → open final modal
                await interaction.response.send_modal(
                    ProfileFinalModal(self.lane, self.cls,
                                      self.current_rank, self.current_stars,
                                      "Grandmaster", 0, self.existing))
        else:
            # Show sub-tier picker
            next_step = self.progress + 1
            e = discord.Embed(
                title=f"⚙️ Profile Setup — Step {next_step} of 7",
                description=(f"✅ {tier} selected.\n\nNow pick the **sub-tier**:"),
                color=EMPIRE_PURPLE)
            brand(e)
            await interaction.response.edit_message(
                embed=e,
                view=RankSubTierView(self.user_id, self.lane, self.cls, self.existing,
                                     purpose=self.purpose, tier=tier,
                                     current_rank=self.current_rank,
                                     current_stars=self.current_stars,
                                     progress=next_step))


# ── Reusable: Sub-tier picker ─────────────────────────────────────────
class RankSubTierView(View):
    def __init__(self, user_id: int, lane: str, cls: str,
                 existing: Optional[dict], purpose: str, tier: str,
                 current_rank: str = "", current_stars: int = 0,
                 progress: int = 4):
        super().__init__(timeout=180)
        self.user_id       = user_id
        self.lane          = lane
        self.cls           = cls
        self.existing      = existing
        self.purpose       = purpose
        self.tier          = tier
        self.current_rank  = current_rank
        self.current_stars = current_stars
        self.progress      = progress

        subtiers = HOK_SUBTIERS[tier]
        opts = [
            discord.SelectOption(label=f"{tier} {sub}", value=sub,
                                 emoji=HOK_RANK_EMOJIS[tier])
            for sub in subtiers
        ]
        label = "current" if purpose == "current" else "peak"
        sel   = Select(
            placeholder=f"📊 Step {progress} of 7 — Select {label} sub-tier...",
            options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True); return
        sub  = interaction.data["values"][0]
        rank = f"{self.tier} {sub}"   # e.g. "Gold III"

        if self.purpose == "current":
            # Now pick peak rank tier
            e = discord.Embed(
                title="⚙️ Profile Setup — Step 5 of 7",
                description=(f"✅ Current Rank: **{format_rank(rank)}**\n\n"
                             "Now select your **peak / highest rank tier**:"),
                color=EMPIRE_PURPLE)
            brand(e)
            await interaction.response.edit_message(
                embed=e,
                view=RankTierView(self.user_id, self.lane, self.cls, self.existing,
                                  purpose="peak", current_rank=rank,
                                  current_stars=0, progress=5))
        else:
            # Both ranks confirmed — open final modal
            await interaction.response.send_modal(
                ProfileFinalModal(self.lane, self.cls,
                                  self.current_rank, self.current_stars,
                                  rank, 0, self.existing))


# ── Step 7 — Final Modal ──────────────────────────────────────────────
class ProfileFinalModal(Modal):
    """
    Collects: IGN, GM star counts (if any rank is Grandmaster), Region.
    Fields are added dynamically so we only show GM stars when relevant.
    """
    def __init__(self, lane: str, cls: str,
                 curr_rank: str, curr_stars_prefill: int,
                 peak_rank: str, peak_stars_prefill: int,
                 existing: Optional[dict]):
        super().__init__(title="⚜ Profile — Final Step (7/7)")
        self.lane      = lane
        self.cls       = cls
        self.curr_rank = curr_rank
        self.peak_rank = peak_rank

        # IGN — always present
        self._ign = TextInput(
            label="In-Game Name (IGN)",
            placeholder="Your HoK username exactly as shown in-game",
            required=True, max_length=50,
            default=existing.get("ign", "") if existing else "")
        self.add_item(self._ign)

        # Star count for current rank (only if Grandmaster)
        self._curr_stars: Optional[TextInput] = None
        if curr_rank == "Grandmaster":
            self._curr_stars = TextInput(
                label="Current Grandmaster — star count",
                placeholder="e.g. 12 (King <25) · 38 (Mythic <50) · 72 (Epic <100) · 120 (Legend)",
                required=True, max_length=5,
                default=str(curr_stars_prefill) if curr_stars_prefill else "")
            self.add_item(self._curr_stars)

        # Star count for peak rank (only if Grandmaster)
        self._peak_stars: Optional[TextInput] = None
        if peak_rank == "Grandmaster":
            label_text = ("Peak Grandmaster — star count"
                          if curr_rank != "Grandmaster"
                          else "Peak Grandmaster — star count (if different)")
            self._peak_stars = TextInput(
                label=label_text,
                placeholder="e.g. 47 (Mythic) · 85 (Epic) · 130 (Legend)",
                required=True, max_length=5,
                default=str(peak_stars_prefill) if peak_stars_prefill else "")
            self.add_item(self._peak_stars)

        # Region — always present (optional)
        self._region = TextInput(
            label="Region  (optional)",
            placeholder="e.g. SEA, EU, NA, ME, East Asia, Global",
            required=False, max_length=20,
            default=existing.get("region", "") if existing else "")
        self.add_item(self._region)

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        md  = db["members"].get(uid) or new_member(interaction.user.id)

        # Parse star counts safely
        def to_int(ti: Optional[TextInput]) -> int:
            if ti is None: return 0
            v = ti.value.strip()
            return int(v) if v.isdigit() else 0

        curr_stars = to_int(self._curr_stars)
        peak_stars = to_int(self._peak_stars)

        md.update({
            "ign":           self._ign.value.strip(),
            "current_rank":  self.curr_rank,
            "current_stars": curr_stars,
            "peak_rank":     self.peak_rank,
            "peak_stars":    peak_stars,
            "main_lane":     self.lane,
            "hero_class":    self.cls,
            "region":        self._region.value.strip(),
            "updated_at":    datetime.utcnow().isoformat(),
        })
        db["members"][uid] = md
        save_db(db)

        le = HOK_LANE_EMOJIS.get(self.lane, "🎮")
        ce = HOK_CLASS_EMOJIS.get(self.cls, "🎮")
        e = discord.Embed(title="✅ Profile Saved!", color=EMPIRE_GREEN,
                          description="Your Oblivion Empire warrior profile is live.")
        e.add_field(name="🎮 IGN",           value=md["ign"],                                       inline=True)
        e.add_field(name=f"{le} Lane",       value=f"{le} {self.lane}",                             inline=True)
        e.add_field(name=f"{ce} Class",      value=f"{ce} {self.cls}",                              inline=True)
        e.add_field(name="📊 Current Rank",  value=format_rank(self.curr_rank, curr_stars),         inline=True)
        e.add_field(name="🏆 Peak Rank",     value=format_rank(self.peak_rank, peak_stars),         inline=True)
        if md.get("region"):
            e.add_field(name="🌐 Region",    value=md["region"],                                    inline=True)
        brand(e, thumb=False)
        await interaction.response.send_message(embed=e, ephemeral=True)
        await log_action(interaction.guild, "📝 Profile Updated",
            f"{interaction.user.mention} — **{md['ign']}** | "
            f"{format_rank(self.curr_rank, curr_stars)} | "
            f"Peak: {format_rank(self.peak_rank, peak_stars)}")

# ══════════════════════════════════════════════════════════════════════
#  EMBED BUILDERS
# ══════════════════════════════════════════════════════════════════════

def build_profile_embed(member: discord.Member) -> discord.Embed:
    md = db["members"].get(str(member.id))
    if not md or not md.get("ign"):
        e = discord.Embed(
            title="⚜ Profile Not Found",
            description=(f"{member.mention} hasn't set up their profile yet.\n"
                         "Use `/oblivion` → **Setup Profile** to get started!"),
            color=EMPIRE_PURPLE)
        e.set_thumbnail(url=member.display_avatar.url)
        return e

    le = HOK_LANE_EMOJIS.get(md.get("main_lane", ""), "🎮")
    ce = HOK_CLASS_EMOJIS.get(md.get("hero_class", ""), "🎮")
    cr = format_rank(md.get("current_rank", ""), md.get("current_stars", 0))
    pr = format_rank(md.get("peak_rank", ""),    md.get("peak_stars", 0))

    e = discord.Embed(
        title=f"⚜ {md['ign']}",
        description=f"*{member.mention} — Oblivion Empire*",
        color=EMPIRE_GOLD)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="🎮 IGN",          value=md["ign"],                    inline=True)
    e.add_field(name="📊 Current Rank", value=cr,                           inline=True)
    e.add_field(name="🏆 Peak Rank",    value=pr,                           inline=True)
    e.add_field(name=f"{le} Main Lane", value=md.get("main_lane","—"),      inline=True)
    e.add_field(name=f"{ce} Class",     value=md.get("hero_class","—"),     inline=True)
    e.add_field(name="🌐 Region",       value=md.get("region","—"),         inline=True)
    try:
        upd = datetime.fromisoformat(md["updated_at"]).strftime("%b %d, %Y")
    except Exception:
        upd = "—"
    e.set_footer(text=f"⚜ Oblivion Empire | Updated {upd}")
    return e


def build_leaderboard_embed(members_list: list[dict], guild: discord.Guild,
                             title: str, subtitle: str = "") -> discord.Embed:
    e = discord.Embed(title=title,
                      description=subtitle or "*Oblivion Empire Rankings*",
                      color=EMPIRE_GOLD)
    if not members_list:
        e.add_field(name="No Data",
                    value="No profiles yet — use `/oblivion` → Setup Profile!",
                    inline=False)
        brand(e); return e

    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for i, md in enumerate(members_list[:15], 1):
        mem    = guild.get_member(md["discord_id"])
        name   = mem.display_name if mem else f"ID:{md['discord_id']}"
        pr     = format_rank(md.get("peak_rank", "?"), md.get("peak_stars", 0))
        le     = HOK_LANE_EMOJIS.get(md.get("main_lane", ""), "")
        pos    = medals[i - 1] if i <= 3 else f"`{i}.`"
        lines.append(f"{pos} {le} **{name}** — {pr}")
    e.add_field(name="Rankings", value="\n".join(lines), inline=False)
    brand(e); return e


def build_event_embed(ev: dict) -> discord.Embed:
    yes   = len(ev.get("rsvp_yes", []))
    maybe = len(ev.get("rsvp_maybe", []))
    no    = len(ev.get("rsvp_no", []))
    e = discord.Embed(title=f"🎯 {ev['title']}", description=ev["description"],
                      color=EMPIRE_CYAN)
    e.add_field(name="📅 Date & Time", value=ev["date"],   inline=False)
    e.add_field(name="✅ Going",        value=str(yes),     inline=True)
    e.add_field(name="❓ Maybe",        value=str(maybe),   inline=True)
    e.add_field(name="❌ Not Going",    value=str(no),      inline=True)
    if ev.get("image_url"):
        e.set_image(url=ev["image_url"])
    brand(e); return e

# ══════════════════════════════════════════════════════════════════════
#  MEMBER SEARCH
# ══════════════════════════════════════════════════════════════════════

class SearchModal(Modal, title="🔍 Search Member"):
    query = TextInput(label="Name, display name, or Discord ID",
                      placeholder="Type part of their name...",
                      required=True, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        results = fuzzy_search(interaction.guild, self.query.value)
        if not results:
            await interaction.response.send_message(
                embed=discord.Embed(title="🔍 No Results",
                                    description=f"Nobody found for `{self.query.value}`.",
                                    color=EMPIRE_RED), ephemeral=True)
            return
        if len(results) == 1:
            await interaction.response.send_message(
                embed=build_profile_embed(results[0]), ephemeral=True)
        else:
            e = discord.Embed(title=f"🔍 {len(results)} Found",
                              description="Select the right person:", color=EMPIRE_CYAN)
            await interaction.response.send_message(
                embed=e, view=SearchResultView(results), ephemeral=True)


class SearchResultView(View):
    def __init__(self, members: list[discord.Member]):
        super().__init__(timeout=120)
        self._map = {str(m.id): m for m in members[:25]}
        opts = [
            discord.SelectOption(label=m.display_name[:100], value=str(m.id),
                                 description=f"@{m.name}"[:100])
            for m in members[:25]
        ]
        sel = Select(placeholder="👤 Select...", options=opts)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        uid    = interaction.data["values"][0]
        member = self._map.get(uid) or interaction.guild.get_member(int(uid))
        if not member:
            await interaction.response.send_message("❌ Not found.", ephemeral=True); return
        await interaction.response.edit_message(embed=build_profile_embed(member), view=None)

# ══════════════════════════════════════════════════════════════════════
#  LEADERBOARD MENU
# ══════════════════════════════════════════════════════════════════════

class LeaderboardMenuView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=120)
        self.guild = guild
        opts = (
            [discord.SelectOption(label="Overall Peak Rank", value="overall",
                                  emoji="🏆", description="All players · sorted by peak rank")]
            + [discord.SelectOption(label=f"{HOK_LANE_EMOJIS[l]} {l}", value=l,
                                    description=f"Top {l} mains") for l in HOK_LANES]
            + [discord.SelectOption(label=f"{HOK_CLASS_EMOJIS[c]} {c}", value=c,
                                    description=f"Top {c} players") for c in HOK_CLASSES]
        )
        sel = Select(placeholder="📊 Choose leaderboard...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        val  = interaction.data["values"][0]
        all_m = [m for m in db["members"].values() if m.get("ign")]
        if val == "overall":
            data, title, sub = (sorted(all_m, key=rank_sort_key, reverse=True),
                                "🏆 Overall Rankings",
                                "All players sorted by peak rank")
        elif val in HOK_LANES:
            data, title, sub = (sorted(
                [m for m in all_m if m.get("main_lane") == val],
                key=rank_sort_key, reverse=True),
                f"{HOK_LANE_EMOJIS[val]} {val} Rankings",
                f"Top {val} mains by peak rank")
        else:
            data, title, sub = (sorted(
                [m for m in all_m if m.get("hero_class") == val],
                key=rank_sort_key, reverse=True),
                f"{HOK_CLASS_EMOJIS[val]} {val} Rankings",
                f"Top {val} players by peak rank")
        await interaction.response.edit_message(
            embed=build_leaderboard_embed(data, self.guild, title, sub), view=None)

# ══════════════════════════════════════════════════════════════════════
#  EVENT SYSTEM
# ══════════════════════════════════════════════════════════════════════

class EventRSVPView(View):
    """Persistent across restarts — stable custom_ids."""
    def __init__(self, event_id: str):
        super().__init__(timeout=None)
        self.event_id = event_id
        for status, label, emoji, style in [
            ("yes",   "Going",     "✅", discord.ButtonStyle.success),
            ("maybe", "Maybe",     "❓", discord.ButtonStyle.primary),
            ("no",    "Not Going", "❌", discord.ButtonStyle.danger),
        ]:
            btn = Button(label=label, emoji=emoji, style=style,
                         custom_id=f"rsvp_{status}_{event_id}")
            btn.callback = lambda i, s=status: self._rsvp(i, s)
            self.add_item(btn)

    async def _rsvp(self, interaction: discord.Interaction, status: str):
        ev = db["events"].get(self.event_id)
        if not ev:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True); return
        uid = interaction.user.id
        for key in ("rsvp_yes", "rsvp_maybe", "rsvp_no"):
            if uid in ev[key]: ev[key].remove(uid)
        ev[f"rsvp_{status}"].append(uid)
        save_db(db)
        labels = {"yes": "✅ Going", "maybe": "❓ Maybe", "no": "❌ Not Going"}
        await interaction.response.send_message(
            f"RSVP updated — **{labels[status]}**", ephemeral=True)
        if ev.get("channel_id") and ev.get("message_id"):
            try:
                ch  = interaction.guild.get_channel(ev["channel_id"])
                msg = await ch.fetch_message(ev["message_id"])
                await msg.edit(embed=build_event_embed(ev))
            except Exception:
                pass


class EventModal(Modal, title="🎯 Create Event"):
    ev_title = TextInput(label="Event Title",
                         placeholder="e.g. Ranked Scrimmage Night",
                         required=True, max_length=150)
    ev_desc  = TextInput(label="Description",
                         placeholder="What is this event about?",
                         required=True, max_length=1500,
                         style=discord.TextStyle.paragraph)
    ev_date  = TextInput(label="Date & Time",
                         placeholder="e.g. June 20 · 8:00 PM UTC",
                         required=True, max_length=100)
    ev_image = TextInput(label="Banner URL (optional)",
                         placeholder="https://...",
                         required=False, max_length=500)
    ev_ping  = TextInput(label="Role to ping (name, 'everyone', or blank)",
                         placeholder="e.g. Members   or   everyone",
                         required=False, max_length=50)

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.target_channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        ev_id = str(uuid.uuid4())[:8]
        ev = {
            "id":          ev_id,
            "title":       self.ev_title.value.strip(),
            "description": self.ev_desc.value.strip(),
            "date":        self.ev_date.value.strip(),
            "image_url":   self.ev_image.value.strip() if self.ev_image.value else "",
            "created_by":  interaction.user.id,
            "created_at":  datetime.utcnow().isoformat(),
            "rsvp_yes":    [], "rsvp_maybe": [], "rsvp_no": [],
            "message_id":  None, "channel_id": None,
        }
        db["events"][ev_id] = ev
        save_db(db)
        bot.add_view(EventRSVPView(ev_id))

        pv = (self.ev_ping.value or "").strip().lower()
        if pv == "everyone":      ping = "@everyone"
        elif pv == "here":        ping = "@here"
        elif pv:
            r = discord.utils.get(interaction.guild.roles,
                                  name=self.ev_ping.value.strip())
            ping = r.mention if r else None
        else:                     ping = None

        try:
            msg = await self.target_channel.send(
                content=ping, embed=build_event_embed(ev),
                view=EventRSVPView(ev_id))
            db["events"][ev_id]["message_id"] = msg.id
            db["events"][ev_id]["channel_id"] = self.target_channel.id
            save_db(db)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I can't post in that channel.", ephemeral=True); return

        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Event Created!",
                                description=f"**{ev['title']}** posted in {self.target_channel.mention}.",
                                color=EMPIRE_GREEN), ephemeral=True)
        await log_action(interaction.guild, "🎯 Event Created",
            f"{interaction.user.mention} → **{ev['title']}** in {self.target_channel.mention}")


class EventManagerView(View):
    def __init__(self):
        super().__init__(timeout=120)
        events = list(db["events"].values())
        if not events: return
        opts = [
            discord.SelectOption(
                label=ev["title"][:100], value=ev["id"],
                description=f"{ev['date'][:40]} | ✅{len(ev.get('rsvp_yes',[]))}"[:100])
            for ev in events[:25]
        ]
        sel = Select(placeholder="🗑️ Select event to delete...", options=opts)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        ev_id = interaction.data["values"][0]
        ev    = db["events"].pop(ev_id, None)
        save_db(db)
        if ev:
            if ev.get("channel_id") and ev.get("message_id"):
                try:
                    ch  = interaction.guild.get_channel(ev["channel_id"])
                    msg = await ch.fetch_message(ev["message_id"])
                    await msg.delete()
                except Exception: pass
            await interaction.response.edit_message(
                embed=discord.Embed(title="🗑️ Event Deleted",
                                    description=f"**{ev['title']}** removed.",
                                    color=EMPIRE_RED), view=None)
            await log_action(interaction.guild, "🗑️ Event Deleted",
                f"{interaction.user.mention} deleted **{ev['title']}**")
        else:
            await interaction.response.edit_message(content="❌ Not found.", embed=None, view=None)

# ══════════════════════════════════════════════════════════════════════
#  ANNOUNCEMENT SYSTEM — mods pick ANY server channel
# ══════════════════════════════════════════════════════════════════════

def _channel_pages(guild: discord.Guild) -> list[list[discord.TextChannel]]:
    channels = guild.text_channels
    return [channels[i:i+25] for i in range(0, len(channels), 25)] or [[]]


class ChannelPickerView(View):
    """
    Paginated dropdown showing ALL text channels in the server.
    Works for both Announce and Create Event flows.
    """
    def __init__(self, guild: discord.Guild, purpose: str, page: int = 0):
        super().__init__(timeout=180)
        self.guild   = guild
        self.purpose = purpose   # "announce" or "event"
        self.page    = page
        self.pages   = _channel_pages(guild)

        page_channels = self.pages[page] if page < len(self.pages) else []
        opts = [
            discord.SelectOption(
                label=f"#{ch.name}"[:100], value=str(ch.id),
                description=(ch.topic[:80] if ch.topic else "Text channel")[:100])
            for ch in page_channels
        ]
        if opts:
            sel = Select(
                placeholder=f"📋 Pick a channel  (page {page+1}/{len(self.pages)})...",
                options=opts)
            sel.callback = self._picked
            self.add_item(sel)

        if page > 0:
            prev = Button(label="◀ Prev", style=discord.ButtonStyle.secondary)
            prev.callback = lambda i: self._turn(i, page - 1)
            self.add_item(prev)
        if page < len(self.pages) - 1:
            nxt = Button(label="Next ▶", style=discord.ButtonStyle.secondary)
            nxt.callback = lambda i: self._turn(i, page + 1)
            self.add_item(nxt)

    async def _turn(self, interaction: discord.Interaction, new_page: int):
        e = discord.Embed(
            title=("📢 Choose Channel" if self.purpose == "announce"
                   else "🎯 Choose Event Channel"),
            description=f"Page {new_page+1}/{len(self.pages)}",
            color=EMPIRE_GOLD)
        brand(e)
        await interaction.response.edit_message(
            embed=e, view=ChannelPickerView(self.guild, self.purpose, new_page))

    async def _picked(self, interaction: discord.Interaction):
        ch = interaction.guild.get_channel(int(interaction.data["values"][0]))
        if not ch:
            await interaction.response.send_message("❌ Channel not found.", ephemeral=True); return

        if self.purpose == "announce":
            e = discord.Embed(
                title="📢 Announcement — Step 2 of 3",
                description=f"✅ Channel: {ch.mention}\n\nPick a role to ping (or skip):",
                color=EMPIRE_GOLD)
            brand(e)
            await interaction.response.edit_message(embed=e, view=PingPickerView(ch))

        elif self.purpose == "event":
            await interaction.response.send_modal(EventModal(ch))


class PingPickerView(View):
    def __init__(self, target_channel: discord.TextChannel):
        super().__init__(timeout=180)
        self.target_channel = target_channel
        guild = target_channel.guild
        roles = [r for r in guild.roles if not r.is_default() and not r.managed][:23]
        opts  = (
            [discord.SelectOption(label="@everyone",      value="everyone", emoji="📣"),
             discord.SelectOption(label="No ping / skip", value="none",     emoji="🔇")]
            + [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles]
        )
        sel = Select(placeholder="🔔 Pick role to ping...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        val = interaction.data["values"][0]
        if val == "everyone":        ping_role = "everyone"
        elif val == "none":          ping_role = None
        else:
            r = interaction.guild.get_role(int(val))
            ping_role = r if r else None
        await interaction.response.send_modal(
            AnnouncementModal(self.target_channel, ping_role))


class AnnouncementModal(Modal, title="📢 Write Your Announcement"):
    ann_title = TextInput(label="Title", placeholder="Announcement title...",
                          required=True, max_length=200)
    ann_body  = TextInput(label="Message", placeholder="Your announcement text...",
                          required=True, max_length=2000,
                          style=discord.TextStyle.paragraph)
    ann_image = TextInput(label="Banner / Image URL (optional)",
                          placeholder="https://...",
                          required=False, max_length=500)

    def __init__(self, target_channel: discord.TextChannel, ping_role):
        super().__init__()
        self.target_channel = target_channel
        self.ping_role      = ping_role

    async def on_submit(self, interaction: discord.Interaction):
        e = discord.Embed(
            title=f"📢 {self.ann_title.value.strip()}",
            description=self.ann_body.value.strip(),
            color=EMPIRE_GOLD, timestamp=datetime.utcnow())
        img = self.ann_image.value.strip() if self.ann_image.value else ""
        if img.startswith("http"):
            e.set_image(url=img)
        e.set_footer(
            text=f"⚜ Oblivion Empire | {interaction.user.display_name}",
            icon_url=bot_avatar())
        brand(e, thumb=True)

        if self.ping_role == "everyone":              mention = "@everyone"
        elif isinstance(self.ping_role, discord.Role): mention = self.ping_role.mention
        else:                                          mention = None

        try:
            await self.target_channel.send(content=mention, embed=e)
            await interaction.response.send_message(
                embed=discord.Embed(title="✅ Published!",
                                    description=f"Posted in {self.target_channel.mention}",
                                    color=EMPIRE_GREEN), ephemeral=True)
            await log_action(interaction.guild, "📢 Announcement",
                f"{interaction.user.mention} → **{self.ann_title.value}** in {self.target_channel.mention}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to post there.", ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  MAIN PANELS
# ══════════════════════════════════════════════════════════════════════

class OblivionPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="My Profile",      emoji="⚜️", style=discord.ButtonStyle.primary,   row=0)
    async def my_profile(self, i: discord.Interaction, _: Button):
        await i.response.send_message(embed=build_profile_embed(i.user), ephemeral=True)

    @discord.ui.button(label="Setup Profile",   emoji="⚙️", style=discord.ButtonStyle.success,   row=0)
    async def setup_profile(self, i: discord.Interaction, _: Button):
        e = discord.Embed(title="⚙️ Profile Setup — Step 1 of 7",
                          description="Select your **main lane** in Honor of Kings:",
                          color=EMPIRE_PURPLE)
        brand(e)
        await i.response.send_message(embed=e, view=SetupLaneView(i.user.id), ephemeral=True)

    @discord.ui.button(label="Search Profile",  emoji="🔍", style=discord.ButtonStyle.secondary, row=0)
    async def search_profile(self, i: discord.Interaction, _: Button):
        await i.response.send_modal(SearchModal())

    @discord.ui.button(label="Leaderboards",    emoji="🏆", style=discord.ButtonStyle.primary,   row=1)
    async def leaderboards(self, i: discord.Interaction, _: Button):
        e = discord.Embed(title="📊 Leaderboards",
                          description="Which leaderboard do you want to see?",
                          color=EMPIRE_GOLD)
        brand(e)
        await i.response.send_message(embed=e, view=LeaderboardMenuView(i.guild), ephemeral=True)

    @discord.ui.button(label="Community Stats", emoji="📈", style=discord.ButtonStyle.secondary, row=1)
    async def community_stats(self, i: discord.Interaction, _: Button):
        all_m = [m for m in db["members"].values() if m.get("ign")]
        lane_c: dict[str, int] = {}
        rank_c: dict[str, int] = {}
        cls_c:  dict[str, int] = {}
        for m in all_m:
            if m.get("main_lane"):
                lane_c[m["main_lane"]] = lane_c.get(m["main_lane"], 0) + 1
            if m.get("current_rank"):
                main = m["current_rank"].split()[0]
                rank_c[main] = rank_c.get(main, 0) + 1
            if m.get("hero_class"):
                cls_c[m["hero_class"]] = cls_c.get(m["hero_class"], 0) + 1

        e = discord.Embed(title="📈 Community Stats", color=EMPIRE_CYAN)
        e.add_field(name="👥 Server",
                    value=f"**{len(i.guild.members)}** total · **{len(all_m)}** registered",
                    inline=False)
        if lane_c:
            e.add_field(name="🗺️ Lanes",
                value="\n".join(f"{HOK_LANE_EMOJIS.get(l,'🎮')} **{l}**: {c}"
                                for l, c in sorted(lane_c.items(), key=lambda x: -x[1])),
                inline=True)
        if rank_c:
            e.add_field(name="📊 Rank Tiers",
                value="\n".join(f"{HOK_RANK_EMOJIS.get(r,'🎮')} **{r}**: {c}"
                                for r, c in sorted(rank_c.items(),
                                                   key=lambda x: -HOK_RANK_ORDER.get(x[0], 0))),
                inline=True)
        if cls_c:
            e.add_field(name="🎯 Classes",
                value="\n".join(f"{HOK_CLASS_EMOJIS.get(c,'🎮')} **{c}**: {v}"
                                for c, v in sorted(cls_c.items(), key=lambda x: -x[1])),
                inline=True)
        brand(e)
        await i.response.send_message(embed=e, ephemeral=True)


class AdminPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    def _guard(self, i: discord.Interaction) -> bool:
        return is_admin(i.user)

    @discord.ui.button(label="Announce",      emoji="📢", style=discord.ButtonStyle.primary,   row=0)
    async def announce(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        e = discord.Embed(
            title="📢 Announcement — Step 1 of 3",
            description="**Pick the channel to post in:**\nEvery text channel in this server is listed.",
            color=EMPIRE_GOLD)
        brand(e)
        await i.response.send_message(embed=e, view=ChannelPickerView(i.guild, "announce"), ephemeral=True)
        await log_action(i.guild, "📢 Announce", f"{i.user.mention} opened the announcement tool")

    @discord.ui.button(label="Create Event",  emoji="🎯", style=discord.ButtonStyle.success,   row=0)
    async def create_event(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        e = discord.Embed(title="🎯 Create Event — Pick Channel",
                          description="Select which channel to post the event in:",
                          color=EMPIRE_CYAN)
        brand(e)
        await i.response.send_message(embed=e, view=ChannelPickerView(i.guild, "event"), ephemeral=True)

    @discord.ui.button(label="Manage Events", emoji="🗓️", style=discord.ButtonStyle.secondary, row=0)
    async def manage_events(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        if not db["events"]:
            await i.response.send_message(
                embed=discord.Embed(title="🗓️ No Events",
                                    description="No events yet.", color=EMPIRE_PURPLE), ephemeral=True); return
        e = discord.Embed(title="🗓️ Manage Events",
                          description="Select an event to delete:", color=EMPIRE_RED)
        brand(e)
        await i.response.send_message(embed=e, view=EventManagerView(), ephemeral=True)

    @discord.ui.button(label="Lookup Member", emoji="🔍", style=discord.ButtonStyle.primary,   row=1)
    async def lookup(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        await i.response.send_modal(SearchModal())

    @discord.ui.button(label="Backup Data",   emoji="💾", style=discord.ButtonStyle.secondary, row=1)
    async def backup(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        if not os.path.exists(DATA_FILE):
            await i.response.send_message("❌ No data file.", ephemeral=True); return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        await i.response.send_message(
            content="💾 **Oblivion Empire Data Backup**",
            file=discord.File(DATA_FILE, filename=f"oblivion_backup_{ts}.json"),
            ephemeral=True)
        await log_action(i.guild, "💾 Backup", f"{i.user.mention} downloaded backup")

    @discord.ui.button(label="Server Stats",  emoji="📊", style=discord.ButtonStyle.secondary, row=2)
    async def server_stats(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        reg = sum(1 for m in db["members"].values() if m.get("ign"))
        e = discord.Embed(title="📊 Admin — Server Stats", color=EMPIRE_PURPLE)
        e.add_field(name="👥 Members",  value=f"**{len(i.guild.members)}**", inline=True)
        e.add_field(name="📝 Profiles", value=f"**{reg}** complete",         inline=True)
        e.add_field(name="🎯 Events",   value=f"**{len(db['events'])}**",    inline=True)
        brand(e)
        await i.response.send_message(embed=e, ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════════════════════════════

@bot.tree.command(name="oblivion",
                  description="⚜ Open the Oblivion Empire community panel")
async def cmd_oblivion(interaction: discord.Interaction):
    md    = db["members"].get(str(interaction.user.id))
    extra = ""
    if md and md.get("current_rank"):
        le    = HOK_LANE_EMOJIS.get(md.get("main_lane", ""), "")
        extra = f"\n{format_rank(md['current_rank'], md.get('current_stars',0))} {le} {md.get('main_lane','')}"
    e = discord.Embed(
        title="⚜ Oblivion Empire",
        description=(f"*Welcome, **{interaction.user.display_name}**.*{extra}\n\n"
                     "*Rise through the ranks. Conquer the arena.*"),
        color=EMPIRE_GOLD)
    reg = sum(1 for m in db["members"].values() if m.get("ign"))
    e.add_field(name="🌐 Community",
                value=f"👥 {reg} warriors registered · 🎯 {len(db['events'])} events",
                inline=False)
    brand(e)
    await interaction.response.send_message(embed=e, view=OblivionPanelView())
    await log_action(interaction.guild, "🔹 /oblivion", f"{interaction.user.mention} opened community panel")


@bot.tree.command(name="admins",
                  description="🛡 Open the Oblivion Empire admin panel")
async def cmd_admins(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You don't have permission to access the admin panel.", ephemeral=True); return
    reg = sum(1 for m in db["members"].values() if m.get("ign"))
    e = discord.Embed(title="🛡 Admin Command Center",
                      description="*Full control panel — use your powers wisely.*",
                      color=EMPIRE_RED)
    e.add_field(name="📊 Overview",
                value=(f"👥 **{len(interaction.guild.members)}** members\n"
                       f"📝 **{reg}** complete profiles\n"
                       f"🎯 **{len(db['events'])}** events"), inline=False)
    brand(e)
    await interaction.response.send_message(embed=e, view=AdminPanelView(), ephemeral=True)
    await log_action(interaction.guild, "🔸 /admins", f"{interaction.user.mention} opened admin panel")


@bot.tree.command(name="games", description="🎮 Open the Oblivion Empire games panel")
async def cmd_games_placeholder(interaction: discord.Interaction):
    await interaction.response.send_message("❌ Games cog not loaded.", ephemeral=True)


@bot.tree.command(name="profile",
                  description="⚜ View any member's Oblivion Empire profile")
@app_commands.describe(member="The member to look up")
async def cmd_profile(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(embed=build_profile_embed(member))
    await log_action(interaction.guild, "👤 /profile",
                     f"{interaction.user.mention} viewed {member.mention}'s profile")


@bot.tree.command(name="help", description="📜 View all Oblivion Empire commands")
async def cmd_help(interaction: discord.Interaction):
    e = discord.Embed(title="📜 Oblivion Empire — Bot Guide",
                      description="*Honor of Kings Community Bot*",
                      color=EMPIRE_PURPLE)
    e.add_field(name="⚜ /oblivion", value=(
        "Community hub — open to everyone.\n"
        "• My Profile / Setup Profile / Search Profile\n"
        "• Leaderboards (overall · lane · class)\n"
        "• Community Stats"), inline=False)
    e.add_field(name="🛡 /admins", value=(
        "Admin panel — restricted to configured roles.\n"
        "• **Announce** — post to ANY channel + role ping\n"
        "• **Create Event** — post events with live RSVP to any channel\n"
        "• Manage Events · Lookup Member · Backup · Stats"), inline=False)
    e.add_field(name="🎮 /games", value=(
        "• **Guess the Hero** — image quiz (add images in games.py)\n"
        "• **Mafia** — social deduction game\n"
        "• **Game Scores** — all-time leaderboard"), inline=False)
    e.add_field(name="📌 Quick Commands", value=(
        "`/profile @member` — view any profile\n"
        "`/restore` — restore backup *(admin only)*"), inline=False)
    e.add_field(name="🎯 HoK Rank Ladder", value=(
        "🥉 Bronze I-III  →  🥈 Silver I-III  →  🥇 Gold I-IV\n"
        "→  💠 Platinum I-IV  →  💎 Diamond I-V  →  ⚡ Master I-V\n"
        "→  👑 Grandmaster (star ladder)\n"
        "  · 👑 King (0⭐)  · 🔮 Mythic (25⭐)\n"
        "  · 🌟 Epic (50⭐)  · 🏆 Legend (100⭐)"), inline=False)
    brand(e)
    await interaction.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(name="restore",
                  description="💾 Restore data from a backup file (Admin only)")
@app_commands.describe(backup="The .json backup file")
async def cmd_restore(interaction: discord.Interaction, backup: discord.Attachment):
    global db
    if not is_admin(interaction.user):
        await interaction.response.send_message("❌ Admin only.", ephemeral=True); return
    if not backup.filename.endswith(".json"):
        await interaction.response.send_message("❌ Attach a `.json` file.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    try:
        raw  = await backup.read()
        data = json.loads(raw.decode("utf-8"))
        for k, v in _blank_db().items():
            data.setdefault(k, v)
        save_db(data); db = data
        e = discord.Embed(title="✅ Restored",
                          description=(f"`{backup.filename}`\n"
                                       f"👥 {len(data['members'])} profiles · "
                                       f"🎯 {len(data['events'])} events"),
                          color=EMPIRE_GREEN)
        brand(e, thumb=False)
        await interaction.followup.send(embed=e, ephemeral=True)
        await log_action(interaction.guild, "💾 Restore",
                         f"{interaction.user.mention} restored `{backup.filename}`")
    except json.JSONDecodeError:
        await interaction.followup.send("❌ Invalid JSON.", ephemeral=True)
    except Exception as ex:
        await interaction.followup.send(f"❌ Error: {ex}", ephemeral=True)

# ─── BOT EVENTS ───────────────────────────────────────────────────────
@bot.event
async def on_ready():
    for ev_id in db["events"]:
        bot.add_view(EventRSVPView(ev_id))
    await bot.tree.sync()
    print(f"✅  {bot.user} online — Oblivion Empire Bot ready!")
    print(f"🛡  Admin role IDs: {ADMIN_ROLE_IDS or 'None set — add ADMIN_ROLE_IDS env var'}")
    print(f"💾  Data file: {DATA_FILE}")

# ─── ENTRY POINT ──────────────────────────────────────────────────────
async def main():
    async with bot:
        await bot.load_extension("games")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
