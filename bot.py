# ══════════════════════════════════════════════════════════════════════
#  bot.py  —  Oblivion Empire Discord Bot
#  Honor of Kings Community
# ══════════════════════════════════════════════════════════════════════
#
#  RAILWAY ENV VARIABLES:
#    DISCORD_TOKEN   — your bot token
#    ADMIN_ROLE_IDS  — comma-separated role IDs  e.g. "111,222"
#    DATA_DIR        — /data  (Railway persistent volume)
#  SERVER LOGO:
#    Just add  logo.png  to the root of your GitHub repo and push.
#    Railway already knows which repo it is — no configuration needed.
#
#  HOW TO ADD HERO IMAGES:
#    /set_hero_image → pick hero → attach image file
#    Multiple images per hero are supported.
#    /remove_hero_image to delete one.
#    /hero_images to see status of all heroes.
#
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
from discord import app_commands
import os, json, asyncio, uuid, aiohttp
from datetime import datetime
from typing import Optional

# ─── INTENTS ──────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members        = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── ENV ──────────────────────────────────────────────────────────────
ADMIN_ROLE_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_ROLE_IDS", "").split(",") if x.strip().isdigit()
]
DATA_DIR        = os.getenv("DATA_DIR", "/data")
DATA_FILE       = os.path.join(DATA_DIR, "oblivion_data.json")
HERO_IMAGES_DIR = os.path.join(DATA_DIR, "hero_images")
os.makedirs(DATA_DIR,        exist_ok=True)
os.makedirs(HERO_IMAGES_DIR, exist_ok=True)

# ─── SERVER LOGO ──────────────────────────────────────────────────────
# Just add  logo.png  to the root of your GitHub repo and push.
# Railway automatically provides the repo details — nothing else needed.
_GH_OWNER  = os.getenv("RAILWAY_GIT_REPO_OWNER", "")
_GH_REPO   = os.getenv("RAILWAY_GIT_REPO_NAME",  "")
_GH_BRANCH = os.getenv("RAILWAY_GIT_BRANCH",     "main")

_LOGO_URL = (
    f"https://raw.githubusercontent.com/{_GH_OWNER}/{_GH_REPO}/{_GH_BRANCH}/logo.png"
    if _GH_OWNER and _GH_REPO else ""
)

LOG_CHANNEL_NAME = "oblivion-logs"

# ══════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE  —  Dark Empire × Honor of Kings
# ══════════════════════════════════════════════════════════════════════
OBSIDIAN      = 0x0a0a0f   # near-black for dark backgrounds
GOLD          = 0xd4a017   # deep empire gold
CRIMSON       = 0x7b0d0d   # deep red for danger/admins
VIOLET        = 0x4a0080   # royal purple for special actions
TEAL          = 0x0d7a7a   # teal accent for info/events
EMERALD       = 0x0d6b3b   # green for success
STEEL         = 0x2c2f3a   # dark steel for neutral embeds
AMBER         = 0xb8860b   # amber for warnings/games
DEEP_BLUE     = 0x0d1b4a   # deep blue for community stats
PHANTOM       = 0x1a0a2e   # deep violet for mafia/night

# ══════════════════════════════════════════════════════════════════════
#  HOK RANK SYSTEM
# ══════════════════════════════════════════════════════════════════════
HOK_MAIN_RANKS = [
    "Bronze","Silver","Gold","Platinum","Diamond","Master","Grandmaster"
]
HOK_RANK_ORDER = {r: i for i, r in enumerate(HOK_MAIN_RANKS)}
HOK_SUBTIERS: dict[str, list[str]] = {
    "Bronze": ["I","II","III"], "Silver": ["I","II","III"],
    "Gold": ["I","II","III","IV"], "Platinum": ["I","II","III","IV"],
    "Diamond": ["I","II","III","IV","V"], "Master": ["I","II","III","IV","V"],
    "Grandmaster": [],
}
HOK_RANK_EMOJIS = {
    "Bronze":"🥉","Silver":"🥈","Gold":"🥇",
    "Platinum":"💠","Diamond":"💎","Master":"⚡","Grandmaster":"👑",
}
HOK_GM_MILESTONES = [
    (100,"Legend","🏆"),(50,"Epic","🌟"),(25,"Mythic","🔮"),(0,"King","👑"),
]
HOK_LANES = ["Clash Lane","Jungle","Mid Lane","Farm Lane","Roaming"]
HOK_LANE_EMOJIS = {
    "Clash Lane":"⚔️","Jungle":"🌿","Mid Lane":"⚡","Farm Lane":"🌾","Roaming":"🌀",
}
HOK_CLASSES = ["Tank","Fighter","Assassin","Mage","Marksman","Support"]
HOK_CLASS_EMOJIS = {
    "Tank":"🛡️","Fighter":"⚔️","Assassin":"🗡️","Mage":"🔮","Marksman":"🏹","Support":"💚",
}

def gm_milestone(stars: int) -> tuple[str,str]:
    for min_s,name,emoji in HOK_GM_MILESTONES:
        if stars >= min_s: return name,emoji
    return "King","👑"

def format_rank(rank_str: str, stars: int = 0) -> str:
    if not rank_str: return "—"
    main  = rank_str.split()[0]
    emoji = HOK_RANK_EMOJIS.get(main,"🎮")
    if main == "Grandmaster":
        ms_name,ms_emoji = gm_milestone(stars)
        return f"{emoji} Grandmaster · {ms_emoji} {ms_name} ({stars}⭐)"
    return f"{emoji} {rank_str}"

def sub_tier_index(sub: str) -> int:
    order = ["I","II","III","IV","V"]
    return order.index(sub) if sub in order else 0

def rank_sort_key(md: dict) -> tuple[int,int]:
    """Sort by current rank tier first, then peak_points as tiebreaker."""
    cur  = md.get("current_rank","")
    main = cur.split()[0] if cur else ""
    tier = HOK_RANK_ORDER.get(main, -1)
    if main == "Grandmaster":
        return (tier, md.get("current_stars", 0))
    sub = cur.split()[-1] if " " in cur else "I"
    return (tier, sub_tier_index(sub))

# ══════════════════════════════════════════════════════════════════════
#  DATA LAYER
# ══════════════════════════════════════════════════════════════════════
def _blank_db() -> dict:
    return {
        "members":     {},
        "events":      {},
        "game_scores": {},
        "hero_images": {},
        "config":      {"admin_role_ids": ADMIN_ROLE_IDS},
        # legacy migration: peak_rank/peak_stars are no longer used — peak_points only
    }

def load_db() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE,"r",encoding="utf-8") as f:
            data = json.load(f)
        for k,v in _blank_db().items():
            data.setdefault(k,v)
        for hero,val in data.get("hero_images",{}).items():
            if isinstance(val,str):
                data["hero_images"][hero] = [val] if val else []
        return data
    fresh = _blank_db()
    save_db(fresh)
    return fresh

def save_db(data: dict) -> None:
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)

def new_member(discord_id: int) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "discord_id":discord_id,"ign":"",
        "current_rank":"","current_stars":0,
        "peak_points":0,
        "main_lane":"","hero_class":"","region":"",
        "registered_at":now,"updated_at":now,
    }

db = load_db()

# ══════════════════════════════════════════════════════════════════════
#  BRANDING HELPERS
# ══════════════════════════════════════════════════════════════════════
def logo_url() -> str:
    """Logo from GitHub repo if configured, else bot avatar."""
    if _LOGO_URL:
        return _LOGO_URL
    return bot.user.display_avatar.url if bot.user else ""

