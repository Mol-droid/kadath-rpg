#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KADATH v4.0 — La Búsqueda Onírica de la Desconocida Kadath
EDICIÓN ONÍRICA COMPLETA | Molvic Studio © 2024
Basado en H.P. Lovecraft | Motor: curses (stdlib)

NOVEDADES v4.0:
- Trastornos de cordura (Paranoia, Alucinaciones, Amnesia, etc.)
- 8 finales múltiples con consecuencias reales
- Sistema de conjuros expandido (6 rituales)
- Entidades cósmicas (Nyarlathotep, Nodens)
- Descripciones atmosféricas (día/noche, cordura)
- New Game+ con persistencia de logros
- 20 logros expandados
- Capas de sueño (profundidad onírica)
"""
import curses, os, sys, json, time, random, signal
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum, auto
from copy import deepcopy

VERSION, STUDIO = "4.0", "Molvic Studio © 2024"
MAX_INV, PESO_MAX, VEL_BASE = 12, 20, 10
XP_TABLA = {1:0, 2:100, 3:200, 4:350, 5:500, 6:800, 7:1200}
SAVE_DIR = Path.home() / ".kadath_saves"

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS Y CLASES BASE
# ═══════════════════════════════════════════════════════════════════════════════
class GS(Enum):
    MENU=auto(); EXPLOR=auto(); COMBAT=auto(); INV=auto()
    TIENDA=auto(); MAPA=auto(); PAUSA=auto(); LVLUP=auto()
    MUERTE=auto(); FINAL=auto(); QUESTS=auto(); AYUDA=auto()
    RITUAL=auto(); ENTIDAD=auto(); NGPLUS=auto()

class Ciclo(Enum):
    DIA="DIA"; NOCHE="NOCHE"

class Trastorno(Enum):
    """Trastornos mentales lovecraftianos"""
    PARANOIA = "Paranoia: Sospechas de todos"
    ALUCINACIONES = "Alucinaciones: Ves lo que no existe"
    AMNESIA = "Amnesia: Olvidas el camino"
    MEGALOMANIA = "Megalomanía: Te crees un dios"
    CATATONIA = "Catatonía: Te congelas en combate"
    INSOMNIO = "Insomnio: No puedes descansar"

class CapaSueño(Enum):
    """Profundidad del sueño onírico"""
    SUPERFICIAL = 1
    PROFUNDO = 2
    ABISMAL = 3
    INSONDABLE = 4
    VACIO = 5

@dataclass
class Item:
    id: str; nombre: str; tipo: str; desc: str = ""
    valor_c: int = 0; valor_v: int = 0; peso: int = 1
    usable: bool = False; cantidad: int = 1
    dmin: int = 0; dmax: int = 0; tdano: str = "FISICO"
    dur: int = -1; durmax: int = -1
    defensa: int = 0; resist: int = 0; bvel: int = 0
    efecto: Dict = field(default_factory=dict)
    ritual: bool = False; conjuro: str = ""
    
    def to_dict(self): 
        return {k:v for k,v in self.__dict__.items() if not callable(v)}

@dataclass
class Enemy:
    id: str; nombre: str; vida: int; vidamax: int
    dmin: int; dmax: int; tdano: str; defensa: int
    vel: int; xp: int; oro_min: int; oro_max: int
    loot: List[Tuple[str,float]] = field(default_factory=list)
    jefe: bool = False; estados: List[str] = field(default_factory=list)
    entidad: bool = False; combative: bool = True

@dataclass
class Quest:
    id: str; titulo: str; giver: str; zona: str; desc: str
    objetivo: Dict; recompensa: Dict
    activa: bool = False; completada: bool = False

@dataclass
class Conjuro:
    id: str; nombre: str; coste: int; desc: str
    efecto: Dict; requisito: str = ""

# ═══════════════════════════════════════════════════════════════════════════════
# DATOS DEL JUEGO - EXPANDIDOS v4.0
# ═══════════════════════════════════════════════════════════════════════════════
ARMAS = {
    "punos": Item("punos","Puños","ARMA","Tus manos",0,0,0,dmin=3,dmax=8),
    "daga_onirica": Item("daga_onirica","Daga Onírica","ARMA","Hoja de sueños",80,32,1,dmin=8,dmax=15,tdano="ONIRICO",dur=10,durmax=10),
    "espada_sueno": Item("espada_sueno","Espada del Sueño","ARMA","Forjada en Celephaïs",200,80,2,dmin=15,dmax=25,dur=10,durmax=10),
    "cetro_ngranek": Item("cetro_ngranek","Cetro de Ngranek","ARMA","Poder ancestral",300,120,2,dmin=20,dmax=35,tdano="MAGICO",dur=8,durmax=8),
    "hoja_nodens": Item("hoja_nodens","Hoja de Nodens","ARMA","Bendecida por el dios",500,200,3,dmin=25,dmax=45,tdano="SAGRADO",dur=15,durmax=15),
}

ARMADURAS = {
    "sin_armadura": Item("sin_armadura","Sin armadura","ARMADURA","",0,0,0),
    "ropas_viajero": Item("ropas_viajero","Ropas de Viajero","ARMADURA","Cómodas",40,16,1,defensa=2,bvel=1),
    "capa_niebla": Item("capa_niebla","Capa de Niebla","ARMADURA","Etérea",120,48,1,defensa=5,resist=3,bvel=2),
    "armadura_gato": Item("armadura_gato","Armadura de Gato","ARMADURA","Bendecida",150,60,2,defensa=4,resist=5),
    "vestiduras_sueno": Item("vestiduras_sueno","Vestiduras del Sueño","ARMADURA","Tejidas en Kadath",400,160,3,defensa=8,resist=8,bvel=1),
}

CONSUMIBLES = {
    "pocion_cordura": Item("pocion_cordura","Poción de Cordura","CONSUMIBLE","Calma la mente",30,12,1,usable=True,efecto={"cordura":25}),
    "balsamo_onirico": Item("balsamo_onirico","Bálsamo Onírico","CONSUMIBLE","Sana heridas",25,10,1,usable=True,efecto={"vida":30}),
    "elixir_voluntad": Item("elixir_voluntad","Elixir de Voluntad","CONSUMIBLE","Fortalece",35,14,1,usable=True,efecto={"voluntad":20}),
    "pan_gatos": Item("pan_gatos","Pan de los Gatos","CONSUMIBLE","Delicioso",15,6,1,usable=True,efecto={"vida":10,"cordura":5}),
    "incienso_ritual": Item("incienso_ritual","Incienso Ritual","CONSUMIBLE","Para rituales",50,20,1,usable=False,ritual=True),
    "sangre_antigua": Item("sangre_antigua","Sangre Antigua","CONSUMIBLE","De los Antiguos",100,40,1,usable=False,ritual=True),
}

MISION_ITEMS = {
    "piedra_comun": Item("piedra_comun","Piedra Común","MISION","Los Zoog la valoran"),
    "gatito_onirico": Item("gatito_onirico","Gatito Onírico","MISION","Perdido en el bosque"),
    "trofeo_ghast": Item("trofeo_ghast","Trofeo de Ghast","TROFEO","Colmillo de bestia",0,50,1),
    "mapa_frag": Item("mapa_frag","Fragmento del Mapa","MISION","Parte del mapa a Kadath"),
    "llave_catacumbas": Item("llave_catacumbas","Llave Catacumbas","CLAVE","Abre el paso"),
    "pergamino": Item("pergamino","Pergamino Antiguos","MISION","Texto pre-humano"),
    "cristal_sueno": Item("cristal_sueno","Cristal de Sueño","MISION","Contiene un sueño atrapado"),
    "ojo_yog": Item("ojo_yog","Ojo de Yog","RELQUIA","Te permite ver lo invisible"),
}

CONJUROS = {
    "conjuro_menor": Conjuro("conjuro_menor", "Conjuro Menor", 20, 
        "30-50 daño mágico", {"dano": (30,50), "tipo": "magico"}),
    "abrir_portico": Conjuro("abrir_portico", "Abrir Pórtico", 30,
        "Teletransporte a zona visitada", {"teletransporte": True}),
    "ver_invisible": Conjuro("ver_invisible", "Ver lo Invisible", 20,
        "Revela objetos/NPCs ocultos", {"revelar": True}),
    "hablar_muerto": Conjuro("hablar_muerto", "Hablar con Muerto", 40,
        "Interrogar enemigos caídos", {"interrogar": True}),
    "forma_eterea": Conjuro("forma_eterea", "Forma Etérea", 50,
        "Inmunidad 3 turnos", {"inmunidad": 3}),
    "invocar_nodens": Conjuro("invocar_nodens", "Invocar a Nodens", 100,
        "Aliado en combate (1 vez)", {"aliado": "nodens"}),
}

ENEMIGOS = {
    "zoog": Enemy("zoog","Zoog Traicionero",10,10,3,8,"FISICO",0,15,22,2,8,[("pan_gatos",0.3)]),
    "ghul": Enemy("ghul","Ghul Carroñero",35,35,8,15,"FISICO",2,8,47,5,15,[("trofeo_ghast",0.4)]),
    "ghast": Enemy("ghast","Ghast Cavernas",60,60,15,25,"FISICO",5,18,82,10,25,[("trofeo_ghast",0.6)]),
    "sacerdote": Enemy("sacerdote","Sacerdote sin Rostro",45,45,10,20,"ONIRICO",8,10,102,20,40,[("pergamino",0.3)]),
    "nightgaunt": Enemy("nightgaunt","Nightgaunt",40,40,12,22,"ONIRICO",4,16,88,8,20,[]),
    "guardian": Enemy("guardian","Guardián de Leng",150,150,25,40,"FISICO",10,12,252,80,120,[],jefe=True),
    "brujo_leng": Enemy("brujo_leng","Brujo de Leng",80,80,20,35,"MAGICO",6,14,150,40,80,[("pergamino",0.5)]),
}

# ENTIDADES CÓSMICAS - No siempre combative
ENTIDADES = {
    "nyarlathotep": Enemy("nyarlathotep","Nyarlathotep",999,999,50,100,"COSMICO",20,25,0,0,0,[],entidad=True,combative=False),
    "nodens": Enemy("nodens","Nodens el Anciano",999,999,0,0,"SAGRADO",0,0,0,0,0,[],entidad=True,combative=False),
    "hastur": Enemy("hastur","Hastur el Innombrable",999,999,60,120,"COSMICO",15,30,0,0,0,[],entidad=True,combative=False),
}

QUESTS = {
    "q01": Quest("q01","El Favor de los Gatos","menes","zona_1","Encuentra a Whisper",
        {"tipo":"tener","item":"gatito_onirico"},{"oro":50,"xp":80,"flag":"GATOS_ALIADOS"}),
    "q02": Quest("q02","El Trato de los Zoog","zoog","zona_2","Entrega el gatito a los Zoog",
        {"tipo":"entregar","item":"gatito_onirico"},{"oro":30,"xp":60,"item":"mapa_frag"}),
    "q03": Quest("q03","La Deuda de Dylath","arash","zona_3","Consigue un fragmento de cerámica",
        {"tipo":"tener","item":"trofeo_ghast"},{"oro":100,"xp":100,"flag":"RUTA_SEGURA"}),
    "q04": Quest("q04","El Ritual de Nodens","kuranes","zona_6","Reúne los componentes del ritual",
        {"tipo":"tener","item":"cristal_sueno"},{"oro":200,"xp":150,"conjuro":"invocar_nodens"}),
}

# ZONAS CON DESCRIPCIONES ATMOSFÉRICAS
ZONAS = {
    "zona_1": {
        "nombre": "Ulthar", "segura": True, "posada": True,
        "desc_dia": "El sol brilla sobre Ulthar, y los gatos te observan desde los tejados.",
        "desc_noche": "Las sombras se alargan. Los gatos susurran en los tejados...",
        "desc_cordura_alta": "Ves la belleza onírica de este lugar. Los gatos son sabios aliados.",
        "desc_cordura_baja": "Las piedras parecen respirar. Los gatos... son demasiados. Te observan.",
        "ascii": """
