# ══════════════════════════════════════════════════════════════════════
#  bot.py  —  Oblivion Empire Bot  (Honor of Kings Community)
# ══════════════════════════════════════════════════════════════════════
#
#  HOW GUESS THE HERO WORKS (for clarity):
#    1. Bot randomly picks a hero name from its internal list in games.py
#    2. Bot already knows the answer — it picked it
#    3. Bot posts that hero's image (you supply the image URLs)
#    4. Players type the hero name in chat
#    5. Bot checks if the typed text matches the hero name it picked
#    No image recognition or AI needed — it's a quiz show format.
#
#  RAILWAY ENV VARIABLES TO SET:
#    DISCORD_TOKEN   — your bot token
#    ADMIN_ROLE_IDS  — comma-separated role IDs  e.g. "111222,333444"
#    DATA_DIR        — leave as /data  (Railway volume mount point)
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

# ─── COLOUR PALETTE ───────────────────────────────────────────────────
OBSIDIAN      = 0x0d0d1a
EMPIRE_GOLD   = 0xc9a227
EMPIRE_RED    = 0x8b1a1a
EMPIRE_PURPLE = 0x5c0099
EMPIRE_CYAN   = 0x00b4d8
EMPIRE_GREEN  = 0x2ecc71
EMPIRE_DARK   = 0x1a1a2e

# ══════════════════════════════════════════════════════════════════════
#  HONOR OF KINGS — ACCURATE GAME DATA
# ══════════════════════════════════════════════════════════════════════

# HoK rank ladder — in order from lowest to highest
# Each rank (except Mythic & Supreme) has sub-tiers I / II / III
HOK_MAIN_RANKS = [
    "Warrior",
    "Elite",
    "Master",
    "Grandmaster",
    "Epic",
    "Legend",
    "Mythic",
    "Supreme",        # top-tier Mythic players (points-based)
]

# Ranks that use sub-tiers (I / II / III)
HOK_TIERED_RANKS = {"Warrior", "Elite", "Master", "Grandmaster", "Epic", "Legend"}

# Ranks that use raw points instead of stars/tiers
HOK_POINT_RANKS  = {"Mythic", "Supreme"}

HOK_RANK_EMOJIS = {
    "Warrior":     "⚔️",
    "Elite":       "🛡️",
    "Master":      "⚡",
    "Grandmaster": "💫",
    "Epic":        "🔥",
    "Legend":      "👑",
    "Mythic":      "🔮",
    "Supreme":     "🌟",
}

# Used for leaderboard sorting (higher = better)
HOK_RANK_ORDER = {r: i for i, r in enumerate(HOK_MAIN_RANKS)}

# HoK lanes (HoK naming — NOT MLBB naming)
HOK_LANES = ["Baron Lane", "Jungle", "Mid Lane", "Dragon Lane", "Roam"]
HOK_LANE_EMOJIS = {
    "Baron Lane":  "🗡️",   # top lane / exp lane equivalent
    "Jungle":      "🌿",
    "Mid Lane":    "⚡",
    "Dragon Lane": "🐉",   # bot lane / gold lane equivalent
    "Roam":        "🌀",   # support / roamer
}

# HoK hero classes
HOK_CLASSES = ["Tank", "Fighter", "Assassin", "Mage", "Marksman", "Support"]
HOK_CLASS_EMOJIS = {
    "Tank":      "🛡️",
    "Fighter":   "⚔️",
    "Assassin":  "🗡️",
    "Mage":      "🔮",
    "Marksman":  "🏹",
    "Support":   "💚",
}

# ─── DATA LAYER ───────────────────────────────────────────────────────
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
        "current_rank":  "",   # e.g. "Epic III"
        "peak_rank":     "",   # e.g. "Legend I"
        "peak_points":   0,    # Mythic/Supreme point count
        "main_lane":     "",
        "hero_class":    "",
        "region":        "",
        "registered_at": now,
        "updated_at":    now,
    }