def bot_avatar() -> Optional[str]:
    return bot.user.display_avatar.url if bot.user else None

def brand(embed: discord.Embed, thumb: bool = True) -> discord.Embed:
    """Apply Oblivion Empire branding — logo thumbnail + styled footer."""
    av = logo_url()
    if av and thumb:
        embed.set_thumbnail(url=av)
    # Footer with server name + logo icon
    embed.set_footer(
        text="⚜  Oblivion Empire",
        icon_url=av if av else discord.utils.MISSING,
    )
    return embed

def empire_embed(
    title: str,
    description: str = "",
    color: int = GOLD,
    thumb: bool = True,
) -> discord.Embed:
    """Shortcut: create a pre-branded embed."""
    e = discord.Embed(title=title, description=description, color=color)
    brand(e, thumb=thumb)
    return e

# Decorative separators used in embed descriptions
SEP  = "━━━━━━━━━━━━━━━━━━━━━━━"
SEP2 = "▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸▸"

async def log_action(guild: discord.Guild, title: str, desc: str) -> None:
    ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if not ch: return
    e = discord.Embed(
        title=f"📋 {title}", description=desc,
        color=STEEL, timestamp=datetime.utcnow(),
    )
    e.set_footer(text="Oblivion Empire • Logs", icon_url=logo_url() or discord.utils.MISSING)
    try: await ch.send(embed=e)
    except Exception: pass

def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator: return True
    admin_ids = set(db["config"].get("admin_role_ids", ADMIN_ROLE_IDS))
    return any(r.id in admin_ids for r in member.roles)

def fuzzy_search(guild: discord.Guild, query: str) -> list[discord.Member]:
    q = query.strip()
    if q.isdigit():
        m = guild.get_member(int(q)); return [m] if m else []
    if q.startswith("<@") and q.endswith(">"):
        try:
            m = guild.get_member(int(q.strip("<@!>"))); return [m] if m else []
        except Exception: pass
    ql = q.lower()
    return [m for m in guild.members if not m.bot and (
        ql in m.display_name.lower() or ql in m.name.lower()
        or (m.global_name and ql in m.global_name.lower()))][:25]

# Shared hero name list — populated by games.py after cog loads
# autocomplete reads from this but we also read HOK_HEROES directly as backup
_all_hero_names: list[str] = []

# ══════════════════════════════════════════════════════════════════════
#  PROFILE SETUP  (7-step dropdown flow)
# ══════════════════════════════════════════════════════════════════════

def _step_embed(step: int, total: int, prev_choices: list[str] = None, prompt: str = "") -> discord.Embed:
    checks = "\n".join(f"✅ {c}" for c in (prev_choices or []))
    desc   = (checks + "\n\n" if checks else "") + prompt
    e = discord.Embed(
        title=f"⚙️  Profile Setup  —  Step {step} of {total}",
        description=desc, color=VIOLET,
    )
    brand(e)
    return e

class SetupLaneView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        opts = [discord.SelectOption(label=l, emoji=HOK_LANE_EMOJIS[l], description=f"I play {l}") for l in HOK_LANES]
        sel = Select(placeholder="🗺️  Choose your main lane…", options=opts)
        sel.callback = self._picked; self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ Not your setup.", ephemeral=True); return
        lane = i.data["values"][0]
        existing = db["members"].get(str(i.user.id))
        await i.response.edit_message(
            embed=_step_embed(2,7,[f"Lane: {HOK_LANE_EMOJIS[lane]} {lane}"],"Pick your **hero class**:"),
            view=SetupClassView(self.user_id, lane, existing))

class SetupClassView(View):
    def __init__(self, user_id, lane, existing):
        super().__init__(timeout=180)
        self.user_id, self.lane, self.existing = user_id, lane, existing
        opts = [discord.SelectOption(label=c, emoji=HOK_CLASS_EMOJIS[c]) for c in HOK_CLASSES]
        sel = Select(placeholder="🎮  Choose your hero class…", options=opts)
        sel.callback = self._picked; self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ Not your setup.", ephemeral=True); return
        cls = i.data["values"][0]
        prev = [f"Lane: {HOK_LANE_EMOJIS[self.lane]} {self.lane}", f"Class: {HOK_CLASS_EMOJIS[cls]} {cls}"]
        await i.response.edit_message(
            embed=_step_embed(3,7,prev,"Select your **current rank tier**:"),
            view=RankTierView(self.user_id, self.lane, cls, self.existing, "current", progress=3))

class RankTierView(View):
    def __init__(self, user_id, lane, cls, existing, purpose, current_rank="", current_stars=0, progress=3):
        super().__init__(timeout=180)
        self.user_id, self.lane, self.cls, self.existing = user_id, lane, cls, existing
        self.purpose, self.current_rank, self.current_stars, self.progress = purpose, current_rank, current_stars, progress
        label = "current rank" if purpose=="current" else "peak / highest rank"
        opts = []
        for tier in HOK_MAIN_RANKS:
            subs = HOK_SUBTIERS[tier]
            desc = (f"Sub-tiers I–{subs[-1]}" if subs else "Star-count ladder")
            opts.append(discord.SelectOption(label=tier, emoji=HOK_RANK_EMOJIS[tier], description=desc))
        sel = Select(placeholder=f"📊  Step {progress} — Select your {label} tier…", options=opts)
        sel.callback = self._picked; self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ Not your setup.", ephemeral=True); return
        tier = i.data["values"][0]
        if tier == "Grandmaster":
            # Peak rank is now just a points number — send straight to final modal
            await i.response.send_modal(
                ProfileFinalModal(self.lane, self.cls, "Grandmaster", 0, self.existing))
        else:
            next_step = self.progress + 1
            label_type = "current" if self.purpose=="current" else "peak"
            await i.response.edit_message(
                embed=_step_embed(next_step,7,[f"{label_type.capitalize()} tier: {HOK_RANK_EMOJIS[tier]} {tier}"],
                                  f"Pick your **{tier} sub-tier**:"),
                view=RankSubTierView(self.user_id, self.lane, self.cls, self.existing,
                                     self.purpose, tier, self.current_rank, self.current_stars, next_step))

class RankSubTierView(View):
    def __init__(self, user_id, lane, cls, existing, purpose, tier, current_rank="", current_stars=0, progress=4):
        super().__init__(timeout=180)
        self.user_id, self.lane, self.cls, self.existing = user_id, lane, cls, existing
        self.purpose, self.tier, self.current_rank, self.current_stars, self.progress = purpose, tier, current_rank, current_stars, progress
        opts = [discord.SelectOption(label=f"{tier} {sub}", value=sub, emoji=HOK_RANK_EMOJIS[tier])
                for sub in HOK_SUBTIERS[tier]]
        label = "current" if purpose=="current" else "peak"
        sel = Select(placeholder=f"📊  Step {progress} — Select {label} sub-tier…", options=opts)
        sel.callback = self._picked; self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ Not your setup.", ephemeral=True); return
        sub  = i.data["values"][0]
        rank = f"{self.tier} {sub}"
        # Peak rank is now just a points number — no tier dropdown needed
        # Send straight to final modal once current rank sub-tier is picked
        await i.response.send_modal(
            ProfileFinalModal(self.lane, self.cls, rank, self.current_stars, self.existing))