/\\     /\\      ╔══════════════════════╗
/  \\___/  \\     ║     ~ ULTHAR ~       ║
/  o     o  \\    ║  Ciudad de los Gatos ║
/      Y      \\   ╚══════════════════════╝""",
        "conexiones": ["zona_2", "zona_6"],
        "npcs": ["menes"], "tienda": True,
        "encuentros": [("zoog", 0.1)],
        "objetos": [("piedra_comun", "cerca de la fuente")]
    },
    "zona_2": {
        "nombre": "Bosque Zoog", "segura": False, "posada": False,
        "desc_dia": "El Bosque Encantado donde los Zoog acechan entre las sombras.",
        "desc_noche": "La niebla espesa oculta cosas que se arrastran...",
        "desc_cordura_alta": "Los árboles susurran secretos antiguos.",
        "desc_cordura_baja": "Las raíces te agarran. Algo te observa desde la oscuridad.",
        "ascii": """
, - ~ ~ ~ - ,     ╔═════════════════════╗
, '   /\\     /\\   ' , ║  BOSQUE DE LOS ZOOG ║
,    /    \\ /    \\    ,╚═════════════════════╝""",
        "conexiones": ["zona_1", "zona_3", "zona_4"],
        "npcs": ["zoog_gris"], "tienda": True,
        "encuentros": [("zoog", 0.25), ("ghul", 0.1)],
        "objetos": [("gatito_onirico", "entre raíces de roble")]
    },
    "zona_3": {
        "nombre": "Dylath-Leen", "segura": True, "posada": True,
        "desc_dia": "El puerto oscuro de muelles de basalto negro.",
        "desc_noche": "Las aguas reflejan estrellas que no existen en nuestro cielo.",
        "desc_cordura_alta": "Los mercaderes tienen mercancías exóticas.",
        "desc_cordura_baja": "Los muelles se mueven. El agua huele a sangre antigua.",
        "ascii": """
|    |    |      ╔══════════════════╗
)_)  )_)  )_)     ║   DYLATH-LEEN    ║
)___))___))___)    ╚══════════════════╝""",
        "conexiones": ["zona_2", "zona_4", "zona_7"],
        "npcs": ["arash"], "tienda": True,
        "encuentros": [("ghul", 0.15)],
        "objetos": []
    },
    "zona_4": {
        "nombre": "Montañas Humo", "segura": False, "posada": False,
        "desc_dia": "Picos envueltos en vapores sulfurosos donde merodean los Gules.",
        "desc_noche": "Fuegos fatuos bailan entre las rocas. No los sigas.",
        "desc_cordura_alta": "El aire es fino pero respirable.",
        "desc_cordura_baja": "Las montañas te observan. Tienen ojos en las cuevas.",
        "ascii": """
/\\                ╔═══════════════════╗
/  \\    /\\         ║ MONTAÑAS DEL HUMO ║
/    \\  /  \\  /\\    ╚═══════════════════╝""",
        "conexiones": ["zona_2", "zona_3", "zona_5"],
        "npcs": [], "tienda": False,
        "encuentros": [("ghul", 0.2), ("ghast", 0.15)],
        "objetos": []
    },
    "zona_5": {
        "nombre": "Catacumbas Zak", "segura": False, "posada": False,
        "desc_dia": "Laberinto de huesos bajo la tierra.",
        "desc_noche": "Los muertos susurran en la oscuridad eterna.",
        "desc_cordura_alta": "Los huesos están en paz aquí.",
        "desc_cordura_baja": "Te agarran desde las paredes. Los esqueletos caminan.",
        "ascii": """
╔═══╗ ╔═══╗ ╔═══╗   ╔══════════════════╗
║ ☠ ║ ║ ☠ ║ ║ ☠ ║   ║ CATACUMBAS ZAK   ║
╚═══╝ ╚═══╝ ╚═══╝   ╚══════════════════╝""",
        "conexiones": ["zona_4", "zona_6"],
        "npcs": [], "tienda": False,
        "encuentros": [("ghul", 0.3), ("sacerdote", 0.15)],
        "objetos": [("llave_catacumbas", "altar oculto")]
    },
    "zona_6": {
        "nombre": "Celephaïs", "segura": True, "posada": True,
        "desc_dia": "La ciudad maravillosa de torres de ónice bajo cielos eternos.",
        "desc_noche": "Las estrellas forman patrones que no deberías comprender.",
        "desc_cordura_alta": "La belleza de este lugar trasciende lo mortal.",
        "desc_cordura_baja": "Las torres se retuercen. Los cielos sangran luz negra.",
        "ascii": """
╔═══╗   ╔═══╗      ╔══════════════════╗
╔╝   ╚═══╝   ╚╗     ║    CELEPHAÏS     ║
╔╝  ◇     ◇    ╚╗    ╚══════════════════╝""",
        "conexiones": ["zona_1", "zona_5", "zona_7"],
        "npcs": ["kuranes"], "tienda": True,
        "encuentros": [],
        "objetos": [("cristal_sueno", "torre de Kuranes")]
    },
    "zona_7": {
        "nombre": "Mar Oriab", "segura": False, "posada": False,
        "desc_dia": "Aguas misteriosas que conectan los reinos del sueño.",
        "desc_noche": "Algo enorme se mueve bajo las olas...",
        "desc_cordura_alta": "El mar canta una canción antigua.",
        "desc_cordura_baja": "Las aguas te llaman. Puedes respirar bajo ellas.",
        "ascii": """
~  ~  ~  ~  ~  ~  ~    ╔══════════════════╗
~    ⛵    ~    ~    ~   ║    MAR ORIAB     ║
~  ~  ~  ~  ~  ~  ~  ~  ~ ╚══════════════════╝""",
        "conexiones": ["zona_3", "zona_6", "zona_8"],
        "npcs": [], "tienda": False,
        "encuentros": [("nightgaunt", 0.2)],
        "objetos": []
    },
    "zona_8": {
        "nombre": "Inquanok", "segura": False, "posada": False,
        "desc_dia": "La ciudad de ónice, última parada antes de Leng.",
        "desc_noche": "Las sombras tienen forma humana. No todas lo son.",
        "desc_cordura_alta": "Los habitantes son corteses pero distantes.",
        "desc_cordura_baja": "Sus rostros cambian cuando no miras directamente.",
        "ascii": """
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   ╔══════════════════╗
▓  ╔════════╗   ▓   ║     INQUANOK     ║
▓  ║ ÓNICE  ║   ▓   ╚══════════════════╝""",
        "conexiones": ["zona_7", "zona_9"],
        "npcs": [], "tienda": False,
        "encuentros": [("sacerdote", 0.25), ("nightgaunt", 0.2)],
        "objetos": []
    },
    "zona_9": {
        "nombre": "Meseta Leng", "segura": False, "posada": False,
        "desc_dia": "Tierra prohibida donde la realidad se desmorona.",
        "desc_noche": "Los Dioses Exteriores susurran en tu mente.",
        "desc_cordura_alta": "Puedes sentir el poder de este lugar.",
        "desc_cordura_baja": "La realidad se deshilacha. Ves lo que hay detrás del velo.",
        "ascii": """
▲       ▲       ▲    ╔══════════════════╗
/█\\     /█\\     /█\\   ║   MESETA LENG    ║
/███\\   /███\\   /███\\  ╚══════════════════╝""",
        "conexiones": ["zona_8", "zona_10"],
        "npcs": [], "tienda": False,
        "encuentros": [("sacerdote", 0.3), ("guardian", 0.1), ("brujo_leng", 0.05)],
        "objetos": []
    },
    "zona_10": {
        "nombre": "Kadath", "segura": False, "posada": False,
        "desc_dia": "La Desconocida Kadath. El destino de tu búsqueda.",
        "desc_noche": "Los Dioses del Sueño te esperan. ¿Estás listo?",
        "desc_cordura_alta": "Comprendes la verdad. Eres más que mortal.",
        "desc_cordura_baja": "La verdad te destruye. No deberías haber venido.",
        "ascii": """
