# ══════════════════════════════════════════════════════════════════════
#  empire.py  —  سجلات الإمبراطورية المظلمة
#  نظام التقدم والمغامرات لسيرفر Oblivion Empire
#
#  الدخول: /empire  →  لوحة واحدة تضم كل الأزرار
#  لا توجد أوامر منفصلة — كل شيء من مكان واحد
# ══════════════════════════════════════════════════════════════════════

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal, TextInput
from discord import app_commands
import asyncio, random, json, os
from datetime import datetime, timedelta
from typing import Optional

from bot import (
    db, save_db, brand, empire_embed, logo_url, log_action, bot,
    bot_avatar, is_admin,
    GOLD, CRIMSON, VIOLET, TEAL, EMERALD, STEEL, AMBER, PHANTOM,
    OBSIDIAN, SEP,
)

# ══════════════════════════════════════════════════════════════════════
#  الألوان
# ══════════════════════════════════════════════════════════════════════
DEEP_GOLD   = 0xC9A227
DARK_EMPIRE = 0x1A0A2E
SHARD_BLUE  = 0x0D2A5C
GUILD_GREEN = 0x0D4A2A

# ══════════════════════════════════════════════════════════════════════
#  الفئات — Classes
# ══════════════════════════════════════════════════════════════════════
CLASSES: dict[str, dict] = {
    "سيد النصل": {
        "emoji": "⚔️",
        "bonus": "ضرر المبارزة +20%",
        "stat":  "strength",
        "desc":  "عدواني ومباشر. يتفوق في المبارزات والمواجهات المباشرة.",
        "color": CRIMSON,
    },
    "ساحر الظلام": {
        "emoji": "🔮",
        "bonus": "احتمالية الأحداث النادرة +30%",
        "stat":  "fortune",
        "desc":  "غامض وفوضوي. يعتمد على الحظ والأحداث غير المتوقعة.",
        "color": VIOLET,
    },
    "حارس الحديد": {
        "emoji": "🛡️",
        "bonus": "الضرر في الزنزانة -40%",
        "stat":  "endurance",
        "desc":  "صلب لا يُهزم. يتفوق في الزنازين والتحمل الطويل.",
        "color": STEEL,
    },
    "الشبح": {
        "emoji": "🗡️",
        "bonus": "ذهب السطو +25%",
        "stat":  "cunning",
        "desc":  "خفي وذكي. يتفوق في الاستطلاع والتسلل والسطو.",
        "color": 0x2C0A3A,
    },
    "حافظ العلم": {
        "emoji": "💚",
        "bonus": "الخبرة من كل الأنشطة +50%",
        "stat":  "fortune",
        "desc":  "عالم صبور. الأسرع في الارتقاء عبر الرتب.",
        "color": GUILD_GREEN,
    },
}

# ══════════════════════════════════════════════════════════════════════
#  الرتب — Ranks
# ══════════════════════════════════════════════════════════════════════
RANKS = [
    (0,      1, "🪨  فلاح الحجر"),
    (500,    2, "⚔️  جندي الحديد"),
    (1500,   3, "🛡️  فارس البرونز"),
    (4000,   4, "🥈  حارس الفضة"),
    (10000,  5, "🥇  قائد الذهب"),
    (25000,  6, "💎  جنرال الماس"),
    (60000,  7, "👑  إمبراطور الأوبسيديان"),
]
RANK_DISCOUNTS = {1: 0, 2: 5, 3: 10, 4: 15, 5: 20, 6: 25, 7: 30}

def get_rank(xp: int) -> tuple[int, str]:
    r = (1, "🪨  فلاح الحجر")
    for threshold, level, name in RANKS:
        if xp >= threshold:
            r = (level, name)
    return r

def xp_to_next(xp: int) -> int:
    for threshold, level, name in RANKS:
        if xp < threshold:
            return threshold - xp
    return 0

# ══════════════════════════════════════════════════════════════════════
#  سيناريوهات المغامرة اليومية (20 سيناريو)
# ══════════════════════════════════════════════════════════════════════
EXPEDITION_SCENARIOS = [
    {
        "text": "🌑 تدخل غابة الرماد عند الغسق. تاجر بقبعة سوداء يسد طريقك، عيناه تلمعان بغرابة مثيرة للقلق.",
        "choices": [
            {"label": "أ) اسحب سيفك وأجبره على الكلام",     "stat": "strength", "thresh": 12},
            {"label": "ب) اعرض عليه رشوة من جيبك",           "stat": "fortune",  "thresh": 10},
            {"label": "ج) تسلل خلفه في ظلام الأشجار",        "stat": "cunning",  "thresh": 11},
        ],
    },
    {
        "text": "⚗️ تجد خرائب معبد قديم. في مركزه صندوق يتوهج بضوء ذهبي، محاط بنقوش تحذيرية باللغة القديمة.",
        "choices": [
            {"label": "أ) افتح الصندوق مباشرة دون تفكير",     "stat": "fortune",  "thresh": 13},
            {"label": "ب) ادرس النقوش بعناية قبل المساس به",  "stat": "cunning",  "thresh": 11},
            {"label": "ج) اعترض الطريق وكسره بقوة",           "stat": "strength", "thresh": 14},
        ],
    },
    {
        "text": "🏚️ تسمع بكاء في منزل مهجور وسط السهل. يخبرك السكان أن أشباحاً تسكنه منذ قرن.",
        "choices": [
            {"label": "أ) ادخل وواجه ما بداخله",              "stat": "strength", "thresh": 11},
            {"label": "ب) راقب المنزل من بعيد أولاً",         "stat": "cunning",  "thresh": 10},
            {"label": "ج) ابتعد وتجاهل الأمر تماماً",         "stat": "endurance","thresh": 9},
        ],
    },
    {
        "text": "🌊 تصل إلى ميناء صغير. قبطان سفينة يعرض عليك صفقة غريبة: مرافقته إلى جزيرة مجهولة مقابل كنز.",
        "choices": [
            {"label": "أ) اقبل الصفقة بلا تردد",              "stat": "fortune",  "thresh": 12},
            {"label": "ب) فاوضه على حصة أكبر من الكنز",       "stat": "cunning",  "thresh": 11},
            {"label": "ج) ارفض وامضِ في طريقك",               "stat": "endurance","thresh": 8},
        ],
    },
    {
        "text": "🔥 لصوص يهاجمون قافلة تجار أمامك. التجار يصرخون طلباً للنجدة. اللصوص مسلحون جيداً.",
        "choices": [
            {"label": "أ) اندفع لإنقاذ التجار",               "stat": "strength", "thresh": 13},
            {"label": "ب) خطط لهجوم مباغت من الخلف",          "stat": "cunning",  "thresh": 11},
            {"label": "ج) اختبئ حتى ينتهي القتال",            "stat": "endurance","thresh": 9},
        ],
    },
    {
        "text": "🌿 تعثر على عشاب يبيع دواء غريباً يدّعي أنه يمنح قوة خارقة. مظهره موثوق لكن الثمن مرتفع.",
        "choices": [
            {"label": "أ) اشترِ العشب وتجرعه فوراً",           "stat": "fortune",  "thresh": 11},
            {"label": "ب) تفاوض معه لتخفيض السعر",             "stat": "cunning",  "thresh": 10},
            {"label": "ج) ارفض وواصل طريقك",                   "stat": "endurance","thresh": 7},
        ],
    },
    {
        "text": "⛰️ في منتصف الممر الجبلي، يسدّه ذئب ضخم ينظر إليك بعيون حمراء. الطريق الوحيدة تمر من أمامه.",
        "choices": [
            {"label": "أ) واجه الذئب مباشرة",                  "stat": "strength", "thresh": 12},
            {"label": "ب) ابحث عن طريق بديل",                  "stat": "cunning",  "thresh": 10},
            {"label": "ج) ابقَ ثابتاً وانتظر حتى يمل",         "stat": "endurance","thresh": 11},
        ],
    },
    {
        "text": "🎭 أمير مقنّع يدعوك لحفلة في قصره. كل المدعوين يرتدون أقنعة وتشعر أن شيئاً مريباً يدور.",
        "choices": [
            {"label": "أ) اقبل الدعوة وادخل القصر",            "stat": "fortune",  "thresh": 12},
            {"label": "ب) تجسس على القصر من الخارج أولاً",     "stat": "cunning",  "thresh": 11},
            {"label": "ج) ارفض الدعوة بلباقة",                  "stat": "endurance","thresh": 8},
        ],
    },
    {
        "text": "📜 تجد خريطة قديمة دفنها شخص ما بعجلة. تشير إلى كنز في الوادي المحظور المليء بالأفاعي.",
        "choices": [
            {"label": "أ) توجه فوراً إلى الوادي",              "stat": "strength", "thresh": 12},
            {"label": "ب) ابحث عن معلومات قبل الذهاب",         "stat": "cunning",  "thresh": 10},
            {"label": "ج) بِع الخريطة لمن يرغب",               "stat": "fortune",  "thresh": 11},
        ],
    },
    {
        "text": "🌙 في منتصف الليل، تستيقظ على صوت خطوات خارج خيمتك. ظل ضخم يمر أمام نسيج الخيمة.",
        "choices": [
            {"label": "أ) اخرج فوراً بسيفك مسلولاً",           "stat": "strength", "thresh": 11},
            {"label": "ب) اختبئ وانتظر ترى ما يحدث",           "stat": "cunning",  "thresh": 10},
            {"label": "ج) اصنع ضجيجاً لإخافة الكائن",          "stat": "fortune",  "thresh": 9},
        ],
    },
    {
        "text": "🏛️ بائع في السوق يعرض عليك قطعة أثرية نادرة بسعر رخيص مريب. يبدو قلقاً ويلتفت كثيراً.",
        "choices": [
            {"label": "أ) اشترِ القطعة فوراً",                  "stat": "fortune",  "thresh": 10},
            {"label": "ب) اسأله عن مصدرها بدهاء",               "stat": "cunning",  "thresh": 11},
            {"label": "ج) أبلغ الحرس عن الأمر",                 "stat": "endurance","thresh": 8},
        ],
    },
    {
        "text": "🌋 جماعة تُنجز طقوساً غريبة حول بركان نائم. يلتفتون إليك ويدعونك للانضمام إليهم.",
        "choices": [
            {"label": "أ) انضم إليهم ببسالة",                   "stat": "fortune",  "thresh": 13},
            {"label": "ب) راقبهم من بعيد وسجّل ما تشاهد",      "stat": "cunning",  "thresh": 10},
            {"label": "ج) ابتعد بسرعة من المنطقة",              "stat": "endurance","thresh": 9},
        ],
    },
    {
        "text": "🐉 أثناء تسلق الجبل تجد بيضة تنين ضخمة مكسورة. صغير التنين ينظر إليك بعيون ذهبية.",
        "choices": [
            {"label": "أ) حاول ترويضه",                        "stat": "fortune",  "thresh": 14},
            {"label": "ب) اتركه وانسحب بهدوء",                  "stat": "cunning",  "thresh": 10},
            {"label": "ج) احمله معك",                           "stat": "strength", "thresh": 12},
        ],
    },
    {
        "text": "⚓ سفينة تغرق قريباً. تسمع صرخات الغرقى. زورق الإنقاذ الوحيد يتسع لشخصين فقط.",
        "choices": [
            {"label": "أ) اقفز إلى البحر لإنقاذ من تستطيع",    "stat": "strength", "thresh": 13},
            {"label": "ب) انتشل أقرب شخصين بذكاء",              "stat": "cunning",  "thresh": 11},
            {"label": "ج) أشِر إلى الزورق الآخر البعيد",        "stat": "fortune",  "thresh": 10},
        ],
    },
    {
        "text": "🌺 ساحرة عجوز تعيش في الغابة تعرض قراءة مستقبلك مقابل أسرارك. تشعر بأنها لا تكذب.",
        "choices": [
            {"label": "أ) أخبرها بكل أسرارك",                   "stat": "fortune",  "thresh": 11},
            {"label": "ب) أعطها سراً صغيراً غير مهم",           "stat": "cunning",  "thresh": 11},
            {"label": "ج) ارفض العرض",                          "stat": "endurance","thresh": 8},
        ],
    },
    {
        "text": "💎 في كهف مظلم تجد منجماً مهجوراً مليئاً بالمعادن الثمينة. لكن الصخور فوقك تبدو هشة.",
        "choices": [
            {"label": "أ) احفر بسرعة وأخذ ما تستطيع",          "stat": "strength", "thresh": 12},
            {"label": "ب) ادرس البنية قبل الحفر",               "stat": "cunning",  "thresh": 11},
            {"label": "ج) عُد لاحقاً بمعدات مناسبة",            "stat": "endurance","thresh": 10},
        ],
    },
    {
        "text": "👤 غريب يدّعي أنه يعرف سر كنز عظيم ويعرض مشاركتك. لكن ملابسه ممزقة وعيناه قلقتان.",
        "choices": [
            {"label": "أ) ثق به وتبعه فوراً",                   "stat": "fortune",  "thresh": 12},
            {"label": "ب) اختبر صدقه بأسئلة ذكية",              "stat": "cunning",  "thresh": 11},
            {"label": "ج) ارفض وأخبره أنك لا تثق بالغرباء",    "stat": "endurance","thresh": 9},
        ],
    },
    {
        "text": "🏺 تجد مزهرية قديمة في أنقاض قصر محروق. تصدر منها همهمة غريبة وضوء خافت من الداخل.",
        "choices": [
            {"label": "أ) افتح المزهرية وانظر ما بداخلها",      "stat": "fortune",  "thresh": 12},
            {"label": "ب) ادرس النقوش على سطحها",               "stat": "cunning",  "thresh": 10},
            {"label": "ج) اكسرها بحجر من بعيد",                 "stat": "strength", "thresh": 11},
        ],
    },
    {
        "text": "🌫️ ضباب كثيف يحيط بك فجأة وسط الطريق. أصوات غريبة تأتي من كل الاتجاهات. بوصلتك تدور بجنون.",
        "choices": [
            {"label": "أ) اتحرك بثقة نحو الأصوات",              "stat": "strength", "thresh": 11},
            {"label": "ب) اجلس وانتظر حتى يتبدد الضباب",        "stat": "endurance","thresh": 12},
            {"label": "ج) اتبع الغريزة وامشِ نحو الضوء الخافت", "stat": "fortune",  "thresh": 11},
        ],
    },
    {
        "text": "🎪 سيرك متجول يعرض عروضاً سحرية. صاحبه يدّعي قدرته على مضاعفة ثروتك في لحظة.",
        "choices": [
            {"label": "أ) جرّب الحظ وأعطه جزءاً من شظاياك",    "stat": "fortune",  "thresh": 13},
            {"label": "ب) ابحث عن الحيلة وراء عرضه",            "stat": "cunning",  "thresh": 11},
            {"label": "ج) امضِ دون الاكتراث",                    "stat": "endurance","thresh": 8},
        ],
    },
]