class ProfileFinalModal(Modal):
    """
    Final step — IGN, GM stars (if Grandmaster), Peak Points, Region.

    Peak Points = a raw number that lives independently of rank tier.
    It is NOT a rank — it's just however many points the player has reached
    at their peak (e.g. 109 or 1500). Stored in md["peak_points"].
    """
    def __init__(self, lane: str, cls: str, curr_rank: str,
                 curr_stars_pre: int, existing: Optional[dict]):
        super().__init__(title="⚜  Profile — Final Step")
        self.lane, self.cls, self.curr_rank = lane, cls, curr_rank

        self._ign = TextInput(label="In-Game Name (IGN)",
                              placeholder="Your HoK username exactly as shown in-game",
                              required=True, max_length=50,
                              default=existing.get("ign", "") if existing else "")
        self.add_item(self._ign)

        # Only ask for GM stars when current rank is Grandmaster
        self._curr_stars: Optional[TextInput] = None
        if curr_rank == "Grandmaster":
            self._curr_stars = TextInput(
                label="Grandmaster star count",
                placeholder="0–24 = King · 25–49 = Mythic · 50–99 = Epic · 100+ = Legend",
                required=True, max_length=5,
                default=str(curr_stars_pre) if curr_stars_pre else "")
            self.add_item(self._curr_stars)

        # Peak points — always shown, always just a number
        self._peak_points = TextInput(
            label="Peak Points",
            placeholder="Your highest points ever reached  (e.g. 109 or 1500)",
            required=False, max_length=6,
            default=str(existing.get("peak_points", "")) if existing and existing.get("peak_points") else "")
        self.add_item(self._peak_points)

        self._region = TextInput(label="Region (optional)",
                                  placeholder="e.g. SEA, EU, NA, ME, East Asia",
                                  required=False, max_length=20,
                                  default=existing.get("region", "") if existing else "")
        self.add_item(self._region)

    async def on_submit(self, i: discord.Interaction):
        uid = str(i.user.id)
        md  = db["members"].get(uid) or new_member(i.user.id)

        def to_int(ti: Optional[TextInput]) -> int:
            if ti is None: return 0
            v = (ti.value or "").strip()
            return int(v) if v.isdigit() else 0

        curr_stars  = to_int(self._curr_stars)
        peak_points = to_int(self._peak_points)

        md.update({
            "ign":           self._ign.value.strip(),
            "current_rank":  self.curr_rank,
            "current_stars": curr_stars,
            "peak_points":   peak_points,
            "main_lane":     self.lane,
            "hero_class":    self.cls,
            "region":        self._region.value.strip(),
            "updated_at":    datetime.utcnow().isoformat(),
        })
        # Clean out old schema fields if present
        md.pop("peak_rank",  None)
        md.pop("peak_stars", None)
        db["members"][uid] = md; save_db(db)

        le, ce = HOK_LANE_EMOJIS.get(self.lane, "🎮"), HOK_CLASS_EMOJIS.get(self.cls, "🎮")
        peak_str = f"`{peak_points:,} pts`" if peak_points else "—"
        e = discord.Embed(
            title="✅  Profile Saved!",
            description=f"{SEP}\n**{md['ign']}** — your warrior profile is live.\n{SEP}",
            color=EMERALD)
        e.add_field(name="🎮 IGN",         value=f"`{md['ign']}`",                        inline=True)
        e.add_field(name=f"{le} Lane",     value=self.lane,                               inline=True)
        e.add_field(name=f"{ce} Class",    value=self.cls,                                inline=True)
        e.add_field(name="📊 Current Rank",value=format_rank(self.curr_rank, curr_stars), inline=True)
        e.add_field(name="🏆 Peak Points", value=peak_str,                                inline=True)
        if md.get("region"): e.add_field(name="🌐 Region", value=md["region"],            inline=True)
        brand(e, thumb=False)
        await i.response.send_message(embed=e, ephemeral=True)
        await log_action(i.guild, "📝 Profile Updated",
            f"{i.user.mention} — **{md['ign']}** | "
            f"{format_rank(self.curr_rank, curr_stars)} | Peak: {peak_str}")

# ══════════════════════════════════════════════════════════════════════
#  EMBED BUILDERS
# ══════════════════════════════════════════════════════════════════════

def build_profile_embed(member: discord.Member) -> discord.Embed:
    md = db["members"].get(str(member.id))
    if not md or not md.get("ign"):
        e = discord.Embed(
            title="🔍  Warrior Not Found",
            description=(
                f"{SEP}\n"
                f"{member.mention} hasn't set up their profile yet.\n\n"
                "Use `/oblivion` → **Setup Profile** to enlist.\n"
                f"{SEP}"
            ), color=VIOLET,
        )
        e.set_thumbnail(url=member.display_avatar.url)
        brand(e, thumb=False)
        return e
    le = HOK_LANE_EMOJIS.get(md.get("main_lane",""),"🎮")
    ce = HOK_CLASS_EMOJIS.get(md.get("hero_class",""),"🎮")
    e = discord.Embed(
        title=f"⚜  {md['ign']}",
        description=(
            f"{SEP}\n"
            f"*{member.mention}  ·  Oblivion Empire Warrior*\n"
            f"{SEP}"
        ), color=GOLD,
    )
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="🎮 IGN",          value=f"`{md['ign']}`",                                         inline=True)
    e.add_field(name="📊 Current Rank", value=format_rank(md.get("current_rank",""), md.get("current_stars",0)), inline=True)
    e.add_field(name="🏆 Peak Points",  value=f"`{md.get('peak_points',0):,} pts`" if md.get("peak_points") else "—", inline=True)
    e.add_field(name=f"{le} Lane",      value=md.get("main_lane","—"),                                  inline=True)
    e.add_field(name=f"{ce} Class",     value=md.get("hero_class","—"),                                 inline=True)
    e.add_field(name="🌐 Region",        value=md.get("region","—") or "—",                             inline=True)
    try:    upd = datetime.fromisoformat(md["updated_at"]).strftime("%b %d, %Y")
    except: upd = "—"
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Updated {upd}", icon_url=logo_url() or discord.utils.MISSING)
    return e

def build_leaderboard_embed(members_list, guild, title, subtitle=""):
    e = discord.Embed(
        title=title,
        description=f"{SEP}\n{subtitle or 'Oblivion Empire Rankings'}\n{SEP}",
        color=GOLD,
    )
    if not members_list:
        e.add_field(name="No Warriors Yet", value="Be the first — use `/oblivion` → Setup Profile!", inline=False)
        brand(e); return e
    medals = ["🥇","🥈","🥉"]; lines = []
    for i, md in enumerate(members_list[:15], 1):
        mem  = guild.get_member(md["discord_id"])
        name = mem.display_name if mem else f"ID:{md['discord_id']}"
        pp   = md.get("peak_points", 0)
        pr   = f"`{pp:,} pts`" if pp else "—"
        le   = HOK_LANE_EMOJIS.get(md.get("main_lane",""), "")
        pos  = medals[i-1] if i <= 3 else f"`{i}.`"
        lines.append(f"{pos}  {le} **{name}**\n　　{pr}")
    e.add_field(name="Rankings", value="\n".join(lines), inline=False)
    brand(e); return e

