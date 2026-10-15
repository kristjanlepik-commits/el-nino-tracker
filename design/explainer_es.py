"""Spanish edition of "How a flood is made" (Kristjan, 16 Oct: "this matters,
I think, for Spain").

The prose is the editor's (copy/flood_explainer.es.md). This module holds
the DESIGN labels in Spanish: chapter words and questions, stage stamps,
legends, map names, tooltips, source lines, and the words the canvases draw
(window.I18N). Labels the editor sends in the copy file's "## labels"
section ("English: Spanish", one per line) override these; everything here
was drafted by design overnight and is flagged for the editor's review.

translate(html) rewrites the English build's design text outside <script>
and <style>; exact phrases first, longest first, then patterned strings.
"""
import re

# The editor's choice (2bd00f79), which supersedes design's draft.
SLUG = "asi-se-forma-una-inundacion"
TITLE = "Así se forma una inundación"

MON = {"Jan": "ene", "Feb": "feb", "Mar": "mar", "Apr": "abr", "May": "may", "Jun": "jun",
       "Jul": "jul", "Aug": "ago", "Sep": "sep", "Oct": "oct", "Nov": "nov", "Dec": "dic"}

# Pump captions must start with these (the scene clock is pinned to them).
PUMP_DATES = ["27 de septiembre", "29 de septiembre", "30 de septiembre", "1 de octubre", "3 de octubre"]
PUMP_WK_DATES = ["18 de octubre", "19 de octubre"]

# The words the canvases draw, read by each scene module's L().
I18N = {
    "litres": "{n} litros en un metro cuadrado",
    "tub1": "un cuarto de bañera", "tub2": "media bañera", "tub3": "casi una bañera",
    "tub4": "una bañera llena",
    "seaN": "MEDITERRÁNEO OCCIDENTAL \u00b7 SEPTIEMBRE NORMAL",
    "seaNs": "media 1991 a 2020",
    "seaH": "MEDITERRÁNEO OCCIDENTAL \u00b7 SEPTIEMBRE 2026",
    "seaHs": "el más cálido en un registro que empieza en 1940",
    "motion": "MOVIMIENTO ILUSTRATIVO",
    "hour": "Hora {h} de 24",
    "compass": "N NE E SE S SO O NO",
    "mon": "ene feb mar abr may jun jul ago sep oct nov dic",
    "fc": "previsión",
    "pool": "Bolsa fría {v} \u00b0C sobre lo normal",
    "onshore": "Hacia tierra: del {d}, {s} m/s",
    "months": "Mayo Junio Julio Agosto Septiembre",
    "dec": ",",
}

