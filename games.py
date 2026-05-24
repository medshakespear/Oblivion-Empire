# ══════════════════════════════════════════════════════════════════════
#  bot.py  —  Oblivion Empire Discord Bot
#  Honor of Kings Community
# ══════════════════════════════════════════════════════════════════════
#
#  RAILWAY ENV VARIABLES:
#    DISCORD_TOKEN   — your bot token
#    ADMIN_ROLE_IDS  — comma-separated role IDs  e.g. "111,222"
#    DATA_DIR        — /data  (Railway persistent volume)
#    SERVER_LOGO_URL — (optional) direct image URL to your server logo
#                      used as thumbnail in all embeds
#                      e.g. https://cdn.discordapp.com/icons/...
#                      if blank, falls back to the bot's own avatar
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
SERVER_LOGO_URL = os.getenv("SERVER_LOGO_URL", "")  # your server logo URL
os.makedirs(DATA_DIR,        exist_ok=True)
os.makedirs(HERO_IMAGES_DIR, exist_ok=True)

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
    peak = md.get("peak_rank","")
    main = peak.split()[0] if peak else ""
    tier = HOK_RANK_ORDER.get(main,-1)
    if main == "Grandmaster": return (tier, md.get("peak_stars",0))
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
        "hero_images": {},
        "config":      {"admin_role_ids": ADMIN_ROLE_IDS},
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
        "peak_rank":"","peak_stars":0,
        "main_lane":"","hero_class":"","region":"",
        "registered_at":now,"updated_at":now,
    }

db = load_db()

# ══════════════════════════════════════════════════════════════════════
#  BRANDING HELPERS
# ══════════════════════════════════════════════════════════════════════
def logo_url() -> str:
    """Server logo if set, else bot avatar."""
    if SERVER_LOGO_URL:
        return SERVER_LOGO_URL
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
            if self.purpose == "current":
                await i.response.edit_message(
                    embed=_step_embed(5,7,[f"Current Rank: 👑 Grandmaster"],"Select your **peak rank tier**:"),
                    view=RankTierView(self.user_id, self.lane, self.cls, self.existing,
                                      "peak", current_rank="Grandmaster", progress=5))
            else:
                await i.response.send_modal(
                    ProfileFinalModal(self.lane, self.cls, self.current_rank, self.current_stars, "Grandmaster", 0, self.existing))
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
        if self.purpose == "current":
            await i.response.edit_message(
                embed=_step_embed(5,7,[f"Current Rank: {format_rank(rank)}"],"Select your **peak / highest rank tier**:"),
                view=RankTierView(self.user_id, self.lane, self.cls, self.existing,
                                  "peak", current_rank=rank, progress=5))
        else:
            await i.response.send_modal(
                ProfileFinalModal(self.lane, self.cls, self.current_rank, self.current_stars, rank, 0, self.existing))