def build_event_embed(ev: dict) -> discord.Embed:
    yes, maybe, no = len(ev.get("rsvp_yes",[])), len(ev.get("rsvp_maybe",[])), len(ev.get("rsvp_no",[]))
    total = yes + maybe + no
    e = discord.Embed(
        title=f"🎯  {ev['title']}",
        description=(
            f"{SEP}\n"
            f"{ev['description']}\n"
            f"{SEP}"
        ), color=TEAL,
    )
    e.add_field(name="📅 Date & Time", value=f"`{ev['date']}`",        inline=False)
    e.add_field(name="✅ Going",        value=f"**{yes}**",             inline=True)
    e.add_field(name="❓ Maybe",        value=f"**{maybe}**",           inline=True)
    e.add_field(name="❌ Not Going",    value=f"**{no}**",              inline=True)
    if total > 0:
        bar_len  = 12
        yes_bars = round(yes / total * bar_len)
        bar      = "🟩" * yes_bars + "⬜" * (bar_len - yes_bars)
        e.add_field(name="📊 RSVP", value=f"{bar} `{total} responses`", inline=False)
    if ev.get("image_url"): e.set_image(url=ev["image_url"])
    brand(e); return e

# ══════════════════════════════════════════════════════════════════════
#  MEMBER SEARCH
# ══════════════════════════════════════════════════════════════════════

class SearchModal(Modal, title="🔍  Search Warrior"):
    query = TextInput(label="Name, display name, or Discord ID",
                      placeholder="Type part of their name…", required=True, max_length=100)

    async def on_submit(self, i: discord.Interaction):
        results = fuzzy_search(i.guild, self.query.value)
        if not results:
            await i.response.send_message(embed=empire_embed(
                "🔍  No Results",
                f"No warrior found for `{self.query.value}`.\nCheck the spelling and try again.",
                color=CRIMSON), ephemeral=True); return
        if len(results) == 1:
            await i.response.send_message(embed=build_profile_embed(results[0]), ephemeral=True)
        else:
            e = empire_embed("🔍  Multiple Warriors Found",
                             f"Found **{len(results)}** results. Select the right one:", color=TEAL)
            await i.response.send_message(embed=e, view=SearchResultView(results), ephemeral=True)

class SearchResultView(View):
    def __init__(self, members):
        super().__init__(timeout=120)
        self._map = {str(m.id): m for m in members[:25]}
        opts = [discord.SelectOption(label=m.display_name[:100], value=str(m.id),
                                     description=f"@{m.name}"[:100]) for m in members[:25]]
        sel = Select(placeholder="👤  Select the warrior…", options=opts)
        sel.callback = self._on_select; self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        uid    = i.data["values"][0]
        member = self._map.get(uid) or i.guild.get_member(int(uid))
        if not member:
            await i.response.send_message("❌ Not found.", ephemeral=True); return
        await i.response.edit_message(embed=build_profile_embed(member), view=None)

# ══════════════════════════════════════════════════════════════════════
#  LEADERBOARD MENU
# ══════════════════════════════════════════════════════════════════════

class LeaderboardMenuView(View):
    def __init__(self, guild):
        super().__init__(timeout=120)
        self.guild = guild
        opts = ([discord.SelectOption(label="Overall Peak Rank", value="overall", emoji="🏆",
                                      description="All warriors sorted by peak rank")]
                + [discord.SelectOption(label=f"{HOK_LANE_EMOJIS[l]} {l}", value=l,
                                        description=f"Top {l} mains") for l in HOK_LANES]
                + [discord.SelectOption(label=f"{HOK_CLASS_EMOJIS[c]} {c}", value=c,
                                        description=f"Top {c} heroes") for c in HOK_CLASSES])
        sel = Select(placeholder="📊  Choose a leaderboard…", options=opts)
        sel.callback = self._picked; self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        val   = i.data["values"][0]
        all_m = [m for m in db["members"].values() if m.get("ign")]
        if val == "overall":
            data, title, sub = sorted(all_m, key=rank_sort_key, reverse=True), "🏆  Overall Rankings", "All warriors by peak rank"
        elif val in HOK_LANES:
            data, title, sub = (sorted([m for m in all_m if m.get("main_lane")==val],
                key=rank_sort_key, reverse=True),
                f"{HOK_LANE_EMOJIS[val]}  {val} Rankings", f"Top {val} mains")
        else:
            data, title, sub = (sorted([m for m in all_m if m.get("hero_class")==val],
                key=rank_sort_key, reverse=True),
                f"{HOK_CLASS_EMOJIS[val]}  {val} Rankings", f"Top {val} players")
        await i.response.edit_message(embed=build_leaderboard_embed(data, self.guild, title, sub), view=None)

# ══════════════════════════════════════════════════════════════════════
#  EVENT SYSTEM
# ══════════════════════════════════════════════════════════════════════

class EventRSVPView(View):
    def __init__(self, event_id: str):
        super().__init__(timeout=None)
        self.event_id = event_id
        for status, label, emoji, style in [
            ("yes","Going","✅",discord.ButtonStyle.success),
            ("maybe","Maybe","❓",discord.ButtonStyle.primary),
            ("no","Not Going","❌",discord.ButtonStyle.danger),
        ]:
            btn = Button(label=label, emoji=emoji, style=style, custom_id=f"rsvp_{status}_{event_id}")
            btn.callback = lambda inter, s=status: self._rsvp(inter, s)
            self.add_item(btn)

    async def _rsvp(self, i: discord.Interaction, status: str):
        ev = db["events"].get(self.event_id)
        if not ev:
            await i.response.send_message("❌ Event not found.", ephemeral=True); return
        uid = i.user.id
        for key in ("rsvp_yes","rsvp_maybe","rsvp_no"):
            if uid in ev[key]: ev[key].remove(uid)
        ev[f"rsvp_{status}"].append(uid); save_db(db)
        labels = {"yes":"✅  You're going!","maybe":"❓  Maybe!","no":"❌  Not going."}
        await i.response.send_message(labels[status], ephemeral=True)
        if ev.get("channel_id") and ev.get("message_id"):
            try:
                ch  = i.guild.get_channel(ev["channel_id"])
                msg = await ch.fetch_message(ev["message_id"])
                await msg.edit(embed=build_event_embed(ev))
            except Exception: pass

class EventModal(Modal, title="🎯  Create Event"):
    ev_title = TextInput(label="Event Title", placeholder="e.g. Ranked Scrimmage Night", required=True, max_length=150)
    ev_desc  = TextInput(label="Description", placeholder="What is this event about?", required=True, max_length=1500, style=discord.TextStyle.paragraph)
    ev_date  = TextInput(label="Date & Time", placeholder="e.g. June 20 · 8:00 PM UTC", required=True, max_length=100)
    ev_image = TextInput(label="Banner URL (optional)", placeholder="https://…", required=False, max_length=500)
    ev_ping  = TextInput(label="Role to ping (name, 'everyone', or blank)", placeholder="Members  or  everyone", required=False, max_length=50)

    def __init__(self, channel):
        super().__init__(); self.target_channel = channel

    async def on_submit(self, i: discord.Interaction):
        ev_id = str(uuid.uuid4())[:8]
        ev = {"id":ev_id, "title":self.ev_title.value.strip(),
              "description":self.ev_desc.value.strip(), "date":self.ev_date.value.strip(),
              "image_url":self.ev_image.value.strip() if self.ev_image.value else "",
              "created_by":i.user.id, "created_at":datetime.utcnow().isoformat(),
              "rsvp_yes":[],"rsvp_maybe":[],"rsvp_no":[],"message_id":None,"channel_id":None}
        db["events"][ev_id] = ev; save_db(db); bot.add_view(EventRSVPView(ev_id))
        pv = (self.ev_ping.value or "").strip().lower()
        if pv == "everyone": ping = "@everyone"
        elif pv == "here":   ping = "@here"
        elif pv:
            r = discord.utils.get(i.guild.roles, name=self.ev_ping.value.strip()); ping = r.mention if r else None
        else: ping = None
        try:
            msg = await self.target_channel.send(content=ping, embed=build_event_embed(ev), view=EventRSVPView(ev_id))
            db["events"][ev_id]["message_id"] = msg.id
            db["events"][ev_id]["channel_id"]  = self.target_channel.id
            save_db(db)
        except discord.Forbidden:
            await i.response.send_message("❌ Can't post in that channel — check my permissions.", ephemeral=True); return
        await i.response.send_message(embed=empire_embed(
            "✅  Event Created!",
            f"**{ev['title']}** is live in {self.target_channel.mention}.",
            color=EMERALD), ephemeral=True)
        await log_action(i.guild,"🎯 Event Created",
            f"{i.user.mention} → **{ev['title']}** in {self.target_channel.mention}")