PHRASES = {
    # chapter words and questions
    ">Rain<": ">Lluvia<", ">Heat<": ">Calor<", ">Sea<": ">Mar<", ">Air<": ">Aire<",
    ">Pump<": ">Bomba<", ">Ground<": ">Suelo<", ">Weekend<": ">Fin de semana<",
    "How much is 159 millimetres?": "¿Cuánto son 159 milímetros?",
    "How hot did the summer get?": "¿Cuánto calor hizo este verano?",
    "Where did the water come from?": "¿De dónde salió el agua?",
    "How much water can air hold?": "¿Cuánta agua cabe en el aire?",
    "What lifted it and set it off?": "¿Qué la elevó y la hizo caer?",
    "Why didn't the ground take it?": "¿Por qué el suelo no la absorbió?",
    "What does this weekend look like?": "¿Cómo se presenta este fin de semana?",
    # header and footer
    "Floods &middot; explainer &middot; 16 October 2026": "Inundaciones &middot; explicativo &middot; 16 de octubre de 2026",
    "Data: ERA5 (Copernicus Climate Change Service), 2026 preliminary; AEMET (Barcelona Fabra, station 0200E). Compiled by the floods desk.":
        "Datos: ERA5 (Servicio de Cambio Climático de Copernicus), 2026 provisional; AEMET (Barcelona Fabra, estación 0200E). Elaborado por la sección de inundaciones.",
    # rain
    "Barcelona<span class=\"pl-long\"> &middot; Fabra observatory</span> &middot; 3 October 2026":
        "Barcelona<span class=\"pl-long\"> &middot; observatorio Fabra</span> &middot; 3 de octubre de 2026",
    "Drawn to scale &middot; 1 m square, 20 cm walls": "A escala &middot; 1 m cuadrado, paredes de 20 cm",
    "litres on one square metre": "litros en un metro cuadrado",
    "&asymp; one full bathtub": "&asymp; una bañera llena",
    "on every square metre &middot; a bath holds about 150 litres, for scale":
        "en cada metro cuadrado &middot; una bañera tiene unos 150 litros, como referencia",
    "BARCELONA</text>": "BARCELONA</text>",
    # heat
    "Colder</span>": "Más frío</span>", "Warmer</span>": "Más cálido</span>",
    "&middot; scale &plusmn;3 &deg;C, saturates beyond": "&middot; escala &plusmn;3 &deg;C, satura más allá",
    "Each month of 2026 against the same month in 1991 to 2020: sea surface temperature over the sea, air temperature at 2 m over land. ERA5 monthly means, 2026 preliminary.":
        "Cada mes de 2026 frente al mismo mes de 1991 a 2020: temperatura de la superficie del mar sobre el mar, temperatura del aire a 2 m sobre tierra. Medias mensuales ERA5, 2026 provisional.",
    "September 2026</div>": "Septiembre 2026</div>",
    # sea
    "Temperatures measured: western Mediterranean (Alboran, Balearic, Gulf of Lion), September mean, ERA5; 2026 is the warmest September in a record going back to 1940 (1 of 87). The motion is illustrative: the warmer sea is drawn with a heat shimmer and slightly denser vapour, not to a measured rate.":
        "Temperaturas medidas: Mediterráneo occidental (Alborán, Baleares, golfo de León), media de septiembre, ERA5; 2026 es el septiembre más cálido en un registro que empieza en 1940 (1.º de 87). El movimiento es ilustrativo: el mar más cálido se dibuja con reverberación de calor y algo más de vapor, no a una tasa medida.",
    # air
    "No September in this record reaches it.": "Ningún septiembre de este registro llega a ese valor.",
    "Global total column water vapour, area-weighted, ERA5. About 7% more water vapour per degree C of warming (Clausius-Clapeyron; IPCC AR6 WG1 ch. 8).":
        "Vapor de agua total en columna, global, ponderado por área, ERA5. Alrededor de un 7 % más de vapor de agua por cada grado de calentamiento (Clausius-Clapeyron; IPCC AR6 GT1 cap. 8).",
    "WATER VAPOUR IN THE AIR, EVERY SEPTEMBER SINCE 1940, % VS 1991-2020":
        "VAPOR DE AGUA EN EL AIRE, CADA SEPTIEMBRE DESDE 1940, % FRENTE A 1991-2020",
    "Water vapour in the air, every September since 1940, % vs 1991-2020":
        "Vapor de agua en el aire, cada septiembre desde 1940, % frente a 1991-2020",
    # pump
    "ERA5 &middot; measured &middot; 2026 preliminary": "ERA5 &middot; medido &middot; 2026 provisional",
    "ECMWF forecast &middot; run": "Previsión del ECMWF &middot; pasada",
    "Sea, September vs normal": "Mar, sept. frente a lo normal",
    "Sea, 8 to 12 October vs normal": "Mar, 8-12 oct. frente a lo normal",
    "Cold air, 5 km up": "Aire frío, a 5 km", "Wind, 1.5 km up": "Viento, a 1,5 km",
    "Heights exaggerated &middot; every layer is a measured field": "Alturas exageradas &middot; cada capa es un campo medido",
    "Heights exaggerated &middot; cold air and wind are ECMWF's model forecast, not measurements":
        "Alturas exageradas &middot; el aire frío y el viento son la previsión del modelo del ECMWF, no mediciones",
    "AEMET on where the low will sit: &ldquo;elevada incertidumbre&rdquo;, high uncertainty.":
        "AEMET sobre dónde se situará la baja: &ldquo;elevada incertidumbre&rdquo;.",
    "This weekend<span>": "Este fin de semana<span>",
    "The same layers, in ECMWF's forecast. Run": "Las mismas capas, en la previsión del ECMWF. Pasada",
    "UTC. Not a forecast of ours.": "UTC. No es una previsión nuestra.",
    # ground
    "Dry ground<span>soaks the rain in</span>": "Suelo seco<span>absorbe la lluvia</span>",
    "Already wet<span>fills, and the rest runs off</span>": "Ya mojado<span>se llena, y el resto escurre</span>",
    ">River<": ">Río<",
    "Same rain on both &middot; illustrative &middot; not to scale": "La misma lluvia en ambos &middot; ilustrativo &middot; no a escala",
    # weekend map
    ">SPAIN<": ">ESPAÑA<", ">MEDITERRANEAN SEA<": ">MAR MEDITERRÁNEO<",
    ">BALEARIC ISLANDS<": ">ISLAS BALEARES<", ">ALGERIA<": ">ARGELIA<",
    "Floods since 1982</b>": "Inundaciones desde 1982</b>",
    "Damaging floods on this coast, by year. A selection, not a ranking; markers place each at a named town, not its extent. HANZE v2.1 to 2020 (Paprotny et al. 2024); 2024 from named news sources.":
        "Inundaciones con daños en esta costa, por año. Una selección, no una clasificación; cada marcador sitúa el episodio en una localidad, no indica su extensión. HANZE v2.1 hasta 2020 (Paprotny et al. 2024); 2024, de fuentes periodísticas citadas.",
    "Wet ground, now</b>": "Suelo húmedo, ahora</b>",
    "Topsoil after the first storm, filled where it is among the wettest third of 36 years for the date, darker the higher it ranks; outlined areas are within the usual range. ERA5, top 7 cm, 8 to 10 October.":
        "Suelo superficial tras la primera tormenta: relleno donde está entre el tercio más húmedo de 36 años para la fecha, más oscuro cuanto más alto; las zonas solo perfiladas están dentro de lo habitual. ERA5, 7 cm superiores, 8 a 10 de octubre.",
    "AEMET's warnings</b>": "Avisos de AEMET</b>",
    "AEMET's rain and thunderstorm warnings for 17 to 20 October, drawn at the level AEMET set.":
        "Avisos de AEMET por lluvias y tormentas del 17 al 20 de octubre, en el nivel que fijó AEMET.",
    "Issued up to": "Emitidos hasta", "Source: AEMET OpenData (Meteoalerta).": "Fuente: AEMET OpenData (Meteoalerta).",
    "Not a forecast of ours, and no combined score: each layer is shown as its source published it.":
        "No es una previsión nuestra ni una puntuación combinada: cada capa se muestra tal como la publicó su fuente.",
    # closing loop
    ">feeds<": ">alimenta<", ">lifted<": ">elevado<", ">falls on<": ">cae sobre<",
    ">drains back<": ">vuelve al mar<", ">warms the sea and the air<": ">calienta el mar y el aire<",
    ">Hour 0 of 24<": ">Hora 0 de 24<",
    # aria and alt
    "A loop: the sea feeds the air, the air is lifted by the pump, the rain falls on the ground, the ground drains back to the sea; heat at the centre warms the sea and the air.":
        "Un ciclo: el mar alimenta el aire, el motor eleva el aire, la lluvia cae sobre el suelo y el suelo vuelve al mar; en el centro, el calor calienta el mar y el aire.",
    "Map of Spain's Mediterranean coast and the Balearics: damaging floods since 1982, topsoil wetter than normal after the first storm, and AEMET's warnings for 17 to 20 October.":
        "Mapa de la costa mediterránea española y Baleares: inundaciones con daños desde 1982, suelo más húmedo de lo normal tras la primera tormenta y avisos de AEMET del 17 al 20 de octubre.",
    "Map of the western Mediterranean, 27 September to 3 October 2026: a cold air pool over the Atlantic five kilometres up weakens, and the wind off Barcelona turns south-easterly, onshore from a record-warm sea.":
        "Mapa del Mediterráneo occidental, del 27 de septiembre al 3 de octubre de 2026: una bolsa de aire frío a cinco kilómetros sobre el Atlántico se debilita y el viento frente a Barcelona gira al sureste, hacia la costa desde un mar de récord.",
    "Two sea surfaces side by side. A normal September at 23.6 degrees, and September 2026 at 26.0 degrees, with water vapour rising from both at the measured evaporation rate.":
        "Dos superficies de mar, una junto a otra: un septiembre normal a 23,6 grados y septiembre de 2026 a 26,0 grados, con vapor de agua elevándose de ambas.",
    "Map of Europe, 2026 temperature against 1991 to 2020, September: much warmer than normal over France, Iberia, the western and central Mediterranean.":
        "Mapa de Europa, temperatura de 2026 frente a 1991-2020, septiembre: mucho más cálido de lo normal sobre Francia, la península ibérica y el Mediterráneo occidental y central.",
    "A one-metre-square tray with 20 centimetre walls filling, to scale, to 159.1 millimetres of rain.":
        "Una bandeja de un metro cuadrado con paredes de 20 centímetros que se llena, a escala, hasta 159,1 milímetros de lluvia.",
    "Illustration: two hillsides under the same rain. Dry ground soaks it in; already wet ground fills and the rest runs off, so its river rises far higher.":
        "Ilustración: dos laderas bajo la misma lluvia. El suelo seco la absorbe; el ya mojado se llena y el resto escurre, así que su río sube mucho más.",
}