★  ★  ★  ★  ★     ╔══════════════════╗
★ ╔══════════╗ ★  ║      KADATH      ║
★ ╔╝  ☆☆☆☆  ╚╗ ★  ╚══════════════════╝""",
        "conexiones": [],
        "npcs": [], "tienda": False,
        "encuentros": [],
        "objetos": []
    },
}

TIENDA_CATALOGO = {
    "zona_1": ["pocion_cordura", "balsamo_onirico", "pan_gatos", "daga_onirica"],
    "zona_2": ["pan_gatos", "pocion_cordura"],
    "zona_3": ["elixir_voluntad", "capa_niebla", "espada_sueno"],
    "zona_6": ["cetro_ngranek", "armadura_gato", "elixir_voluntad", "hoja_nodens", "vestiduras_sueno"],
}

HABILIDADES = {
    2: ("paso_silencioso", "Paso Silencioso", "30% evitar encuentros"),
    3: ("vision_onirica", "Visión Onírica", "Revela objetos ocultos"),
    4: ("conjuro_menor", "Conjuro Menor", "30-50 daño mágico"),
    5: ("pacto_onirico", "Pacto Onírico", "Negociar con enemigos"),
    6: ("forma_niebla", "Forma de Niebla", "Inmunidad física 2 turnos"),
    7: ("ritual_mayor", "Ritual Mayor", "Acceso a conjuros avanzados"),
}

MEJORAS = [
    ("vida_15", "+15 Vida máxima"),
    ("cordura_15", "+15 Cordura máxima"),
    ("voluntad_15", "+15 Voluntad máxima"),
    ("dano_10", "+10% daño permanente"),
    ("resist_10", "+10% resistencia"),
    ("vel_2", "+2 Velocidad"),
    ("suerte_5", "+5 Suerte (mejor loot)"),
]

LOGROS = {
    "logro_01": ("Primer Sangre", "Derrota tu primer enemigo"),
    "logro_02": ("Gatito Salvado", "Encuentra al gatito onírico"),
    "logro_03": ("Rico Soñador", "Consigue 500 oro"),
    "logro_04": ("Cordura Frágil", "Sobrevive con cordura < 20 por 10 turnos"),
    "logro_05": ("Aliado Felino", "Consigue la alianza de los gatos"),
    "logro_06": ("Traidor", "Traiciona a los gatos"),
    "logro_07": ("Explorador", "Visita todas las zonas"),
    "logro_08": ("Coleccionista", "Consigue todo el equipo legendario"),
    "logro_09": ("Ritualista", "Aprende todos los conjuros"),
    "logro_10": ("Superviviente", "Sobrevive 100 turnos"),
    "logro_11": ("Nyarlathotep Visto", "Encuentra al Dios Caótico"),
    "logro_12": ("Nodens Bendice", "Invoca a Nodens exitosamente"),
    "logro_13": ("Kadath Alcanzado", "Llega a la ciudad desconocida"),
    "logro_14": ("Apoteosis", "Consigue el final verdadero"),
    "logro_15": ("Ciclo Roto", "Completa el juego en NG+"),
    "logro_16": ("Pacifista", "Completa sin matar"),
    "logro_17": ("Cazador", "Derrota 50 enemigos"),
    "logro_18": ("Ritual Prohibido", "Completa un ritual oscuro"),
    "logro_19": ("Soñador Eterno", "Alcanza la capa de sueño 5"),
    "logro_20": ("Maestro del Sueño", "Todos los logros desbloqueados"),
}

# ═══════════════════════════════════════════════════════════════════════════════
# CLASE PLAYER - EXPANDIDA v4.0
# ═══════════════════════════════════════════════════════════════════════════════
class Player:
    def __init__(self, ng_plus: bool = False, logros_previos: List[str] = None):
        self.vida = self.vida_max = 100
        self.cordura = self.cordura_max = 100
        self.voluntad = self.voluntad_max = 100
        self.vel_base = VEL_BASE
        self.reputacion = 0
        self.oro = 20 if not ng_plus else 50
        self.nivel = 1
        self.xp = 0
        self.bonus_dano = 0.0
        self.bonus_resist = 0.0
        self.arma = Item("punos","Puños","ARMA",dmin=3,dmax=8)
        self.armadura = Item("sin_armadura","Sin armadura","ARMADURA")
        self.inventario: List[Item] = [] if not ng_plus else [Item("piedra_comun","Piedra Común","MISION")]
        self.habilidades: List[str] = [] if not ng_plus else ["paso_silencioso"]
        self.estados: Dict[str,int] = {}
        self.flags: Dict[str,bool] = {"GATOS_ALIADOS":False,"GATOS_HOSTILES":False,
            "RUTA_SEGURA":False,"PACIFISTA":True,"tutorial":False,
            "NYARLATHOTEP_VISTO":False,"NODENS_BENDICE":False}
        self.mapa_frags = 0
        self.muertes = 0
        self.quests_activas: List[str] = []
        self.quests_completas: List[str] = []
        self.logros: List[str] = logros_previos if logros_previos else []
        self.bestiario: Dict[str,int] = {}
        self.zona = "zona_1"
        self.zonas_visitadas = ["zona_1"] if not ng_plus else ["zona_1"]
        self.descansos = 0
        self.ciclo = Ciclo.DIA
        self.turno = 0
        self.tiempo = 0
        self.eventos: List[str] = []
        self.decisiones: List[str] = []
        # NUEVO v4.0
        self.trastornos: List[Trastorno] = []
        self.capa_sueño = CapaSueño.SUPERFICIAL
        self.conjuros_aprendidos: List[str] = ["conjuro_menor"]
        self.ng_plus = ng_plus
        self.partidas_completadas = 0
        self.enemigos_derrotados = 0
        self.turnos_totales = 0
        self.rituales_completados = 0

    def vel_efectiva(self) -> int:
        v = self.vel_base + self.nivel
        if self.armadura: v += self.armadura.bvel
        return max(1, v)

    def cat_rep(self) -> str:
        if self.reputacion > 80: return "HEROICA"
        if self.reputacion >= 50: return "POSITIVA"
        if self.reputacion >= 20: return "NEUTRAL"
        if self.reputacion >= 0: return "SOSPECHOSA"
        return "TEMIDA"

    def xp_siguiente(self) -> int:
        return XP_TABLA.get(self.nivel+1, 9999)

    def puede_subir(self) -> bool:
        return self.nivel < 7 and self.xp >= self.xp_siguiente()

    def subir_nivel(self):
        if self.nivel < 7:
            self.nivel += 1
            if self.nivel in HABILIDADES:
                h = HABILIDADES[self.nivel]
                if h[0] not in self.habilidades:
                    self.habilidades.append(h[0])

    def mod_stat(self, stat: str, val: int):
        if stat == "vida": self.vida = max(0, min(self.vida_max, self.vida + val))
        elif stat == "cordura": 
            self.cordura = max(0, min(self.cordura_max, self.cordura + val))
            self._verificar_trastornos()
        elif stat == "voluntad": self.voluntad = max(0, min(self.voluntad_max, self.voluntad + val))
        elif stat == "oro": self.oro = max(0, min(9999, self.oro + val))
        elif stat == "reputacion": self.reputacion = max(-100, min(100, self.reputacion + val))

    def _verificar_trastornos(self):
        """NUEVO v4.0: Aplicar trastornos según cordura"""
        if self.cordura < 25 and len(self.trastornos) < 2:
            disponibles = [t for t in Trastorno if t not in self.trastornos]
            if disponibles and random.random() < 0.3:
                self.trastornos.append(random.choice(disponibles))
        elif self.cordura < 50 and len(self.trastornos) < 1:
            disponibles = [t for t in Trastorno if t not in self.trastornos]
            if disponibles and random.random() < 0.15:
                self.trastornos.append(random.choice(disponibles))
        elif self.cordura >= 75 and self.trastornos:
            if random.random() < 0.2:
                self.trastornos.pop()

    def tiene_item(self, iid: str) -> bool:
        return any(i.id == iid for i in self.inventario)

    def add_item(self, item: Item) -> bool:
        if len(self.inventario) >= MAX_INV: return False
        self.inventario.append(item)
        return True

    def rem_item(self, iid: str) -> bool:
        for i, it in enumerate(self.inventario):
            if it.id == iid:
                self.inventario.pop(i)
                return True
        return False

    def aprender_conjuro(self, conjuro_id: str) -> bool:
        if conjuro_id not in self.conjuros_aprendidos:
            self.conjuros_aprendidos.append(conjuro_id)
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "vida": self.vida, "vida_max": self.vida_max,
            "cordura": self.cordura, "cordura_max": self.cordura_max,
            "voluntad": self.voluntad, "voluntad_max": self.voluntad_max,
            "vel_base": self.vel_base, "reputacion": self.reputacion,
            "oro": self.oro, "nivel": self.nivel, "xp": self.xp,
            "bonus_dano": self.bonus_dano, "bonus_resist": self.bonus_resist,
            "arma": self.arma.id if self.arma else "punos",
            "armadura": self.armadura.id if self.armadura else "sin_armadura",
            "inventario": [i.id for i in self.inventario],
            "habilidades": self.habilidades, "flags": self.flags,
            "mapa_frags": self.mapa_frags, "muertes": self.muertes,
            "quests_activas": self.quests_activas, "quests_completas": self.quests_completas,
            "logros": self.logros, "bestiario": self.bestiario,
            "zona": self.zona, "zonas_visitadas": self.zonas_visitadas,
            "descansos": self.descansos, "ciclo": self.ciclo.value,
            "turno": self.turno, "tiempo": self.tiempo,
            "eventos": self.eventos, "decisiones": self.decisiones,
            # NUEVO v4.0
            "trastornos": [t.name for t in self.trastornos],
            "capa_sueño": self.capa_sueño.name,
            "conjuros_aprendidos": self.conjuros_aprendidos,
            "ng_plus": self.ng_plus,
            "partidas_completadas": self.partidas_completadas,
            "enemigos_derrotados": self.enemigos_derrotados,
            "turnos_totales": self.turnos_totales,
            "rituales_completados": self.rituales_completados,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Player':
        p = cls(ng_plus=d.get("ng_plus", False))
        for k in ["vida","vida_max","cordura","cordura_max","voluntad","voluntad_max",
            "vel_base","reputacion","oro","nivel","xp","bonus_dano","bonus_resist",
            "mapa_frags","muertes","descansos","turno","tiempo",
            "partidas_completadas","enemigos_derrotados","turnos_totales","rituales_completados"]:
            if k in d: setattr(p, k, d[k])
        if d.get("arma") in ARMAS:
            p.arma = deepcopy(ARMAS[d["arma"]])
        if d.get("armadura") in ARMADURAS:
            p.armadura = deepcopy(ARMADURAS[d["armadura"]])
        p.inventario = []
        for iid in d.get("inventario", []):
            if iid in CONSUMIBLES: p.inventario.append(deepcopy(CONSUMIBLES[iid]))
            elif iid in MISION_ITEMS: p.inventario.append(deepcopy(MISION_ITEMS[iid]))
            elif iid in ARMAS: p.inventario.append(deepcopy(ARMAS[iid]))
            elif iid in ARMADURAS: p.inventario.append(deepcopy(ARMADURAS[iid]))
        p.habilidades = d.get("habilidades", [])
        p.flags = d.get("flags", p.flags)
        p.quests_activas = d.get("quests_activas", [])
        p.quests_completas = d.get("quests_completas", [])
        p.logros = d.get("logros", [])
        p.bestiario = d.get("bestiario", {})
        p.zona = d.get("zona", "zona_1")
        p.zonas_visitadas = d.get("zonas_visitadas", ["zona_1"])
        p.ciclo = Ciclo(d.get("ciclo", "DIA"))
        p.eventos = d.get("eventos", [])
        p.decisiones = d.get("decisiones", [])
        # NUEVO v4.0
        p.trastornos = [Trastorno[t] for t in d.get("trastornos", []) if t in Trastorno.__members__]
        p.capa_sueño = CapaSueño[d.get("capa_sueño", "SUPERFICIAL")]
        p.conjuros_aprendidos = d.get("conjuros_aprendidos", ["conjuro_menor"])
        return p

# ═══════════════════════════════════════════════════════════════════════════════
# UI MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class UI:
    def __init__(self, scr):
        self.scr = scr
        self.my, self.mx = scr.getmaxyx()
        self.colors = False
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_MAGENTA, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_RED, -1)
            curses.init_pair(6, curses.COLOR_BLUE, -1)
            curses.init_pair(7, curses.COLOR_WHITE, -1)
            self.colors = True
        except: pass
        curses.curs_set(0)
        scr.keypad(True)

    def resize(self):
        self.my, self.mx = self.scr.getmaxyx()

    def addstr(self, y, x, s, attr=0) -> bool:
        try:
            if 0 <= y < self.my and 0 <= x < self.mx:
                self.scr.addstr(y, x, s[:self.mx-x-1], attr)
                return True
        except: pass
        return False

    def col(self, n): return curses.color_pair(n) if self.colors else 0

    def barra(self, y, x, val, mx, w=10, c=1):
        try:
            p = max(0, min(w, int(val/mx*w))) if mx > 0 else 0
            self.addstr(y, x, "[" + "█"*p + "░"*(w-p) + "]", self.col(c))
        except: pass

    def caja(self, y, x, h, w, titulo=""):
        try:
            self.addstr(y, x, "╔" + "═"*(w-2) + "╗")
            for i in range(1, h-1):
                self.addstr(y+i, x, "║" + " "*(w-2) + "║")
            self.addstr(y+h-1, x, "╚" + "═"*(w-2) + "╝")
            if titulo:
                self.addstr(y, x+2, f" {titulo} ", self.col(4))
        except: pass

    def clear(self): self.scr.clear()
    def refresh(self): self.scr.refresh()
    def getch(self): return self.scr.getch()
    def wait(self): self.scr.getch()

# ═══════════════════════════════════════════════════════════════════════════════
# COMBAT ENGINE - EXPANDIDO v4.0
# ═══════════════════════════════════════════════════════════════════════════════
class Combat:
    def __init__(self, ui: UI, player: Player):
        self.ui, self.p = ui, player
        self.e: Optional[Enemy] = None
        self.turno = 0
        self.log: List[str] = []
        self.activo = False

    def iniciar(self, enemigo: Enemy) -> str:
        self.e = deepcopy(enemigo)
        self.turno = 0
        self.activo = True
        self.log = [f"¡{self.e.nombre} te ataca!"]
        if self.e.id not in self.p.bestiario:
            self.p.bestiario[self.e.id] = 0
        return self._loop()

    def _loop(self) -> str:
        while self.activo:
            self.turno += 1
            self._dibujar()
            res = self._turno_jugador()
            if res: return res
            if self.e.vida <= 0:
                return self._victoria()
            self._turno_enemigo()
            if self.p.vida <= 0: return "muerte"
            if self.p.cordura <= 0: return "locura"
            time.sleep(0.3)
        return "victoria" if self.e.vida <= 0 else "huida"

    def _dibujar(self):
        self.ui.clear()
        self.ui.addstr(0, 2, f"⚔ COMBATE - Turno {self.turno} ⚔", self.ui.col(5)|curses.A_BOLD)
        
        # Mostrar trastornos activos
        if self.p.trastornos:
            trastorno_text = ", ".join([t.name[:10] for t in self.p.trastornos[:2]])
            self.ui.addstr(1, 2, f"⚠ Trastornos: {trastorno_text}", self.ui.col(3))
        
        y = 2 if not self.p.trastornos else 3
        self.ui.addstr(y, 2, f"┌{'─'*35}┐")
        self.ui.addstr(y+1, 2, f"│ {self.e.nombre:^33} │", self.ui.col(5))
        pct = self.e.vida / self.e.vidamax if self.e.vidamax > 0 else 0
        blen = int(pct * 25)
        self.ui.addstr(y+2, 2, f"│ HP: [{'█'*blen}{'░'*(25-blen)}] {self.e.vida}/{self.e.vidamax} │")
        self.ui.addstr(y+3, 2, f"└{'─'*35}┘")
        
        y = 7
        self.ui.addstr(y, 2, f"┌{'─'*35}┐")
        self.ui.addstr(y+1, 2, f"│ {'RANDOLPH CARTER':^33} │", self.ui.col(1))
        self.ui.addstr(y+2, 2, "│ VIDA:     "); self.ui.barra(y+2, 14, self.p.vida, self.p.vida_max, 8, 1)
        self.ui.addstr(y+2, 26, f"{self.p.vida:3}/{self.p.vida_max:3} │")
        self.ui.addstr(y+3, 2, "│ CORDURA:  "); self.ui.barra(y+3, 14, self.p.cordura, self.p.cordura_max, 8, 2)
        self.ui.addstr(y+3, 26, f"{self.p.cordura:3}/{self.p.cordura_max:3} │")
        self.ui.addstr(y+4, 2, f"│ Arma: {self.p.arma.nombre[:25]:25} │")
        self.ui.addstr(y+5, 2, f"└{'─'*35}┘")
        
        y = 14
        for line in self.log[-4:]:
            self.ui.addstr(y, 2, line[:70])
            y += 1
        
        y = 19
        self.ui.addstr(y, 2, "[1] Atacar  [2] Usar Objeto  [3] Esquivar  [4] Huir", self.ui.col(4))
        if "conjuro_menor" in self.p.habilidades:
            self.ui.addstr(y+1, 2, "[5] Conjuro Menor")
        if "ritual_mayor" in self.p.habilidades and len(self.p.conjuros_aprendidos) > 1:
            self.ui.addstr(y+2, 2, "[6] Ritual Mayor")
        self.ui.refresh()

    def _turno_jugador(self) -> Optional[str]:
        # Verificar catatonía
        if Trastorno.CATATONIA in self.p.trastornos and random.random() < 0.2:
            self.log.append("¡Catatonía! Pierdes el turno")
            return None
        
        k = self.ui.getch()
        if k == ord('1'):
            dano = random.randint(self.p.arma.dmin, self.p.arma.dmax)
            dano += self.p.nivel * 2
            dano = max(1, dano - self.e.defensa)
            dano = int(dano * (1 + self.p.bonus_dano))
            # Megalomanía aumenta daño pero reduce defensa
            if Trastorno.MEGALOMANIA in self.p.trastornos:
                dano = int(dano * 1.3)
            self.e.vida -= dano
            self.log.append(f"Atacas con {self.p.arma.nombre}! {dano} daño")
            if self.p.arma.dur > 0:
                self.p.arma.dur -= 1
                if self.p.arma.dur <= 2:
                    self.log.append(f"¡{self.p.arma.nombre} casi se rompe!")
        elif k == ord('2'):
            cons = [i for i in self.p.inventario if i.usable]
            if cons:
                c = cons[0]
                for stat, val in c.efecto.items():
                    self.p.mod_stat(stat, val)
                self.log.append(f"Usas {c.nombre}")
                self.p.rem_item(c.id)
            else:
                self.log.append("No tienes consumibles")
        elif k == ord('3'):
            self.p.estados["esquivando"] = 1
            self.log.append("Te preparas para esquivar")
        elif k == ord('4'):
            prob = min(90, 40 + max(0, self.p.cordura - 50))
            if random.randint(1, 100) <= prob:
                self.log.append("¡Escapas!")
                self.activo = False
                return "huida"
            else:
                self.log.append("¡No puedes escapar!")
        elif k == ord('5') and "conjuro_menor" in self.p.habilidades:
            if self.p.voluntad >= 20:
                self.p.mod_stat("voluntad", -20)
                dano = random.randint(30, 50)
                self.e.vida -= dano
                self.log.append(f"¡Conjuro Menor! {dano} daño mágico")
            else:
                self.log.append("Sin voluntad suficiente")
        elif k == ord('6') and "ritual_mayor" in self.p.habilidades:
            self._ritual_mayor()
        return None

    def _ritual_mayor(self):
        """NUEVO v4.0: Sistema de rituales"""
        if self.p.voluntad >= 40:
            self.p.mod_stat("voluntad", -40)
            conjuro = random.choice(self.p.conjuros_aprendidos[1:]) if len(self.p.conjuros_aprendidos) > 1 else "forma_eterea"
            if conjuro == "forma_eterea":
                self.p.estados["inmunidad"] = 3
                self.log.append("¡Forma Etérea! Inmunidad 3 turnos")
            elif conjuro == "invocar_nodens":
                self.e.vida -= 100
                self.log.append("¡Nodens te ayuda! -100 daño")
                self.p.flags["NODENS_BENDICE"] = True
            self.p.rituales_completados += 1
        else:
            self.log.append("Sin voluntad suficiente para ritual")

    def _turno_enemigo(self):
        # Verificar inmunidad
        if "inmunidad" in self.p.estados and self.p.estados["inmunidad"] > 0:
            self.p.estados["inmunidad"] -= 1
            self.log.append("¡Inmunidad! El ataque no te afecta")
            return
        
        if "esquivando" in self.p.estados:
            if random.random() < 0.6:
                self.log.append("¡Esquivas el ataque!")
                del self.p.estados["esquivando"]
                return
            del self.p.estados["esquivando"]
        
        dano = random.randint(self.e.dmin, self.e.dmax)
        def_total = self.p.armadura.defensa if self.p.armadura else 0
        if self.e.tdano != "FISICO":
            def_total = self.p.armadura.resist if self.p.armadura else 0
        dano = max(1, dano - def_total)
        dano = int(dano * (1 - self.p.bonus_resist))
        
        # Paranoia aumenta daño recibido
        if Trastorno.PARANOIA in self.p.trastornos:
            dano = int(dano * 1.2)
        
        self.p.mod_stat("vida", -dano)
        self.log.append(f"{self.e.nombre} ataca! -{dano} vida")
        
        # Entidades cósmicas dañan cordura
        if self.e.entidad:
            self.p.mod_stat("cordura", -10)
            self.log.append("¡Presencia cósmica! -10 cordura")

    def _victoria(self) -> str:
        self.activo = False
        xp = self.e.xp
        oro = random.randint(self.e.oro_min, self.e.oro_max)
        self.p.xp += xp
        self.p.mod_stat("oro", oro)
        self.p.bestiario[self.e.id] = self.p.bestiario.get(self.e.id, 0) + 1
        self.p.enemigos_derrotados += 1
        
        if "logro_01" not in self.p.logros:
            self.p.logros.append("logro_01")
        if self.p.enemigos_derrotados >= 50 and "logro_17" not in self.p.logros:
            self.p.logros.append("logro_17")
        
        self.p.flags["PACIFISTA"] = False
        
        for iid, prob in self.e.loot:
            if random.random() < prob:
                if iid in CONSUMIBLES:
                    self.p.add_item(deepcopy(CONSUMIBLES[iid]))
                elif iid in MISION_ITEMS:
                    self.p.add_item(deepcopy(MISION_ITEMS[iid]))
        
        self.ui.clear()
        self.ui.caja(5, 10, 8, 45, "¡VICTORIA!")
        self.ui.addstr(7, 15, f"Derrotaste a {self.e.nombre}!")
        self.ui.addstr(9, 15, f"+{xp} XP  +{oro} oro")
        self.ui.addstr(12, 15, "Pulsa cualquier tecla...")
        self.ui.refresh()
        self.ui.wait()
        return "victoria"

# ═══════════════════════════════════════════════════════════════════════════════
# SAVE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class SaveMgr:
    def __init__(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)

    def guardar(self, p: Player, slot: str = "auto") -> bool:
        try:
            data = {"version": VERSION, "ts": datetime.now().isoformat(), "player": p.to_dict()}
            with open(SAVE_DIR / f"{slot}.json", 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            return False

    def cargar(self, slot: str = "auto") -> Optional[Player]:
        try:
            with open(SAVE_DIR / f"{slot}.json") as f:
                data = json.load(f)
                if data.get("version", "1.0") != VERSION:
                    print(f"⚠️ Save versión {data.get('version')} != {VERSION}")
                return Player.from_dict(data["player"])
        except Exception as e:
            print(f"❌ Error cargando: {e}")
            return None

    def slots(self) -> List[dict]:
        result = []
        for s in ["auto", "slot_1", "slot_2", "slot_3"]:
            fp = SAVE_DIR / f"{s}.json"
            if fp.exists():
                try:
                    with open(fp) as f:
                        d = json.load(f)
                        result.append({"nombre": s, "existe": True,
                            "zona": d["player"].get("zona", "?"),
                            "nivel": d["player"].get("nivel", 1)})
                except Exception as e:
                    result.append({"nombre": s, "existe": True, "corrupto": True})
            else:
                result.append({"nombre": s, "existe": False})
        return result

# ═══════════════════════════════════════════════════════════════════════════════
# GAME CONTROLLER - EXPANDIDO v4.0
# ═══════════════════════════════════════════════════════════════════════════════
class Game:
    def __init__(self, scr):
        self.scr = scr
        self.ui = UI(scr)
        self.p: Optional[Player] = None
        self.save = SaveMgr()
        self.combat: Optional[Combat] = None
        self.estado = GS.MENU
        self.running = True
        signal.signal(signal.SIGWINCH, lambda s,f: self.ui.resize())

    def run(self):
        try:
            while self.running:
                if self.estado == GS.MENU: self._menu()
                elif self.estado == GS.EXPLOR: self._explorar()
                elif self.estado == GS.COMBAT: self._combate()
                elif self.estado == GS.INV: self._inventario()
                elif self.estado == GS.MAPA: self._mapa()
                elif self.estado == GS.PAUSA: self._pausa()
                elif self.estado == GS.LVLUP: self._nivel_up()
                elif self.estado == GS.MUERTE: self._muerte()
                elif self.estado == GS.FINAL: self._final()
                elif self.estado == GS.QUESTS: self._quests()
                elif self.estado == GS.AYUDA: self._ayuda()
                elif self.estado == GS.TIENDA: self._tienda()
                elif self.estado == GS.RITUAL: self._ritual_menu()
                elif self.estado == GS.ENTIDAD: self._encuentro_entidad()
                elif self.estado == GS.NGPLUS: self._ng_plus_menu()
        except Exception as e:
            self._error(e)

    def _error(self, e):
        try:
            self.ui.clear()
            self.ui.caja(5, 5, 10, 60, "ERROR")
            self.ui.addstr(8, 10, f"Error: {str(e)[:45]}")
            if self.p: self.save.guardar(self.p, "crash")
            self.ui.addstr(10, 10, "Guardado de emergencia intentado.")
            self.ui.addstr(12, 10, "Pulsa tecla para salir...")
            self.ui.refresh()
            self.ui.wait()
        except: pass

    def _menu(self):
        self.ui.clear()
        logo = ["██╗  ██╗ █████╗ ██████╗  █████╗ ████████╗██╗  ██╗",
            "██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██║  ██║",
            "█████╔╝ ███████║██║  ██║███████║   ██║   ███████║",
            "██╔═██╗ ██╔══██║██║  ██║██╔══██║   ██║   ██╔══██║",
            "██║  ██╗██║  ██║██████╔╝██║  ██║   ██║   ██║  ██║",
            "╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝"]
        y = 2
        for l in logo:
            x = (self.ui.mx - len(l)) // 2
            self.ui.addstr(y, max(0,x), l, self.ui.col(4)|curses.A_BOLD)
            y += 1
        self.ui.addstr(y+1, (self.ui.mx-45)//2, "La Búsqueda Onírica de la Desconocida Kadath", self.ui.col(6))
        self.ui.addstr(y+2, (self.ui.mx-25)//2, "EDICIÓN ONÍRICA v4.0", self.ui.col(3))
        opts = ["[N] Nueva Partida", "[C] Continuar", "[G] NG+", "[S] Salir"]
        y += 4
        for o in opts:
            self.ui.addstr(y, (self.ui.mx-len(o))//2, o)
            y += 1
        self.ui.addstr(self.ui.my-2, (self.ui.mx-len(STUDIO))//2, STUDIO, self.ui.col(6))
        self.ui.refresh()
        k = self.ui.getch()
        if k in [ord('n'), ord('N')]:
            self.p = Player()
            self.combat = Combat(self.ui, self.p)
            self.save.guardar(self.p, "auto")
            self._intro()
            self.estado = GS.EXPLOR
        elif k in [ord('c'), ord('C')]:
            self._cargar()
        elif k in [ord('g'), ord('G')]:
            self._ng_plus_menu()
        elif k in [ord('s'), ord('S')]:
            self.running = False

    def _intro(self):
        self.ui.clear()
        texto = [
            "Tres veces soñé con la maravillosa ciudad en la cima de las montañas,",
            "y tres veces fui arrebatado antes de poder entrar en ella.",
            "",
            "Me llamo Randolph Carter, y he decidido buscar la ciudad",
            "en las Tierras del Sueño, donde los Dioses moran en Kadath.",
            "",
            "Mi viaje comienza en Ulthar, donde ningún hombre puede matar a un gato...",
            "",
            "⚠️ ADVERTENCIA: Tu cordura será puesta a prueba."
        ]
        self.ui.caja(3, 5, len(texto)+6, 70, "LA BÚSQUEDA COMIENZA")
        y = 6
        for l in texto:
            self.ui.addstr(y, 10, l, self.ui.col(6))
            y += 1
        self.ui.addstr(y+2, 10, "Pulsa cualquier tecla...")
        self.ui.refresh()
        self.ui.wait()

    def _cargar(self):
        self.ui.clear()
        self.ui.addstr(2, 2, "═══ CARGAR PARTIDA ═══", self.ui.col(4))
        slots = self.save.slots()
        y = 4
        for i, s in enumerate(slots):
            if s.get("corrupto"):
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: CORRUPTO", self.ui.col(5))
            elif s.get("existe"):
                zn = ZONAS.get(s.get("zona",""), {}).get("nombre", "?")
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: {zn} - Niv.{s.get('nivel',1)}")
            else:
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: VACÍO", self.ui.col(6))
            y += 2
        self.ui.addstr(y+1, 4, "[0] Volver")
        self.ui.refresh()
        k = self.ui.getch()
        if k >= ord('1') and k <= ord('4'):
            idx = k - ord('1')
            if idx < len(slots) and slots[idx].get("existe") and not slots[idx].get("corrupto"):
                p = self.save.cargar(slots[idx]["nombre"])
                if p:
                    self.p = p
                    self.combat = Combat(self.ui, self.p)
                    self.estado = GS.EXPLOR

    def _ng_plus_menu(self):
        """NUEVO v4.0: Menú New Game+"""
        self.ui.clear()
        self.ui.addstr(2, 2, "═══ NEW GAME+ ═══", self.ui.col(3))
        self.ui.addstr(4, 4, "NG+ mantiene:")
        self.ui.addstr(5, 6, "• Logros desbloqueados")
        self.ui.addstr(6, 6, "• Habilidades aprendidas")
        self.ui.addstr(7, 6, "• Conocimiento de conjuros")
        self.ui.addstr(9, 4, "NG+ pierde:")
        self.ui.addstr(10, 6, "• Items y oro")
        self.ui.addstr(11, 6, "• Quests activas")
        self.ui.addstr(13, 4, "Requisito: Haber completado 1 partida")
        self.ui.addstr(15, 4, "[N] Iniciar NG+  [X] Volver")
        self.ui.refresh()
        k = self.ui.getch()
        if k in [ord('n'), ord('N')]:
            logros_prev = self.p.logros if self.p else []
            self.p = Player(ng_plus=True, logros_previos=logros_prev)
            self.p.partidas_completadas = (self.p.partidas_completadas + 1) if self.p else 1
            self.combat = Combat(self.ui, self.p)
            self.save.guardar(self.p, "auto")
            self._intro()
            self.estado = GS.EXPLOR
        elif k in [ord('x'), ord('X')]:
            self.estado = GS.MENU

    def _explorar(self):
        z = ZONAS.get(self.p.zona, {})
        if self.p.zona not in self.p.zonas_visitadas:
            self.p.zonas_visitadas.append(self.p.zona)
            self.p.xp += 25
            self.p.descansos = 0
            if len(self.p.zonas_visitadas) >= 10 and "logro_07" not in self.p.logros:
                self.p.logros.append("logro_07")
        self._dibujar_explor(z)
        k = self.ui.getch()
        if k == ord('1'): self._explorar_zona(z)
        elif k == ord('2'): self._viajar(z)
        elif k == ord('3'): self._descansar(z)
        elif k == ord('4') and z.get("tienda"): self.estado = GS.TIENDA
        elif k == ord('5') and z.get("npcs"): self._hablar_npc(z)
        elif k in [ord('i'), ord('I')]: self.estado = GS.INV
        elif k in [ord('m'), ord('M')]: self.estado = GS.MAPA
        elif k in [ord('p'), ord('P')]: self.estado = GS.PAUSA
        elif k in [ord('q'), ord('Q')]: self.estado = GS.QUESTS
        elif k == ord('?'): self.estado = GS.AYUDA
        elif k == ord('r'): self.estado = GS.RITUAL
        if self.p.puede_subir(): self.estado = GS.LVLUP
        if self.p.vida <= 0: self.estado = GS.MUERTE
        if self.p.cordura <= 0: self.estado = GS.FINAL
        self.p.turno += 1
        self.p.turnos_totales += 1
        if self.p.turnos_totales >= 100 and "logro_10" not in self.p.logros:
            self.p.logros.append("logro_10")
        if self.p.turno % 20 == 0:
            self.p.ciclo = Ciclo.NOCHE if self.p.ciclo == Ciclo.DIA else Ciclo.DIA
        self._check_logros()
        self._encuentro_aleatorio_entidad()

    def _dibujar_explor(self, z: dict):
        self.ui.clear()
        nombre = z.get("nombre", "???")
        self.ui.addstr(0, 2, f"═══ {nombre} ═══", self.ui.col(4)|curses.A_BOLD)
        
        # NUEVO v4.0: Descripción atmosférica
        desc = self._get_desc_atmosferica(z)
        y = 2
        self.ui.addstr(y, 2, desc[:70], self.ui.col(6))
        
        y = 3
        for line in z.get("ascii", "").splitlines()[:5]:
            self.ui.addstr(y, 2, line[:60])
            y += 1
        
        hx = self.ui.mx - 22
        self.ui.addstr(1, hx, "VIDA:    "); self.ui.barra(1, hx+9, self.p.vida, self.p.vida_max, 8, 1)
        self.ui.addstr(2, hx, "CORDURA: "); self.ui.barra(2, hx+9, self.p.cordura, self.p.cordura_max, 8, 2)
        self.ui.addstr(3, hx, "VOLUNTAD:"); self.ui.barra(3, hx+9, self.p.voluntad, self.p.voluntad_max, 8, 3)
        self.ui.addstr(4, hx, f"VEL: {self.p.vel_efectiva():2} | {self.p.cat_rep()[:8]}")
        self.ui.addstr(5, hx, f"◈ ORO: {self.p.oro}", self.ui.col(4))
        self.ui.addstr(6, hx, f"✦ NIV: {self.p.nivel} XP:{self.p.xp}/{self.p.xp_siguiente()}")
        ciclo = "☀ DÍA" if self.p.ciclo == Ciclo.DIA else "☾ NOCHE"
        self.ui.addstr(7, hx, f"{ciclo} T:{self.p.turno}")
        self.ui.addstr(8, hx, f"🌙 Capa: {self.p.capa_sueño.name[:10]}")
        self.ui.addstr(9, hx, "─"*18)
        arma = self.p.arma.nombre if self.p.arma else "Ninguna"
        self.ui.addstr(10, hx, f"ARMA: {arma[:12]}")
        arm = self.p.armadura.nombre if self.p.armadura else "Ninguna"
        self.ui.addstr(11, hx, f"ARM: {arm[:13]}")
        
        # Mostrar trastornos
        if self.p.trastornos:
            y = 12
            self.ui.addstr(y, hx, "⚠ Trastornos:", self.ui.col(5))
            for t in self.p.trastornos[:2]:
                y += 1
                self.ui.addstr(y, hx, f"  • {t.value[:15]}", self.ui.col(3))
        
        y = self.ui.my - 6
        self.ui.addstr(y, 2, "[1] Explorar  [2] Viajar  [3] Descansar", self.ui.col(4))
        y += 1
        if z.get("tienda"): self.ui.addstr(y, 2, "[4] Tienda")
        if z.get("npcs"): self.ui.addstr(y, 18, "[5] Hablar")
        self.ui.addstr(y, 35, "[R] Ritual")
        y += 1
        self.ui.addstr(y, 2, "[I] Inventario  [M] Mapa  [P] Pausa  [Q] Quests  [?] Ayuda")
        self.ui.refresh()

    def _get_desc_atmosferica(self, z: dict) -> str:
        """NUEVO v4.0: Descripción según cordura y ciclo"""
        ciclo_key = "desc_dia" if self.p.ciclo == Ciclo.DIA else "desc_noche"
        cordura_key = "desc_cordura_alta" if self.p.cordura >= 60 else "desc_cordura_baja"
        
        # Priorizar descripción de cordura si es muy baja/alta
        if self.p.cordura < 40 and cordura_key in z:
            return z.get(cordura_key, z.get(ciclo_key, z.get("desc", "")))
        return z.get(ciclo_key, z.get("desc", ""))

    def _explorar_zona(self, z: dict):
        enc = z.get("encuentros", [])
        mod = 0.7 if self.p.ciclo == Ciclo.DIA else 1.3
        if "paso_silencioso" in self.p.habilidades and random.random() < 0.3:
            mod = 0
        for eid, prob in enc:
            if random.random() < prob * mod:
                if eid in ENEMIGOS:
                    self.combat.e = deepcopy(ENEMIGOS[eid])
                    self.estado = GS.COMBAT
                    return
        for iid, loc in z.get("objetos", []):
            if not self.p.tiene_item(iid):
                item = None
                if iid in CONSUMIBLES: item = deepcopy(CONSUMIBLES[iid])
                elif iid in MISION_ITEMS: item = deepcopy(MISION_ITEMS[iid])
                if item and self.p.add_item(item):
                    self.ui.clear()
                    self.ui.caja(8, 10, 5, 45, "¡ENCONTRADO!")
                    self.ui.addstr(10, 15, f"{item.nombre}")
                    self.ui.addstr(11, 15, f"En: {loc}")
                    self.ui.refresh()
                    time.sleep(1.5)
                    if iid == "gatito_onirico" and "logro_02" not in self.p.logros:
                        self.p.logros.append("logro_02")
                    return
        self.ui.addstr(self.ui.my-3, 2, "Exploras pero no encuentras nada...")
        self.ui.refresh()
        time.sleep(1)

    def _viajar(self, z: dict):
        conex = z.get("conexiones", [])
        if not conex: return
        self.ui.clear()
        self.ui.addstr(2, 2, "═══ VIAJAR ═══", self.ui.col(4))
        y = 4
        dests = []
        for zid in conex:
            zdata = ZONAS.get(zid, {})
            dests.append((zid, zdata.get("nombre", zid)))
            self.ui.addstr(y, 4, f"[{len(dests)}] {dests[-1][1]}")
            y += 1
        self.ui.addstr(y+1, 4, "[0] Cancelar")
        self.ui.refresh()
        k = self.ui.getch()
        if k >= ord('1') and k <= ord('9'):
            idx = k - ord('1')
            if idx < len(dests):
                self.p.zona = dests[idx][0]
                self.p.descansos = 0
                self.save.guardar(self.p, "auto")

    def _descansar(self, z: dict):
        # NUEVO v4.0: Insomnio puede impedir descanso
        if Trastorno.INSOMNIO in self.p.trastornos:
            self.ui.addstr(self.ui.my-3, 2, "¡Insomnio! No puedes descansar...")
            self.ui.refresh()
            time.sleep(1)
            return
        if not z.get("segura") and not z.get("posada"):
            self.ui.addstr(self.ui.my-3, 2, "Lugar no seguro para descansar...")
            self.ui.refresh()
            time.sleep(1)
            return
        if self.p.descansos >= 2 and not z.get("posada"):
            self.ui.addstr(self.ui.my-3, 2, "Ya descansaste suficiente aquí.")
            self.ui.refresh()
            time.sleep(1)
            return
        self.p.mod_stat("cordura", 15)
        self.p.mod_stat("voluntad", 10)
        self.p.mod_stat("vida", 5)
        self.p.descansos += 1
        self.ui.addstr(self.ui.my-3, 2, "Descansas y recuperas fuerzas...")
        self.ui.refresh()
        time.sleep(1)

    def _hablar_npc(self, z: dict):
        npcs = z.get("npcs", [])
        if not npcs: return
        npc = npcs[0]
        self.ui.clear()
        if npc == "menes":
            self._dialogo_menes()
        elif npc == "zoog_gris":
            self._dialogo_zoog()
        elif npc == "arash":
            self._dialogo_arash()
        elif npc == "kuranes":
            self._dialogo_kuranes()
        else:
            self.ui.addstr(5, 4, f"{npc.replace('_',' ').title()} te saluda.")
            self.ui.addstr(7, 4, "[0] Despedirse")
            self.ui.refresh()
            self.ui.wait()

    def _dialogo_menes(self):
        self.ui.addstr(2, 2, "═══ Menes el Felino ═══", self.ui.col(4))
        self.ui.addstr(4, 4, "Bienvenido a Ulthar, soñador.")
        y = 6
        self.ui.addstr(y, 4, "[1] Información sobre Kadath")
        y += 1
        self.ui.addstr(y, 4, "[2] Ver tienda")
        y += 1
        if "q01" not in self.p.quests_activas and "q01" not in self.p.quests_completas:
            self.ui.addstr(y, 4, "[3] He oído que falta un gatito...")
            y += 1
        elif self.p.tiene_item("gatito_onirico") and "q01" in self.p.quests_activas:
            self.ui.addstr(y, 4, "[3] Encontré a Whisper", self.ui.col(1))
            y += 1
        self.ui.addstr(y+1, 4, "[0] Despedirse")
        self.ui.refresh()
        k = self.ui.getch()
        if k == ord('2'):
            self.estado = GS.TIENDA
        elif k == ord('3'):
            if self.p.tiene_item("gatito_onirico") and "q01" in self.p.quests_activas:
                self.p.rem_item("gatito_onirico")
                self.p.quests_activas.remove("q01")
                self.p.quests_completas.append("q01")
                self.p.mod_stat("oro", 50)
                self.p.xp += 80
                self.p.flags["GATOS_ALIADOS"] = True
                if "logro_05" not in self.p.logros:
                    self.p.logros.append("logro_05")
                self.ui.addstr(y+3, 4, "¡Quest completada! +50 oro, +80 XP", self.ui.col(1))
                self.ui.refresh()
                time.sleep(2)
            elif "q01" not in self.p.quests_activas:
                self.p.quests_activas.append("q01")
                self.ui.addstr(y+3, 4, "¡Nueva quest: El Favor de los Gatos!", self.ui.col(4))
                self.ui.refresh()
                time.sleep(2)

    def _dialogo_zoog(self):
        self.ui.addstr(2, 2, "═══ Zoog Gris ═══", self.ui.col(4))
        self.ui.addstr(4, 4, "¿Qué quieres, soñador?")
        y = 6
        self.ui.addstr(y, 4, "[1] Comerciar")
        y += 1
        if self.p.tiene_item("gatito_onirico"):
            self.ui.addstr(y, 4, "[2] Tengo un gatito...", self.ui.col(4))
            y += 1
        self.ui.addstr(y+1, 4, "[0] Despedirse")
        self.ui.refresh()
        k = self.ui.getch()
        if k == ord('1'):
            self.estado = GS.TIENDA
        elif k == ord('2') and self.p.tiene_item("gatito_onirico"):
            self._decision_gatito()

    def _decision_gatito(self):
        self.ui.clear()
        self.ui.caja(5, 5, 10, 55, "DECISIÓN CLAVE")
        self.ui.addstr(7, 10, "¿A quién entregas el Gatito?")
        self.ui.addstr(9, 10, "[1] Devolver a Menes (Gatos aliados)", self.ui.col(1))
        self.ui.addstr(10, 10, "[2] Dar a los Zoog (Mapa, Gatos hostiles)", self.ui.col(5))
        self.ui.addstr(12, 10, "Decisión PERMANENTE. Afecta el final.")
        self.ui.refresh()
        while True:
            k = self.ui.getch()
            if k == ord('1'):
                self.p.decisiones.append("gatos")
                self.p.mod_stat("reputacion", 15)
                break
            elif k == ord('2'):
                self.p.decisiones.append("zoog")
                self.p.rem_item("gatito_onirico")
                self.p.quests_activas = [q for q in self.p.quests_activas if q != "q01"]
                self.p.quests_completas.append("q02")
                self.p.mod_stat("oro", 30)
                self.p.xp += 60
                self.p.mapa_frags += 1
                self.p.flags["GATOS_HOSTILES"] = True
                if "logro_06" not in self.p.logros:
                    self.p.logros.append("logro_06")
                self.p.add_item(deepcopy(MISION_ITEMS["mapa_frag"]))
                break
        self.ui.scr.timeout(-1)

    def _dialogo_arash(self):
        self.ui.addstr(2, 2, "═══ Capitán Arash ═══", self.ui.col(4))
        self.ui.addstr(4, 4, "Soy el Capitán Arash. ¿Buscas pasaje?")
        y = 6
        if "q03" not in self.p.quests_activas and "q03" not in self.p.quests_completas:
            self.ui.addstr(y, 4, "[1] ¿Necesitas algo? (Quest)")
            y += 1
        elif self.p.tiene_item("trofeo_ghast") and "q03" in self.p.quests_activas:
            self.ui.addstr(y, 4, "[1] Tengo el trofeo", self.ui.col(1))
            y += 1
        self.ui.addstr(y+1, 4, "[0] Despedirse")
        self.ui.refresh()
        k = self.ui.getch()
        if k == ord('1'):
            if self.p.tiene_item("trofeo_ghast") and "q03" in self.p.quests_activas:
                self.p.rem_item("trofeo_ghast")
                self.p.quests_activas.remove("q03")
                self.p.quests_completas.append("q03")
                self.p.mod_stat("oro", 100)
                self.p.xp += 100
                self.p.flags["RUTA_SEGURA"] = True
                self.ui.addstr(y+3, 4, "¡Quest completada!", self.ui.col(1))
                self.ui.refresh()
                time.sleep(2)
            elif "q03" not in self.p.quests_activas:
                self.p.quests_activas.append("q03")
                self.ui.addstr(y+3, 4, "¡Nueva quest!", self.ui.col(4))
                self.ui.refresh()
                time.sleep(2)

    def _dialogo_kuranes(self):
        """NUEVO v4.0: Kuranes ofrece quest de ritual"""
        self.ui.addstr(2, 2, "═══ Kuranes el Soñador ═══", self.ui.col(4))
        self.ui.addstr(4, 4, "He visto tu destino en los sueños, Carter.")
        y = 6
        if "q04" not in self.p.quests_activas and "q04" not in self.p.quests_completas:
            self.ui.addstr(y, 4, "[1] ¿Puedes ayudarme? (Quest Ritual)")
            y += 1
        elif self.p.tiene_item("cristal_sueno") and "q04" in self.p.quests_activas:
            self.ui.addstr(y, 4, "[1] Tengo el Cristal de Sueño", self.ui.col(1))
            y += 1
        self.ui.addstr(y+1, 4, "[0] Despedirse")
        self.ui.refresh()
        k = self.ui.getch()
        if k == ord('1'):
            if self.p.tiene_item("cristal_sueno") and "q04" in self.p.quests_activas:
                self.p.rem_item("cristal_sueno")
                self.p.quests_activas.remove("q04")
                self.p.quests_completas.append("q04")
                self.p.mod_stat("oro", 200)
                self.p.xp += 150
                self.p.aprender_conjuro("invocar_nodens")
                if "logro_09" not in self.p.logros:
                    self.p.logros.append("logro_09")
                self.ui.addstr(y+3, 4, "¡Aprendes: Invocar a Nodens!", self.ui.col(1))
                self.ui.refresh()
                time.sleep(2)
            elif "q04" not in self.p.quests_activas:
                self.p.quests_activas.append("q04")
                self.ui.addstr(y+3, 4, "¡Nueva quest: El Ritual de Nodens!", self.ui.col(4))
                self.ui.refresh()
                time.sleep(2)

    def _combate(self):
        if self.combat and self.combat.e:
            res = self.combat.iniciar(self.combat.e)
            if res == "muerte":
                self.estado = GS.MUERTE
            elif res == "locura":
                self.estado = GS.FINAL
            else:
                self.estado = GS.EXPLOR
            if self.p.puede_subir():
                self.estado = GS.LVLUP

    def _inventario(self):
        while True:
            self.ui.clear()
            self.ui.addstr(0, 2, "═══ INVENTARIO ═══", self.ui.col(4))
            self.ui.addstr(1, 2, f"Slots: {len(self.p.inventario)}/{MAX_INV}")
            y = 3
            for i, it in enumerate(self.p.inventario):
                self.ui.addstr(y, 4, f"[{i+1}] [{it.tipo[0]}] {it.nombre}")
                y += 1
            y += 1
            self.ui.addstr(y, 2, "── EQUIPADO ──", self.ui.col(6))
            y += 1
            if self.p.arma:
                self.ui.addstr(y, 4, f"Arma: {self.p.arma.nombre} ({self.p.arma.dmin}-{self.p.arma.dmax})")
                y += 1
            if self.p.armadura:
                self.ui.addstr(y, 4, f"Armadura: {self.p.armadura.nombre} (D:{self.p.armadura.defensa})")
            y += 1
            self.ui.addstr(y, 2, "── CONJUROS ──", self.ui.col(3))
            y += 1
            for c in self.p.conjuros_aprendidos[:3]:
                conjuro = CONJUROS.get(c)
                if conjuro:
                    self.ui.addstr(y, 4, f"• {conjuro.nombre} ({conjuro.coste} VOL)")
                    y += 1
            self.ui.addstr(self.ui.my-3, 2, "[E] Equipar  [U] Usar  [D] Descartar  [X] Cerrar")
            self.ui.refresh()
            k = self.ui.getch()
            if k in [ord('x'), ord('X')]: break
            elif k in [ord('e'), ord('E')]: self._equipar()
            elif k in [ord('u'), ord('U')]: self._usar()
            elif k in [ord('d'), ord('D')]: self._descartar()
        self.estado = GS.EXPLOR

    def _equipar(self):
        self.ui.addstr(self.ui.my-2, 2, "Número a equipar (0 cancelar): ")
        self.ui.refresh()
        k = self.ui.getch()
        if k >= ord('1') and k <= ord('9'):
            idx = k - ord('1')
            if idx < len(self.p.inventario):
                it = self.p.inventario[idx]
                if it.tipo == "ARMA":
                    if self.p.arma and self.p.arma.id != "punos":
                        self.p.inventario.append(self.p.arma)
                    self.p.arma = it
                    self.p.inventario.pop(idx)
                elif it.tipo == "ARMADURA":
                    if self.p.armadura and self.p.armadura.id != "sin_armadura":
                        self.p.inventario.append(self.p.armadura)
                    self.p.armadura = it
                    self.p.inventario.pop(idx)

    def _usar(self):
        self.ui.addstr(self.ui.my-2, 2, "Número a usar (0 cancelar): ")
        self.ui.refresh()
        k = self.ui.getch()
        if k >= ord('1') and k <= ord('9'):
            idx = k - ord('1')
            if idx < len(self.p.inventario):
                it = self.p.inventario[idx]
                if it.usable:
                    for stat, val in it.efecto.items():
                        self.p.mod_stat(stat, val)
                    self.p.inventario.pop(idx)

    def _descartar(self):
        self.ui.addstr(self.ui.my-2, 2, "Número a descartar (0 cancelar): ")
        self.ui.refresh()
        k = self.ui.getch()
        if k >= ord('1') and k <= ord('9'):
            idx = k - ord('1')
            if idx < len(self.p.inventario):
                it = self.p.inventario[idx]
                if it.tipo not in ["MISION", "CLAVE"]:
                    self.p.inventario.pop(idx)

    def _tienda(self):
        catalogo = TIENDA_CATALOGO.get(self.p.zona, [])
        while True:
            self.ui.clear()
            zn = ZONAS.get(self.p.zona, {}).get("nombre", "Tienda")
            self.ui.addstr(0, 2, f"═══ Tienda de {zn} ═══", self.ui.col(4))
            self.ui.addstr(1, 2, f"Tu oro: {self.p.oro} ◈")
            y = 3
            items = []
            for iid in catalogo:
                it = None
                if iid in CONSUMIBLES:
                    it = deepcopy(CONSUMIBLES[iid])
                elif iid in ARMAS:
                    it = deepcopy(ARMAS[iid])
                elif iid in ARMADURAS:
                    it = deepcopy(ARMADURAS[iid])
                if it:
                    items.append(it)
                    color = 0 if it.valor_c <= self.p.oro else self.ui.col(5)
                    self.ui.addstr(y, 4, f"[{len(items)}] {it.nombre:20} - {it.valor_c} ◈", color)
                    y += 1
            self.ui.addstr(y+1, 4, "[X] Salir")
            self.ui.refresh()
            k = self.ui.getch()
            if k in [ord('x'), ord('X')]:
                break
            elif k >= ord('1') and k <= ord('9'):
                idx = k - ord('1')
                if idx < len(items):
                    it = items[idx]
                    if it.valor_c <= self.p.oro and len(self.p.inventario) < MAX_INV:
                        self.p.mod_stat("oro", -it.valor_c)
                        self.p.add_item(it)
                        self.estado = GS.EXPLOR

    def _mapa(self):
        self.ui.clear()
        self.ui.addstr(0, 2, "═══ MAPA DEL MUNDO ═══", self.ui.col(4))
        mapa = """