class EventManagerView(View):
    def __init__(self):
        super().__init__(timeout=120)
        events = list(db["events"].values())
        if not events: return
        opts = [discord.SelectOption(label=ev["title"][:100], value=ev["id"],
                                     description=f"{ev['date'][:40]} | ✅{len(ev.get('rsvp_yes',[]))}"[:100])
                for ev in events[:25]]
        sel = Select(placeholder="🗑️  Select event to delete…", options=opts)
        sel.callback = self._on_select; self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        ev_id = i.data["values"][0]; ev = db["events"].pop(ev_id, None); save_db(db)
        if ev:
            if ev.get("channel_id") and ev.get("message_id"):
                try:
                    ch  = i.guild.get_channel(ev["channel_id"])
                    msg = await ch.fetch_message(ev["message_id"])
                    await msg.delete()
                except Exception: pass
            await i.response.edit_message(embed=empire_embed(
                "🗑️  Event Deleted", f"**{ev['title']}** has been removed.", color=CRIMSON), view=None)
            await log_action(i.guild,"🗑️ Event Deleted",f"{i.user.mention} deleted **{ev['title']}**")
        else:
            await i.response.edit_message(content="❌ Not found.", embed=None, view=None)

# ══════════════════════════════════════════════════════════════════════
#  ANNOUNCEMENT + CHANNEL PICKER
# ══════════════════════════════════════════════════════════════════════

def _channel_pages(guild):
    channels = guild.text_channels
    return [channels[i:i+25] for i in range(0,len(channels),25)] or [[]]

class ChannelPickerView(View):
    def __init__(self, guild, purpose, page=0):
        super().__init__(timeout=180)
        self.guild, self.purpose, self.page = guild, purpose, page
        self.pages = _channel_pages(guild)
        page_chs   = self.pages[page] if page < len(self.pages) else []
        opts = [discord.SelectOption(label=f"#{ch.name}"[:100], value=str(ch.id),
                                     description=(ch.topic[:80] if ch.topic else "Text channel")[:100])
                for ch in page_chs]
        if opts:
            sel = Select(placeholder=f"📋  Pick channel  (page {page+1}/{len(self.pages)})…", options=opts)
            sel.callback = self._picked; self.add_item(sel)
        if page > 0:
            prev = Button(label="◀ Prev", style=discord.ButtonStyle.secondary)
            prev.callback = lambda i: self._turn(i, page-1); self.add_item(prev)
        if page < len(self.pages)-1:
            nxt = Button(label="Next ▶", style=discord.ButtonStyle.secondary)
            nxt.callback = lambda i: self._turn(i, page+1); self.add_item(nxt)

    async def _turn(self, i, new_page):
        title = "📢  Choose Announcement Channel" if self.purpose=="announce" else "🎯  Choose Event Channel"
        await i.response.edit_message(embed=empire_embed(title, f"Page {new_page+1}/{len(self.pages)}", GOLD),
                                      view=ChannelPickerView(self.guild, self.purpose, new_page))

    async def _picked(self, i):
        ch = i.guild.get_channel(int(i.data["values"][0]))
        if not ch:
            await i.response.send_message("❌ Channel not found.", ephemeral=True); return
        if self.purpose == "announce":
            await i.response.edit_message(
                embed=empire_embed("📢  Announcement — Step 2 of 3",
                                   f"✅ Channel: {ch.mention}\n\nPick a role to ping (or skip):", GOLD),
                view=PingPickerView(ch))
        elif self.purpose == "event":
            await i.response.send_modal(EventModal(ch))

class PingPickerView(View):
    def __init__(self, target_channel):
        super().__init__(timeout=180)
        self.target_channel = target_channel
        roles = [r for r in target_channel.guild.roles if not r.is_default() and not r.managed][:23]
        opts  = ([discord.SelectOption(label="@everyone", value="everyone", emoji="📣"),
                  discord.SelectOption(label="No ping / skip", value="none", emoji="🔇")]
                 + [discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles])
        sel = Select(placeholder="🔔  Pick a role to ping…", options=opts)
        sel.callback = self._picked; self.add_item(sel)

    async def _picked(self, i):
        val = i.data["values"][0]
        if val == "everyone":            ping_role = "everyone"
        elif val == "none":              ping_role = None
        else:
            r = i.guild.get_role(int(val)); ping_role = r if r else None
        await i.response.send_modal(AnnouncementModal(self.target_channel, ping_role))