# Global in-memory db — also imported by games.py
db = load_db()

# ─── HELPERS ──────────────────────────────────────────────────────────
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


def format_rank(rank_str: str) -> str:
    """Return a display-friendly rank string with emoji."""
    if not rank_str:
        return "—"
    # Extract main rank name (first word or two)
    main = rank_str.split()[0] if rank_str else ""
    emoji = HOK_RANK_EMOJIS.get(main, "🎮")
    return f"{emoji} {rank_str}"


def rank_sort_key(md: dict) -> tuple[int, int]:
    """Sort by peak rank tier first, then peak points."""
    main = md.get("peak_rank", "").split()[0] if md.get("peak_rank") else ""
    return (HOK_RANK_ORDER.get(main, -1), md.get("peak_points", 0))

# ══════════════════════════════════════════════════════════════════════
#  PROFILE SETUP FLOW  (3 steps → Lane → Class → Modal)
# ══════════════════════════════════════════════════════════════════════

class SetupLaneView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        opts = [
            discord.SelectOption(
                label=lane, emoji=HOK_LANE_EMOJIS[lane],
                description=f"I main {lane}")
            for lane in HOK_LANES
        ]
        sel = Select(placeholder="🗺️ Choose your main lane...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your setup.", ephemeral=True)
            return
        lane     = interaction.data["values"][0]
        existing = db["members"].get(str(interaction.user.id))
        e = discord.Embed(
            title="⚙️ Profile Setup — Step 2 of 3",
            description=(f"✅ Lane: **{HOK_LANE_EMOJIS[lane]} {lane}**\n\n"
                         "Now pick your main **Hero Class**:"),
            color=EMPIRE_PURPLE,
        )
        brand(e)
        await interaction.response.edit_message(
            embed=e, view=SetupClassView(self.user_id, lane, existing))


class SetupClassView(View):
    def __init__(self, user_id: int, lane: str, existing: Optional[dict]):
        super().__init__(timeout=180)
        self.user_id  = user_id
        self.lane     = lane
        self.existing = existing
        opts = [
            discord.SelectOption(
                label=c, emoji=HOK_CLASS_EMOJIS[c],
                description=f"I play {c} heroes")
            for c in HOK_CLASSES
        ]
        sel = Select(placeholder="🎮 Choose your hero class...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your setup.", ephemeral=True)
            return
        cls = interaction.data["values"][0]
        await interaction.response.send_modal(
            ProfileModal(self.lane, cls, self.existing))