class ProfileFinalModal(Modal):
    def __init__(self, lane, cls, curr_rank, curr_stars_pre, peak_rank, peak_stars_pre, existing):
        super().__init__(title="⚜  Profile — Final Step (7/7)")
        self.lane, self.cls, self.curr_rank, self.peak_rank = lane, cls, curr_rank, peak_rank
        self._ign = TextInput(label="In-Game Name (IGN)",
                              placeholder="Your HoK username exactly as shown in-game",
                              required=True, max_length=50,
                              default=existing.get("ign","") if existing else "")
        self.add_item(self._ign)
        self._curr_stars: Optional[TextInput] = None
        if curr_rank == "Grandmaster":
            self._curr_stars = TextInput(label="Current GM star count",
                                          placeholder="0+=King · 25+=Mythic · 50+=Epic · 100+=Legend",
                                          required=True, max_length=5,
                                          default=str(curr_stars_pre) if curr_stars_pre else "")
            self.add_item(self._curr_stars)
        self._peak_stars: Optional[TextInput] = None
        if peak_rank == "Grandmaster":
            self._peak_stars = TextInput(label="Peak GM star count",
                                          placeholder="0+=King · 25+=Mythic · 50+=Epic · 100+=Legend",
                                          required=True, max_length=5,
                                          default=str(peak_stars_pre) if peak_stars_pre else "")
            self.add_item(self._peak_stars)
        self._region = TextInput(label="Region (optional)",
                                  placeholder="e.g. SEA, EU, NA, ME, East Asia",
                                  required=False, max_length=20,
                                  default=existing.get("region","") if existing else "")
        self.add_item(self._region)

    async def on_submit(self, i: discord.Interaction):
        uid = str(i.user.id)
        md  = db["members"].get(uid) or new_member(i.user.id)
        def to_int(ti): return int(ti.value.strip()) if ti and ti.value.strip().isdigit() else 0
        curr_stars = to_int(self._curr_stars)
        peak_stars = to_int(self._peak_stars)
        md.update({"ign":self._ign.value.strip(),"current_rank":self.curr_rank,
                   "current_stars":curr_stars,"peak_rank":self.peak_rank,"peak_stars":peak_stars,
                   "main_lane":self.lane,"hero_class":self.cls,
                   "region":self._region.value.strip(),"updated_at":datetime.utcnow().isoformat()})
        db["members"][uid] = md; save_db(db)
        le,ce = HOK_LANE_EMOJIS.get(self.lane,"🎮"), HOK_CLASS_EMOJIS.get(self.cls,"🎮")
        e = discord.Embed(
            title="✅  Profile Saved!",
            description=(
                f"{SEP}\n"
                f"**{md['ign']}** — your warrior profile is live.\n"
                f"{SEP}"
            ), color=EMERALD,
        )
        e.add_field(name="🎮 IGN",        value=f"`{md['ign']}`",                              inline=True)
        e.add_field(name=f"{le} Lane",    value=self.lane,                                     inline=True)
        e.add_field(name=f"{ce} Class",   value=self.cls,                                      inline=True)
        e.add_field(name="📊 Current",    value=format_rank(self.curr_rank, curr_stars),       inline=True)
        e.add_field(name="🏆 Peak",       value=format_rank(self.peak_rank, peak_stars),       inline=True)
        if md.get("region"): e.add_field(name="🌐 Region", value=md["region"], inline=True)
        brand(e, thumb=False)
        await i.response.send_message(embed=e, ephemeral=True)
        await log_action(i.guild,"📝 Profile Updated",
            f"{i.user.mention} — **{md['ign']}** | {format_rank(self.curr_rank,curr_stars)} | Peak: {format_rank(self.peak_rank,peak_stars)}")

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
    e.add_field(name="🏆 Peak Rank",    value=format_rank(md.get("peak_rank",""),    md.get("peak_stars",0)),    inline=True)
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
        pr   = format_rank(md.get("peak_rank","?"), md.get("peak_stars",0))
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
            embed=_step_embed(1,7,[],"Select your **main lane** in Honor of Kings:"),
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

@bot.event
async def on_ready():
    for ev_id in db["events"]: bot.add_view(EventRSVPView(ev_id))
    await bot.tree.sync()
    print(f"✅  {bot.user}  —  Oblivion Empire Bot online!")
    print(f"🛡  Admin IDs : {ADMIN_ROLE_IDS or 'none — set ADMIN_ROLE_IDS env var'}")
    print(f"🖼️  Logo URL  : {SERVER_LOGO_URL or 'not set — using bot avatar'}")
    print(f"💾  Data      : {DATA_FILE}")