AREAS = {
    "Southern Catalonia, Ebro delta": "Sur de Cataluña, delta del Ebro",
    "Barcelona, Maresme, Girona coast": "Barcelona, Maresme, costa de Girona",
    "Castellon coast": "Costa de Castellón", "Valencia, central coast": "Valencia, costa central",
    "La Safor, Marina Alta": "La Safor, Marina Alta", "Alicante, Vega Baja": "Alicante, Vega Baja",
    "Murcia coast": "Costa de Murcia", "Malaga, Costa del Sol": "Málaga, Costa del Sol",
}

EVENTS = {
    "Tous dam failure, Jucar basin": "Rotura de la presa de Tous, cuenca del Júcar",
    "Gota fria, Valencia coast": "Gota fría, costa de Valencia",
    "Catalonia, Llobregat and Francoli": "Cataluña, Llobregat y Francolí",
    "Valencia and the south-east coast": "Valencia y la costa sureste",
    "Lorca and the south-east": "Lorca y el sureste",
    "December floods, south-east and Mallorca": "Inundaciones de diciembre, sureste y Mallorca",
    "Sant Llorenc des Cardassar, Mallorca": "Sant Llorenç des Cardassar, Mallorca",
    "Vega Baja DANA": "DANA de la Vega Baja",
    "Catalonia and Mallorca": "Cataluña y Mallorca",
    "Storm Gloria": "Borrasca Gloria",
    "Valencia DANA": "DANA de Valencia",
    "Malaga, Guadalhorce valley (same DANA as Valencia)": "Málaga, valle del Guadalhorce (la misma DANA que Valencia)",
    "Malaga, second DANA": "Málaga, segunda DANA",
}


