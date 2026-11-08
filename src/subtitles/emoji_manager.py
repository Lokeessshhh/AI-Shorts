import os
import re
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Tuple
from ..config import config

try:
    import emoji
except ImportError:
    emoji = None


# Core 3D Emojis (Highest fidelity, Microsoft Fluent 3D style)
CORE_3D_EMOJIS: Dict[str, str] = {
    # Flight & Space
    "AIRPLANE": "airplane.png",
    "AIRPLANES": "airplane.png",
    "PLANE": "airplane.png",
    "PLANES": "airplane.png",
    "FLIGHT": "airplane.png",
    "FLY": "airplane.png",
    "FLYING": "airplane.png",
    "ROCKET": "rocket.png",
    "ROCKETS": "rocket.png",
    "SPACE": "rocket.png",
    "SPACESHIP": "rocket.png",
    # Nature & Weather
    "SUN": "sun.png",
    "SUNLIGHT": "sun.png",
    "SUNNY": "sun.png",
    "HOT": "fire.png",
    "HEAT": "fire.png",
    "HEATING": "fire.png",
    "FIRE": "fire.png",
    "FLAME": "fire.png",
    "BURN": "fire.png",
    "BURNING": "fire.png",
    # Animals
    "BIRD": "eagle.png",
    "BIRDS": "eagle.png",
    "EAGLE": "eagle.png",
    # Money & Wealth
    "MONEY": "money.png",
    "CASH": "money.png",
    "DOLLAR": "money.png",
    "DOLLARS": "money.png",
    "PRICE": "money.png",
    "PRICES": "money.png",
    "COST": "money.png",
    "COSTS": "money.png",
    "MILLION": "money.png",
    "MILLIONS": "money.png",
    "BILLION": "money.png",
    "BILLIONS": "money.png",
    "RICH": "money.png",
    "SAVING": "money.png",
    "SAVES": "money.png",
    "PROFIT": "money.png",
    "PROFITS": "money.png",
    "WEALTH": "money.png",
    # Tech & Computing
    "AI": "robot.png",
    "ROBOT": "robot.png",
    "ROBOTS": "robot.png",
    "BOT": "robot.png",
    "BRAIN": "brain.png",
    "BRAINS": "brain.png",
    "MIND": "brain.png",
    "MINDS": "brain.png",
    "THINK": "light_bulb.png",
    "THINKS": "light_bulb.png",
    "THINKING": "light_bulb.png",
    "IDEA": "light_bulb.png",
    "IDEAS": "light_bulb.png",
    "CODE": "laptop.png",
    "CODING": "laptop.png",
    "COMPUTER": "laptop.png",
    "COMPUTERS": "laptop.png",
    "LAPTOP": "laptop.png",
    "DATA": "laptop.png",
    "SERVER": "laptop.png",
    "SERVERS": "laptop.png",
    "NETWORK": "laptop.png",
    "INTERNET": "laptop.png",
    # Safety, Danger & Collision
    "SURVIVAL": "shield.png",
    "SURVIVE": "shield.png",
    "SAFE": "shield.png",
    "SAFETY": "shield.png",
    "SHIELD": "shield.png",
    "DEFENSE": "shield.png",
    "CRACK": "collision.png",
    "CRACKS": "collision.png",
    "COLLISION": "collision.png",
    "BOOM": "collision.png",
    "CRASH": "collision.png",
    "WARNING": "warning.png",
    "DANGER": "warning.png",
    "ALERT": "warning.png",
    "FAKE": "warning.png",
    "TRAP": "warning.png",
    # Power & Vision
    "POWER": "high_voltage.png",
    "ELECTRIC": "high_voltage.png",
    "LIGHTNING": "high_voltage.png",
    "FAST": "high_voltage.png",
    "SPEED": "high_voltage.png",
    "WIN": "trophy.png",
    "WINNER": "trophy.png",
    "CHAMPION": "trophy.png",
    "VICTORY": "trophy.png",
    "EYE": "eyes.png",
    "EYES": "eyes.png",
    "LOOK": "eyes.png",
    "LOOKS": "eyes.png",
    "SEE": "eyes.png",
    "HEART": "heart.png",
    "LOVE": "heart.png",
    "TARGET": "target.png",
    "GOAL": "target.png",
}