class ProfileModal(Modal, title="⚜ Profile Setup — Step 3 of 3"):
    ign = TextInput(
        label="In-Game Name (IGN)",
        placeholder="Your HoK username exactly as shown in-game",
        required=True, max_length=50)

    current_rank = TextInput(
        label="Current Rank  (e.g. Epic III, Legend I, Mythic)",
        placeholder="Main rank + tier  e.g.  Legend II   or   Mythic",
        required=True, max_length=30)

    peak_rank = TextInput(
        label="Peak Rank  (highest you have ever reached)",
        placeholder="e.g.  Legend III   or   Supreme",
        required=True, max_length=30)

    peak_points = TextInput(
        label="Peak Points  (Mythic / Supreme players only)",
        placeholder="Leave blank if you are below Mythic",
        required=False, max_length=10)

    region = TextInput(
        label="Region  (e.g. SEA, EU, NA, ME, East Asia)",
        placeholder="Your server region",
        required=False, max_length=20)

    def __init__(self, lane: str, cls: str, existing: Optional[dict]):
        super().__init__()
        self.lane     = lane
        self.cls      = cls
        if existing:
            if existing.get("ign"):           self.ign.default           = existing["ign"]
            if existing.get("current_rank"):  self.current_rank.default  = existing["current_rank"]
            if existing.get("peak_rank"):     self.peak_rank.default     = existing["peak_rank"]
            if existing.get("peak_points"):   self.peak_points.default   = str(existing["peak_points"])
            if existing.get("region"):        self.region.default        = existing["region"]

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        md  = db["members"].get(uid) or new_member(interaction.user.id)

        # Normalise rank: accept "epic 3", "epic iii", "epic III" → "Epic III"
        def clean_rank(raw: str) -> str:
            mapping = {"1": "I", "2": "II", "3": "III",
                       "i": "I", "ii": "II", "iii": "III"}
            parts = raw.strip().split()
            if len(parts) >= 2:
                main  = parts[0].capitalize()
                sub   = mapping.get(parts[-1].lower(), parts[-1].upper())
                return f"{main} {sub}"
            return raw.strip().capitalize()

        cr = clean_rank(self.current_rank.value)
        pr = clean_rank(self.peak_rank.value)
        pp = int(self.peak_points.value.strip()) if self.peak_points.value.strip().isdigit() else 0

        md.update({
            "ign":          self.ign.value.strip(),
            "current_rank": cr,
            "peak_rank":    pr,
            "peak_points":  pp,
            "main_lane":    self.lane,
            "hero_class":   self.cls,
            "region":       self.region.value.strip(),
            "updated_at":   datetime.utcnow().isoformat(),
        })
        db["members"][uid] = md
        save_db(db)

        pts_line = f" • **{pp} pts**" if pp else ""
        e = discord.Embed(title="✅ Profile Saved!", color=EMPIRE_GREEN,
                          description="Your Oblivion Empire warrior profile is live.")
        e.add_field(name="🎮 IGN",           value=md["ign"],                            inline=True)
        e.add_field(name="📊 Current Rank",  value=format_rank(cr),                      inline=True)
        e.add_field(name="🏆 Peak Rank",     value=format_rank(pr) + pts_line,           inline=True)
        e.add_field(name="🗺️ Lane",          value=f"{HOK_LANE_EMOJIS[self.lane]} {self.lane}", inline=True)
        e.add_field(name="🎯 Class",         value=f"{HOK_CLASS_EMOJIS[self.cls]} {self.cls}",  inline=True)
        brand(e, thumb=False)
        await interaction.response.send_message(embed=e, ephemeral=True)
        await log_action(interaction.guild, "📝 Profile Updated",
            f"{interaction.user.mention} — IGN: **{md['ign']}** | {cr} → Peak: {pr}")

# ══════════════════════════════════════════════════════════════════════
#  EMBED BUILDERS
# ══════════════════════════════════════════════════════════════════════