class AnnouncementModal(Modal, title="📢  Write Your Announcement"):
    ann_title = TextInput(label="Title", placeholder="Announcement title…", required=True, max_length=200)
    ann_body  = TextInput(label="Message", placeholder="Your announcement text…", required=True, max_length=2000, style=discord.TextStyle.paragraph)
    ann_image = TextInput(label="Banner / Image URL (optional)", placeholder="https://…", required=False, max_length=500)

    def __init__(self, target_channel, ping_role):
        super().__init__(); self.target_channel, self.ping_role = target_channel, ping_role

    async def on_submit(self, i: discord.Interaction):
        e = discord.Embed(
            title=f"📢  {self.ann_title.value.strip()}",
            description=(f"{SEP}\n{self.ann_body.value.strip()}\n{SEP}"),
            color=GOLD, timestamp=datetime.utcnow(),
        )
        img = self.ann_image.value.strip() if self.ann_image.value else ""
        if img.startswith("http"): e.set_image(url=img)
        e.set_footer(text=f"⚜  Oblivion Empire  ·  {i.user.display_name}",
                     icon_url=logo_url() or discord.utils.MISSING)
        if logo_url(): e.set_thumbnail(url=logo_url())
        if self.ping_role == "everyone":               mention = "@everyone"
        elif isinstance(self.ping_role, discord.Role): mention = self.ping_role.mention
        else:                                           mention = None
        try:
            await self.target_channel.send(content=mention, embed=e)
            await i.response.send_message(embed=empire_embed(
                "✅  Published!", f"Posted in {self.target_channel.mention}", EMERALD), ephemeral=True)
            await log_action(i.guild,"📢 Announcement",
                f"{i.user.mention} → **{self.ann_title.value}** in {self.target_channel.mention}")
        except discord.Forbidden:
            await i.response.send_message("❌ I don't have permission to post there.", ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  MAIN PANELS
# ══════════════════════════════════════════════════════════════════════

class OblivionPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="My Profile",      emoji="⚜️", style=discord.ButtonStyle.primary,   row=0)
    async def my_profile(self, i, _):
        await i.response.send_message(embed=build_profile_embed(i.user), ephemeral=True)

    @discord.ui.button(label="Setup Profile",   emoji="⚙️", style=discord.ButtonStyle.success,   row=0)
    async def setup_profile(self, i, _):
        await i.response.send_message(
            embed=_step_embed(1,5,[],"Select your **main lane** in Honor of Kings:"),
            view=SetupLaneView(i.user.id), ephemeral=True)

    @discord.ui.button(label="Search Profile",  emoji="🔍", style=discord.ButtonStyle.secondary, row=0)
    async def search_profile(self, i, _):
        await i.response.send_modal(SearchModal())

    @discord.ui.button(label="Leaderboards",    emoji="🏆", style=discord.ButtonStyle.primary,   row=1)
    async def leaderboards(self, i, _):
        await i.response.send_message(
            embed=empire_embed("📊  Leaderboards","Choose which leaderboard to view:", GOLD),
            view=LeaderboardMenuView(i.guild), ephemeral=True)

    @discord.ui.button(label="Community Stats", emoji="📈", style=discord.ButtonStyle.secondary, row=1)
    async def community_stats(self, i, _):
        all_m  = [m for m in db["members"].values() if m.get("ign")]
        lane_c: dict = {}; rank_c: dict = {}; cls_c: dict = {}
        for m in all_m:
            if m.get("main_lane"):    lane_c[m["main_lane"]] = lane_c.get(m["main_lane"],0)+1
            if m.get("current_rank"):
                mn = m["current_rank"].split()[0]; rank_c[mn] = rank_c.get(mn,0)+1
            if m.get("hero_class"):   cls_c[m["hero_class"]] = cls_c.get(m["hero_class"],0)+1
        e = discord.Embed(
            title="📈  Oblivion Empire  —  Community Stats",
            description=f"{SEP}\n*{len(i.guild.members)} total members  ·  {len(all_m)} registered warriors*\n{SEP}",
            color=DEEP_BLUE,
        )
        if lane_c:
            e.add_field(name="🗺️ Lanes",
                value="\n".join(f"{HOK_LANE_EMOJIS.get(l,'🎮')} **{l}** `×{c}`"
                                for l,c in sorted(lane_c.items(),key=lambda x:-x[1])), inline=True)
        if rank_c:
            e.add_field(name="📊 Ranks",
                value="\n".join(f"{HOK_RANK_EMOJIS.get(r,'🎮')} **{r}** `×{c}`"
                                for r,c in sorted(rank_c.items(),key=lambda x:-HOK_RANK_ORDER.get(x[0],0))), inline=True)
        if cls_c:
            e.add_field(name="🎯 Classes",
                value="\n".join(f"{HOK_CLASS_EMOJIS.get(c,'🎮')} **{c}** `×{v}`"
                                for c,v in sorted(cls_c.items(),key=lambda x:-x[1])), inline=True)
        brand(e); await i.response.send_message(embed=e, ephemeral=True)