[1:ULTHAR★]━━━[2:ZOOG]━━━[3:DYLATH]
│               │          │
[6:CEL★]       [4:HUMO]   [7:ORIAB]
│               │          │
[5:ZAK]   [8:INQUANOK]
│
[9:LENG]
│
[10:KADATH]
"""
        y = 3
        for line in mapa.splitlines():
            self.ui.addstr(y, 2, line)
            y += 1
        zn = ZONAS.get(self.p.zona, {}).get("nombre", "???")
        self.ui.addstr(y+1, 4, f"Ubicación: {zn}", self.ui.col(4))
        self.ui.addstr(y+2, 4, f"Fragmentos mapa: {self.p.mapa_frags}/3")
        self.ui.addstr(y+3, 4, f"Zonas visitadas: {len(self.p.zonas_visitadas)}/10")
        self.ui.addstr(self.ui.my-2, 2, "Pulsa tecla para volver...")
        self.ui.refresh()
        self.ui.wait()
        self.estado = GS.EXPLOR

    def _pausa(self):
        self.ui.clear()
        self.ui.caja(5, 20, 12, 30, "⏸ PAUSA")
        opts = ["[G] Guardar", "[M] Mapa", "[Q] Quests", "[L] Logros", "[?] Ayuda", "[X] Volver", "[S] Salir al menú"]
        y = 7
        for o in opts:
            self.ui.addstr(y, 25, o)
            y += 1
        self.ui.refresh()
        k = self.ui.getch()
        if k in [ord('g'), ord('G')]:
            self._guardar_menu()
        elif k in [ord('m'), ord('M')]:
            self.estado = GS.MAPA
        elif k in [ord('q'), ord('Q')]:
            self.estado = GS.QUESTS
        elif k in [ord('l'), ord('L')]:
            self._logros_menu()
        elif k == ord('?'):
            self.estado = GS.AYUDA
        elif k in [ord('x'), ord('X')]:
            self.estado = GS.EXPLOR
        elif k in [ord('s'), ord('S')]:
            self.save.guardar(self.p, "auto")
            self.estado = GS.MENU

    def _logros_menu(self):
        """NUEVO v4.0: Menú de logros"""
        self.ui.clear()
        self.ui.addstr(0, 2, "═══ LOGROS ═══", self.ui.col(4))
        y = 2
        total = len(LOGROS)
        desbloqueados = len(self.p.logros)
        self.ui.addstr(y, 2, f"Progreso: {desbloqueados}/{total}", self.ui.col(4))
        y += 2
        for lid, (nombre, desc) in LOGROS.items():
            estado = "✓" if lid in self.p.logros else "○"
            color = self.ui.col(1) if lid in self.p.logros else 0
            self.ui.addstr(y, 4, f"{estado} {nombre}", color)
            y += 1
            if y > self.ui.my - 3:
                break
        self.ui.addstr(self.ui.my-2, 2, "Pulsa tecla para volver...")
        self.ui.refresh()
        self.ui.wait()
        self.estado = GS.PAUSA

    def _ritual_menu(self):
        """NUEVO v4.0: Menú de rituales"""
        self.ui.clear()
        self.ui.addstr(0, 2, "═══ RITUALES ═══", self.ui.col(3))
        y = 2
        self.ui.addstr(y, 2, f"Voluntad: {self.p.voluntad}/{self.p.voluntad_max}")
        y += 2
        for cid in self.p.conjuros_aprendidos:
            conjuro = CONJUROS.get(cid)
            if conjuro:
                disponible = self.p.voluntad >= conjuro.coste
                color = self.ui.col(1) if disponible else self.ui.col(5)
                self.ui.addstr(y, 4, f"[{cid[0].upper()}] {conjuro.nombre} (-{conjuro.coste} VOL)", color)
                self.ui.addstr(y+1, 6, conjuro.desc[:50])
                y += 3
        self.ui.addstr(self.ui.my-2, 2, "Presiona la letra del conjuro o [X] volver")
        self.ui.refresh()
        k = self.ui.getch()
        if k in [ord('a'), ord('A')] and "abrir_portico" in self.p.conjuros_aprendidos:
            self._usar_conjuro("abrir_portico")
        elif k in [ord('v'), ord('V')] and "ver_invisible" in self.p.conjuros_aprendidos:
            self._usar_conjuro("ver_invisible")
        elif k in [ord('x'), ord('X')]:
            self.estado = GS.EXPLOR

    def _usar_conjuro(self, conjuro_id: str):
        """NUEVO v4.0: Usar conjuro fuera de combate"""
        conjuro = CONJUROS.get(conjuro_id)
        if not conjuro:
            return
        if self.p.voluntad >= conjuro.coste:
            self.p.mod_stat("voluntad", -conjuro.coste)
            if conjuro_id == "abrir_portico":
                self.ui.addstr(self.ui.my-3, 2, "¿A qué zona? (nombre): ")
                self.ui.refresh()
            elif conjuro_id == "ver_invisible":
                self.ui.addstr(self.ui.my-3, 2, "Objetos ocultos revelados...")
                self.ui.refresh()
                time.sleep(1)
        else:
            self.ui.addstr(self.ui.my-3, 2, "Voluntad insuficiente")
            self.ui.refresh()
            time.sleep(1)
        self.estado = GS.EXPLOR

    def _encuentro_aleatorio_entidad(self):
        """NUEVO v4.0: Encuentro aleatorio con entidades cósmicas"""
        if random.random() < 0.02 and not self.p.flags.get("NYARLATHOTEP_VISTO"):
            entidad_id = random.choice(list(ENTIDADES.keys()))
            self._iniciar_encuentro_entidad(entidad_id)

    def _iniciar_encuentro_entidad(self, entidad_id: str):
        """NUEVO v4.0: Iniciar encuentro con entidad"""
        self.estado = GS.ENTIDAD
        self.entidad_actual = ENTIDADES.get(entidad_id)
        self.p.flags["NYARLATHOTEP_VISTO"] = True
        if "logro_11" not in self.p.logros:
            self.p.logros.append("logro_11")

    def _encuentro_entidad(self):
        """NUEVO v4.0: Pantalla de encuentro con entidad"""
        self.ui.clear()
        self.ui.caja(3, 5, 15, 60, "⚠ ENTIDAD CÓSMICA ⚠")
        self.ui.addstr(5, 10, f"{self.entidad_actual.nombre} se man