# ══════════════════════════════════════════════════════════════════════
#  نبوءات العرّاف (20 نبوءة)
# ══════════════════════════════════════════════════════════════════════
ORACLE_PROPHECIES = [
    ("الظل يخدم اليد الصابرة — دع الآخرين يتحركون أولاً.",        True),
    ("الذهب يعمي عيون التاجر لا عيون المحارب.",                   True),
    ("ثلاثة طرق تمتد أمامك. الطريق الأوسط كذبة.",                 False),
    ("ما تخشاه في الظلام يخشاك أكثر مما تظن.",                    True),
    ("الصبر أحدّ من أي سيف — لا تبادر بالضربة الأولى.",           True),
    ("الحجر الصامت يحمل سر الكنز الأعظم.",                        False),
    ("من يمشي بصمت يصل أبعد ممن يجري بضوضاء.",                   True),
    ("النجم الساقط يجلب الحظ لمن يمسكه قبل أن يلمس الأرض.",       False),
    ("ثق بأول حدس يخطر في ذهنك — العقل يكذب أحياناً والحدس لا.",  True),
    ("ما يبدو كنزاً قد يكون فخاً، وما يبدو خطراً قد يكون نجاةً.", False),
    ("القوة لا تُقاس بالعضلات — من يصمد أخيراً هو الأقوى.",       True),
    ("الطريق المسدود يخفي باباً سرياً لمن يتدبر.",                 True),
    ("الفراغ الكبير يسبق دائماً الامتلاء الأكبر.",                 False),
    ("حين تقابل ذئباً، لا تجرِ — الجري يستدعي الصيد.",            True),
    ("الشجرة التي تنحني في العاصفة تنجو؛ الصلبة تنكسر.",          True),
    ("الثروة الحقيقية لا توجد في أعمق الكهوف بل في أقرب قرار.",   False),
    ("الغموض سلاح — من لا يُعرف لا يُستهدف.",                     True),
    ("الخيار الثالث دائماً الأذكى حين يبدو الموقف ثنائياً.",       False),
    ("الضوء الخافت في آخر الممر ليس نهاية — بل بداية.",            True),
    ("حين يمد الجميع يدهم، أنتَ أمسك إليهم.",                     False),
]

# ══════════════════════════════════════════════════════════════════════
#  المتجر — Store Catalog
# ══════════════════════════════════════════════════════════════════════
STORE_CATEGORIES = {
    "🎖️ إضافات خاصة": [
        {"id": "pass_expedition", "name": "🎯 تصريح مغامرة إضافية", "price": 800,  "type": "pass",
         "desc": "يلغي انتظار المغامرة اليومية مرة واحدة", "pass_key": "last_expedition"},
        {"id": "pass_dungeon",    "name": "🏰 تصريح زنزانة طارئة",  "price": 1200, "type": "pass",
         "desc": "يلغي انتظار الزنزانة الأسبوعية مرة واحدة", "pass_key": "last_dungeon"},
        {"id": "pass_duel",       "name": "⚔️ تصريح مبارزة إضافية", "price": 600,  "type": "pass",
         "desc": "يلغي انتظار المبارزة مرة واحدة", "pass_key": "last_duel"},
        {"id": "boost_shards",    "name": "💎 مضاعف الشظايا",        "price": 1500, "type": "boost",
         "desc": "شظايا المغامرة ×2 لمدة 24 ساعة", "effect": "مضاعف_شظايا"},
        {"id": "streak_shield",   "name": "🛡️ درع السلسلة",         "price": 1000, "type": "special",
         "desc": "يحمي سلسلتك من الانقطاع مرة واحدة", "effect": "درع_سلسلة"},
    ],
    "✨ شارات الملف": [
        {"id": "badge_dragon", "name": "🐉 قاتل التنين",         "price": 1500, "type": "badge",   "desc": "شارة على ملفك الشخصي"},
        {"id": "badge_owl",    "name": "🌙 بومة الليل",           "price": 1000, "type": "badge",   "desc": "شارة على ملفك الشخصي"},
        {"id": "badge_star",   "name": "⭐ نجم الإمبراطورية",     "price": 1200, "type": "badge",   "desc": "شارة مضيئة نادرة"},
    ],
    "⚗️ جرعات ومعدات": [
        {"id": "potion_str",   "name": "🍶 جرعة قوة",            "price": 400,  "type": "potion",  "desc": "قوة +30% للمغامرة القادمة", "effect": "قوة_مؤقتة"},
        {"id": "potion_heal",  "name": "🌿 عشبة الشفاء",          "price": 300,  "type": "potion",  "desc": "يزيل تأثير 'مجروح' فوراً",  "effect": "شفاء"},
        {"id": "potion_luck",  "name": "✨ بلورة الحظ",           "price": 500,  "type": "potion",  "desc": "حظ +50% للمغامرة القادمة",  "effect": "حظ_مؤقت"},
        {"id": "equip_blade",  "name": "🗡️ شفرة الظل",           "price": 1200, "type": "equip",   "desc": "دهاء +10 دائم",             "stat": "cunning",  "bonus": 10},
        {"id": "equip_armor",  "name": "🛡️ درع الرماد",          "price": 1200, "type": "equip",   "desc": "تحمل +10 دائم",             "stat": "endurance","bonus": 10},
        {"id": "eye_oracle",   "name": "🔮 عين العرّاف",          "price": 900,  "type": "special", "desc": "نبوءة مضمونة صحيحة (مرة)",  "effect": "عين_عراف"},
    ],
    "🎮 معدلات الألعاب": [
        {"id": "mod_double",   "name": "🃏 نقاط مضاعفة",          "price": 500,  "type": "mod",     "desc": "نقاط ×2 في لعبة التخمين القادمة", "effect": "نقاط_مضاعفة"},
        {"id": "mod_hint",     "name": "💡 رمز تلميح",            "price": 350,  "type": "mod",     "desc": "يكشف فئة البطل في لعبة الصور",    "effect": "تلميح"},
        {"id": "mod_shield",   "name": "🛡️ درع الليل",           "price": 900,  "type": "mod",     "desc": "لا يمكن قتلك ليلاً في ماافيا",    "effect": "درع_ماافيا"},
    ],
    "🎁 صندوق الغموض": [
        {"id": "mystery_box",  "name": "🎁 صندوق الغموض",         "price": 750,  "type": "mystery", "desc": "محتوى عشوائي مفاجئ! (مرة/أسبوع)"},
    ],
}

# محتويات صندوق الغموض
MYSTERY_CONTENTS = [
    (40, "shards",  400,              "💰 حصلت على {v} شظية!"),
    (25, "item",    "potion_str",     "🍶 جرعة قوة!"),
    (15, "badge",   "badge_star",     "⭐ شارة نجم الإمبراطورية!"),
    (10, "pass",    "pass_dungeon",   "🏰 تصريح زنزانة طارئة!"),
    (7,  "shards",  2000,             "💰💰 حصلت على {v} شظية!"),
    (3,  "special", "streak_shield",  "🛡️ درع السلسلة — سلسلتك محمية!"),
]

# ══════════════════════════════════════════════════════════════════════
#  الوصفات — Crafting Recipes
# ══════════════════════════════════════════════════════════════════════
CRAFTING_RECIPES = [
    {
        "id": "craft_potion_str",
        "name": "🍶 جرعة قوة",
        "materials": {"عشبة مجففة": 2, "خام حديد": 1},
        "result_type": "potion",
        "result_id": "potion_str",
        "result_name": "جرعة قوة",
    },
    {
        "id": "craft_potion_luck",
        "name": "✨ بلورة الحظ",
        "materials": {"حجر الفراغ": 1, "غبار سحري": 2},
        "result_type": "potion",
        "result_id": "potion_luck",
        "result_name": "بلورة الحظ",
    },
    {
        "id": "craft_equip_blade",
        "name": "🗡️ شفرة الظل",
        "materials": {"قشرة تنين": 1, "جوهر ظلامي": 2},
        "result_type": "equip",
        "result_id": "equip_blade",
        "result_name": "شفرة الظل",
    },
    {
        "id": "craft_equip_armor",
        "name": "🛡️ درع الرماد",
        "materials": {"خام حديد": 2, "قشرة تنين": 1},
        "result_type": "equip",
        "result_id": "equip_armor",
        "result_name": "درع الرماد",
    },
    {
        "id": "craft_eye",
        "name": "🔮 عين العرّاف",
        "materials": {"بلورة الفراغ": 1, "شظية الروح": 1},
        "result_type": "special",
        "result_id": "eye_oracle",
        "result_name": "عين العرّاف",
    },
]

# المواد الممكنة (تسقط من المغامرات والزنازين)
MATERIALS_COMMON   = ["عشبة مجففة", "خام حديد", "عظام محطمة"]
MATERIALS_UNCOMMON = ["جوهر ظلامي", "غبار سحري", "حجر الفراغ"]
MATERIALS_RARE     = ["قشرة تنين", "بلورة الفراغ", "شظية الروح"]

# ══════════════════════════════════════════════════════════════════════
#  الألقاب — Titles
# ══════════════════════════════════════════════════════════════════════
TITLES_CATALOG = [
    {"id": "relentless",  "name": "«الذي لا يتوقف»",     "req": "أتم 10 مغامرات"},
    {"id": "dungeon",     "name": "«ناهب الزنازين»",      "req": "اجتاز 5 زنازين"},
    {"id": "deceiver",    "name": "«أبو خداع»",           "req": "فاز بـ5 مبارزات"},
    {"id": "streak30",    "name": "«صوت الإمبراطورية»",   "req": "سلسلة 30 يوم"},
    {"id": "rich",        "name": "«خزينة الإمبراطورية»", "req": "جمع 50,000 شظية"},
    {"id": "max_rank",    "name": "«الإمبراطور الأول»",   "req": "وصل للرتبة 7"},
]

# ══════════════════════════════════════════════════════════════════════
#  تأثيرات الحالة — Status Effects
# ══════════════════════════════════════════════════════════════════════
STATUS_EFFECTS = {
    "مجروح":    {"emoji": "🩸", "desc": "معدل النجاح -20%",          "hours": 24},
    "مبارك":    {"emoji": "🌟", "desc": "جميع الفحوصات +15%",         "hours": 24},
    "ملعون":    {"emoji": "😵", "desc": "إحصائية عشوائية تنعكس",      "hours": 48},
    "منهك":     {"emoji": "💤", "desc": "خيارات دفاعية فقط في المبارزة","hours": 12},
    "مستعر":    {"emoji": "🔥", "desc": "ضرر المبارزة +40% لكن الدهاء ممنوع","hours": 24},
    "مظلل":     {"emoji": "🌑", "desc": "ذهب السطو +25% لكن النجاح -15%","hours": 36},
    "مشحون":    {"emoji": "⚡", "desc": "هجوم مؤكد في الزنزانة مرة",  "hours": 24},
}

# ══════════════════════════════════════════════════════════════════════
#  مساعدات البيانات — Data Helpers
# ══════════════════════════════════════════════════════════════════════

def _emp() -> dict:
    """Ensure empire section in db."""
    if "empire" not in db:
        db["empire"] = {"members": {}, "heist": {"active": False}, "config": {}}
    if "members" not in db["empire"]:
        db["empire"]["members"] = {}
    return db["empire"]

def _get_member(uid: str) -> Optional[dict]:
    return _emp()["members"].get(uid)

def _new_member(uid: str, cls: str) -> dict:
    return {
        "uid":              uid,
        "class":            cls,
        "stats":            {"strength": 10, "cunning": 10, "endurance": 10, "fortune": 10},
        "xp":               0,
        "shards":           200,
        "streak":           0,
        "last_daily":       None,
        "last_expedition":  None,
        "last_dungeon":     None,
        "last_duel":        None,
        "last_oracle":      None,
        "last_mystery":     None,
        "active_effects":   [],
        "inventory":        {"potions": [], "equip": [], "special": [], "materials": {}, "badges": []},
        "equipped":         {},
        "titles":           [],
        "active_title":     None,
        "created_at":       datetime.utcnow().isoformat(),
        "total_expeditions": 0,
        "total_dungeons":   0,
        "total_duels_won":  0,
        "total_heists":     0,
    }

def _save():
    save_db(db)

def _cd_ok(md: dict, key: str, hours: float) -> bool:
    """True if cooldown has passed."""
    last = md.get(key)
    if not last: return True
    try:
        dt = datetime.fromisoformat(last)
        return datetime.utcnow() >= dt + timedelta(hours=hours)
    except Exception:
        return True