async def main():
    async with bot:
        await bot.load_extension("games")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
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
        self._auto_tallying  = False

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
        # Dead player → allowed (out of the game, no advantage)
        # Spectator admin (not in players list) → allowed
        # Alive player (even admin) → NOT allowed (cheating)
        requester      = i.guild.get_member(i.user.id)
        is_in_game     = i.user in self.game.players
        is_alive       = i.user in self.game.alive
        is_admin_user  = requester is not None and is_admin(requester)
        is_dead        = is_in_game and not is_alive
        is_spec_admin  = is_admin_user and not is_in_game

        if not (is_dead or is_spec_admin):
            if is_in_game and is_alive:
                await i.response.send_message(
                    "❌ You're still alive — seeing all roles would be cheating!\n"

                    "This button unlocks once you're eliminated.",
                    ephemeral=True)
            else:
                await i.response.send_message("❌ Not permitted.", ephemeral=True)
            return

        lines = []
        for m in self.game.players:
            role      = self.game.get_role(m)
            ri        = MAFIA_ROLES[role]
            status    = "✅" if m in self.game.alive else "💀"
            lines.append(f"{status} {ri['emoji']} **{m.display_name}** — {role}")
        who = "Dead Player" if is_dead else "Spectator Admin"
        e = discord.Embed(
            title="🔍  All Roles",
            description="\n".join(lines) or "No players yet.",
            color=CRIMSON)
        e.set_footer(text=f"⚜  Visible only to you  ·  {who}")
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

    def _vote_status(self) -> str:
        """Progress bar + who voted / who hasn't yet."""
        voted     = [m for m in self.game.alive if m.id in self.game.votes]
        not_voted = [m for m in self.game.alive if m.id not in self.game.votes]
        total     = len(self.game.alive)
        voted_n   = len(voted)
        bar_len   = 10
        filled    = round(voted_n / total * bar_len) if total else 0
        bar       = "🟩" * filled + "⬜" * (bar_len - filled)
        v_names   = ", ".join(m.display_name for m in voted)    or "—"
        nv_names  = ", ".join(m.display_name for m in not_voted) or "—"
        return (
            f"{bar}  **{voted_n}/{total}** voted\n"
            f"✅ Voted: {v_names}\n"
            f"⏳ Waiting: {nv_names}"
        )

    async def _on_vote(self, i: discord.Interaction):
        if i.user not in self.game.alive:
            await i.response.send_message("❌ You are eliminated.", ephemeral=True)
            return
        tid = int(i.data["values"][0])
        if tid == i.user.id:
            await i.response.send_message("❌ You can't vote for yourself.", ephemeral=True)
            return

        self.game.votes[i.user.id] = tid   # allows vote change
        target  = i.guild.get_member(tid)
        tname   = target.display_name if target else "?"
        voted_n = len(self.game.votes)
        total   = len(self.game.alive)

        if voted_n >= total and not self.game._auto_tallying:
            # All alive players have voted → auto-tally
            self.game._auto_tallying = True
            self.stop()
            await i.response.send_message(
                f"🗳️ Voted for **{tname}** — "
                f"**All {total} players have voted! Tallying automatically…**",
                ephemeral=True)
            await self.game.channel.send(embed=discord.Embed(
                title="🗳️  All Players Voted — Auto Tallying!",
                description=self._vote_status(),
                color=GOLD))
            await _mafia_resolve_votes(self.game)
        else:
            await i.response.send_message(
                f"🗳️ Voted for **{tname}**.\n\n{self._vote_status()}",
                ephemeral=True)

    @discord.ui.button(label="⚖️ Tally Votes", style=discord.ButtonStyle.danger, emoji="⚖️", row=1)
    async def tally_btn(self, i: discord.Interaction, _: Button):
        m = i.guild.get_member(i.user.id)
        if m is None or not is_admin(m):
            await i.response.send_message("❌ Admin only.", ephemeral=True)
            return
        if self.game._auto_tallying:
            await i.response.send_message("Already tallying automatically.", ephemeral=True)
            return
        self.game._auto_tallying = True
        self.stop()
        await i.response.defer()
        await self.game.channel.send(embed=discord.Embed(
            title="⚖️  Admin Tallying Votes",
            description=self._vote_status(),
            color=GOLD))
        await _mafia_resolve_votes(self.game)


async def _mafia_day(game: MafiaGame):
    game.phase = "day"
    game.day  += 1
    game.votes = {}
    game._auto_tallying = False

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