def build_profile_embed(member: discord.Member) -> discord.Embed:
    md = db["members"].get(str(member.id))
    if not md or not md.get("ign"):
        e = discord.Embed(
            title="⚜ Profile Not Found",
            description=(f"{member.mention} hasn't set up their profile yet.\n"
                         "Use `/oblivion` → **Setup Profile** to get started."),
            color=EMPIRE_PURPLE,
        )
        e.set_thumbnail(url=member.display_avatar.url)
        return e

    pts_line = f"  `{md['peak_points']} pts`" if md.get("peak_points") else ""
    le = HOK_LANE_EMOJIS.get(md.get("main_lane", ""), "🎮")
    ce = HOK_CLASS_EMOJIS.get(md.get("hero_class", ""), "🎮")

    e = discord.Embed(
        title=f"⚜ {md['ign']}",
        description=f"*{member.mention} — Oblivion Empire*",
        color=EMPIRE_GOLD,
    )
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="🎮 IGN",          value=md["ign"],                           inline=True)
    e.add_field(name="📊 Current Rank", value=format_rank(md.get("current_rank","—")), inline=True)
    e.add_field(name="🏆 Peak Rank",    value=format_rank(md.get("peak_rank","—")) + pts_line, inline=True)
    e.add_field(name=f"{le} Main Lane", value=md.get("main_lane","—"),             inline=True)
    e.add_field(name=f"{ce} Class",     value=md.get("hero_class","—"),            inline=True)
    e.add_field(name="🌐 Region",        value=md.get("region","—"),               inline=True)
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
        e.add_field(name="Empty", value="No profiles yet. Use `/oblivion` → Setup Profile!", inline=False)
        brand(e); return e
    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for i, md in enumerate(members_list[:15], 1):
        mem  = guild.get_member(md["discord_id"])
        name = mem.display_name if mem else f"ID:{md['discord_id']}"
        pr   = md.get("peak_rank", "?")
        pts  = f" `{md['peak_points']}pts`" if md.get("peak_points") else ""
        le   = HOK_LANE_EMOJIS.get(md.get("main_lane", ""), "")
        pos  = medals[i - 1] if i <= 3 else f"`{i}.`"
        lines.append(f"{pos} {le} **{name}** — {format_rank(pr)}{pts}")
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
                embed=discord.Embed(
                    title="🔍 No Results",
                    description=f"No member found for `{self.query.value}`.",
                    color=EMPIRE_RED), ephemeral=True)
            return
        if len(results) == 1:
            e = build_profile_embed(results[0])
            await interaction.response.send_message(embed=e, ephemeral=True)
        else:
            e = discord.Embed(title=f"🔍 {len(results)} Members Found",
                              description="Select the correct person:", color=EMPIRE_CYAN)
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
            await interaction.response.send_message("❌ Member not found.", ephemeral=True); return
        e = build_profile_embed(member)
        await interaction.response.edit_message(embed=e, view=None)

# ══════════════════════════════════════════════════════════════════════
#  LEADERBOARD MENU
# ══════════════════════════════════════════════════════════════════════