class AdminPanelView(View):
    def __init__(self): super().__init__(timeout=None)

    def _guard(self, i): return is_admin(i.user)

    @discord.ui.button(label="Announce",      emoji="📢", style=discord.ButtonStyle.primary,   row=0)
    async def announce(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        await i.response.send_message(
            embed=empire_embed("📢  Announcement — Step 1 of 3",
                               "Every text channel in your server is listed below.", GOLD),
            view=ChannelPickerView(i.guild,"announce"), ephemeral=True)
        await log_action(i.guild,"📢 Announce",f"{i.user.mention} opened announcement tool")

    @discord.ui.button(label="Create Event",  emoji="🎯", style=discord.ButtonStyle.success,   row=0)
    async def create_event(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        await i.response.send_message(
            embed=empire_embed("🎯  Create Event — Pick Channel","Select which channel to post the event in:", TEAL),
            view=ChannelPickerView(i.guild,"event"), ephemeral=True)

    @discord.ui.button(label="Manage Events", emoji="🗓️", style=discord.ButtonStyle.secondary, row=0)
    async def manage_events(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        if not db["events"]:
            await i.response.send_message(empire_embed("🗓️  No Events","No events created yet.", VIOLET), ephemeral=True); return
        await i.response.send_message(
            embed=empire_embed("🗓️  Manage Events","Select an event to delete:", CRIMSON),
            view=EventManagerView(), ephemeral=True)

    @discord.ui.button(label="Backup Data",   emoji="💾", style=discord.ButtonStyle.secondary, row=1)
    async def backup(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        if not os.path.exists(DATA_FILE):
            await i.response.send_message("❌ No data file.", ephemeral=True); return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        await i.response.send_message(content="💾  **Oblivion Empire — Data Backup**",
            file=discord.File(DATA_FILE, filename=f"oblivion_backup_{ts}.json"), ephemeral=True)
        await log_action(i.guild,"💾 Backup",f"{i.user.mention} downloaded backup")

    @discord.ui.button(label="Server Stats",  emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def server_stats(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌ No permission.", ephemeral=True); return
        reg       = sum(1 for m in db["members"].values() if m.get("ign"))
        img_count = sum(len(v) for v in db.get("hero_images",{}).values())
        e = discord.Embed(
            title="📊  Admin  —  Server Overview",
            description=f"{SEP}\n*Real-time snapshot of Oblivion Empire*\n{SEP}",
            color=STEEL,
        )
        e.add_field(name="👥 Members",     value=f"**{len(i.guild.members)}**", inline=True)
        e.add_field(name="📝 Profiles",    value=f"**{reg}** complete",         inline=True)
        e.add_field(name="🎯 Events",      value=f"**{len(db['events'])}**",    inline=True)
        e.add_field(name="🖼️ Hero Images", value=f"**{img_count}** total",      inline=True)
        e.add_field(name="🎮 Game Scores", value=f"**{len(db['game_scores'])}** players", inline=True)
        brand(e); await i.response.send_message(embed=e, ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ══════════════════════════════════════════════════════════════════════

@bot.tree.command(name="oblivion", description="⚜ Open the Oblivion Empire community panel")
async def cmd_oblivion(i: discord.Interaction):
    md    = db["members"].get(str(i.user.id))
    extra = ""
    if md and md.get("current_rank"):
        le    = HOK_LANE_EMOJIS.get(md.get("main_lane",""),"")
        extra = (f"\n{SEP}\n"
                 f"{format_rank(md['current_rank'], md.get('current_stars',0))}  {le} {md.get('main_lane','')}")
    reg = sum(1 for m in db["members"].values() if m.get("ign"))
    e = discord.Embed(
        title="⚜  Oblivion Empire",
        description=(
            f"*Welcome back,* **{i.user.display_name}**.*{extra}*\n\n"
            f"{SEP}\n"
            "**Rise through the ranks. Conquer the arena. Build your legacy.**\n"
            f"{SEP}"
        ), color=GOLD,
    )
    e.set_thumbnail(url=logo_url() or i.user.display_avatar.url)
    e.add_field(name="🌐 Community",
                value=f"👥 **{reg}** warriors registered\n🎯 **{len(db['events'])}** active events", inline=True)
    e.add_field(name="🎮 Games",
                value=f"🖼️ Guess by Picture\n💬 Guess by Quote\n🎭 Mafia", inline=True)
    brand(e, thumb=False)
    await i.response.send_message(embed=e, view=OblivionPanelView())
    await log_action(i.guild,"🔹 /oblivion",f"{i.user.mention} opened community panel")


@bot.tree.command(name="admins", description="🛡 Open the Oblivion Empire admin panel")
async def cmd_admins(i: discord.Interaction):
    if not is_admin(i.user):
        await i.response.send_message(
            embed=empire_embed("🚫  Access Denied","You don't have permission to access the admin panel.",CRIMSON),
            ephemeral=True); return
    reg       = sum(1 for m in db["members"].values() if m.get("ign"))
    img_count = sum(len(v) for v in db.get("hero_images",{}).values())
    e = discord.Embed(
        title="🛡️  Admin Command Center",
        description=(
            f"{SEP}\n"
            "*Full control panel — use your powers wisely.*\n"
            f"{SEP}"
        ), color=CRIMSON,
    )
    e.set_thumbnail(url=logo_url() or i.user.display_avatar.url)
    e.add_field(name="📊 Overview",
                value=(f"👥 **{len(i.guild.members)}** members\n"
                       f"📝 **{reg}** profiles\n"
                       f"🎯 **{len(db['events'])}** events\n"
                       f"🖼️ **{img_count}** hero images"), inline=True)
    e.add_field(name="⚙️ Tools",
                value="📢 Announce to any channel\n🎯 Create events with RSVP\n💾 Backup your data\n🖼️ `/set_hero_image` to add images", inline=True)
    brand(e, thumb=False)
    await i.response.send_message(embed=e, view=AdminPanelView(), ephemeral=True)
    await log_action(i.guild,"🔸 /admins",f"{i.user.mention} opened admin panel")


@bot.tree.command(name="games", description="🎮 Open the Oblivion Empire games panel")
async def cmd_games_placeholder(i: discord.Interaction):
    await i.response.send_message("❌ Games cog not loaded — check bot logs.", ephemeral=True)


@bot.tree.command(name="profile", description="⚜ View any member's Oblivion Empire profile")
@app_commands.describe(member="The member to look up")
async def cmd_profile(i: discord.Interaction, member: discord.Member):
    await i.response.send_message(embed=build_profile_embed(member))
    await log_action(i.guild,"👤 /profile",f"{i.user.mention} viewed {member.mention}'s profile")


# ─── Hero image commands ────────────────────────────────────────────────────
# FIX: autocomplete now directly imports from games.py at call time
# so it always has heroes even on first boot before cog fully initialises.

async def _hero_autocomplete(i: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    # Try the live list first (populated by cog); fall back to import
    names = list(_all_hero_names)
    if not names:
        try:
            from games import HOK_HEROES as _hh
            names = sorted(_hh.keys())
        except Exception:
            pass
    return [app_commands.Choice(name=h, value=h)
            for h in names if current.lower() in h.lower()][:25]


@bot.tree.command(name="set_hero_image",
                  description="🖼️ Upload an image for Guess by Picture (Admin only)")
@app_commands.describe(hero="Pick the hero from the list",
                       image="Attach the image file (.png/.jpg/.webp)")
@app_commands.autocomplete(hero=_hero_autocomplete)
async def cmd_set_hero_image(i: discord.Interaction, hero: str, image: discord.Attachment):
    if not is_admin(i.user):
        await i.response.send_message("❌ Admin only.", ephemeral=True); return

    # Accept the hero even if not in the list — the user typed it manually
    if not image.content_type or not image.content_type.startswith("image/"):
        await i.response.send_message("❌ Attach an image file (.png, .jpg, .webp).", ephemeral=True); return

    await i.response.defer(ephemeral=True)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(image.url) as r:
                if r.status != 200:
                    await i.followup.send("❌ Failed to download the image.", ephemeral=True); return
                data = await r.read()
    except Exception as ex:
        await i.followup.send(f"❌ Download error: {ex}", ephemeral=True); return

    slug     = hero.lower().replace(" ","_").replace("&","and").replace(".","").replace("'","")
    ts       = int(datetime.utcnow().timestamp())
    ext      = (image.content_type.split("/")[-1].split(";")[0] or "png")
    filename = f"{slug}_{ts}.{ext}"
    filepath = os.path.join(HERO_IMAGES_DIR, filename)

    with open(filepath,"wb") as f:
        f.write(data)

    if hero not in db["hero_images"]:
        db["hero_images"][hero] = []
    db["hero_images"][hero].append(filepath)
    save_db(db)

    count = len(db["hero_images"][hero])
    total = sum(len(v) for v in db["hero_images"].values())
    e = discord.Embed(
        title="✅  Hero Image Saved!",
        description=(
            f"{SEP}\n"
            f"**{hero}** now has **{count}** image{'s' if count!=1 else ''} in the pool.\n"
            f"Total across all heroes: **{total}**\n"
            f"{SEP}"
        ), color=EMERALD,
    )
    e.set_image(url=image.url)
    e.add_field(name="💡 Tip", value="Upload more images per hero — the bot picks randomly each round.", inline=False)
    brand(e, thumb=False)
    await i.followup.send(embed=e, ephemeral=True)
    await log_action(i.guild,"🖼️ Hero Image Added",
        f"{i.user.mention} added image #{count} for **{hero}** ({total} total)")


@bot.tree.command(name="remove_hero_image",
                  description="🗑️ Remove an image from a hero (Admin only)")
@app_commands.describe(hero="Pick the hero")
@app_commands.autocomplete(hero=_hero_autocomplete)
async def cmd_remove_hero_image(i: discord.Interaction, hero: str):
    if not is_admin(i.user):
        await i.response.send_message("❌ Admin only.", ephemeral=True); return
    images = db.get("hero_images",{}).get(hero,[])
    if not images:
        await i.response.send_message(
            embed=empire_embed("❌  No Images",f"**{hero}** has no images uploaded.", CRIMSON),
            ephemeral=True); return
    e = empire_embed("🗑️  Remove Image",
                     f"**{hero}** has **{len(images)}** image{'s' if len(images)!=1 else ''}. Select one to remove:",
                     CRIMSON)
    await i.response.send_message(embed=e, view=RemoveHeroImageView(hero, images), ephemeral=True)

class RemoveHeroImageView(View):
    def __init__(self, hero: str, images: list[str]):
        super().__init__(timeout=120)
        self.hero, self.images = hero, images
        opts = [discord.SelectOption(label=f"Image {n+1}  ({os.path.basename(p)[:60]})", value=p)
                for n,p in enumerate(images[:25])]
        sel = Select(placeholder="Select image to remove…", options=opts)
        sel.callback = self._on_select; self.add_item(sel)

    async def _on_select(self, i: discord.Interaction):
        filepath = i.data["values"][0]
        images   = db["hero_images"].get(self.hero,[])
        if filepath in images:
            images.remove(filepath)
            if not images: db["hero_images"].pop(self.hero,None)
            save_db(db)
            if os.path.exists(filepath):
                try: os.remove(filepath)
                except Exception: pass
        remaining = len(db["hero_images"].get(self.hero,[]))
        await i.response.edit_message(embed=empire_embed(
            "🗑️  Image Removed",
            f"**{self.hero}** now has **{remaining}** image{'s' if remaining!=1 else ''}.",
            CRIMSON), view=None)
        await log_action(i.guild,"🗑️ Hero Image Removed",
            f"{i.user.mention} removed an image for **{self.hero}**")


@bot.tree.command(name="hero_images",
                  description="🖼️ See image status for all heroes (Admin only)")
async def cmd_hero_images(i: discord.Interaction):
    if not is_admin(i.user):
        await i.response.send_message("❌ Admin only.", ephemeral=True); return

    # Get hero list from cog or direct import
    all_heroes = list(_all_hero_names)
    if not all_heroes:
        try:
            from games import HOK_HEROES as _hh
            all_heroes = sorted(_hh.keys())
        except Exception:
            all_heroes = []

    images  = db.get("hero_images",{})
    ready   = {h: len(v) for h,v in images.items() if v}
    missing = [h for h in all_heroes if h not in ready]
    total   = sum(ready.values())

    e = discord.Embed(
        title="🖼️  Hero Image Status",
        description=(
            f"{SEP}\n"
            f"**{len(ready)}** of **{len(all_heroes)}** heroes have images  ·  **{total}** total images\n"
            f"Use `/set_hero_image` to add more.\n"
            f"{SEP}"
        ), color=AMBER,
    )
    if ready:
        lines = "\n".join(f"✅ **{h}** `×{c}`" for h,c in sorted(ready.items()))[:1020]
        e.add_field(name="Ready to Play", value=lines or "—", inline=True)
    if missing:
        lines = "\n".join(f"❌ {h}" for h in sorted(missing))[:1020]
        e.add_field(name="Need Images", value=lines or "—", inline=True)
    brand(e, thumb=False)
    await i.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(name="help", description="📜 View all Oblivion Empire commands")
async def cmd_help(i: discord.Interaction):
    e = discord.Embed(
        title="📜  Oblivion Empire  —  Command Guide",
        description=(
            f"{SEP}\n"
            "*Honor of Kings Community Bot*\n"
            f"{SEP}"
        ), color=VIOLET,
    )
    e.set_thumbnail(url=logo_url() or i.user.display_avatar.url)
    e.add_field(name="⚜ /oblivion", value=(
        "Community hub — open to everyone.\n"
        "`My Profile` · `Setup Profile` · `Search Profile`\n"
        "`Leaderboards` · `Community Stats`"), inline=False)
    e.add_field(name="🛡 /admins", value=(
        "Admin panel — restricted to configured roles.\n"
        "`Announce` · `Create Event` · `Manage Events` · `Backup` · `Stats`"), inline=False)
    e.add_field(name="🎮 /games", value=(
        "`🖼️ Guess by Picture` — crop difficulty: Easy / Medium / Hard / Random\n"
        "`💬 Guess by Quote` — identify the hero from their quote\n"
        "`🎭 Mafia` — host-controlled social deduction\n"
        "`🏅 All-Time Scores`"), inline=False)
    e.add_field(name="📌 Admin Slash Commands", value=(
        "`/set_hero_image` — upload image for a hero\n"
        "`/remove_hero_image` — delete an image\n"
        "`/hero_images` — see image status\n"
        "`/profile @member` — view any profile\n"
        "`/restore` — restore from backup"), inline=False)
    e.add_field(name="🎯 HoK Rank Ladder", value=(
        "🥉 Bronze I-III  →  🥈 Silver I-III  →  🥇 Gold I-IV\n"
        "💠 Platinum I-IV  →  💎 Diamond I-V  →  ⚡ Master I-V\n"
        "👑 Grandmaster:  👑 King  ·  🔮 Mythic  ·  🌟 Epic  ·  🏆 Legend"), inline=False)
    e.add_field(name="🗺️ HoK Lanes", value=(
        "⚔️ Clash Lane  ·  🌿 Jungle  ·  ⚡ Mid Lane\n"
        "🌾 Farm Lane  ·  🌀 Roaming"), inline=False)
    brand(e, thumb=False)
    await i.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(name="restore", description="💾 Restore data from a backup file (Admin only)")
@app_commands.describe(backup="The .json backup file")
async def cmd_restore(i: discord.Interaction, backup: discord.Attachment):
    global db
    if not is_admin(i.user):
        await i.response.send_message("❌ Admin only.", ephemeral=True); return
    if not backup.filename.endswith(".json"):
        await i.response.send_message("❌ Attach a `.json` file.", ephemeral=True); return
    await i.response.defer(ephemeral=True)
    try:
        raw  = await backup.read()
        data = json.loads(raw.decode("utf-8"))
        for k,v in _blank_db().items(): data.setdefault(k,v)
        save_db(data); db = data
        await i.followup.send(embed=empire_embed(
            "✅  Restored",
            f"`{backup.filename}`\n👥 {len(data['members'])} profiles · 🎯 {len(data['events'])} events",
            EMERALD), ephemeral=True)
        await log_action(i.guild,"💾 Restore",f"{i.user.mention} restored `{backup.filename}`")
    except json.JSONDecodeError:
        await i.followup.send("❌ Invalid JSON file.", ephemeral=True)
    except Exception as ex:
        await i.followup.send(f"❌ Error: {ex}", ephemeral=True)


# ─── BOT EVENTS ────────────────────────────────────────────────────────────


@bot.tree.command(name="profiles", description="📋 View all registered warrior profiles (Admin only)")
@app_commands.describe(page="Page number to view")
async def cmd_profiles(interaction: discord.Interaction, page: int = 1):
    if not is_admin(interaction.user):
        await interaction.response.send_message(
            embed=empire_embed("🚫 Access Denied", "Admin only.", CRIMSON), ephemeral=True)
        return
    all_members = [md for md in db["members"].values() if md.get("ign")]
    if not all_members:
        await interaction.response.send_message(
            embed=empire_embed("📋 No Profiles Yet",
                               "No warriors have registered yet.\n"
                               "Players use `/oblivion` → Setup Profile to register.", VIOLET),
            ephemeral=True)
        return
    per_page = 10
    total    = len(all_members)
    pages    = max(1, (total + per_page - 1) // per_page)
    page     = max(1, min(page, pages))
    start    = (page - 1) * per_page
    chunk    = all_members[start:start + per_page]
    lines    = []
    for md in chunk:
        mem   = interaction.guild.get_member(md["discord_id"])
        dname = mem.display_name if mem else f"ID:{md['discord_id']}"
        cr    = format_rank(md.get("current_rank", ""), md.get("current_stars", 0))
        pp    = md.get("peak_points", 0)
        le    = HOK_LANE_EMOJIS.get(md.get("main_lane", ""), "")
        ce    = HOK_CLASS_EMOJIS.get(md.get("hero_class", ""), "")
        peak  = f"🏆 {pp:,} pts" if pp else ""
        lines.append(
            f"**{md['ign']}** ({dname})\n"
            f"  {cr}  {peak}  {le}{ce}"
        )
    e = discord.Embed(
        title=f"📋  Registered Warriors  —  Page {page}/{pages}",
        description=(
            f"{SEP}\n"
            f"*{total} warriors registered in total.*\n\n"
            + "\n\n".join(lines)
            + f"\n{SEP}"
        ),
        color=DEEP_BLUE)
    e.set_footer(text=f"⚜  Oblivion Empire  ·  Admin View  ·  {total} total profiles",
                 icon_url=logo_url() or discord.utils.MISSING)
    brand(e, thumb=False)
    await interaction.response.send_message(embed=e, ephemeral=True)
    await log_action(interaction.guild, "📋 /profiles",
                     f"{interaction.user.mention} viewed profiles page {page}/{pages}")

@bot.event
async def on_ready():
    for ev_id in db["events"]: bot.add_view(EventRSVPView(ev_id))
    await bot.tree.sync()
    print(f"✅  {bot.user}  —  Oblivion Empire Bot online!")
    print(f"🛡  Admin IDs : {ADMIN_ROLE_IDS or 'none — set ADMIN_ROLE_IDS env var'}")
    print(f"🖼️  Logo URL  : {_LOGO_URL or 'not set — edit GITHUB_USER and GITHUB_REPO in bot.py'}")
    print(f"💾  Data      : {DATA_FILE}")

async def main():
    async with bot:
        await bot.load_extension("games")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