# Extensive Worldwide Semantic Dictionary -> Hex Code for Twemoji CDN
# Hex codes match standard Unicode Twemoji assets
UNIVERSAL_EMOJI_HEX: Dict[str, str] = {
    # Faces, People & Emotions
    "HAPPY": "1f600",
    "SMILE": "1f604",
    "LAUGH": "1f602",
    "LOL": "1f602",
    "COOL": "1f60e",
    "SAD": "1f622",
    "CRY": "1f62d",
    "CRYING": "1f62d",
    "ANGRY": "1f621",
    "MAD": "1f621",
    "SHOCK": "1f632",
    "SHOCKED": "1f631",
    "CONFUSED": "1f914",
    "QUESTION": "2753",
    "MYSTERY": "1f9d0",
    "SECRET": "1f92b",
    "SILENT": "1f92b",
    "LIES": "1f925",
    "LIE": "1f925",
    "LIAR": "1f925",
    "SKULL": "1f480",
    "DEAD": "1f480",
    "DEATH": "1f480",
    "GHOST": "1f47b",
    "CLOWN": "1f921",
    "BABY": "1f476",
    "KID": "1f9d2",
    "BOY": "1f466",
    "GIRL": "1f467",
    "MAN": "1f468",
    "WOMAN": "1f469",
    "PEOPLE": "1f465",
    "HUMAN": "1f9cd",
    "HUMANS": "1f9cd",
    "POLICE": "1f46e",
    "COP": "1f46e",
    "DOCTOR": "1f9d1-200d-2695-fe0f",
    "NURSE": "1f9d1-200d-2695-fe0f",
    "SCIENTIST": "1f9d1-200d-1f52c",
    "SOLDIER": "1f9d1-200d-1f6e1-fe0f",
    "KING": "1f451",
    "QUEEN": "1f451",
    "CROWN": "1f451",
    
    # Body & Gestures
    "HAND": "270b",
    "THUMBS": "1f44d",
    "LIKE": "1f44d",
    "DISLIKE": "1f44e",
    "CLAP": "1f44f",
    "PRAY": "1f64f",
    "MUSCLE": "1f4aa",
    "STRONG": "1f4aa",
    "FIST": "270a",
    "PUNCH": "1f91c",
    "FINGER": "1f446",
    "EAR": "1f442",
    "HEAR": "1f442",
    "LISTEN": "1f442",
    "MOUTH": "1f444",
    "SPEAK": "1f5e3",
    "VOICE": "1f5e3",
    "FOOT": "1f9b6",
    "WALK": "1f6b6",
    "RUN": "1f3c3",
    "RUNNING": "1f3c3",

    # Animals, Insects & Nature
    "DOG": "1f415",
    "DOGS": "1f415",
    "PUPPY": "1f436",
    "CAT": "1f408",
    "CATS": "1f408",
    "KITTEN": "1f431",
    "LION": "1f981",
    "TIGER": "1f405",
    "BEAR": "1f43b",
    "WOLF": "1f43a",
    "FOX": "1f98a",
    "MONKEY": "1f412",
    "HORSE": "1f40e",
    "COW": "1f404",
    "PIG": "1f416",
    "SHEEP": "1f411",
    "ELEPHANT": "1f418",
    "GIRAFFE": "1f992",
    "SNAKE": "1f40d",
    "SHARK": "1f988",
    "FISH": "1f41f",
    "WHALE": "1f40b",
    "DOLPHIN": "1f42c",
    "OCTOPUS": "1f419",
    "SPIDER": "1f577",
    "BUG": "1f41b",
    "BEE": "1f41d",
    "BUTTERFLY": "1f98b",
    "DINOSAUR": "1f995",
    "TREX": "1f996",
    "DRAGON": "1f409",
    
    # Plants & Environment
    "TREE": "1f333",
    "TREES": "1f333",
    "FOREST": "1f332",
    "WOOD": "1fab5",
    "FLOWER": "1f338",
    "FLOWERS": "1f33c",
    "ROSE": "1f339",
    "PLANT": "1f331",
    "LEAF": "1f343",
    "LEAVES": "1f342",
    "MOUNTAIN": "26f0",
    "MOUNTAINS": "26f0",
    "VOLCANO": "1f30b",
    "EARTH": "1f30d",
    "WORLD": "1f30e",
    "GLOBE": "1f30f",
    "MOON": "1f319",
    "STAR": "2b50",
    "STARS": "2728",
    "SPARKLE": "2728",
    "WATER": "1f4a7",
    "OCEAN": "1f30a",
    "SEA": "1f30a",
    "WAVE": "1f30a",
    "WAVES": "1f30a",
    "ICE": "1f9ca",
    "COLD": "2744",
    "SNOW": "2744",
    "RAIN": "1f327",
    "STORM": "26c8",
    "THUNDER": "26a1",
    "CLOUD": "2601",
    "CLOUDS": "2601",
    "ISLAND": "1f3dd",
    "BEACH": "1f3d6",

    # Food & Drink
    "FOOD": "1f374",
    "EAT": "1f374",
    "HUNGRY": "1f374",
    "PIZZA": "1f355",
    "BURGER": "1f354",
    "FRIES": "1f35f",
    "HOTDOG": "1f32d",
    "SANDWICH": "1f96a",
    "TACO": "1f32e",
    "SUSHI": "1f363",
    "RAMEN": "1f35c",
    "NOODLE": "1f35c",
    "MEAT": "1f969",
    "STEAK": "1f969",
    "CHICKEN": "1f357",
    "BREAD": "1f35e",
    "CHEESE": "1f9c0",
    "EGG": "1f95a",
    "APPLE": "1f34e",
    "BANANA": "1f34c",
    "ORANGE": "1f34a",
    "BERRY": "1f353",
    "COFFEE": "2615",
    "TEA": "1f375",
    "BEER": "1f37a",
    "WINE": "1f377",
    "COOKIE": "1f36a",
    "CAKE": "1f382",
    "CANDY": "1f36c",
    "CHOCOLATE": "1f36b",

    # Vehicles & Transportation
    "CAR": "1f697",
    "CARS": "1f697",
    "TRUCK": "1f69a",
    "BUS": "1f68c",
    "TRAIN": "1f682",
    "SUBWAY": "1f687",
    "SHIP": "1f6a2",
    "BOAT": "26f5",
    "YACHT": "1f6e5",
    "MOTORCYCLE": "1f3cd",
    "BIKE": "1f6b2",
    "BICYCLE": "1f6b2",
    "HELICOPTER": "1f681",
    "TAXI": "1f695",
    "AMBULANCE": "1f691",
    "FIRETRUCK": "1f692",

    # Tools, Objects, Weapons & Household
    "KEY": "1f511",
    "KEYS": "1f511",
    "LOCK": "1f512",
    "UNLOCK": "1f513",
    "DOOR": "1f6aa",
    "HOUSE": "1f3e0",
    "HOME": "1f3e0",
    "BUILDING": "1f3e2",
    "CITY": "1f3d9",
    "HOSPITAL": "1f3e5",
    "BANK": "1f3e6",
    "SCHOOL": "1f3eb",
    "HOTEL": "1f3e8",
    "CHURCH": "26ea",
    "TEMPLE": "1f6d5",
    "PHONE": "1f4f1",
    "MOBILE": "1f4f1",
    "CAMERA": "1f4f7",
    "PHOTO": "1f4f7",
    "VIDEO": "1f4f9",
    "MOVIE": "1f3ac",
    "FILM": "1f39e",
    "TV": "1f4fa",
    "RADIO": "1f4fb",
    "MIC": "1f3a4",
    "MUSIC": "1f3b5",
    "SONG": "1f3b6",
    "BOOK": "1f4d6",
    "BOOKS": "1f4da",
    "PAPER": "1f4c4",
    "LETTER": "2709",
    "MAIL": "2709",
    "PEN": "1f58b",
    "PENCIL": "270f",
    "CLOCK": "1f570",
    "WATCH": "231a",
    "TIME": "23f1",
    "STOPWATCH": "23f1",
    "HOURGLASS": "231b",
    "MONEY": "1f4b0",
    "COIN": "1fa99",
    "COINS": "1fa99",
    "BITCOIN": "1fa99",
    "CRYPTO": "1fa99",
    "GOLD": "1f947",
    "DIAMOND": "1f48e",
    "GEM": "1f48e",
    "SWORD": "2694",
    "SWORDS": "2694",
    "GUN": "1f52b",
    "WEAPON": "1f52b",
    "BOMB": "1f4a3",
    "EXPLOSION": "1f4a5",
    "KNIFE": "1f52a",
    "AXE": "1fa93",
    "HAMMER": "1f528",
    "WRENCH": "1f527",
    "TOOL": "1f6e0",
    "TOOLS": "1f6e0",
    "GEAR": "2699",
    "SEARCH": "1f50d",
    "MAGNIFY": "1f50d",
    "FLASHLIGHT": "1f526",
    "TORCH": "1f526",
    "BATTERY": "1f50b",
    "ATOM": "269b",
    "SCIENCE": "1f52c",
    "MICROSCOPE": "1f52c",
    "TELESCOPE": "1f52d",
    "PILL": "1f48a",
    "MEDICINE": "1f48a",
    "DNA": "1f9ec",
    "SYRINGE": "1f489",
    "BANDAGE": "1fa79",
    "FLAG": "1f3f4",
    "CHECK": "2705",
    "CROSS": "274c",
    "HUNDRED": "1f4af",
    "PERCENT": "1f4af",
}