class LeaderboardMenuView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=120)
        self.guild = guild
        opts = [
            discord.SelectOption(label="Overall Peak Rank", value="overall",
                                 emoji="🏆", description="All players sorted by peak rank"),
        ] + [
            discord.SelectOption(label=f"{HOK_LANE_EMOJIS[l]} {l}", value=l,
                                 description=f"Top {l} mains")
            for l in HOK_LANES
        ] + [
            discord.SelectOption(label=f"{HOK_CLASS_EMOJIS[c]} {c}", value=c,
                                 description=f"Top {c} players")
            for c in HOK_CLASSES
        ]
        sel = Select(placeholder="📊 Choose a leaderboard...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        val = interaction.data["values"][0]
        all_members = [m for m in db["members"].values() if m.get("ign")]
        if val == "overall":
            data     = sorted(all_members, key=rank_sort_key, reverse=True)
            title    = "🏆 Oblivion Empire — Overall Rankings"
            subtitle = "Sorted by peak rank tier then peak points"
        elif val in HOK_LANES:
            data     = sorted(
                [m for m in all_members if m.get("main_lane") == val],
                key=rank_sort_key, reverse=True)
            title    = f"{HOK_LANE_EMOJIS[val]} {val} Rankings"
            subtitle = f"Top {val} mains by peak rank"
        else:  # class filter
            data     = sorted(
                [m for m in all_members if m.get("hero_class") == val],
                key=rank_sort_key, reverse=True)
            title    = f"{HOK_CLASS_EMOJIS[val]} {val} Rankings"
            subtitle = f"Top {val} players by peak rank"
        e = build_leaderboard_embed(data, self.guild, title, subtitle)
        await interaction.response.edit_message(embed=e, view=None)

# ══════════════════════════════════════════════════════════════════════
#  EVENT SYSTEM
# ══════════════════════════════════════════════════════════════════════

class EventRSVPView(View):
    """Persistent — survives bot restarts thanks to stable custom_ids."""
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
    ev_title  = TextInput(label="Event Title",
                          placeholder="e.g. Ranked Scrimmage Night",
                          required=True, max_length=150)
    ev_desc   = TextInput(label="Description",
                          placeholder="What is the event about?",
                          required=True, max_length=1500,
                          style=discord.TextStyle.paragraph)
    ev_date   = TextInput(label="Date & Time",
                          placeholder="e.g. June 20 • 8:00 PM UTC",
                          required=True, max_length=100)
    ev_image  = TextInput(label="Banner Image URL (optional)",
                          placeholder="https://...",
                          required=False, max_length=500)
    ev_ping   = TextInput(label="Role to ping (name or 'everyone', blank = none)",
                          placeholder="e.g.  Members   or   everyone",
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

        # Resolve ping
        ping = None
        pv   = (self.ev_ping.value or "").strip().lower()
        if pv == "everyone": ping = "@everyone"
        elif pv == "here":   ping = "@here"
        elif pv:
            r = discord.utils.get(interaction.guild.roles, name=self.ev_ping.value.strip())
            if r: ping = r.mention

        try:
            msg = await self.target_channel.send(
                content=ping, embed=build_event_embed(ev), view=EventRSVPView(ev_id))
            db["events"][ev_id]["message_id"] = msg.id
            db["events"][ev_id]["channel_id"] = self.target_channel.id
            save_db(db)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I can't post in that channel — check my permissions.", ephemeral=True)
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Event Created!",
                description=(f"**{ev['title']}** posted in {self.target_channel.mention}"),
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
            await interaction.response.edit_message(
                content="❌ Event not found.", embed=None, view=None)

# ══════════════════════════════════════════════════════════════════════
#  ANNOUNCEMENT SYSTEM  —  mods pick ANY channel in the server
# ══════════════════════════════════════════════════════════════════════

def _channel_pages(guild: discord.Guild) -> list[list[discord.TextChannel]]:
    """Split all text channels into pages of 25 for the dropdown."""
    channels = guild.text_channels  # every text channel
    pages    = []
    for i in range(0, len(channels), 25):
        pages.append(channels[i:i + 25])
    return pages or [[]]


class ChannelPickerView(View):
    """
    Shows ALL server text channels in a paginated dropdown.
    Mods pick any channel they want for announcements or events.
    """
    def __init__(self, guild: discord.Guild, purpose: str, page: int = 0):
        super().__init__(timeout=180)
        self.guild   = guild
        self.purpose = purpose   # "announce" or "event"
        self.page    = page
        self.pages   = _channel_pages(guild)

        current_page = self.pages[page] if page < len(self.pages) else []
        opts = [
            discord.SelectOption(
                label=f"#{ch.name}"[:100], value=str(ch.id),
                description=(ch.topic[:80] if ch.topic else "Text channel")[:100])
            for ch in current_page
        ]
        if opts:
            sel = Select(
                placeholder=f"📋 Pick channel  (page {page + 1}/{len(self.pages)})...",
                options=opts)
            sel.callback = self._picked
            self.add_item(sel)

        # Pagination buttons
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
            title="📢 Choose Channel" if self.purpose == "announce" else "🎯 Choose Event Channel",
            description=f"Page {new_page + 1}/{len(self.pages)}",
            color=EMPIRE_GOLD)
        brand(e)
        await interaction.response.edit_message(
            embed=e, view=ChannelPickerView(self.guild, self.purpose, new_page))

    async def _picked(self, interaction: discord.Interaction):
        ch_id = int(interaction.data["values"][0])
        ch    = interaction.guild.get_channel(ch_id)
        if not ch:
            await interaction.response.send_message("❌ Channel not found.", ephemeral=True); return

        if self.purpose == "announce":
            # Step 2: pick role to ping
            e = discord.Embed(
                title="📢 Announcement — Step 2 of 3",
                description=f"✅ Channel: {ch.mention}\n\nNow pick a role to ping (or skip):",
                color=EMPIRE_GOLD)
            brand(e)
            await interaction.response.edit_message(
                embed=e, view=PingPickerView(ch))

        elif self.purpose == "event":
            await interaction.response.send_modal(EventModal(ch))


class PingPickerView(View):
    """Step 2 of announcement — pick role to ping."""
    def __init__(self, target_channel: discord.TextChannel):
        super().__init__(timeout=180)
        self.target_channel = target_channel
        guild = target_channel.guild
        roles = [r for r in guild.roles if not r.is_default() and not r.managed][:23]
        opts  = [
            discord.SelectOption(label="@everyone", value="everyone", emoji="📣"),
            discord.SelectOption(label="No ping / skip", value="none", emoji="🔇"),
        ] + [
            discord.SelectOption(label=r.name[:100], value=str(r.id))
            for r in roles
        ]
        sel = Select(placeholder="🔔 Pick a role to ping...", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction):
        val = interaction.data["values"][0]
        if val == "everyone":
            ping_role = "everyone"
        elif val == "none":
            ping_role = None
        else:
            r = interaction.guild.get_role(int(val))
            ping_role = r if r else None
        await interaction.response.send_modal(
            AnnouncementModal(self.target_channel, ping_role))


class AnnouncementModal(Modal, title="📢 Write Your Announcement"):
    ann_title = TextInput(label="Title",
                          placeholder="Announcement title...",
                          required=True, max_length=200)
    ann_body  = TextInput(label="Message",
                          placeholder="Your announcement text...",
                          required=True, max_length=2000,
                          style=discord.TextStyle.paragraph)
    ann_image = TextInput(label="Banner / Image URL (optional)",
                          placeholder="https://...",
                          required=False, max_length=500)

    def __init__(self, target_channel: discord.TextChannel,
                 ping_role):   # str "everyone" | discord.Role | None
        super().__init__()
        self.target_channel = target_channel
        self.ping_role      = ping_role

    async def on_submit(self, interaction: discord.Interaction):
        e = discord.Embed(
            title=f"📢 {self.ann_title.value.strip()}",
            description=self.ann_body.value.strip(),
            color=EMPIRE_GOLD,
            timestamp=datetime.utcnow(),
        )
        img = self.ann_image.value.strip() if self.ann_image.value else ""
        if img.startswith("http"):
            e.set_image(url=img)
        e.set_footer(
            text=f"⚜ Oblivion Empire | {interaction.user.display_name}",
            icon_url=bot_avatar())
        brand(e, thumb=True)

        if self.ping_role == "everyone":
            mention = "@everyone"
        elif isinstance(self.ping_role, discord.Role):
            mention = self.ping_role.mention
        else:
            mention = None

        try:
            await self.target_channel.send(content=mention, embed=e)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Announcement Published!",
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
        existing = db["members"].get(str(i.user.id))
        e = discord.Embed(title="⚙️ Profile Setup — Step 1 of 3",
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
                          description="Choose which leaderboard to view:",
                          color=EMPIRE_GOLD)
        brand(e)
        await i.response.send_message(embed=e, view=LeaderboardMenuView(i.guild), ephemeral=True)

    @discord.ui.button(label="Community Stats", emoji="📈", style=discord.ButtonStyle.secondary, row=1)
    async def community_stats(self, i: discord.Interaction, _: Button):
        all_m  = [m for m in db["members"].values() if m.get("ign")]
        lane_c = {}; rank_c = {}; cls_c = {}
        for m in all_m:
            if m.get("main_lane"):    lane_c[m["main_lane"]]    = lane_c.get(m["main_lane"], 0)    + 1
            if m.get("current_rank"):
                main = m["current_rank"].split()[0]
                rank_c[main] = rank_c.get(main, 0) + 1
            if m.get("hero_class"):   cls_c[m["hero_class"]]    = cls_c.get(m["hero_class"], 0)    + 1
        e = discord.Embed(title="📈 Community Stats", color=EMPIRE_CYAN)
        e.add_field(name="👥 Server",
                    value=f"**{len(i.guild.members)}** total • **{len(all_m)}** registered",
                    inline=False)
        if lane_c:
            e.add_field(name="🗺️ Lanes",
                value="\n".join(f"{HOK_LANE_EMOJIS.get(l,'🎮')} **{l}**: {c}"
                                for l, c in sorted(lane_c.items(), key=lambda x: -x[1])),
                inline=True)
        if rank_c:
            e.add_field(name="📊 Rank Distribution",
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

    @discord.ui.button(label="Announce",       emoji="📢", style=discord.ButtonStyle.primary,   row=0)
    async def announce(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        e = discord.Embed(title="📢 Announcement — Step 1 of 3",
                          description="**Pick the channel to post in:**\nAll your server channels are listed.",
                          color=EMPIRE_GOLD)
        brand(e)
        await i.response.send_message(embed=e,
            view=ChannelPickerView(i.guild, "announce"), ephemeral=True)
        await log_action(i.guild, "📢 Announce",
            f"{i.user.mention} opened the announcement tool")

    @discord.ui.button(label="Create Event",   emoji="🎯", style=discord.ButtonStyle.success,   row=0)
    async def create_event(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        e = discord.Embed(title="🎯 Create Event — Pick Channel",
                          description="Select which channel to post the event in:",
                          color=EMPIRE_CYAN)
        brand(e)
        await i.response.send_message(embed=e,
            view=ChannelPickerView(i.guild, "event"), ephemeral=True)

    @discord.ui.button(label="Manage Events",  emoji="🗓️", style=discord.ButtonStyle.secondary, row=0)
    async def manage_events(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        if not db["events"]:
            await i.response.send_message(
                embed=discord.Embed(title="🗓️ No Events",
                                    description="No events created yet.",
                                    color=EMPIRE_PURPLE), ephemeral=True); return
        e = discord.Embed(title="🗓️ Manage Events",
                          description="Select an event to delete:", color=EMPIRE_RED)
        brand(e)
        await i.response.send_message(embed=e, view=EventManagerView(), ephemeral=True)

    @discord.ui.button(label="Lookup Member",  emoji="🔍", style=discord.ButtonStyle.primary,   row=1)
    async def lookup(self, i: discord.Interaction, _: Button):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        await i.response.send_modal(SearchModal())

    @discord.ui.button(label="Backup Data",    emoji="💾", style=discord.ButtonStyle.secondary, row=1)
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

    @discord.ui.button(label="Server Stats",   emoji="📊", style=discord.ButtonStyle.secondary, row=2)
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
        extra = f"\n{format_rank(md['current_rank'])} {le} {md.get('main_lane','')}"
    e = discord.Embed(
        title="⚜ Oblivion Empire",
        description=(f"*Welcome, **{interaction.user.display_name}**.*{extra}\n\n"
                     "*Rise through the ranks. Conquer the arena.*"),
        color=EMPIRE_GOLD,
    )
    reg = sum(1 for m in db["members"].values() if m.get("ign"))
    e.add_field(name="🌐 Community",
                value=f"👥 {reg} warriors registered • 🎯 {len(db['events'])} events",
                inline=False)
    brand(e)
    await interaction.response.send_message(embed=e, view=OblivionPanelView())
    await log_action(interaction.guild, "🔹 /oblivion",
                     f"{interaction.user.mention} opened community panel")


@bot.tree.command(name="admins",
                  description="🛡 Open the Oblivion Empire admin panel")
async def cmd_admins(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        await interaction.response.send_message(
            "❌ You don't have permission to access the admin panel.", ephemeral=True); return
    reg = sum(1 for m in db["members"].values() if m.get("ign"))
    e = discord.Embed(
        title="🛡 Admin Command Center",
        description="*Full control panel — use your powers wisely.*",
        color=EMPIRE_RED,
    )
    e.add_field(name="📊 Overview",
                value=(f"👥 **{len(interaction.guild.members)}** server members\n"
                       f"📝 **{reg}** complete profiles\n"
                       f"🎯 **{len(db['events'])}** events"), inline=False)
    brand(e)
    await interaction.response.send_message(embed=e, view=AdminPanelView(), ephemeral=True)
    await log_action(interaction.guild, "🔸 /admins",
                     f"{interaction.user.mention} opened admin panel")


@bot.tree.command(name="games",
                  description="🎮 Open the Oblivion Empire games panel")
async def cmd_games_placeholder(interaction: discord.Interaction):
    await interaction.response.send_message("❌ Games cog not loaded.", ephemeral=True)


@bot.tree.command(name="profile",
                  description="⚜ View any member's Oblivion Empire profile")
@app_commands.describe(member="The member to look up")
async def cmd_profile(interaction: discord.Interaction, member: discord.Member):
    e = build_profile_embed(member)
    await interaction.response.send_message(embed=e)
    await log_action(interaction.guild, "👤 /profile",
                     f"{interaction.user.mention} viewed {member.mention}'s profile")


@bot.tree.command(name="help",
                  description="📜 View all Oblivion Empire bot commands")
async def cmd_help(interaction: discord.Interaction):
    e = discord.Embed(title="📜 Oblivion Empire — Bot Guide",
                      description="*Honor of Kings Community Bot*",
                      color=EMPIRE_PURPLE)
    e.add_field(name="⚜ /oblivion", value=(
        "Community hub — open to everyone.\n"
        "• My Profile / Setup Profile / Search Profile\n"
        "• Leaderboards (overall + lane + class)\n"
        "• Community Stats"), inline=False)
    e.add_field(name="🛡 /admins", value=(
        "Admin panel — restricted to configured roles.\n"
        "• **Announce** — post to ANY channel with role ping\n"
        "• **Create Event** — post events with RSVP to any channel\n"
        "• Manage Events / Lookup Member / Backup / Stats"), inline=False)
    e.add_field(name="🎮 /games", value=(
        "• **Guess the Hero** — image quiz (you add the images)\n"
        "• **Mafia** — social deduction game\n"
        "• **Game Scores** — all-time leaderboard"), inline=False)
    e.add_field(name="📌 Quick", value=(
        "`/profile @member` — view any profile\n"
        "`/restore` — restore backup *(admin only)*"), inline=False)
    e.add_field(name="🎯 HoK Ranks (low → high)", value=(
        "⚔️ Warrior → 🛡️ Elite → ⚡ Master → 💫 Grandmaster\n"
        "→ 🔥 Epic → 👑 Legend → 🔮 Mythic → 🌟 Supreme\n"
        "Each rank below Mythic has tiers I / II / III"), inline=False)
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
                                       f"👥 {len(data['members'])} profiles "
                                       f"| 🎯 {len(data['events'])} events"),
                          color=EMPIRE_GREEN)
        brand(e, thumb=False)
        await interaction.followup.send(embed=e, ephemeral=True)
        await log_action(interaction.guild, "💾 Restore",
                         f"{interaction.user.mention} restored `{backup.filename}`")
    except json.JSONDecodeError:
        await interaction.followup.send("❌ Invalid JSON file.", ephemeral=True)
    except Exception as ex:
        await interaction.followup.send(f"❌ Error: {ex}", ephemeral=True)

# ─── BOT EVENTS ───────────────────────────────────────────────────────
@bot.event
async def on_ready():
    for ev_id in db["events"]:
        bot.add_view(EventRSVPView(ev_id))
    await bot.tree.sync()
    print(f"✅  {bot.user} online — Oblivion Empire Bot ready!")
    print(f"🛡  Admin role IDs: {ADMIN_ROLE_IDS or 'none set — add ADMIN_ROLE_IDS env var'}")
    print(f"💾  Data file: {DATA_FILE}")

# ─── ENTRY POINT ──────────────────────────────────────────────────────
async def main():
    async with bot:
        await bot.load_extension("games")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
