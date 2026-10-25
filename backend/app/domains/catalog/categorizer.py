import re
import unicodedata
from typing import Dict, List, Optional


def normalize_text(text: str) -> str:
    """Removes accents, lowercases, and strips punctuation."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


# Mapping from Mercadona Online primary categories to system category slugs
MERCADONA_TOP_CATEGORY_MAP: Dict[str, str] = {
    "Fruta y verdura": "frutas-y-verduras",
    "Huevos, leche y mantequilla": "lacteos-y-huevos",
    "Postres y yogures": "lacteos-y-huevos",
    "Carne": "carniceria-y-charcuteria",
    "Charcutería y quesos": "carniceria-y-charcuteria",
    "Marisco y pescado": "pescaderia",
    "Panadería y pastelería": "panaderia-y-pasteleria",
    "Cereales y galletas": "panaderia-y-pasteleria",
    "Arroz, legumbres y pasta": "despensa-y-conservas",
    "Conservas, caldos y cremas": "despensa-y-conservas",
    "Aceite, especias y salsas": "despensa-y-conservas",
    "Aperitivos": "despensa-y-conservas",
    "Azúcar, caramelos y chocolate": "despensa-y-conservas",
    "Cacao, café e infusiones": "despensa-y-conservas",
    "Agua y refrescos": "bebidas-y-refrescos",
    "Bodega": "bebidas-y-refrescos",
    "Zumos": "bebidas-y-refrescos",
    "Congelados": "congelados",
    "Limpieza y hogar": "limpieza-y-hogar",
    "Cuidado del cabello": "cuidado-personal-y-perfumeria",
    "Cuidado facial y corporal": "cuidado-personal-y-perfumeria",
    "Maquillaje": "cuidado-personal-y-perfumeria",
    "Bebé": "cuidado-personal-y-perfumeria",
    "Fitoterapia y parafarmacia": "cuidado-personal-y-perfumeria",
    "Pizzas y platos preparados": "platos-preparados",
    "Mascotas": "mascotas",
}

# Heuristic keyword matching for tickets or products without online category
CATEGORY_KEYWORDS: List[tuple[List[str], str]] = [
    # Pescadería
    (
        [
            "pescado", "merluza", "salmon", "rape", "bonito", "atun", "dorada", "lubina",
            "bacalao", "sepia", "calamar", "gamba", "langostino", "mejillon", "almeja",
            "pulpo", "sardina", "boqueron", "rodajas", "colas de rape", "gulas", "surimi",
            "pez espada", "emperador", "pescadilla", "lenguado", "trucha", "marisco"
        ],
        "pescaderia",
    ),
    # Carnicería y Charcutería
    (
        [
            "jamon", "chorizo", "lomo", "pavo", "pollo", "carne", "ternera", "cerdo",
            "salchichas", "salchichon", "bacon", "salami", "pechuga", "secreto",
            "costilla", "picada", "hamburguesa", "conejo", "morcilla", "fuet",
            "chistorra", "embutido", "fiambre", "alitas", "jamoncitos", "contramuslo",
            "cabecero", "longaniza", "butifarra", "sobrasada", "mortadela", "serrano",
            "serranito", "frankfurt", "chuleton", "entrecot", "solomillo", "carpaccio"
        ],
        "carniceria-y-charcuteria",
    ),
    # Lácteos y Huevos
    (
        [
            "leche", "queso", "yogur", "mantequilla", "cuajada", "kefir", "nata",
            "huevos", "rallado", "gouda", "mozzarella", "mozza", "emmental", "parmesano",
            "brie", "camembert", "semicurado", "curado", "desnatada", "semidesnatada",
            "entera", "beber fresa", "beber", "yogures", "flan", "natillas", "petit"
        ],
        "lacteos-y-huevos",
    ),
    # Bebidas y Refrescos
    (
        [
            "agua", "vino", "cerveza", "cerv", "c s gluten", "s gluten", "refresco", "cola", "fanta", "nestea",
            "fuze", "tea", "zumo", "sidra", "ginebra", "ron", "whisky", "vodka",
            "licor", "tonica", "gaseosa", "bebida", "fontabil", "fontebil", "font", "font vella", "cortes",
            "radler", "shandy", "isotonico", "aquarius", "red bull", "monster", "ambar", "botellin",
            "botellines", "triple zero", "sin alcohol", "cerveza tostada"
        ],
        "bebidas-y-refrescos",
    ),
    # Frutas y Verduras
    (
        [
            "acelga", "borraja", "cardo", "tomate", "patata", "cebolla", "zanahoria",
            "manzana", "platano", "naranja", "lechuga", "batata", "calabacin", "champiñon",
            "champi", "kiwi", "freson", "ciruela", "melocoton", "mandarina", "uva", "pera",
            "limon", "pimiento", "ajo", "puerro", "judia", "espinaca", "esparrago",
            "brocoli", "coliflor", "pepino", "aguacate", "fruta", "verdura", "ensalada",
            "berenjena", "alcachofa", "setas", "castaña", "nectarina", "sandia", "melon",
            "escarola", "romana", "rucula", "canonges", "canonigos", "remolacha",
            "calabaza", "frambuesa", "arandanos", "cereza", "ens nueva", "paraguayo"
        ],
        "frutas-y-verduras",
    ),
    # Panadería y Pastelería
    (
        [
            "pan", "barra", "integral", "tostadas", "pan tostado", "biscotes", "molde", "croissant", "galletas",
            "magdalenas", "bollo", "picos", "reganas", "colines", "napolitana", "bizcocho",
            "harina", "masa", "panecillo", "panecillo tostado", "hogaza", "chapata", "baguette", "cruasan",
            "palmera", "donuts", "rosquillas", "crackers"
        ],
        "panaderia-y-pasteleria",
    ),
    # Platos Preparados
    (
        [
            "pizza", "lasaña", "tortilla", "canelones", "empanada", "sushi", "sandwich",
            "ensaladilla", "gazpacho", "salmorejo", "dochi", "tarta", "listo para comer",
            "hummus", "guacamole", "poke", "arroz al horno", "paella"
        ],
        "platos-preparados",
    ),
    # Congelados
    (
        [
            "congelado", "ultracongelado", "helado", "hielo", "nuggets", "croquetas",
            "varitas", "polos", "corneto", "sorbete"
        ],
        "congelados",
    ),
    # Limpieza y Hogar
    (
        [
            "detergente", "suavizante", "lavavajillas", "lejia", "limpiador", "friegasuelos",
            "bolsas", "bolsa", "papel higienico", "servilleta", "servilletas", "estropajo",
            "bayeta", "insecticida", "ambientador", "recambio liquido", "lavadora",
            "pastillas", "papel cocina", "aluminio", "film", "difusor", "parking",
            "vaso reutilizable", "cuchilloreutilizable", "bandejas", "cubiertos",
            "fregona", "escoba", "plato llano", "plato grande", "vasos"
        ],
        "limpieza-y-hogar",
    ),
    # Cuidado Personal y Perfumería
    (
        [
            "champu", "gel", "desodorante", "dentifrico", "pasta dientes", "cepillo",
            "crema", "toallitas", "cuchillas", "afeitado", "colonia", "pañales", "jabon",
            "maquinillas", "body", "deliplus", "perfume", "maquillaje", "locion",
            "limpia manos", "enjuague", "balsamo", "acondicionador", "mascarilla",
            "protector solar", "tampones", "compresas", "algodon"
        ],
        "cuidado-personal-y-perfumeria",
    ),
    # Mascotas
    (
        [
            "perro", "gato", "compy", "mascota", "pienso", "arena gatos",
            "snack perro", "comida perro", "comida gato"
        ],
        "mascotas",
    ),
    # Despensa y Conservas (General pantry fallback for dry food)
    (
        [
            "arroz", "pasta", "fideos", "macarrones", "espagueti", "lentejas",
            "garbanzos", "alubias", "tomate frito", "conserva", "aceite", "oliva",
            "girasol", "vinagre", "sal", "especias", "pimienta", "oregano", "pimenton",
            "caldo", "azucar", "cafe", "te", "miel", "cacao", "mayonesa", "salsa",
            "allioli", "ketchup", "mostaza", "aceituna", "pringles", "cacahuete",
            "almendra", "nuez", "avellana", "turron", "chocolate", "choco", "pat classicas",
            "patatas fritas", "snacks", "capsulas", "espresso", "soja"
        ],
        "despensa-y-conservas",
    ),
]


def classify_product(
    canonical_name: str,
    aliases: Optional[List[str]] = None,
    mercadona_category_path: Optional[str] = None,
    mercadona_display_name: Optional[str] = None,
) -> str:
    """
    Infers the best matching system category slug.
    Priority order:
    1. Mercadona Online official category_path (if linked).
    2. Heuristic keywords from canonical name, aliases, and display name.
    3. Default fallback: 'otros'.
    """
    # 1. Use official Mercadona Online category path if available
    if mercadona_category_path and " > " in mercadona_category_path:
        top_category = mercadona_category_path.split(" > ")[0].strip()
        dname_lower = (mercadona_display_name or "").lower()

        # Disambiguate cheese vs meat in "Charcutería y quesos"
        if top_category == "Charcutería y quesos":
            if any(k in dname_lower for k in ["queso", "gouda", "mozza", "parmesano", "brie", "rallado", "curado"]):
                return "lacteos-y-huevos"
            return "carniceria-y-charcuteria"

        matched_slug = MERCADONA_TOP_CATEGORY_MAP.get(top_category)
        if matched_slug:
            return matched_slug

    # 2. Keyword heuristic on all available names
    tokens_to_search: List[str] = [canonical_name]
    if aliases:
        tokens_to_search.extend(aliases)
    if mercadona_display_name:
        tokens_to_search.append(mercadona_display_name)

    combined_text = normalize_text(" ".join(tokens_to_search))

    for keywords_list, slug in CATEGORY_KEYWORDS:
        for kw in keywords_list:
            norm_kw = normalize_text(kw)
            pattern = rf"\b{re.escape(norm_kw)}(?:s|es)?\b"
            if re.search(pattern, combined_text):
                return slug

    return "otros"