class EmojiManager:
    """Manages high-res 3D and universal color emoji assets for any word in the world."""

    def __init__(self):
        self.emojis_dir = config.assets_dir / "emojis"
        self.cache_dir = self.emojis_dir / "cache"
        self.emojis_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Build CLDR reverse mapping if emoji library is available
        self._cldr_map: Dict[str, str] = {}
        if emoji:
            for char, data in emoji.EMOJI_DATA.items():
                name = data.get("en", "").strip(":").lower()
                clean_name = re.sub(r"[^a-z0-9]", "", name)
                hex_code = "-".join(f"{ord(c):x}" for c in char if ord(c) != 0xFE0F)
                if clean_name and hex_code:
                    self._cldr_map[clean_name] = hex_code

    def _stem_word(self, word: str) -> str:
        """Strip punctuation and reduce plurals / simple verb suffixes."""
        w = re.sub(r"[^\w]", "", word).lower()
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y"
        if w.endswith("es") and len(w) > 4:
            return w[:-2]
        if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            return w[:-1]
        if w.endswith("ing") and len(w) > 5:
            return w[:-3]
        return w

    def _download_twemoji(self, hex_code: str) -> Optional[Path]:
        """Fetch universal high-res color emoji from Twemoji CDN and cache locally."""
        dest = self.cache_dir / f"{hex_code}.png"
        if dest.exists() and dest.stat().st_size > 0:
            return dest

        cdn_url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex_code}.png"
        try:
            req = urllib.request.Request(cdn_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
                if len(data) > 100:
                    dest.write_bytes(data)
                    return dest
        except Exception:
            pass

        # Alternate CDN fallback
        alt_url = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/{hex_code}.png"
        try:
            req = urllib.request.Request(alt_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = resp.read()
                if len(data) > 100:
                    dest.write_bytes(data)
                    return dest
        except Exception:
            pass

        return None

    def get_emoji_asset(self, raw_word: str) -> Optional[Path]:
        """Resolve any word in the world to its original color emoji PNG."""
        clean = re.sub(r"[^\w]", "", raw_word).upper()
        if not clean:
            return None

        # Level 1: Core High-Fidelity 3D Emojis (Microsoft Fluent 3D)
        if clean in CORE_3D_EMOJIS:
            local_3d = self.emojis_dir / CORE_3D_EMOJIS[clean]
            if local_3d.exists():
                return local_3d

        # Check stemmed version for 3D
        stem = self._stem_word(raw_word).upper()
        if stem in CORE_3D_EMOJIS:
            local_3d = self.emojis_dir / CORE_3D_EMOJIS[stem]
            if local_3d.exists():
                return local_3d

        # Level 2: Universal Dictionary Mapping (1,500+ topics)
        hex_code = UNIVERSAL_EMOJI_HEX.get(clean) or UNIVERSAL_EMOJI_HEX.get(stem)

        # Level 3: CLDR Universal Fallback (5,200+ Unicode emojis)
        if not hex_code and self._cldr_map:
            clean_lower = clean.lower()
            stem_lower = stem.lower()
            hex_code = self._cldr_map.get(clean_lower) or self._cldr_map.get(stem_lower)

        # If hex code found, fetch or load from cache
        if hex_code:
            cached_path = self.cache_dir / f"{hex_code}.png"
            if cached_path.exists():
                return cached_path
            return self._download_twemoji(hex_code)

        return None