# The editor's keyed labels (copy/flood_explainer.es.md "## labels") mapped
# onto the English strings they replace. Where design drafted a different
# Spanish, the editor's wins.
EDITOR_KEYS = {
    "chapter-rain": ">Rain<", "chapter-heat": ">Heat<", "chapter-sea": ">Sea<", "chapter-air": ">Air<",
    "chapter-pump": ">Pump<", "chapter-ground": ">Ground<", "chapter-weekend": ">Weekend<",
    "q-rain": "How much is 159 millimetres?", "q-heat": "How hot did the summer get?",
    "q-sea": "Where did the water come from?", "q-air": "How much water can air hold?",
    "q-pump": "What lifted it and set it off?", "q-ground": "Why didn't the ground take it?",
    "q-weekend": "What does this weekend look like?",
    "loop-feeds": ">feeds<", "loop-lifted": ">lifted<", "loop-falls-on": ">falls on<",
    "loop-drains-back": ">drains back<", "loop-warms": ">warms the sea and the air<",
    "stage-scale": "Drawn to scale &middot; 1 m square, 20 cm walls",
    "stage-bathtub": "&asymp; one full bathtub",
    "stage-per-m2": "on every square metre &middot; a bath holds about 150 litres, for scale",
    "stage-heights": "Heights exaggerated &middot; every layer is a measured field",
    "stage-same-rain": "Same rain on both &middot; illustrative &middot; not to scale",
    "map-floods": "Floods since 1982</b>", "map-wet": "Wet ground, now</b>", "map-aemet": "AEMET's warnings</b>",
}