def _cd_remaining(md: dict, key: str, hours: float) -> str:
    """Human-readable time remaining on cooldown."""
    last = md.get(key)
    if not last: return "0 دقيقة"
    try:
        dt      = datetime.fromisoformat(last)
        expires = dt + timedelta(hours=hours)
        delta   = expires - datetime.utcnow()
        if delta.total_seconds() <= 0: return "0 دقيقة"
        total_m = int(delta.total_seconds() // 60)
        h, m    = divmod(total_m, 60)
        if h > 0: return f"{h} ساعة و{m} دقيقة"
        return f"{m} دقيقة"
    except Exception:
        return "؟"

def award_xp(md: dict, amount: int) -> tuple[int, bool]:
    """Award XP, return (new_xp, ranked_up)."""
    cls_info   = CLASSES.get(md["class"], {})
    multiplier = 1.5 if md["class"] == "حافظ العلم" else 1.0
    actual     = int(amount * multiplier)
    old_rank   = get_rank(md["xp"])[0]
    md["xp"]  += actual
    new_rank   = get_rank(md["xp"])[0]
    return actual, (new_rank > old_rank)

def award_shards(md: dict, amount: int):
    md["shards"] = md.get("shards", 0) + amount

def has_effect(md: dict, effect: str) -> bool:
    now = datetime.utcnow()
    for e in md.get("active_effects", []):
        if e["name"] == effect:
            try:
                if datetime.fromisoformat(e["expires"]) > now:
                    return True
            except Exception:
                pass
    return False

def apply_effect(md: dict, effect: str):
    hours = STATUS_EFFECTS.get(effect, {}).get("hours", 24)
    clean_effects(md)
    md["active_effects"] = [e for e in md["active_effects"] if e["name"] != effect]
    md["active_effects"].append({
        "name":    effect,
        "expires": (datetime.utcnow() + timedelta(hours=hours)).isoformat(),
    })

def clean_effects(md: dict):
    now = datetime.utcnow()
    md["active_effects"] = [
        e for e in md.get("active_effects", [])
        if (lambda x: datetime.fromisoformat(x) > now if x else False)(e.get("expires"))
    ]

def stat_check(md: dict, stat: str, threshold: int) -> bool:
    """Roll a stat check. Returns True on success."""
    base    = md["stats"].get(stat, 10)
    equip   = md.get("equipped", {})
    bonus   = 0
    # Equipment bonuses
    if "equip_blade"  in equip and stat == "cunning":   bonus += 10
    if "equip_armor"  in equip and stat == "endurance": bonus += 10
    # Class bonus on primary stat
    cls_stat = CLASSES.get(md["class"], {}).get("stat", "")
    if cls_stat == stat: bonus += 3
    # Effect modifiers
    if has_effect(md, "مبارك"):  bonus += 3
    if has_effect(md, "مجروح"): bonus -= 4
    if has_effect(md, "ملعون"): bonus -= random.randint(0, 5)
    effective = base + bonus
    roll      = random.randint(1, 20)
    return (effective + roll) >= threshold

def apply_rank_role(guild: discord.Guild, member: discord.Member, rank: int):
    """Best-effort: does not crash if roles don't exist."""
    pass  # Admin can manually assign Discord roles based on /leaderboard

def check_titles(md: dict):
    earned = md.get("titles", [])
    if md.get("total_expeditions", 0) >= 10   and "relentless" not in earned: earned.append("relentless")
    if md.get("total_dungeons", 0)    >= 5    and "dungeon"    not in earned: earned.append("dungeon")
    if md.get("total_duels_won", 0)   >= 5    and "deceiver"   not in earned: earned.append("deceiver")
    if md.get("streak", 0)            >= 30   and "streak30"   not in earned: earned.append("streak30")
    if md.get("shards", 0)            >= 50000 and "rich"      not in earned: earned.append("rich")
    if get_rank(md.get("xp", 0))[0]  >= 7    and "max_rank"   not in earned: earned.append("max_rank")
    md["titles"] = earned

def build_character_embed(member: discord.Member, md: dict) -> discord.Embed:
    clean_effects(md)
    rank_lvl, rank_name = get_rank(md["xp"])
    cls_info   = CLASSES.get(md["class"], {})
    next_xp    = xp_to_next(md["xp"])
    equipped   = md.get("equipped", {})
    effects    = md.get("active_effects", [])
    titles_raw = md.get("titles", [])
    active_t   = md.get("active_title")

    title_name = next(
        (t["name"] for t in TITLES_CATALOG if t["id"] == active_t), ""
    ) if active_t else ""

    e = discord.Embed(
        title=f"{cls_info.get('emoji','⚔️')}  {member.display_name}  {title_name}",
        description=(
            f"{SEP}\n"
            f"*محارب الإمبراطورية المظلمة*\n"
            f"{SEP}"
        ),
        color=cls_info.get("color", GOLD),
    )
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="🏷️ الفئة",        value=f"{cls_info.get('emoji','')} {md['class']}", inline=True)
    e.add_field(name="👑 الرتبة",        value=rank_name,                                   inline=True)
    e.add_field(name="🖤 الشظايا",       value=f"**{md.get('shards',0):,}**",               inline=True)
    e.add_field(name="⭐ الخبرة",        value=f"**{md.get('xp',0):,}**" + (f"  *(التالية: {next_xp:,})*" if next_xp else " *(أقصى رتبة!)*"), inline=True)
    e.add_field(name="🔥 السلسلة",       value=f"**{md.get('streak',0)}** يوم",              inline=True)
    e.add_field(name="📊 الإحصائيات",
        value=(
            f"💪 قوة: **{md['stats']['strength'] + equipped.get('str_bonus',0)}**  "
            f"🧠 دهاء: **{md['stats']['cunning'] + (10 if 'equip_blade' in equipped else 0)}**\n"
            f"🏃 تحمل: **{md['stats']['endurance'] + (10 if 'equip_armor' in equipped else 0)}**  "
            f"🍀 حظ: **{md['stats']['fortune']}**"
        ), inline=False)
    if effects:
        eff_lines = []
        for eff in effects:
            info = STATUS_EFFECTS.get(eff["name"], {})
            try:
                exp = datetime.fromisoformat(eff["expires"])
                remaining = int((exp - datetime.utcnow()).total_seconds() // 3600)
                eff_lines.append(f"{info.get('emoji','✨')} {eff['name']} ({remaining}h)")
            except Exception:
                pass
        if eff_lines:
            e.add_field(name="✨ التأثيرات النشطة", value="  ".join(eff_lines), inline=False)
    if titles_raw:
        title_names = [t["name"] for t in TITLES_CATALOG if t["id"] in titles_raw]
        if title_names:
            e.add_field(name="🏅 الألقاب المكتسبة", value="  ·  ".join(title_names[:5]), inline=False)
    e.set_footer(text="⚜  الإمبراطورية المظلمة  ·  سجلات الشرف",
                 icon_url=logo_url() or discord.utils.MISSING)
    return e

# ══════════════════════════════════════════════════════════════════════
#  إنشاء الشخصية — Character Creation
# ══════════════════════════════════════════════════════════════════════

class ClassSelectionView(View):
    def __init__(self, uid: str):
        super().__init__(timeout=180)
        self.uid = uid
        opts = [
            discord.SelectOption(
                label=f"{info['emoji']} {cls_name}",
                value=cls_name,
                description=info["bonus"][:100],
            )
            for cls_name, info in CLASSES.items()
        ]
        sel = Select(placeholder="⚔️  اختر فئتك في الإمبراطورية…", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        if str(i.user.id) != self.uid:
            await i.response.send_message("❌ ليس ملفك.", ephemeral=True); return
        cls      = i.data["values"][0]
        cls_info = CLASSES[cls]
        md       = _new_member(self.uid, cls)
        _emp()["members"][self.uid] = md
        _save()
        e = discord.Embed(
            title=f"{cls_info['emoji']}  مرحباً في الإمبراطورية!",
            description=(
                f"{SEP}\n"
                f"فئتك: **{cls_info['emoji']} {cls}**\n\n"
                f"{cls_info['desc']}\n\n"
                f"**ميزتك:** {cls_info['bonus']}\n\n"
                f"تبدأ بـ **200 شظية** 🖤  في جيبك.\n"
                f"استخدم لوحة الإمبراطورية للمغامرة!\n"
                f"{SEP}"
            ), color=cls_info["color"])
        brand(e, thumb=False)
        self.stop()
        await i.response.edit_message(embed=e, view=None)
        await log_action(i.guild, "⚔️ محارب جديد",
            f"{i.user.mention} انضم كـ **{cls}**")

# ══════════════════════════════════════════════════════════════════════
#  المغامرة اليومية — Daily Expedition
# ══════════════════════════════════════════════════════════════════════

class ExpeditionView(View):
    def __init__(self, uid: str, scenario: dict, channel_id: int):
        super().__init__(timeout=300)
        self.uid        = uid
        self.scenario   = scenario
        self.channel_id = channel_id
        for idx, ch in enumerate(scenario["choices"]):
            labels = ["أ)", "ب)", "ج)"]
            btn = Button(
                label=ch["label"][:80],
                style=[discord.ButtonStyle.primary, discord.ButtonStyle.success,
                       discord.ButtonStyle.secondary][idx],
                row=0,
            )
            btn.callback = self._make_cb(ch)
            self.add_item(btn)

    def _make_cb(self, choice: dict):
        async def cb(i: discord.Interaction):
            if str(i.user.id) != self.uid:
                await i.response.send_message("❌ مغامرتك أنت.", ephemeral=True); return
            self.stop()
            md      = _get_member(self.uid)
            success = stat_check(md, choice["stat"], choice["thresh"])
            partial = not success and random.random() < 0.35

            if success:
                base_shards = random.randint(150, 300)
                shards = base_shards * 2 if has_effect(md, "مضاعف_شظايا") else base_shards
                xp_amt = 120
                mat    = random.choice(MATERIALS_COMMON + MATERIALS_UNCOMMON)
                inv_m  = md["inventory"].setdefault("materials", {})
                inv_m[mat] = inv_m.get(mat, 0) + random.randint(1, 2)
                award_shards(md, shards)
                gained_xp, ranked = award_xp(md, xp_amt)
                md["total_expeditions"] = md.get("total_expeditions", 0) + 1
                check_titles(md)
                md["last_expedition"] = datetime.utcnow().isoformat()
                _save()
                result = (
                    f"✅ **نجاح كامل!**\n\n"
                    f"حصلت على **{shards:,}** 🖤 و**{gained_xp}** ⭐ خبرة\n"
                    f"مادة نادرة: **{mat}**"
                    + (f"\n\n🎉 **ارتقيت رتبة!** — {get_rank(md['xp'])[1]}" if ranked else "")
                )
                color = EMERALD
            elif partial:
                shards = random.randint(50, 100)
                xp_amt = 50
                eff    = random.choice(list(STATUS_EFFECTS.keys()))
                award_shards(md, shards)
                gained_xp, ranked = award_xp(md, xp_amt)
                apply_effect(md, eff)
                md["total_expeditions"] = md.get("total_expeditions", 0) + 1
                md["last_expedition"] = datetime.utcnow().isoformat()
                _save()
                eff_info = STATUS_EFFECTS.get(eff, {})
                result = (
                    f"⚠️ **نجاح جزئي!**\n\n"
                    f"حصلت على **{shards:,}** 🖤 و**{gained_xp}** ⭐ خبرة\n"
                    f"لكن تأثير **{eff_info.get('emoji','')} {eff}** أصابك!"
                )
                color = AMBER
            else:
                xp_amt = 20
                eff    = "مجروح"
                gained_xp, _ = award_xp(md, xp_amt)
                apply_effect(md, eff)
                md["last_expedition"] = datetime.utcnow().isoformat()
                _save()
                result = (
                    f"💀 **فشل!**\n\n"
                    f"حصلت على **{gained_xp}** ⭐ خبرة (تعزية)\n"
                    f"أصابك تأثير 🩸 **{eff}** لـ24 ساعة"
                )
                color = CRIMSON

            e = discord.Embed(
                title="📜  نتيجة المغامرة",
                description=f"{SEP}\n{result}\n{SEP}",
                color=color,
            )
            brand(e)
            await i.response.edit_message(embed=e, view=None)
        return cb

# ══════════════════════════════════════════════════════════════════════
#  الزنزانة — Dungeon System
# ══════════════════════════════════════════════════════════════════════

DUNGEON_ROOMS = [
    {"type": "combat",   "emoji": "⚔️",  "name": "غرفة القتال",    "stat": "strength",  "thresh": 12},
    {"type": "puzzle",   "emoji": "🧠",  "name": "غرفة الألغاز",   "stat": "cunning",   "thresh": 11},
    {"type": "trap",     "emoji": "🕸️", "name": "غرفة الفخاخ",    "stat": "endurance", "thresh": 11},
    {"type": "treasure", "emoji": "💰",  "name": "غرفة الكنوز",    "stat": "fortune",   "thresh": 10},
    {"type": "npc",      "emoji": "🧙",  "name": "لقاء الغريب",    "stat": "cunning",   "thresh": 10},
]
DUNGEON_CHOICES = {
    "combat":   [("اهجم بقوة",  "strength"), ("احاصره بذكاء","cunning"), ("ادافع وانتظر","endurance")],
    "puzzle":   [("فكّر بعمق",  "cunning"),  ("استخدم القوة","strength"),("جرّب الحظ",   "fortune")],
    "trap":     [("تجنبه بخفة", "cunning"),  ("تحمّل الضرر", "endurance"),("ارجع للخلف", "fortune")],
    "treasure": [("افتح الصندوق","fortune"),  ("ابحث بدقة",  "cunning"),  ("خذ كل شيء",  "strength")],
    "npc":      [("فاوضه",      "cunning"),  ("تحدّاه",      "strength"), ("تجاهله",     "endurance")],
}

active_dungeons: dict[int, dict] = {}  # user_id → dungeon state

class DungeonRoomView(View):
    def __init__(self, user_id: int, room_idx: int):
        super().__init__(timeout=300)
        self.user_id  = user_id
        self.room_idx = room_idx
        room    = DUNGEON_ROOMS[room_idx % len(DUNGEON_ROOMS)]
        choices = DUNGEON_CHOICES[room["type"]]
        labels  = ["أ)", "ب)", "ج)"]
        styles  = [discord.ButtonStyle.primary, discord.ButtonStyle.success, discord.ButtonStyle.secondary]
        for idx, (label, stat) in enumerate(choices):
            btn = Button(label=f"{labels[idx]} {label}", style=styles[idx], row=0)
            btn.callback = self._make_cb(stat)
            self.add_item(btn)
        # Force Exit button
        exit_btn = Button(label="🚪 اخرج من الزنزانة", style=discord.ButtonStyle.danger, row=1)
        exit_btn.callback = self._exit
        self.add_item(exit_btn)

    def _make_cb(self, stat: str):
        async def cb(i: discord.Interaction):
            if i.user.id != self.user_id:
                await i.response.send_message("❌ ليست زنزانتك.", ephemeral=True); return
            self.stop()
            state  = active_dungeons.get(self.user_id)
            if not state:
                await i.response.send_message("❌ لا توجد زنزانة نشطة.", ephemeral=True); return
            md     = _get_member(str(self.user_id))
            room   = DUNGEON_ROOMS[self.room_idx % len(DUNGEON_ROOMS)]
            success = stat_check(md, stat, room["thresh"])
            state["room"] = self.room_idx + 1
            loot_mat = None
            if success:
                reward = random.randint(80, 200)
                award_shards(md, reward)
                loot_mat = random.choice(MATERIALS_COMMON + MATERIALS_UNCOMMON)
                inv_m    = md["inventory"].setdefault("materials", {})
                inv_m[loot_mat] = inv_m.get(loot_mat, 0) + 1
                state["loot"] += reward
                result = f"✅ نجحت!  +{reward} 🖤  +{loot_mat}"
                color  = EMERALD
            else:
                dmg    = random.randint(15, 30)
                state["hp"] = max(0, state["hp"] - dmg)
                result = f"❌ فشلت! خسرت {dmg} نقطة حياة. (نقاط الحياة: {state['hp']}/100)"
                color  = CRIMSON
                if state["hp"] == 0:
                    active_dungeons.pop(self.user_id, None)
                    xp_g, _ = award_xp(md, 50)
                    _save()
                    e = discord.Embed(
                        title="💀  سقطت في الزنزانة!",
                        description=(
                            f"{SEP}\n"
                            f"نقاط حياتك وصلت للصفر.\n"
                            f"غنائمك: **{state['loot']}** 🖤 (محتفظ بها)\n"
                            f"خبرة: **{xp_g}** ⭐\n"
                            f"{SEP}"
                        ), color=CRIMSON)
                    brand(e)
                    await i.response.edit_message(embed=e, view=None)
                    return
            next_room = state["room"]
            if next_room >= 3:  # 3 rooms = dungeon cleared
                active_dungeons.pop(self.user_id, None)
                total_loot = state["loot"]
                xp_g, ranked = award_xp(md, 400)
                md["total_dungeons"] = md.get("total_dungeons", 0) + 1
                md["last_dungeon"]   = datetime.utcnow().isoformat()
                check_titles(md)
                _save()
                e = discord.Embed(
                    title="🏆  اجتزت الزنزانة!",
                    description=(
                        f"{SEP}\n"
                        f"نجحت في اجتياز **3 غرف**!\n\n"
                        f"**الغنائم الإجمالية:** {total_loot} 🖤\n"
                        f"**الخبرة:** {xp_g} ⭐"
                        + (f"\n🎉 **ارتقيت رتبة!** — {get_rank(md['xp'])[1]}" if ranked else "")
                        + f"\n{SEP}"
                    ), color=EMERALD)
                brand(e)
                await i.response.edit_message(embed=e, view=None)
                return
            _save()
            next_r  = DUNGEON_ROOMS[next_room % len(DUNGEON_ROOMS)]
            desc    = (
                f"{SEP}\n"
                f"الغرفة {next_room}/3  {result}\n\n"
                f"**الغرفة القادمة:** {next_r['emoji']} {next_r['name']}\n"
                f"نقاط الحياة: **{state['hp']}/100**  ·  الغنائم: **{state['loot']}** 🖤\n"
                f"{SEP}"
            )
            e = discord.Embed(title=f"🏰  الزنزانة — الغرفة {next_room + 1}/3",
                              description=desc, color=TEAL)
            brand(e)
            await i.response.edit_message(embed=e, view=DungeonRoomView(self.user_id, next_room))
        return cb

    async def _exit(self, i: discord.Interaction):
        if i.user.id != self.user_id:
            await i.response.send_message("❌ ليست زنزانتك.", ephemeral=True); return
        self.stop()
        state  = active_dungeons.pop(self.user_id, {})
        loot   = state.get("loot", 0)
        md     = _get_member(str(self.user_id))
        if md and loot:
            award_shards(md, loot)
            _save()
        await i.response.edit_message(
            embed=empire_embed("🚪  غادرت الزنزانة",
                               f"خرجت بسلام بـ **{loot}** 🖤 غنائم.", STEEL),
            view=None)
        # Public announcement


# ══════════════════════════════════════════════════════════════════════
#  المبارزة — Duel System
# ══════════════════════════════════════════════════════════════════════

active_duels: dict[str, dict] = {}  # f"{uid_a}_{uid_b}" → state

DUEL_ACTIONS = {
    "heavy":   {"ar": "⚔️ ضربة ثقيلة",       "dmg": (25, 40), "stat": "strength", "counter": "feint"},
    "feint":   {"ar": "🌀 خداع + هجمة مضادة", "dmg": (10, 20), "stat": "cunning",  "counter": "heavy"},
    "defend":  {"ar": "🛡️ موقف دفاعي",        "dmg": (5,  10), "stat": "endurance","counter": None},
    "precise": {"ar": "🎯 ضربة دقيقة",         "dmg": (15, 30), "stat": "fortune",  "counter": "defend"},
}

def _duel_key(uid_a: int, uid_b: int) -> str:
    return "_".join(str(x) for x in sorted([uid_a, uid_b]))

class DuelChallengeView(View):
    def __init__(self, challenger: discord.Member, target: discord.Member, duel_key: str):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.target     = target
        self.duel_key   = duel_key

    @discord.ui.button(label="✅ أقبل التحدي!", style=discord.ButtonStyle.success)
    async def accept(self, i: discord.Interaction, _: Button):
        if i.user.id != self.target.id:
            await i.response.send_message("❌ التحدي ليس لك.", ephemeral=True); return
        self.stop()
        active_duels[self.duel_key] = {
            "a": self.challenger.id, "b": self.target.id,
            "hp": {self.challenger.id: 100, self.target.id: 100},
            "round": 1, "choices": {}, "history": [],
        }
        await i.response.edit_message(
            embed=discord.Embed(
                title="⚔️  المبارزة بدأت!",
                description=(
                    f"{SEP}\n"
                    f"**{self.challenger.display_name}** ضد **{self.target.display_name}**\n\n"
                    f"الجولة 1 من 3 — يضغط كل لاعب على أحد الأزرار سراً\n"
                    f"{SEP}"
                ), color=CRIMSON),
            view=DuelRoundView(self.challenger, self.target, self.duel_key))

    @discord.ui.button(label="❌ أرفض", style=discord.ButtonStyle.danger)
    async def decline(self, i: discord.Interaction, _: Button):
        if i.user.id not in (self.challenger.id, self.target.id):
            await i.response.send_message("❌ ليس شأنك.", ephemeral=True); return
        self.stop()
        active_duels.pop(self.duel_key, None)
        await i.response.edit_message(
            embed=empire_embed("❌  رُفض التحدي", f"**{self.target.display_name}** رفض المبارزة.", STEEL),
            view=None)


class DuelRoundView(View):
    def __init__(self, p_a: discord.Member, p_b: discord.Member, duel_key: str):
        super().__init__(timeout=180)
        self.p_a      = p_a
        self.p_b      = p_b
        self.duel_key = duel_key
        for action_id, info in DUEL_ACTIONS.items():
            btn = Button(label=info["ar"], style=discord.ButtonStyle.secondary, row=0)
            btn.callback = self._make_cb(action_id)
            self.add_item(btn)

    def _make_cb(self, action_id: str):
        async def cb(i: discord.Interaction):
            if i.user.id not in (self.p_a.id, self.p_b.id):
                await i.response.send_message("❌ لست في هذه المبارزة.", ephemeral=True); return
            state = active_duels.get(self.duel_key)
            if not state:
                await i.response.send_message("❌ المبارزة انتهت.", ephemeral=True); return
            state["choices"][i.user.id] = action_id
            await i.response.send_message(
                f"✅ اخترت **{DUEL_ACTIONS[action_id]['ar']}** — انتظر خصمك…", ephemeral=True)
            if len(state["choices"]) >= 2:
                self.stop()
                await _resolve_duel_round(i.channel, self.p_a, self.p_b, self.duel_key)
        return cb


async def _resolve_duel_round(
    channel: discord.TextChannel,
    p_a: discord.Member, p_b: discord.Member,
    duel_key: str,
):
    state   = active_duels.get(duel_key)
    if not state: return
    ch_a    = state["choices"].get(p_a.id, "defend")
    ch_b    = state["choices"].get(p_b.id, "defend")
    md_a    = _get_member(str(p_a.id))
    md_b    = _get_member(str(p_b.id))
    state["choices"] = {}

    def calc_dmg(attacker_md, action_id, defender_action_id):
        info      = DUEL_ACTIONS[action_id]
        dmg_range = info["dmg"]
        dmg       = random.randint(*dmg_range)
        # Counter bonus
        if info.get("counter") == defender_action_id:
            dmg = int(dmg * 1.5)
        # Stat scaling
        stat    = info["stat"]
        s_val   = (attacker_md["stats"].get(stat, 10) if attacker_md else 10)
        dmg     += (s_val - 10) // 2
        # Defender reduces if defending
        if defender_action_id == "defend":
            dmg = max(5, int(dmg * 0.5))
        return max(1, dmg)

    dmg_a = calc_dmg(md_a, ch_a, ch_b)
    dmg_b = calc_dmg(md_b, ch_b, ch_a)
    state["hp"][p_b.id] -= dmg_a
    state["hp"][p_a.id] -= dmg_b
    state["hp"][p_a.id]  = max(0, state["hp"][p_a.id])
    state["hp"][p_b.id]  = max(0, state["hp"][p_b.id])

    round_num = state["round"]
    hp_a      = state["hp"][p_a.id]
    hp_b      = state["hp"][p_b.id]
    state["round"] += 1

    lines = [
        f"**{p_a.display_name}** استخدم {DUEL_ACTIONS[ch_a]['ar']} → {dmg_a} ضرر",
        f"**{p_b.display_name}** استخدم {DUEL_ACTIONS[ch_b]['ar']} → {dmg_b} ضرر",
        f"",
        f"❤️ {p_a.display_name}: **{hp_a}**  ·  {p_b.display_name}: **{hp_b}**",
    ]

    game_over = (state["round"] > 3) or (hp_a == 0) or (hp_b == 0)

    if game_over:
        active_duels.pop(duel_key, None)
        if hp_a > hp_b:
            winner, loser = p_a, p_b
        elif hp_b > hp_a:
            winner, loser = p_b, p_a
        else:
            winner = None

        if winner:
            w_md = _get_member(str(winner.id))
            l_md = _get_member(str(loser.id))
            if w_md:
                award_shards(w_md, 200)
                award_xp(w_md, 150)
                w_md["total_duels_won"] = w_md.get("total_duels_won", 0) + 1
                check_titles(w_md)
            if l_md:
                award_shards(l_md, 50)
                award_xp(l_md, 50)
            _save()
            lines += ["", f"🏆 **{winner.display_name} فاز!**  +200 🖤  +150 ⭐"]
            color = EMERALD
            title = f"⚔️  انتهت الجولة {round_num} — {winner.display_name} الفائز!"
        else:
            for uid in [p_a.id, p_b.id]:
                m = _get_member(str(uid))
                if m:
                    award_shards(m, 80)
                    award_xp(m, 80)
            _save()
            lines += ["", "🤝 **تعادل!**  كلاهما يحصل على 80 🖤  80 ⭐"]
            color = GOLD
            title = f"⚔️  الجولة {round_num} — تعادل!"
        e = discord.Embed(title=title, description=f"{SEP}\n" + "\n".join(lines) + f"\n{SEP}", color=color)
        brand(e)
        await channel.send(embed=e)
    else:
        e = discord.Embed(
            title=f"⚔️  الجولة {round_num} / 3",
            description=f"{SEP}\n" + "\n".join(lines) + f"\n{SEP}\nالجولة {state['round']} — اختر حركتك:",
            color=AMBER)
        brand(e)
        await channel.send(embed=e, view=DuelRoundView(p_a, p_b, duel_key))

# ══════════════════════════════════════════════════════════════════════
#  العرّاف — Oracle
# ══════════════════════════════════════════════════════════════════════

def get_oracle(md: dict) -> tuple[str, bool]:
    if "عين_عراف" in [item.get("id", "") for item in md["inventory"].get("special", [])]:
        # Guaranteed true prophecy
        prophecy, _ = random.choice([p for p in ORACLE_PROPHECIES if p[1]])
        md["inventory"]["special"] = [
            item for item in md["inventory"].get("special", [])
            if item.get("id") != "eye_oracle"
        ]
        return prophecy, True
    prophecy, accurate = random.choice(ORACLE_PROPHECIES)
    return prophecy, accurate

# ══════════════════════════════════════════════════════════════════════
#  المتجر — Store
# ══════════════════════════════════════════════════════════════════════

class StoreCategoryView(View):
    def __init__(self, uid: str, category: str):
        super().__init__(timeout=180)
        self.uid      = uid
        self.category = category
        items = STORE_CATEGORIES.get(category, [])
        if items:
            opts = [
                discord.SelectOption(
                    label=item["name"][:100],
                    value=item["id"],
                    description=f"{item['desc'][:80]}  —  {item['price']:,} 🖤",
                )
                for item in items[:25]
            ]
            sel = Select(placeholder="🛒  اختر عنصراً للشراء…", options=opts)
            sel.callback = self._buy
            self.add_item(sel)

    async def _buy(self, i: discord.Interaction):
        if str(i.user.id) != self.uid:
            await i.response.send_message("❌ ليس متجرك.", ephemeral=True); return
        item_id = i.data["values"][0]
        item    = None
        for items in STORE_CATEGORIES.values():
            for it in items:
                if it["id"] == item_id:
                    item = it
                    break
        if not item:
            await i.response.send_message("❌ العنصر غير موجود.", ephemeral=True); return
        md    = _get_member(self.uid)
        rank  = get_rank(md.get("xp", 0))[0]
        disc  = RANK_DISCOUNTS.get(rank, 0)
        price = int(item["price"] * (1 - disc / 100))
        if md.get("shards", 0) < price:
            await i.response.send_message(
                f"❌ شظاياك غير كافية!  السعر: **{price:,}** 🖤  ·  لديك: **{md['shards']:,}** 🖤",
                ephemeral=True); return
        # Mystery box weekly limit
        if item["type"] == "mystery":
            last = md.get("last_mystery")
            if last and not _cd_ok(md, "last_mystery", 168):
                remaining = _cd_remaining(md, "last_mystery", 168)
                await i.response.send_message(
                    f"❌ صندوق الغموض مرة واحدة في الأسبوع!\nالمتبقي: **{remaining}**",
                    ephemeral=True); return
            md["last_mystery"] = datetime.utcnow().isoformat()

        md["shards"] -= price

        result_msg = f"✅ اشتريت **{item['name']}** بـ **{price:,}** 🖤\n"
        if disc > 0:
            result_msg += f"*وفّرت {disc}% بفضل رتبتك!*\n"

        if item["type"] == "pass":
            # Bypass a specific cooldown immediately
            key = item.get("pass_key", "")
            if key and key in md:
                md[key] = None
            result_msg += f"✅ انتظارك أُلغي — يمكنك استخدام النشاط الآن فوراً!"
        elif item["type"] == "boost":
            apply_effect(md, item.get("effect", "مبارك"))
            result_msg += "🌟 المضاعف نشط لـ24 ساعة — شظايا المغامرة ×2!"
        elif item["type"] == "badge":
            md["inventory"].setdefault("badges", []).append(item["id"])
            result_msg += "الشارة أُضيفت لملفك الشخصي!"
        elif item["type"] == "potion":
            md["inventory"].setdefault("potions", []).append({"id": item["id"], "name": item["name"]})
            result_msg += "الجرعة في مخزونك — استخدمها عبر **مخزوني**."
        elif item["type"] == "equip":
            md["inventory"].setdefault("equip", []).append({"id": item["id"], "name": item["name"], "stat": item.get("stat",""), "bonus": item.get("bonus",0)})
            result_msg += "المعدة في مخزونك — جهّزها عبر **مخزوني**."
        elif item["type"] == "special":
            md["inventory"].setdefault("special", []).append({"id": item["id"], "name": item["name"]})
            result_msg += "العنصر الخاص في مخزونك."
        elif item["type"] == "mod":
            md["inventory"].setdefault("special", []).append({"id": item["id"], "name": item["name"]})
            result_msg += "معدّل اللعبة في مخزونك."
        elif item["type"] == "mystery":
            # Open box immediately
            roll = random.randint(1, 100)
            cumulative = 0
            reward_text = ""
            for prob, rtype, rval, msg in MYSTERY_CONTENTS:
                cumulative += prob
                if roll <= cumulative:
                    if rtype == "shards":
                        award_shards(md, rval)
                        reward_text = msg.format(v=rval)
                    elif rtype == "item":
                        md["inventory"].setdefault("potions", []).append({"id": rval, "name": rval})
                        reward_text = msg
                    elif rtype == "badge":
                        md["inventory"].setdefault("badges", []).append(rval)
                        reward_text = msg
                    elif rtype == "pass":
                        # Find item and clear its cooldown key
                        for cats in STORE_CATEGORIES.values():
                            for it in cats:
                                if it["id"] == rval and it.get("pass_key"):
                                    md[it["pass_key"]] = None
                        reward_text = msg
                    break
            result_msg = f"🎁 **فتحت صندوق الغموض!**\n\n{reward_text}"

        _save()
        e = discord.Embed(title="🏪  المتجر الإمبراطوري",
                          description=f"{SEP}\n{result_msg}\n{SEP}", color=GOLD)
        brand(e)
        await i.response.edit_message(embed=e, view=None)


class StoreMenuView(View):
    def __init__(self, uid: str):
        super().__init__(timeout=180)
        self.uid = uid
        opts = [
            discord.SelectOption(label=cat[:100], value=cat)
            for cat in STORE_CATEGORIES.keys()
        ]
        sel = Select(placeholder="🏪  اختر فئة من المتجر…", options=opts)
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, i: discord.Interaction):
        if str(i.user.id) != self.uid:
            await i.response.send_message("❌ ليس متجرك.", ephemeral=True); return
        cat  = i.data["values"][0]
        items = STORE_CATEGORIES.get(cat, [])
        md   = _get_member(self.uid)
        rank = get_rank(md.get("xp", 0))[0]
        disc = RANK_DISCOUNTS.get(rank, 0)
        lines = []
        for it in items:
            price    = int(it["price"] * (1 - disc / 100))
            can_buy  = "✅" if md.get("shards", 0) >= price else "❌"
            lines.append(f"{can_buy} **{it['name']}** — {price:,} 🖤\n   _{it['desc']}_")
        desc = (
            f"{SEP}\n"
            + "\n\n".join(lines)
            + f"\n\n*رصيدك: **{md.get('shards',0):,}** 🖤*"
            + (f"  ·  *خصم رتبتك: {disc}%*" if disc else "")
            + f"\n{SEP}"
        )
        e = discord.Embed(title=f"🏪  {cat}", description=desc[:4000], color=DEEP_GOLD)
        brand(e)
        await i.response.edit_message(embed=e, view=StoreCategoryView(self.uid, cat))

# ══════════════════════════════════════════════════════════════════════
#  المخزون — Inventory
# ══════════════════════════════════════════════════════════════════════

class InventoryView(View):
    def __init__(self, uid: str, md: dict):
        super().__init__(timeout=120)
        self.uid = uid
        self.md  = md
        equip    = md["inventory"].get("equip", [])
        equipped = md.get("equipped", {})
        if equip:
            opts = [
                discord.SelectOption(
                    label=f"{'✅ ' if e['id'] in equipped else ''}{e['name'][:80]}",
                    value=e["id"],
                    description=f"{e.get('stat','')} +{e.get('bonus',0)}"[:100],
                )
                for e in equip[:25]
            ]
            sel = Select(placeholder="🗡️  جهّز معدة أو انزعها…", options=opts)
            sel.callback = self._toggle_equip
            self.add_item(sel)
        potions = md["inventory"].get("potions", [])
        if potions:
            opts2 = [
                discord.SelectOption(label=p.get("name", p.get("id","؟"))[:80], value=p.get("id",""))
                for p in potions[:25]
            ]
            sel2 = Select(placeholder="🍶  استخدم جرعة…", options=opts2)
            sel2.callback = self._use_potion
            self.add_item(sel2)

    async def _toggle_equip(self, i: discord.Interaction):
        if str(i.user.id) != self.uid:
            await i.response.send_message("❌", ephemeral=True); return
        equip_id = i.data["values"][0]
        equipped = self.md.setdefault("equipped", {})
        if equip_id in equipped:
            del equipped[equip_id]
            msg = f"🔓 نزعت **{equip_id}** من التجهيز."
        else:
            equipped[equip_id] = True
            msg = f"✅ جهّزت **{equip_id}**!"
        _save()
        await i.response.send_message(msg, ephemeral=True)

    async def _use_potion(self, i: discord.Interaction):
        if str(i.user.id) != self.uid:
            await i.response.send_message("❌", ephemeral=True); return
        potion_id = i.data["values"][0]
        potions   = self.md["inventory"].get("potions", [])
        found     = next((p for p in potions if p.get("id") == potion_id), None)
        if not found:
            await i.response.send_message("❌ الجرعة غير موجودة في مخزونك.", ephemeral=True); return
        effect_map = {
            "potion_str":  "قوة_مؤقتة",
            "potion_heal": "شفاء",
            "potion_luck": "حظ_مؤقت",
        }
        eff_name = effect_map.get(potion_id, "مبارك")
        if potion_id == "potion_heal":
            clean_effects(self.md)
            self.md["active_effects"] = [e for e in self.md["active_effects"] if e["name"] != "مجروح"]
            msg = "🌿 أُزيل تأثير **مجروح**!"
        else:
            apply_effect(self.md, eff_name)
            msg = f"✅ فعّلت جرعة **{found['name']}**! التأثير نشط لـ24 ساعة."
        potions.remove(found)
        _save()
        await i.response.send_message(msg, ephemeral=True)


def build_inventory_embed(md: dict) -> discord.Embed:
    inv = md.get("inventory", {})
    e   = discord.Embed(title="📦  مخزونك الإمبراطوري",
                        description=f"{SEP}\n*كل ما تملكه*\n{SEP}", color=TEAL)
    # Materials
    mats = inv.get("materials", {})
    if mats:
        mat_lines = "\n".join(f"• **{k}**: {v}" for k, v in sorted(mats.items()))
        e.add_field(name="⛏️ المواد الخام", value=mat_lines[:1020], inline=True)
    else:
        e.add_field(name="⛏️ المواد", value="لا يوجد", inline=True)
    # Potions
    potions = inv.get("potions", [])
    if potions:
        e.add_field(name="🍶 الجرعات", value="\n".join(f"• {p.get('name',p.get('id','؟'))}" for p in potions[:10]), inline=True)
    else:
        e.add_field(name="🍶 الجرعات", value="لا يوجد", inline=True)
    # Equipment
    equip    = inv.get("equip", [])
    equipped = md.get("equipped", {})
    if equip:
        eq_lines = "\n".join(f"{'✅ ' if e['id'] in equipped else '○ '}{e['name']}" for e in equip)
        e.add_field(name="🗡️ المعدات", value=eq_lines[:1020], inline=True)
    # Special
    special = inv.get("special", [])
    if special:
        e.add_field(name="✨ العناصر الخاصة", value="\n".join(f"• {s.get('name',s.get('id','؟'))}" for s in special[:10]), inline=True)
    # Shards
    e.add_field(name="💰 الرصيد", value=f"**{md.get('shards',0):,}** 🖤", inline=False)
    brand(e)
    return e

# ══════════════════════════════════════════════════════════════════════
#  الصنع — Crafting
# ══════════════════════════════════════════════════════════════════════

class CraftingView(View):
    def __init__(self, uid: str, md: dict):
        super().__init__(timeout=180)
        self.uid = uid
        self.md  = md
        # Show only recipes the player can craft (has all materials)
        mats     = md["inventory"].get("materials", {})
        craftable = [
            r for r in CRAFTING_RECIPES
            if all(mats.get(m, 0) >= qty for m, qty in r["materials"].items())
        ]
        if craftable:
            opts = [
                discord.SelectOption(
                    label=r["name"][:80],
                    value=r["id"],
                    description="المواد: " + ", ".join(f"{m}×{q}" for m,q in r["materials"].items())[:80],
                )
                for r in craftable[:25]
            ]
            sel = Select(placeholder="🛠️  اختر وصفة للصنع…", options=opts)
            sel.callback = self._craft
            self.add_item(sel)

    async def _craft(self, i: discord.Interaction):
        if str(i.user.id) != self.uid:
            await i.response.send_message("❌", ephemeral=True); return
        recipe_id = i.data["values"][0]
        recipe    = next((r for r in CRAFTING_RECIPES if r["id"] == recipe_id), None)
        if not recipe:
            await i.response.send_message("❌ الوصفة غير موجودة.", ephemeral=True); return
        mats = self.md["inventory"].setdefault("materials", {})
        for mat, qty in recipe["materials"].items():
            if mats.get(mat, 0) < qty:
                await i.response.send_message(f"❌ مواد غير كافية: {mat}", ephemeral=True); return
            mats[mat] -= qty
            if mats[mat] == 0: del mats[mat]
        result_type = recipe["result_type"]
        result_id   = recipe["result_id"]
        result_name = recipe["result_name"]
        if result_type == "potion":
            self.md["inventory"].setdefault("potions", []).append({"id": result_id, "name": result_name})
        elif result_type == "equip":
            stat  = next((it.get("stat","") for cat in STORE_CATEGORIES.values() for it in cat if it["id"]==result_id), "")
            bonus = next((it.get("bonus", 0) for cat in STORE_CATEGORIES.values() for it in cat if it["id"]==result_id), 0)
            self.md["inventory"].setdefault("equip", []).append({"id": result_id, "name": result_name, "stat": stat, "bonus": bonus})
        else:
            self.md["inventory"].setdefault("special", []).append({"id": result_id, "name": result_name})
        _save()
        await i.response.send_message(
            f"🛠️ صنعت **{result_name}** بنجاح!\nموجودة الآن في مخزونك.", ephemeral=True)


def build_crafting_embed(md: dict) -> discord.Embed:
    mats = md["inventory"].get("materials", {})
    lines_r, lines_m = [], []
    for r in CRAFTING_RECIPES:
        can  = all(mats.get(m, 0) >= qty for m, qty in r["materials"].items())
        req  = "، ".join(f"{m}×{q}" for m, q in r["materials"].items())
        lines_r.append(f"{'✅' if can else '❌'} **{r['name']}**\n   _{req}_")
    for mat, qty in sorted(mats.items()):
        lines_m.append(f"• **{mat}**: {qty}")
    e = discord.Embed(
        title="🛠️  ورشة الصنع",
        description=(
            f"{SEP}\n"
            "**وصفاتك المتاحة:**\n\n"
            + ("\n\n".join(lines_r) if lines_r else "لا توجد وصفات بعد — اجمع مواد من المغامرات")
            + f"\n{SEP}"
        ), color=AMBER)
    if lines_m:
        e.add_field(name="⛏️ موادك الحالية", value="\n".join(lines_m[:20]), inline=False)
    brand(e)
    return e

# ══════════════════════════════════════════════════════════════════════
#  لوحة الصدارة — Leaderboard
# ══════════════════════════════════════════════════════════════════════

def build_leaderboard_embed(guild: discord.Guild, sort_by: str = "xp") -> discord.Embed:
    members  = _emp().get("members", {})
    all_data = []
    for uid, md in members.items():
        mem = guild.get_member(int(uid))
        if not mem: continue
        all_data.append((mem.display_name, md.get("xp",0), md.get("shards",0),
                         md.get("total_duels_won",0), md.get("total_expeditions",0)))
    if not all_data:
        return empire_embed("🏆  لوحة الصدارة", "لا يوجد محاربون بعد!", GOLD)
    sort_idx = {"xp": 1, "shards": 2, "duels": 3, "expeditions": 4}.get(sort_by, 1)
    all_data.sort(key=lambda x: x[sort_idx], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for n, (name, xp, shards, duels, exps) in enumerate(all_data[:15], 1):
        rank_lvl, rank_name = get_rank(xp)
        medal = medals[n-1] if n <= 3 else f"`{n}.`"
        if sort_by == "xp":
            val = f"{rank_name}  ({xp:,} ⭐)"
        elif sort_by == "shards":
            val = f"{shards:,} 🖤"
        elif sort_by == "duels":
            val = f"{duels} انتصار ⚔️"
        else:
            val = f"{exps} مغامرة 📜"
        lines.append(f"{medal}  **{name}**\n　　{val}")
    titles_map = {"xp": "الخبرة والرتبة", "shards": "الشظايا", "duels": "المبارزات", "expeditions": "المغامرات"}
    e = discord.Embed(
        title=f"🏆  لوحة الصدارة — {titles_map.get(sort_by,'')}",
        description=f"{SEP}\n*أبطال الإمبراطورية المظلمة*\n{SEP}",
        color=DEEP_GOLD,
    )
    e.add_field(name="الترتيب", value="\n".join(lines)[:1020], inline=False)
    brand(e)
    return e


class LeaderboardView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="⭐ الخبرة",        style=discord.ButtonStyle.primary,   row=0)
    async def by_xp(self, i, _):
        await i.response.edit_message(embed=build_leaderboard_embed(i.guild, "xp"), view=self)

    @discord.ui.button(label="🖤 الشظايا",       style=discord.ButtonStyle.secondary,  row=0)
    async def by_shards(self, i, _):
        await i.response.edit_message(embed=build_leaderboard_embed(i.guild, "shards"), view=self)

    @discord.ui.button(label="⚔️ المبارزات",     style=discord.ButtonStyle.danger,     row=0)
    async def by_duels(self, i, _):
        await i.response.edit_message(embed=build_leaderboard_embed(i.guild, "duels"), view=self)

    @discord.ui.button(label="📜 المغامرات",      style=discord.ButtonStyle.success,    row=0)
    async def by_expeditions(self, i, _):
        await i.response.edit_message(embed=build_leaderboard_embed(i.guild, "expeditions"), view=self)

# ══════════════════════════════════════════════════════════════════════
#  لوحة المبارزة (اختيار الخصم)
# ══════════════════════════════════════════════════════════════════════

class DuelTargetView(View):
    def __init__(self, challenger: discord.Member, guild: discord.Guild):
        super().__init__(timeout=120)
        self.challenger = challenger
        members = _emp().get("members", {})
        targets = [
            guild.get_member(int(uid))
            for uid in members
            if int(uid) != challenger.id
        ]
        targets = [m for m in targets if m is not None][:25]
        if targets:
            opts = [
                discord.SelectOption(label=m.display_name[:100], value=str(m.id))
                for m in targets
            ]
            sel = Select(placeholder="⚔️  اختر خصمك…", options=opts)
            sel.callback = self._challenge
            self.add_item(sel)

    async def _challenge(self, i: discord.Interaction):
        if i.user.id != self.challenger.id:
            await i.response.send_message("❌", ephemeral=True); return
        target = i.guild.get_member(int(i.data["values"][0]))
        if not target:
            await i.response.send_message("❌ العضو غير موجود.", ephemeral=True); return
        ch_md = _get_member(str(i.user.id))
        if not _cd_ok(ch_md, "last_duel", 12):
            remaining = _cd_remaining(ch_md, "last_duel", 12)
            await i.response.send_message(
                f"❌ المبارزة على توقف!\nالمتبقي: **{remaining}**", ephemeral=True); return
        ch_md["last_duel"] = datetime.utcnow().isoformat()
        _save()
        duel_key = _duel_key(i.user.id, target.id)
        self.stop()
        e = discord.Embed(
            title="⚔️  تحدي مبارزة!",
            description=(
                f"{SEP}\n"
                f"**{i.user.display_name}** يتحدى **{target.mention}**!\n\n"
                f"هل تقبل المبارزة؟  ⚔️\n"
                f"{SEP}"
            ), color=CRIMSON)
        brand(e)
        await i.response.edit_message(
            embed=e, view=DuelChallengeView(i.guild.get_member(i.user.id), target, duel_key))

# ══════════════════════════════════════════════════════════════════════
#  لوحة الإدارة — Admin Empire Panel
# ══════════════════════════════════════════════════════════════════════

class AdminEmpireView(View):
    def __init__(self): super().__init__(timeout=120)

    def _guard(self, i: discord.Interaction) -> bool:
        m = i.guild.get_member(i.user.id)
        return m is not None and is_admin(m)

    @discord.ui.button(label="💰 منح شظايا",   style=discord.ButtonStyle.success,  row=0)
    async def give_shards(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌", ephemeral=True); return
        await i.response.send_modal(GiveShardsModal())

    @discord.ui.button(label="⭐ منح خبرة",    style=discord.ButtonStyle.primary,  row=0)
    async def give_xp(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌", ephemeral=True); return
        await i.response.send_modal(GiveXPModal())

    @discord.ui.button(label="🔄 إعادة تهيئة يوم", style=discord.ButtonStyle.secondary, row=0)
    async def reset_daily_btn(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌", ephemeral=True); return
        await i.response.send_modal(ResetDailyModal())

    @discord.ui.button(label="👥 إحصائيات النظام", style=discord.ButtonStyle.secondary, row=1)
    async def system_stats(self, i, _):
        if not self._guard(i):
            await i.response.send_message("❌", ephemeral=True); return
        members = _emp().get("members", {})
        total_s = sum(md.get("shards",0)       for md in members.values())
        total_x = sum(md.get("xp",0)           for md in members.values())
        total_e = sum(md.get("total_expeditions",0) for md in members.values())
        cls_cnt: dict[str,int] = {}
        for md in members.values():
            c = md.get("class","؟")
            cls_cnt[c] = cls_cnt.get(c,0) + 1
        cls_lines = "\n".join(f"  {CLASSES.get(c,{}).get('emoji','?')} {c}: **{n}**" for c,n in sorted(cls_cnt.items(), key=lambda x:-x[1]))
        e = discord.Embed(
            title="📊  إحصائيات الإمبراطورية",
            description=(
                f"{SEP}\n"
                f"👤 المحاربون المسجلون: **{len(members)}**\n"
                f"🖤 إجمالي الشظايا: **{total_s:,}**\n"
                f"⭐ إجمالي الخبرة: **{total_x:,}**\n"
                f"📜 إجمالي المغامرات: **{total_e:,}**\n\n"
                f"**الفئات:**\n{cls_lines}\n"
                f"{SEP}"
            ), color=STEEL)
        brand(e)
        await i.response.send_message(embed=e, ephemeral=True)
        await log_action(i.guild, "📊 Admin إحصائيات", f"{i.user.mention} استعرض إحصائيات النظام")


class GiveShardsModal(Modal, title="💰 منح شظايا"):
    user_id = TextInput(label="معرّف المستخدم (ID)",  placeholder="123456789012345678", required=True, max_length=25)
    amount  = TextInput(label="الكمية",               placeholder="مثال: 500",          required=True, max_length=10)

    async def on_submit(self, i: discord.Interaction):
        uid  = self.user_id.value.strip()
        amt  = int(self.amount.value.strip()) if self.amount.value.strip().isdigit() else 0
        md   = _get_member(uid)
        if not md:
            await i.response.send_message(f"❌ لا يوجد حساب بهذا المعرف: {uid}", ephemeral=True); return
        award_shards(md, amt)
        _save()
        mem_obj = i.guild.get_member(int(uid))
        name    = mem_obj.display_name if mem_obj else uid
        await i.response.send_message(f"✅ أُعطيَ **{name}** مبلغ **{amt:,}** 🖤", ephemeral=True)
        await log_action(i.guild,"💰 Admin منح شظايا",f"{i.user.mention} → {name}: {amt:,} شظية")


class GiveXPModal(Modal, title="⭐ منح خبرة"):
    user_id = TextInput(label="معرّف المستخدم (ID)",  placeholder="123456789012345678", required=True, max_length=25)
    amount  = TextInput(label="الكمية",               placeholder="مثال: 500",          required=True, max_length=10)

    async def on_submit(self, i: discord.Interaction):
        uid  = self.user_id.value.strip()
        amt  = int(self.amount.value.strip()) if self.amount.value.strip().isdigit() else 0
        md   = _get_member(uid)
        if not md:
            await i.response.send_message(f"❌ لا يوجد حساب: {uid}", ephemeral=True); return
        gained, ranked = award_xp(md, amt)
        _save()
        mem_obj = i.guild.get_member(int(uid))
        name    = mem_obj.display_name if mem_obj else uid
        await i.response.send_message(
            f"✅ أُعطيَ **{name}** مقدار **{gained:,}** ⭐ خبرة"
            + (f"\n🎉 ارتقى رتبة! — {get_rank(md['xp'])[1]}" if ranked else ""),
            ephemeral=True)


class ResetDailyModal(Modal, title="🔄 إعادة تهيئة اليوم"):
    user_id = TextInput(label="معرّف المستخدم (ID)", placeholder="123456789012345678", required=True, max_length=25)

    async def on_submit(self, i: discord.Interaction):
        uid = self.user_id.value.strip()
        md  = _get_member(uid)
        if not md:
            await i.response.send_message(f"❌ لا يوجد حساب: {uid}", ephemeral=True); return
        md["last_daily"]      = None
        md["last_expedition"] = None
        _save()
        mem_obj = i.guild.get_member(int(uid))
        name    = mem_obj.display_name if mem_obj else uid
        await i.response.send_message(f"✅ أُعيد تهيئة اليوم لـ **{name}**", ephemeral=True)
        await log_action(i.guild, "🔄 Admin إعادة تهيئة", f"{i.user.mention} → {name}: أُعيد تهيئة المغامرة اليومية")


# ══════════════════════════════════════════════════════════════════════
#  دليل النظام — Guide Pages (6 pages)
# ══════════════════════════════════════════════════════════════════════

GUIDE_PAGES: list[dict] = [
    # ── Page 1: Introduction ──────────────────────────────────────
    {
        "title":  "📖  الدليل الشامل  —  مقدمة النظام  (1/6)",
        "color":  0x1A0A2E,
        "desc": (
            "```\n"
            "  ⚜  سجلات الإمبراطورية المظلمة  ⚜\n"
            "  دليل المحارب الكامل\n"
            "```\n\n"
            "نظام مغامرات كامل داخل السيرفر — مستقل عن ألعاب HoK.\n"
            "اكسب الشظايا، ارتقِ في الرتب، واكتشف أسرار الإمبراطورية.\n\n"
            "**🖤 الشظايا (العملة الأساسية)**\n"
            "تُكسب من كل الأنشطة اليومية وتُنفق في المتجر الإمبراطوري.\n\n"
            "**⭐ الخبرة (للارتقاء في الرتب)**\n"
            "تتراكم تلقائياً من المغامرات والزنازين والمبارزات.\n\n"
            "**📊 الإحصائيات الأربع**\n"
            "```\n"
            "  💪 القوة    → يؤثر في المبارزات والمواجهات المباشرة\n"
            "  🧠 الدهاء   → يساعد في التسلل والاستطلاع والمفاوضات\n"
            "  🏃 التحمل  → يقلل الضرر في الزنازين والبقاء الطويل\n"
            "  🍀 الحظ    → يغير نتائج العرّاف والأحداث العشوائية\n"
            "```\n\n"
            "**🚀 كيف تبدأ؟**\n"
            "1️⃣  اضغط **شخصيتي** واختر فئتك\n"
            "2️⃣  اجمع المكافأة اليومية كل يوم (📅)\n"
            "3️⃣  انطلق في مغامرة يومية (🎯)\n"
            "4️⃣  تحدّ محاربين آخرين في الساحة (⚔️)"
        ),
    },
    # ── Page 2: Classes ───────────────────────────────────────────
    {
        "title":  "⚔️  الدليل الشامل  —  الفئات الخمس  (2/6)",
        "color":  CRIMSON,
        "desc": (
            "```\n"
            "  اختر فئتك بعناية — القرار لا يتغير إلا بـ 3,000 🖤\n"
            "```\n\n"
            "**⚔️ سيد النصل**\n"
            "└ ضرر المبارزة +20% · الأفضل في الساحة والمواجهات\n\n"
            "**🔮 ساحر الظلام**\n"
            "└ احتمالية الأحداث النادرة +30% · يعتمد على الحظ والفوضى\n\n"
            "**🛡️ حارس الحديد**\n"
            "└ الضرر في الزنزانة -40% · شبه لا يُهزم في الزنازين\n\n"
            "**🗡️ الشبح**\n"
            "└ ذهب السطو +25% · الأفضل في التسلل والاستطلاع\n\n"
            "**💚 حافظ العلم**\n"
            "└ الخبرة من كل الأنشطة +50% · الأسرع في الارتقاء\n\n"
            "```\n"
            "  💡 نصيحة: الفئة لا تقيدك — كل الأنشطة متاحة للجميع\n"
            "  الفئة فقط تعطيك مزية إضافية في مجال معين\n"
            "```\n\n"
            "**🔄 تغيير الفئة**\n"
            "متاح من المتجر بـ 3,000 🖤 (مرة واحدة فقط)"
        ),
    },
    # ── Page 3: Daily Activities ──────────────────────────────────
    {
        "title":  "🎯  الدليل الشامل  —  الأنشطة اليومية  (3/6)",
        "color":  AMBER,
        "desc": (
            "**📅 المكافأة اليومية** — مجانية · كل 24 ساعة\n"
            "```\n"
            "  يوم 1-3   → 75-100 🖤  ×1.0 - ×1.3\n"
            "  يوم 4-6   → 130 🖤     ×1.7\n"
            "  يوم 7     → 200 🖤     ×2.5 (مكافأة!)\n"
            "  يوم 14    → 350 🖤     ×3.0 + خبرة إضافية\n"
            "  يوم 30+   → 500 🖤     ×4.0 + شارة خاصة\n"
            "```\n\n"
            "**🎯 المغامرة اليومية** — كل 24 ساعة\n"
            "سيناريو قصصي مع 3 خيارات. إحصائياتك تحدد نسبة النجاح.\n"
            "```\n"
            "  ✅ نجاح كامل  → 150-300 🖤  + 120 ⭐  + مادة\n"
            "  ⚠️ نجاح جزئي → 50-100 🖤   + 50 ⭐   + تأثير\n"
            "  💀 فشل        → 20 ⭐ تعزية + تأثير مجروح\n"
            "```\n\n"
            "**🔮 العرّاف** — 100 🖤 · كل 24 ساعة\n"
            "نبوءة غامضة تلمح لما سيحدث في مغامرتك القادمة.\n"
            "60% دقيقة · 40% مضللة. اشترِ عين العرّاف لنبوءة مضمونة.\n\n"
            "**✨ تأثيرات الحالة**\n"
            "```\n"
            "  🩸 مجروح   → نجاح -20%    (24 ساعة)\n"
            "  🌟 مبارك   → فحوصات +15%  (24 ساعة)\n"
            "  😵 ملعون   → إحصائية عشوائية تنعكس (48 ساعة)\n"
            "  💤 منهك    → خيارات دفاعية فقط في المبارزة (12 ساعة)\n"
            "  🔥 مستعر   → ضرر +40% لكن الدهاء ممنوع (24 ساعة)\n"
            "```"
        ),
    },
    # ── Page 4: Combat ────────────────────────────────────────────
    {
        "title":  "⚔️  الدليل الشامل  —  المعارك  (4/6)",
        "color":  CRIMSON,
        "desc": (
            "**🏰 الزنزانة الأسبوعية** — مرة كل 7 أيام\n"
            "3 غرف متتالية · كل غرفة لها نوع مختلف:\n"
            "```\n"
            "  ⚔️ غرفة القتال   → إحصائية القوة\n"
            "  🧠 غرفة الألغاز  → إحصائية الدهاء\n"
            "  🕸️ غرفة الفخاخ  → إحصائية التحمل\n"
            "  💰 غرفة الكنوز  → إحصائية الحظ\n"
            "  🧙 لقاء الغريب  → إحصائية الدهاء\n"
            "```\n"
            "المكافأة عند الإكمال: **300-500** 🖤 + **400** ⭐ + معدة\n\n"
            "**⚔️ المبارزة** — مرتين كل 12 ساعة\n"
            "3 جولات · كل جولة اختار حركتك:\n"
            "```\n"
            "  ⚔️ ضربة ثقيلة   → ضرر عالٍ لكن يُكسر بالخداع\n"
            "  🌀 خداع+هجمة    → يكسر الضربة الثقيلة ويمنح مكافأة\n"
            "  🛡️ موقف دفاعي  → يقلل الضرر + قليل HP\n"
            "  🎯 ضربة دقيقة  → تتفوق على الموقف الدفاعي\n"
            "```\n"
            "**مكافأة الفوز:** 200 🖤 + 150 ⭐\n"
            "**مكافأة الخسارة:** 50 🖤 + 50 ⭐ *(كل المبارزات لها مكافأة!)*"
        ),
    },
    # ── Page 5: Economy ───────────────────────────────────────────
    {
        "title":  "💰  الدليل الشامل  —  الاقتصاد  (5/6)",
        "color":  DEEP_GOLD,
        "desc": (
            "**🏪 المتجر الإمبراطوري** (5 فئات)\n"
            "```\n"
            "  ✨ شارات الملف     → 1,000 - 1,500 🖤\n"
            "  ⚗️ جرعات ومعدات   → 300 - 1,400 🖤\n"
            "  🎮 معدلات الألعاب  → 350 - 900 🖤\n"
            "  🎖️ إضافات خاصة   → 600 - 1,500 🖤\n"
            "  🎁 صندوق الغموض   → 750 🖤 (مرة/أسبوع)\n"
            "```\n"
            "الرتبة الأعلى = خصم أكبر (حتى 30% عند الرتبة 7)\n\n"
            "**🛠️ الصنع** — ادمج المواد لصنع عناصر نادرة\n"
            "```\n"
            "  مواد شائعة  → تسقط من المغامرات اليومية\n"
            "  مواد نادرة  → تسقط من الزنازين والسطو\n"
            "```\n\n"
            "**🎖️ إضافات خاصة (جديد!)**\n"
            "```\n"
            "  🎯 تصريح مغامرة  → يلغي انتظار 24 ساعة (800 🖤)\n"
            "  🏰 تصريح زنزانة  → يلغي انتظار أسبوع  (1,200 🖤)\n"
            "  ⚔️ تصريح مبارزة  → يلغي انتظار 12 ساعة (600 🖤)\n"
            "  💎 مضاعف الشظايا → شظايا ×2 لـ24 ساعة  (1,500 🖤)\n"
            "  🛡️ درع السلسلة  → يحمي سلسلتك مرة     (1,000 🖤)\n"
            "```"
        ),
    },
    # ── Page 6: Ranks & Titles ────────────────────────────────────
    {
        "title":  "👑  الدليل الشامل  —  الرتب والألقاب  (6/6)",
        "color":  DARK_EMPIRE,
        "desc": (
            "**👑 سلم الرتب الإمبراطوري**\n"
            "```\n"
            "  🪨 فلاح الحجر      → 0 ⭐       (البداية)\n"
            "  ⚔️ جندي الحديد    → 500 ⭐      (+5% خصم)\n"
            "  🛡️ فارس البرونز   → 1,500 ⭐    (+10% خصم)\n"
            "  🥈 حارس الفضة     → 4,000 ⭐    (+15% خصم)\n"
            "  🥇 قائد الذهب     → 10,000 ⭐   (+20% خصم)\n"
            "  💎 جنرال الماس    → 25,000 ⭐   (+25% خصم)\n"
            "  👑 إمبراطور الأوبسيديان → 60,000 ⭐ (+30% خصم)\n"
            "```\n\n"
            "**🏅 الألقاب (تُكتسب بالإنجاز فقط)**\n"
            "```\n"
            "  «الذي لا يتوقف»       → أتم 10 مغامرات\n"
            "  «ناهب الزنازين»        → اجتاز 5 زنازين\n"
            "  «أبو خداع»             → فاز بـ5 مبارزات\n"
            "  «صوت الإمبراطورية»     → سلسلة 30 يوم\n"
            "  «خزينة الإمبراطورية»   → جمع 50,000 🖤\n"
            "  «الإمبراطور الأول»     → وصل للرتبة 7\n"
            "```\n\n"
            "**💡 نصائح للمحاربين الجدد**\n"
            "```\n"
            "  ✦ المكافأة اليومية كل يوم = أسرع طريق للشظايا\n"
            "  ✦ لا تنسَ المغامرة — 150-300 🖤 يومياً مجاناً\n"
            "  ✦ الزنزانة الأسبوعية أفضل مصدر للخبرة\n"
            "  ✦ المبارزة تعطي مكافأة حتى لو خسرت\n"
            "  ✦ العرّاف يضاعف فرصك في المغامرة بـ100 🖤 فقط\n"
            "```"
        ),
    },
]


class GuideView(View):
    """6-page illustrated guide with navigation buttons."""
    def __init__(self, page: int = 0):
        super().__init__(timeout=300)
        self.page = page
        total     = len(GUIDE_PAGES)
        if page > 0:
            prev = Button(label="◀  السابق", style=discord.ButtonStyle.secondary, row=0)
            prev.callback = self._prev
            self.add_item(prev)
        page_btn = Button(label=f"📄  {page+1} / {total}",
                          style=discord.ButtonStyle.secondary, row=0, disabled=True)
        self.add_item(page_btn)
        if page < total - 1:
            nxt = Button(label="التالي  ▶", style=discord.ButtonStyle.primary, row=0)
            nxt.callback = self._next
            self.add_item(nxt)

    async def _prev(self, i: discord.Interaction):
        await i.response.edit_message(
            embed=build_guide_embed(self.page - 1),
            view=GuideView(self.page - 1))

    async def _next(self, i: discord.Interaction):
        await i.response.edit_message(
            embed=build_guide_embed(self.page + 1),
            view=GuideView(self.page + 1))


def build_guide_embed(page: int) -> discord.Embed:
    p = GUIDE_PAGES[page]
    e = discord.Embed(title=p["title"], description=p["desc"], color=p["color"])
    e.set_footer(
        text=f"⚜  الإمبراطورية المظلمة  ·  الدليل الشامل  ·  صفحة {page+1}/{len(GUIDE_PAGES)}",
        icon_url=logo_url() or discord.utils.MISSING)
    brand(e, thumb=False)
    return e

# ══════════════════════════════════════════════════════════════════════
#  اللوحة الرئيسية — Main Empire Panel  (كل الأزرار في مكان واحد)
# ══════════════════════════════════════════════════════════════════════

class EmpirePanelView(View):
    def __init__(self, is_adm: bool = False):
        super().__init__(timeout=None)
        self.is_adm = is_adm

    # ── صف 0 ────────────────────────────────────────────────────────
    @discord.ui.button(label="⚔️ شخصيتي",       style=discord.ButtonStyle.primary,   row=0, emoji="⚔️")
    async def my_char(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            e = discord.Embed(
                title="🌑  مرحباً في الإمبراطورية المظلمة!",
                description=(
                    f"{SEP}\n"
                    "لا يوجد لك شخصية بعد.\n\n"
                    "اختر فئتك لتبدأ رحلتك في الإمبراطورية!\n"
                    f"{SEP}"
                ), color=DARK_EMPIRE)
            brand(e)
            await i.response.send_message(embed=e, view=ClassSelectionView(uid), ephemeral=True)
        else:
            clean_effects(md)
            check_titles(md)
            _save()
            await i.response.send_message(
                embed=build_character_embed(i.guild.get_member(i.user.id), md))

    @discord.ui.button(label="🎯 مغامرة",        style=discord.ButtonStyle.success,   row=0)
    async def expedition_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً من زر **شخصيتي**.", ephemeral=True); return
        if not _cd_ok(md, "last_expedition", 24):
            remaining = _cd_remaining(md, "last_expedition", 24)
            await i.response.send_message(
                f"⏰ المغامرة اليومية على انتهت!\nالمتبقي: **{remaining}**", ephemeral=True); return
        scenario = random.choice(EXPEDITION_SCENARIOS)
        e = discord.Embed(
            title="📜  المغامرة اليومية",
            description=(
                "*🌑  سيناريو اليوم  🌑*\n\n"
                + scenario['text']
                + "\n\n*اختر حركتك بحكمة — إحصائياتك تؤثر على النتيجة*"
            ), color=AMBER)
        e.set_footer(text=f"⚜  {i.user.display_name}  ·  المغامرة اليومية",
                     icon_url=i.user.display_avatar.url)
        e.set_footer(text=f"⚜  {i.user.display_name}  ·  المغامرة اليومية",
                     icon_url=i.user.display_avatar.url)
        brand(e)
        await i.response.send_message(
            content=f"🎯 **{i.user.display_name}** انطلق في مغامرة!",
            embed=e, view=ExpeditionView(uid, scenario, i.channel_id))

    @discord.ui.button(label="📅 مكافأة يومية",  style=discord.ButtonStyle.success,   row=0)
    async def daily_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        if not _cd_ok(md, "last_daily", 24):
            remaining = _cd_remaining(md, "last_daily", 24)
            await i.response.send_message(
                f"⏰ المكافأة اليومية على انتهت!\nالمتبقي: **{remaining}**", ephemeral=True); return
        streak = md.get("streak", 0) + 1
        md["streak"] = streak
        # Calculate bonus
        if streak >= 30:
            base, multiplier = 500, 4.0
        elif streak >= 14:
            base, multiplier = 350, 3.0
        elif streak == 7:
            base, multiplier = 200, 2.5
        elif streak >= 4:
            base, multiplier = 130, 1.7
        elif streak >= 2:
            base, multiplier = 100, 1.3
        else:
            base, multiplier = 75, 1.0
        total = int(base * multiplier)
        award_shards(md, total)
        xp_gained, ranked = award_xp(md, 50)
        md["last_daily"] = datetime.utcnow().isoformat()
        check_titles(md)
        _save()
        streak_stars = "🔥" * min(streak, 7)
        e = discord.Embed(
            title="📅  المكافأة اليومية",
            description=(
                f"{SEP}\n"
                f"**+{total:,}** 🖤 شظايا  ·  **+{xp_gained}** ⭐ خبرة\n\n"
                f"{streak_stars} السلسلة: **{streak}** يوم"
                + (f"  ×{multiplier}" if multiplier > 1 else "")
                + (f"\n\n🎉 **ارتقيت رتبة!** — {get_rank(md['xp'])[1]}" if ranked else "")
                + f"\n{SEP}"
            ), color=EMERALD)
        brand(e)
        await i.response.send_message(embed=e, ephemeral=True)

    @discord.ui.button(label="💰 رصيدي",         style=discord.ButtonStyle.secondary, row=0)
    async def balance_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        rank_lvl, rank_name = get_rank(md["xp"])
        next_xp = xp_to_next(md["xp"])
        disc    = RANK_DISCOUNTS.get(rank_lvl, 0)
        e = discord.Embed(
            title="💰  رصيدك الإمبراطوري",
            description=(
                f"{SEP}\n"
                f"🖤 **الشظايا:** {md.get('shards',0):,}\n"
                f"⭐ **الخبرة:** {md.get('xp',0):,}"
                + (f"  *(حتى التالية: {next_xp:,})*" if next_xp else "  *(أقصى رتبة!)*")
                + f"\n👑 **الرتبة:** {rank_name}\n"
                f"🔥 **السلسلة:** {md.get('streak',0)} يوم\n"
                f"🏷️ **خصم المتجر:** {disc}%\n"
                f"{SEP}"
            ), color=DEEP_GOLD)
        brand(e)
        await i.response.send_message(embed=e)

    # ── صف 1 ────────────────────────────────────────────────────────
    @discord.ui.button(label="📦 مخزوني",        style=discord.ButtonStyle.secondary, row=1)
    async def inventory_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        await i.response.send_message(
            embed=build_inventory_embed(md), view=InventoryView(uid, md), ephemeral=True)

    @discord.ui.button(label="🛠️ الصنع",         style=discord.ButtonStyle.secondary, row=1)
    async def crafting_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        await i.response.send_message(
            embed=build_crafting_embed(md), view=CraftingView(uid, md), ephemeral=True)

    @discord.ui.button(label="🏪 المتجر",         style=discord.ButtonStyle.primary,   row=1)
    async def store_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        rank     = get_rank(md.get("xp", 0))[0]
        disc     = RANK_DISCOUNTS.get(rank, 0)
        cat_lines = []
        for cat, items in STORE_CATEGORIES.items():
            prices = [int(it["price"] * (1 - disc/100)) for it in items]
            mn, mx = min(prices), max(prices)
            cat_lines.append(f"**{cat}**\n  *{mn:,} – {mx:,} 🖤*")
        e = discord.Embed(
            title="🏪  المتجر الإمبراطوري",
            description=(
                f"{SEP}\n"
                f"رصيدك: **{md.get('shards',0):,}** 🖤"
                + (f"  ·  خصم رتبتك: **{disc}%**" if disc else "")
                + f"\n\n" + "\n\n".join(cat_lines)
                + f"\n{SEP}"
            ), color=DEEP_GOLD)
        brand(e)
        await i.response.send_message(embed=e, view=StoreMenuView(uid), ephemeral=True)

    @discord.ui.button(label="🏆 الصدارة",        style=discord.ButtonStyle.primary,   row=1)
    async def leaderboard_btn(self, i: discord.Interaction, _: Button):
        await i.response.send_message(
            embed=build_leaderboard_embed(i.guild, "xp"),
            view=LeaderboardView())

    # ── صف 2 ────────────────────────────────────────────────────────
    @discord.ui.button(label="🏰 الزنزانة",       style=discord.ButtonStyle.danger,    row=2)
    async def dungeon_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        if i.user.id in active_dungeons:
            await i.response.send_message("❌ أنت بالفعل داخل زنزانة!", ephemeral=True); return
        if not _cd_ok(md, "last_dungeon", 168):
            remaining = _cd_remaining(md, "last_dungeon", 168)
            await i.response.send_message(
                f"❌ الزنزانة مرة في الأسبوع!\nالمتبقي: **{remaining}**", ephemeral=True); return
        active_dungeons[i.user.id] = {"room": 0, "hp": 100, "loot": 0}
        first_room = DUNGEON_ROOMS[0]
        e = discord.Embed(
            title=f"🏰  {i.user.display_name} دخل الزنزانة!",
            description=(
                f"⚠️  **تحذير:** الزنزانة مليئة بالأخطار!\n"
                f"3 غرف · 100 نقطة حياة · غنائم تنتظرك\n\n"
                f"**الغرفة الأولى:** {first_room['emoji']} {first_room['name']}\n\n"
                "❤️ نقاط الحياة: **100/100**  ·  💰 الغنائم: **0** 🖤\n\n"
                "*اختر طريقتك بعناية — فئتك تؤثر على النتيجة!*"
            ), color=TEAL)
        e.set_footer(text="⚜  الإمبراطورية المظلمة  ·  الزنزانة الأسبوعية")
        brand(e)
        await i.response.send_message(embed=e, view=DungeonRoomView(i.user.id, 0))

    @discord.ui.button(label="⚔️ مبارزة",         style=discord.ButtonStyle.danger,    row=2)
    async def duel_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        if not _cd_ok(md, "last_duel", 12):
            remaining = _cd_remaining(md, "last_duel", 12)
            await i.response.send_message(
                f"⏰ المبارزة متاحة مرتين يومياً!\nالمتبقي: **{remaining}**", ephemeral=True); return
        members = _emp().get("members", {})
        targets = [
            i.guild.get_member(int(uid2))
            for uid2 in members
            if int(uid2) != i.user.id
        ]
        targets = [m for m in targets if m is not None]
        if not targets:
            await i.response.send_message("❌ لا يوجد محاربون آخرون حتى الآن!", ephemeral=True); return
        e = discord.Embed(
            title="⚔️  اختر خصمك للمبارزة",
            description=(
                f"{SEP}\n"
                "المبارزة: 3 جولات ·  أعلى نقاط حياة يفوز\n"
                f"**مكافأة الفوز:** 200 🖤  +  150 ⭐\n"
                f"{SEP}"
            ), color=CRIMSON)
        brand(e)
        await i.response.send_message(embed=e, view=DuelTargetView(i.guild.get_member(i.user.id), i.guild))

    @discord.ui.button(label="🔮 العرّاف",        style=discord.ButtonStyle.secondary, row=2)
    async def oracle_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        if not _cd_ok(md, "last_oracle", 24):
            remaining = _cd_remaining(md, "last_oracle", 24)
            await i.response.send_message(
                f"⏰ العرّاف مرة كل 24 ساعة!\nالمتبقي: **{remaining}**", ephemeral=True); return
        if md.get("shards", 0) < 100:
            await i.response.send_message("❌ تحتاج **100** 🖤 لاستشارة العرّاف!", ephemeral=True); return
        md["shards"] -= 100
        prophecy, accurate = get_oracle(md)
        md["last_oracle"] = datetime.utcnow().isoformat()
        _save()
        e = discord.Embed(
            title="🔮  نبوءة العرّاف  🔮",
            description=(
                "✦  *العرّاف يغمض عينيه ويتكلم…*  ✦\n\n"
                f"**❝  {prophecy}  ❞**\n\n"
                "*النبوءة تنطبق على مغامرتك القادمة.*\n"
                "*60% دقيقة · 40% مضللة*"
            ), color=PHANTOM)
        e.set_author(name=f"{i.user.display_name} — استشار العرّاف",
                     icon_url=i.user.display_avatar.url)
        e.set_footer(text="⚜  استخدم عين العرّاف من المتجر لنبوءة مضمونة الصحة!")
        await i.response.send_message(
            content=f"🔮 **{i.user.display_name}** استشار العرّاف…",
            embed=e)

    @discord.ui.button(label="🏅 الألقاب",        style=discord.ButtonStyle.secondary, row=2)
    async def titles_btn(self, i: discord.Interaction, _: Button):
        uid = str(i.user.id)
        md  = _get_member(uid)
        if not md:
            await i.response.send_message("❌ أنشئ شخصيتك أولاً.", ephemeral=True); return
        check_titles(md)
        _save()
        earned    = md.get("titles", [])
        active_t  = md.get("active_title")
        all_lines = []
        for t in TITLES_CATALOG:
            has  = t["id"] in earned
            is_active = t["id"] == active_t
            icon = "✅ " if has else "🔒 "
            flag = " ← **نشط**" if is_active else ""
            all_lines.append(f"{icon}**{t['name']}**{flag}\n   _{t['req']}_")
        e = discord.Embed(
            title="🏅  ألقابك الإمبراطورية",
            description=(
                f"{SEP}\n"
                + ("\n\n".join(all_lines) if all_lines else "لا ألقاب بعد")
                + f"\n{SEP}"
            ), color=DEEP_GOLD)
        brand(e)
        if earned:
            opts = [
                discord.SelectOption(
                    label=next(t["name"] for t in TITLES_CATALOG if t["id"] == tid),
                    value=tid,
                )
                for tid in earned
            ]
            v = View(timeout=60)
            sel = Select(placeholder="🏅  اختر لقباً للعرض…", options=opts)
            async def _set_title(interaction: discord.Interaction):
                if str(interaction.user.id) != uid:
                    await interaction.response.send_message("❌", ephemeral=True); return
                md["active_title"] = interaction.data["values"][0]
                _save()
                name = next((t["name"] for t in TITLES_CATALOG if t["id"]==md["active_title"]), "")
                await interaction.response.send_message(f"✅ لقبك النشط: **{name}**", ephemeral=True)
            sel.callback = _set_title
            v.add_item(sel)
            await i.response.send_message(embed=e, view=v)
        else:
            await i.response.send_message(embed=e)

    # ── صف 3 — دليل + إدارة ─────────────────────────────────────────
    @discord.ui.button(label="📖 دليل النظام", style=discord.ButtonStyle.primary, row=3)
    async def guide_btn(self, i: discord.Interaction, _: Button):
        await i.response.send_message(
            embed=build_guide_embed(0),
            view=GuideView(0),
            ephemeral=True)

    @discord.ui.button(label="🛡️ لوحة الإدارة", style=discord.ButtonStyle.danger, row=3)
    async def admin_empire_btn(self, i: discord.Interaction, _: Button):
        m = i.guild.get_member(i.user.id)
        if not (m and is_admin(m)):
            await i.response.send_message("❌ الإدارة فقط.", ephemeral=True); return
        e = discord.Embed(
            title="🛡️  لوحة إدارة الإمبراطورية",
            description=(
                f"{SEP}\n"
                "*أدوات التحكم الكاملة في نظام الإمبراطورية*\n"
                f"{SEP}"
            ), color=CRIMSON)
        brand(e)
        await i.response.send_message(embed=e, view=AdminEmpireView(), ephemeral=True)

# ══════════════════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════════════════

class EmpireCog(commands.Cog):
    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance
        # Ensure empire data structure exists
        _emp()

    @app_commands.command(
        name="empire",
        description="⚔️ الإمبراطورية المظلمة — لوحة المغامرات والتقدم"
    )
    async def cmd_empire(self, i: discord.Interaction):
        uid = str(i.user.id)
        md  = _get_member(uid)
        is_adm = is_admin(i.guild.get_member(i.user.id))
        members_count = len(_emp().get("members", {}))
        member_rank   = ""
        if md:
            rank_lvl, rank_name = get_rank(md.get("xp", 0))
            cls_info = CLASSES.get(md.get("class",""), {})
            member_rank = (
                f"\n{cls_info.get('emoji','⚔️')} {md.get('class','')}  ·  "
                f"{rank_name}  ·  "
                f"{md.get('shards',0):,} 🖤"
            )
        SEP2 = "═══════════════════════════"
        e = discord.Embed(
            description=(
                "*⚜  OBLIVION EMPIRE — Dark Empire Chronicles  ⚜*\n"
                f"*مرحباً يا محارب، **{i.user.display_name}**.*{member_rank}\n"
                "🌑 **ارتقِ في الرتب** · 🖤 **اجمع الشظايا** · ⚔️ **واجه خصومك**\n"
                f"👥 **{members_count}** محارب مسجّل في الإمبراطورية"
            ), color=DARK_EMPIRE)
        e.set_thumbnail(url=logo_url() or (bot_avatar() or discord.utils.MISSING))
        e.add_field(
            name="🗡️  ـ الشخصية والتطور ـ",
            value=(
                "⚔️ **شخصيتي** — أنشئ شخصيتك أو راجع إحصائياتك\n"
                "📅 **مكافأة يومية** — شظايا يومية + نظام السلسلة\n"
                "💰 **رصيدي** — شظاياك وخبرتك ورتبتك\n"
                "🏅 **الألقاب** — اعرض إنجازاتك للجميع"
            ), inline=False)
        e.add_field(
            name="⚔️  ـ المعارك والمغامرات ـ",
            value=(
                "🎯 **مغامرة** — سيناريو يومي بخيارات وإحصائيات\n"
                "🏰 **الزنزانة** — 3 غرف أسبوعياً · غنائم ومعارك\n"
                "⚔️ **مبارزة** — تحدّ محارباً آخر في 3 جولات\n"
                "🔮 **العرّاف** — نبوءة غامضة مقابل 100 🖤"
            ), inline=False)
        e.add_field(
            name="💰  ـ الاقتصاد والمخزون ـ",
            value=(
                "🏪 **المتجر** — معدات · جرعات · إضافات خاصة\n"
                "📦 **مخزوني** — عرض وتجهيز عناصرك\n"
                "🛠️ **الصنع** — ادمج المواد لصنع أدوات نادرة\n"
                "🏆 **الصدارة** — قائمة أقوى المحاربين"
            ), inline=False)
        e.add_field(
            name="📖  ـ للمبتدئين ـ",
            value="اضغط **دليل النظام** لتعرف كل شيء عن الإمبراطورية!",
            inline=False)
        e.set_footer(
            text="⚜  الإمبراطورية المظلمة  ·  كل الأزرار في مكان واحد",
            icon_url=logo_url() or discord.utils.MISSING)
        await i.response.send_message(embed=e, view=EmpirePanelView(is_adm))
        await log_action(i.guild, "⚔️ /empire", f"{i.user.mention} فتح لوحة الإمبراطورية")


async def setup(bot_instance: commands.Bot):
    # NOTE: do NOT call tree.sync() here — syncing happens in on_ready()
    await bot_instance.add_cog(EmpireCog(bot_instance))