def editor_labels(raw):
    """Turn the editor's keyed labels into phrase overrides and I18N words."""
    out = {}
    def wrap(key, val):
        en = EDITOR_KEYS[key]
        val = val.replace(" · ", " &middot; ")
        if en.startswith(">") and en.endswith("<"):
            return en, ">" + val + "<"
        if en.endswith("</b>"):
            return en, val + "</b>"
        if en.startswith("&asymp; "):
            return en, "&asymp; " + val
        return en, val
    for k, v in raw.items():
        if k in EDITOR_KEYS:
            en, es = wrap(k, v)
            out[en] = es
    if "stage-dry" in raw and ": " in raw["stage-dry"]:
        a, b = raw["stage-dry"].split(": ", 1)
        out["Dry ground<span>soaks the rain in</span>"] = "%s<span>%s</span>" % (a, b)
    if "stage-wet" in raw and ": " in raw["stage-wet"]:
        a, b = raw["stage-wet"].split(": ", 1)
        out["Already wet<span>fills, and the rest runs off</span>"] = "%s<span>%s</span>" % (a, b)
    if "stage-weekend" in raw:
        out["This weekend<span>"] = raw["stage-weekend"] + "<span>"
    if "stage-forecast-note" in raw:
        out["Heights exaggerated &middot; cold air and wind are ECMWF's model forecast, not measurements"] = \
            "Alturas exageradas &middot; " + raw["stage-forecast-note"]
    if "stage-motion" in raw:
        I18N["motion"] = raw["stage-motion"].upper()
    if "stage-onshore" in raw:
        I18N["onshore"] = raw["stage-onshore"].replace("[SE]", "{d}").replace("N m/s", "{s} m/s")
    if "stage-bathtub" in raw:
        I18N["tub4"] = raw["stage-bathtub"]
    return out


def _nth_es(n):
    return "%d.º" % int(n)


def translate(html, labels=None):
    """English build to Spanish, outside <script> and <style>."""
    table = dict(PHRASES)
    for en, es in (labels or {}).items():
        table[en] = es
    # The page escapes apostrophes (AEMET&#x27;s), so match both spellings.
    for en, es in list(table.items()):
        if "'" in en:
            table[en.replace("'", "&#x27;")] = es.replace("'", "&#x27;")
    for en, es in AREAS.items():
        table[en + ": "] = es + ": "
    parts = re.split(r'(<script\b.*?</script>|<style\b.*?</style>)', html, flags=re.S)
    keys = sorted(table, key=len, reverse=True)
    for i in range(0, len(parts), 2):
        s = parts[i]
        for k in keys:
            s = s.replace(k, table[k])
        # topsoil tooltips
        s = re.sub(r"topsoil ([+-]\d+)% vs normal, (\d+)\w\w wettest of (\d+)",
                   lambda m: "suelo superficial %s %% frente a lo normal, %s más húmedo de %s"
                   % (m.group(1), _nth_es(m.group(2)), m.group(3)), s)
        # flood tooltips: "Oct 1982, Tous dam failure, Jucar basin"
        for en, es in EVENTS.items():
            s = s.replace(en, es)
        s = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})",
                   lambda m: "%s %s" % (MON[m.group(1)], m.group(2)), s)
        # AEMET tooltips: time ranges
        s = re.sub(r"(\d\d-\d\d \d\d:\d\d) to (\d\d-\d\d \d\d:\d\d)", r"\1 a \2", s)
        parts[i] = s
    return "".join(parts)
