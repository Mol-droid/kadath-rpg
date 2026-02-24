#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KADATH v4.0 — La Búsqueda Onírica de la Desconocida Kadath (Edición Lovecraft)
Molvic Studio © 2024 | Basado en H.P. Lovecraft
Motor: curses (stdlib) para TUI con colores
"""

import curses
import os
import sys
import json
import time
import random
import signal
import copy
import math
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum, auto

VERSION, STUDIO = "4.0", "Molvic Studio © 2024"
MAX_INV = 15               # Aumentado para dar cabida a objetos de misión y conjuros
VEL_BASE = 10
XP_TABLA = {1: 0, 2: 100, 3: 200, 4: 350, 5: 500, 6: 800, 7: 1200, 8: 1800, 9: 2600, 10: 3600}
SAVE_DIR = Path.home() / ".kadath_saves"

# Constantes para el sistema de cordura y sueños
LUNAS = ["NUEVA", "CRECIENTE", "LLENA", "MENGUANTE"]
ESTADOS_ANIMO = ["TRANQUILO", "INQUIETO", "PERTURBADO", "ENLOQUECIDO"]

# Nuevos tipos de daño
class TDano(Enum):
    FISICO = "FISICO"
    ONIRICO = "ONIRICO"
    MAGICO = "MAGICO"
    COSMICO = "COSMICO"      # Daño de la cordura, ignorando armadura

class GS(Enum):
    MENU = auto()
    EXPLOR = auto()
    COMBAT = auto()
    INV = auto()
    TIENDA = auto()
    MAPA = auto()
    PAUSA = auto()
    LVLUP = auto()
    MUERTE = auto()
    FINAL = auto()
    QUESTS = auto()
    AYUDA = auto()
    BESTIARIO = auto()        # Nueva pantalla
    SUEÑO = auto()            # Evento onírico

class Ciclo(Enum):
    DIA = "DIA"
    NOCHE = "NOCHE"

class FaseLunar(Enum):
    NUEVA = 0
    CRECIENTE = 1
    LLENA = 2
    MENGUANTE = 3

@dataclass
class Item:
    id: str
    nombre: str
    tipo: str
    desc: str = ""
    valor_c: int = 0
    valor_v: int = 0
    usable: bool = False
    cantidad: int = 1
    # Arma
    dmin: int = 0
    dmax: int = 0
    tdano: str = "FISICO"
    dur: int = -1
    durmax: int = -1
    # Armadura
    defensa: int = 0
    resist: int = 0          # Resistencia a daño no físico
    bvel: int = 0
    # Consumible
    efecto: Dict = field(default_factory=dict)
    # Para pergaminos de conjuro
    conjuro: Optional[str] = None
    coste_voluntad: int = 0

@dataclass
class Enemy:
    id: str
    nombre: str
    vida: int
    vidamax: int
    dmin: int
    dmax: int
    tdano: str
    defensa: int
    vel: int
    xp: int
    oro_min: int
    oro_max: int
    loot: List[Tuple[str, float]] = field(default_factory=list)
    jefe: bool = False
    estados: List[str] = field(default_factory=list)
    # Nuevos atributos para criaturas lovecraftianas
    cordura_dano: int = 0     # Pérdida de cordura al verla
    inmune_miedo: bool = False
    desc_combate: str = ""    # Descripción en combate

@dataclass
class Quest:
    id: str
    titulo: str
    giver: str
    zona: str
    desc: str
    objetivo: Dict
    recompensa: Dict
    activa: bool = False
    completada: bool = False
    faccion: Optional[str] = None   # "GATOS", "ZOOG", "HOMBRES", "NODENS"

@dataclass
class Ally:
    id: str
    nombre: str
    tipo: str          # "GATO", "ZOOG", "GHOUL", etc.
    vida: int
    vidamax: int
    dmin: int
    dmax: int
    defensa: int
    habilidades: List[str] = field(default_factory=list)
    desc: str = ""

# ═══════════════════════════════════════════════════════════════════════════════
# NUEVOS DATOS EXPANDIDOS (Lovecraft Edition)
# ═══════════════════════════════════════════════════════════════════════════════

# Más armas, incluyendo artefactos oníricos
ARMAS = {
    "punos": Item("punos", "Puños", "ARMA", "Tus manos", 0, 0, dmin=3, dmax=8),
    "daga_onirica": Item("daga_onirica", "Daga Onírica", "ARMA", "Hoja de sueños", 80, 32, dmin=8, dmax=15, tdano="ONIRICO", dur=10, durmax=10),
    "espada_sueno": Item("espada_sueno", "Espada del Sueño", "ARMA", "Forjada en Celephaïs", 200, 80, dmin=15, dmax=25, dur=10, durmax=10),
    "cetro_ngranek": Item("cetro_ngranek", "Cetro de Ngranek", "ARMA", "Poder ancestral", 300, 120, dmin=20, dmax=35, tdano="MAGICO", dur=8, durmax=8),
    "hoja_lunar": Item("hoja_lunar", "Hoja Lunar", "ARMA", "Brilla con luz propia", 250, 100, dmin=18, dmax=30, tdano="ONIRICO", dur=12, durmax=12, efecto={"lunar": True}),
    "báculo_nodens": Item("báculo_nodens", "Báculo de Nodens", "ARMA", "Reliquia de los Dioses Arquetípicos", 500, 200, dmin=25, dmax=45, tdano="COSMICO", dur=15, durmax=15, coste_voluntad=10),
}

# Más armaduras
ARMADURAS = {
    "sin_armadura": Item("sin_armadura", "Sin armadura", "ARMADURA", "", 0, 0),
    "ropas_viajero": Item("ropas_viajero", "Ropas de Viajero", "ARMADURA", "Cómodas", 40, 16, defensa=2, bvel=1),
    "capa_niebla": Item("capa_niebla", "Capa de Niebla", "ARMADURA", "Etérea", 120, 48, defensa=5, resist=3, bvel=2),
    "armadura_gato": Item("armadura_gato", "Armadura de Gato", "ARMADURA", "Bendecida", 150, 60, defensa=4, resist=5),
    "túnica_sonámbula": Item("túnica_sonámbula", "Túnica Sonámbula", "ARMADURA", "Tejida con sueños", 220, 88, defensa=3, resist=8, bvel=0, efecto={"cordura_max": 20}),
    "escamas_profundas": Item("escamas_profundas", "Escamas Profundas", "ARMADURA", "De las criaturas de las fosas", 300, 120, defensa=8, resist=4, bvel=-1),
}

# Más consumibles y pergaminos
CONSUMIBLES = {
    "pocion_cordura": Item("pocion_cordura", "Poción de Cordura", "CONSUMIBLE", "Calma la mente", 30, 12, usable=True, efecto={"cordura": 25}),
    "balsamo_onirico": Item("balsamo_onirico", "Bálsamo Onírico", "CONSUMIBLE", "Sana heridas", 25, 10, usable=True, efecto={"vida": 30}),
    "elixir_voluntad": Item("elixir_voluntad", "Elixir de Voluntad", "CONSUMIBLE", "Fortalece", 35, 14, usable=True, efecto={"voluntad": 20}),
    "pan_gatos": Item("pan_gatos", "Pan de los Gatos", "CONSUMIBLE", "Delicioso", 15, 6, usable=True, efecto={"vida": 10, "cordura": 5}),
    "incienso_somni": Item("incienso_somni", "Incienso Somnífero", "CONSUMIBLE", "Induce sueños lúcidos", 50, 20, usable=True, efecto={"sueño": True}),
    "pergamino_proteccion": Item("pergamino_proteccion", "Pergamino de Protección", "CONSUMIBLE", "Palabras antiguas", 80, 32, usable=True, efecto={"escudo": 50}, coste_voluntad=15),
    "pergamino_revelar": Item("pergamino_revelar", "Pergamino de Revelación", "CONSUMIBLE", "Muestra lo oculto", 60, 24, usable=True, efecto={"revelar": True}, coste_voluntad=10),
}

# Objetos de misión y artefactos especiales
MISION_ITEMS = {
    "piedra_comun": Item("piedra_comun", "Piedra Común", "MISION", "Los Zoog la valoran"),
    "gatito_onirico": Item("gatito_onirico", "Gatito Onírico", "MISION", "Perdido en el bosque"),
    "trofeo_ghast": Item("trofeo_ghast", "Trofeo de Ghast", "TROFEO", "Colmillo de bestia", 0, 50),
    "mapa_frag": Item("mapa_frag", "Fragmento del Mapa", "MISION", "Parte del mapa a Kadath"),
    "llave_catacumbas": Item("llave_catacumbas", "Llave Catacumbas", "CLAVE", "Abre el paso"),
    "pergamino": Item("pergamino", "Pergamino Antiguo", "MISION", "Texto pre-humano"),
    "estatua_nodens": Item("estatua_nodens", "Estatua de Nodens", "ARTEFACTO", "Pequeña figura", 200, 100),
    "cuarzo_sonico": Item("cuarzo_sonico", "Cuarzo Sónico", "ARTEFACTO", "Resuena con los sueños", 150, 75),
    "sello_lunar": Item("sello_lunar", "Sello Lunar", "ARTEFACTO", "Marca de los Dioses", 0, 0),
}

# Nuevos enemigos lovecraftianos con pérdida de cordura
ENEMIGOS = {
    "zoog": Enemy("zoog", "Zoog Traicionero", 10, 10, 3, 8, "FISICO", 0, 15, 22, 2, 8, [("pan_gatos", 0.3)], cordura_dano=2, desc_combate="Parecen inofensivos, pero sus ojos brillan con malicia."),
    "ghul": Enemy("ghul", "Ghul Carroñero", 35, 35, 8, 15, "FISICO", 2, 8, 47, 5, 15, [("trofeo_ghast", 0.4)], cordura_dano=5, desc_combate="Huelen a tumba, su risa te hiela la sangre."),
    "ghast": Enemy("ghast", "Ghast Cavernas", 60, 60, 15, 25, "FISICO", 5, 18, 82, 10, 25, [("trofeo_ghast", 0.6)], cordura_dano=8),
    "sacerdote": Enemy("sacerdote", "Sacerdote sin Rostro", 45, 45, 10, 20, "ONIRICO", 8, 10, 102, 20, 40, [("pergamino", 0.3)], cordura_dano=15, desc_combate="Su faz es un velo de oscuridad que absorbe la cordura."),
    "nightgaunt": Enemy("nightgaunt", "Nightgaunt", 40, 40, 12, 22, "ONIRICO", 4, 16, 88, 8, 20, [], cordura_dano=12, desc_combate="Criaturas silenciosas que roban el aliento."),
    "guardian": Enemy("guardian", "Guardián de Leng", 150, 150, 25, 40, "FISICO", 10, 12, 252, 80, 120, [], jefe=True, cordura_dano=25, desc_combate="Un horror pétreo de la meseta prohibida."),
    "shantak": Enemy("shantak", "Shantak", 80, 80, 20, 35, "FISICO", 6, 20, 150, 30, 60, [], cordura_dano=10, desc_combate="Bestia alada con escamas repulsivas."),
    "ghoul_antiguo": Enemy("ghoul_antiguo", "Ghoul Antiguo", 70, 70, 18, 30, "FISICO", 8, 14, 120, 25, 50, [("pergamino", 0.5)], cordura_dano=10),
    "gnophkeh": Enemy("gnophkeh", "Gnophkeh", 100, 100, 22, 38, "FISICO", 12, 10, 200, 40, 80, [], jefe=True, cordura_dano=20, desc_combate="Una masa de hielo y cuernos, pesadilla de las montañas."),
    "nyarlathotep": Enemy("nyarlathotep", "Nyarlathotep (Visión)", 200, 200, 30, 60, "COSMICO", 15, 25, 500, 0, 0, [], jefe=True, cordura_dano=50, desc_combate="El Caos Reptante se manifiesta ante ti."),
}

# Nuevas quests y facciones
QUESTS = {
    "q01": Quest("q01", "El Favor de los Gatos", "menes", "zona_1", "Encuentra a Whisper", {"tipo": "tener", "item": "gatito_onirico"}, {"oro": 50, "xp": 80, "flag": "GATOS_ALIADOS"}, faccion="GATOS"),
    "q02": Quest("q02", "El Trato de los Zoog", "zoog", "zona_2", "Entrega el gatito a los Zoog", {"tipo": "entregar", "item": "gatito_onirico"}, {"oro": 30, "xp": 60, "item": "mapa_frag"}, faccion="ZOOG"),
    "q03": Quest("q03", "La Deuda de Dylath", "arash", "zona_3", "Consigue un fragmento de cerámica", {"tipo": "tener", "item": "trofeo_ghast"}, {"oro": 100, "xp": 100, "flag": "RUTA_SEGURA"}, faccion="HOMBRES"),
    "q04": Quest("q04", "El Secreto de las Profundidades", "kuranes", "zona_6", "Explora las catacumbas de Zak", {"tipo": "explorar", "zona": "zona_5"}, {"xp": 150, "item": "cuarzo_sonico"}, faccion="SABIOS"),
    "q05": Quest("q05", "La Ofrenda a Nodens", "npc_misterioso", "zona_7", "Coloca la estatua en el altar submarino", {"tipo": "usar", "item": "estatua_nodens", "zona": "zona_7"}, {"xp": 200, "habilidad": "forma_niebla"}, faccion="NODENS"),
}

# Zonas actualizadas con más descripciones y encuentros variados
ZONAS = {
    "zona_1": {
        "nombre": "Ulthar",
        "segura": True,
        "posada": True,
        "desc": "La ciudad donde ningún hombre puede matar a un gato. Los felinos te observan desde cada tejado.",
        "ascii": """
    /\\     /\\      ╔══════════════════════╗
   /  \\___/  \\     ║     ~ ULTHAR ~       ║
  /  o     o  \\    ║  Ciudad de los Gatos ║
 /      Y      \\   ╚══════════════════════╝""",
        "conexiones": ["zona_2", "zona_6"],
        "npcs": ["menes"],
        "tienda": True,
        "encuentros": [("zoog", 0.05)],  # Raro en Ulthar
        "objetos": [("piedra_comun", "cerca de la fuente")],
        "altar": False,
    },
    "zona_2": {
        "nombre": "Bosque Zoog",
        "segura": False,
        "posada": False,
        "desc": "El Bosque Encantado donde los Zoog acechan entre las sombras. Los árboles susurran secretos.",
        "ascii": """
      , - ~ ~ ~ - ,     ╔═════════════════════╗
  , '   /\\     /\\   ' , ║  BOSQUE DE LOS ZOOG ║
 ,    /    \\ /    \\    ,╚═════════════════════╝""",
        "conexiones": ["zona_1", "zona_3", "zona_4"],
        "npcs": ["zoog_gris"],
        "tienda": True,
        "encuentros": [("zoog", 0.3), ("ghul", 0.1)],
        "objetos": [("gatito_onirico", "entre raíces de roble")],
        "altar": False,
    },
    "zona_3": {
        "nombre": "Dylath-Leen",
        "segura": True,
        "posada": True,
        "desc": "El puerto oscuro de muelles de basalto negro. Barcos de remos traen mercancías de tierras ignotas.",
        "ascii": """
         |    |    |      ╔══════════════════╗
        )_)  )_)  )_)     ║   DYLATH-LEEN    ║
       )___))___))___)    ╚══════════════════╝""",
        "conexiones": ["zona_2", "zona_4", "zona_7"],
        "npcs": ["arash"],
        "tienda": True,
        "encuentros": [("ghul", 0.15)],
        "objetos": [],
        "altar": False,
    },
    "zona_4": {
        "nombre": "Montañas del Humo",
        "segura": False,
        "posada": False,
        "desc": "Picos envueltos en vapores sulfurosos donde merodean los Gules. Se oyen ecos de criaturas antiguas.",
        "ascii": """
         /\\                ╔═══════════════════╗
        /  \\    /\\         ║ MONTAÑAS DEL HUMO ║
       /    \\  /  \\  /\\    ╚═══════════════════╝""",
        "conexiones": ["zona_2", "zona_3", "zona_5"],
        "npcs": [],
        "tienda": False,
        "encuentros": [("ghul", 0.2), ("ghast", 0.15), ("gnophkeh", 0.05)],
        "objetos": [("cuarzo_sonico", "en una cueva helada")],
        "altar": False,
    },
    "zona_5": {
        "nombre": "Catacumbas de Zak",
        "segura": False,
        "posada": False,
        "desc": "Laberinto de huesos bajo la tierra. Los muertos susurran en lenguas olvidadas.",
        "ascii": """
  ╔═══╗ ╔═══╗ ╔═══╗   ╔══════════════════╗
  ║ ☠ ║ ║ ☠ ║ ║ ☠ ║   ║ CATACUMBAS ZAK   ║
  ╚═══╝ ╚═══╝ ╚═══╝   ╚══════════════════╝""",
        "conexiones": ["zona_4", "zona_6"],
        "npcs": [],
        "tienda": False,
        "encuentros": [("ghul", 0.3), ("sacerdote", 0.15), ("ghoul_antiguo", 0.1)],
        "objetos": [("llave_catacumbas", "altar oculto")],
        "altar": True,
        "dios": "NODENS",
    },
    "zona_6": {
        "nombre": "Celephaïs",
        "segura": True,
        "posada": True,
        "desc": "La ciudad maravillosa de torres de ónice bajo cielos eternos. Kuranes, el rey soñador, gobierna aquí.",
        "ascii": """
       ╔═══╗   ╔═══╗      ╔══════════════════╗
      ╔╝   ╚═══╝   ╚╗     ║    CELEPHAÏS     ║
     ╔╝  ◇     ◇    ╚╗    ╚══════════════════╝""",
        "conexiones": ["zona_1", "zona_5", "zona_7"],
        "npcs": ["kuranes"],
        "tienda": True,
        "encuentros": [],
        "objetos": [("estatua_nodens", "en la sala del trono")],
        "altar": False,
    },
    "zona_7": {
        "nombre": "Mar de Oriab",
        "segura": False,
        "posada": False,
        "desc": "Aguas misteriosas que conectan los reinos del sueño. Bajo la superficie yacen ciudades olvidadas.",
        "ascii": """
   ~  ~  ~  ~  ~  ~  ~    ╔══════════════════╗
 ~    ⛵    ~    ~    ~   ║    MAR ORIAB     ║
~  ~  ~  ~  ~  ~  ~  ~  ~ ╚══════════════════╝""",
        "conexiones": ["zona_3", "zona_6", "zona_8"],
        "npcs": [],
        "tienda": False,
        "encuentros": [("nightgaunt", 0.2), ("shantak", 0.1)],
        "objetos": [],
        "altar": True,
        "dios": "DAGON",
    },
    "zona_8": {
        "nombre": "Inquanok",
        "segura": False,
        "posada": False,
        "desc": "La ciudad de ónice, última parada antes de Leng. Sus habitantes son silenciosos y esquivos.",
        "ascii": """
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   ╔══════════════════╗
  ▓  ╔════════╗   ▓   ║     INQUANOK     ║
  ▓  ║ ÓNICE  ║   ▓   ╚══════════════════╝""",
        "conexiones": ["zona_7", "zona_9"],
        "npcs": [],
        "tienda": False,
        "encuentros": [("sacerdote", 0.25), ("nightgaunt", 0.2)],
        "objetos": [],
        "altar": False,
    },
    "zona_9": {
        "nombre": "Meseta de Leng",
        "segura": False,
        "posada": False,
        "desc": "Tierra prohibida donde la realidad se desmorona. Los dioses de la tierra moran en las cavernas.",
        "ascii": """
  ▲       ▲       ▲    ╔══════════════════╗
 /█\\     /█\\     /█\\   ║   MESETA LENG    ║
/███\\   /███\\   /███\\  ╚══════════════════╝""",
        "conexiones": ["zona_8", "zona_10"],
        "npcs": [],
        "tienda": False,
        "encuentros": [("sacerdote", 0.3), ("guardian", 0.1), ("ghoul_antiguo", 0.15)],
        "objetos": [],
        "altar": True,
        "dios": "NYARLATHOTEP",
    },
    "zona_10": {
        "nombre": "Kadath",
        "segura": False,
        "posada": False,
        "desc": "La Desconocida Kadath. El destino de tu búsqueda. Los Dioses Arquetípicos moran en sus torres de nubes.",
        "ascii": """
        ★  ★  ★  ★  ★     ╔══════════════════╗
       ★ ╔══════════╗ ★  ║      KADATH      ║
      ★ ╔╝  ☆☆☆☆  ╚╗ ★  ╚══════════════════╝""",
        "conexiones": [],
        "npcs": ["dioses"],
        "tienda": False,
        "encuentros": [],
        "objetos": [("sello_lunar", "en el altar central")],
        "altar": True,
        "dios": "ARQUETIPOS",
    },
}

# Catálogo de tiendas ampliado
TIENDA_CATALOGO = {
    "zona_1": ["pocion_cordura", "balsamo_onirico", "pan_gatos", "daga_onirica", "pergamino_proteccion"],
    "zona_2": ["pan_gatos", "pocion_cordura", "incienso_somni"],
    "zona_3": ["elixir_voluntad", "capa_niebla", "espada_sueno", "pergamino_revelar"],
    "zona_6": ["cetro_ngranek", "armadura_gato", "elixir_voluntad", "túnica_sonámbula"],
}

# Nuevas habilidades (más variadas)
HABILIDADES = {
    2: ("paso_silencioso", "Paso Silencioso", "30% evitar encuentros"),
    3: ("vision_onirica", "Visión Onírica", "Revela objetos ocultos"),
    4: ("conjuro_menor", "Conjuro Menor", "30-50 daño mágico"),
    5: ("pacto_onirico", "Pacto Onírico", "Negociar con enemigos"),
    6: ("forma_niebla", "Forma de Niebla", "Inmunidad física 2 turnos"),
    7: ("mente_abierta", "Mente Abierta", "Resistencia a pérdida de cordura +20%"),
    8: ("invocar_aliado", "Invocar Aliado", "Llama a un gato onírico para que luche a tu lado"),
    9: ("visión_cósmica", "Visión Cósmica", "Puedes ver la verdadera naturaleza de los enemigos"),
    10: ("avatar_sueño", "Avatar del Sueño", "Tus ataques ignoran defensa física"),
}

# Mejoras ampliadas
MEJORAS = [
    ("vida_15", "+15 Vida máxima"),
    ("cordura_15", "+15 Cordura máxima"),
    ("voluntad_15", "+15 Voluntad máxima"),
    ("dano_10", "+10% daño permanente"),
    ("resist_10", "+10% resistencia"),
    ("vel_2", "+2 Velocidad"),
    ("mente_5", "+5% resistencia a cordura"),
    ("sueño_lucido", "Los sueños son más reveladores"),
]

# Posibles aliados
ALIADOS = {
    "gato_onirico": Ally("gato_onirico", "Gato Onírico", "GATO", 30, 30, 5, 12, 2, ["esquiva"]),
    "zoog_amigo": Ally("zoog_amigo", "Zoog Amistoso", "ZOOG", 20, 20, 4, 10, 1, []),
    "ghoul_domado": Ally("ghoul_domado", "Ghoul Dócil", "GHOUL", 50, 50, 8, 18, 4, ["resistencia"]),
}

# ═══════════════════════════════════════════════════════════════════════════════
# CLASE PLAYER (ampliada)
# ═══════════════════════════════════════════════════════════════════════════════
class Player:
    def __init__(self):
        self.vida = self.vida_max = 100
        self.cordura = self.cordura_max = 100
        self.voluntad = self.voluntad_max = 100
        self.vel_base = VEL_BASE
        self.reputacion = 0
        self.oro = 20
        self.nivel = 1
        self.xp = 0
        self.bonus_dano = 0.0
        self.bonus_resist = 0.0
        self.bonus_resist_cordura = 0.0   # Nuevo

        self.arma = Item("punos", "Puños", "ARMA", dmin=3, dmax=8)
        self.armadura = Item("sin_armadura", "Sin armadura", "ARMADURA")
        self.inventario: List[Item] = [Item("piedra_comun", "Piedra Común", "MISION")]
        self.habilidades: List[str] = []
        self.estados: Dict[str, int] = {}   # ej. "miedo", "confuso"
        self.aliados: List[Ally] = []        # Nuevo

        self.flags: Dict[str, bool] = {
            "GATOS_ALIADOS": False,
            "GATOS_HOSTILES": False,
            "RUTA_SEGURA": False,
            "PACIFISTA": True,
            "tutorial": False,
            "NODENS_BENDECIDO": False,
            "NYARLATHOTEP_VISTO": False,
        }
        self.mapa_frags = 0
        self.muertes = 0
        self.sellos_lunares = 0

        self.quests_activas: List[str] = []
        self.quests_completas: List[str] = []
        self.logros: List[str] = []
        self.bestiario: Dict[str, int] = {}   # Veces visto/derrotado
        self.conocimiento: Dict[str, bool] = {} # Revelaciones sobre entidades

        self.zona = "zona_1"
        self.zonas_visitadas = ["zona_1"]
        self.descansos = 0
        self.ciclo = Ciclo.DIA
        self.fase_lunar = FaseLunar.NUEVA    # Nuevo
        self.turno = 0
        self.tiempo = 0
        self.eventos: List[str] = []
        self.decisiones: List[str] = []

    def vel_efectiva(self) -> int:
        v = self.vel_base + self.nivel
        if self.armadura:
            v += self.armadura.bvel
        return max(1, v)

    def cat_rep(self) -> str:
        if self.reputacion > 80:
            return "HEROICA"
        if self.reputacion >= 50:
            return "POSITIVA"
        if self.reputacion >= 20:
            return "NEUTRAL"
        if self.reputacion >= 0:
            return "SOSPECHOSA"
        return "TEMIDA"

    def xp_siguiente(self) -> int:
        return XP_TABLA.get(self.nivel + 1, 9999)

    def puede_subir(self) -> bool:
        return self.nivel < 10 and self.xp >= self.xp_siguiente()

    def subir_nivel(self):
        if self.nivel < 10:
            self.nivel += 1
            if self.nivel in HABILIDADES:
                h = HABILIDADES[self.nivel]
                if h[0] not in self.habilidades:
                    self.habilidades.append(h[0])

    def mod_stat(self, stat: str, val: int):
        if stat == "vida":
            self.vida = max(0, min(self.vida_max, self.vida + val))
        elif stat == "cordura":
            # Aplicar resistencia si es pérdida
            if val < 0:
                val = int(val * (1 - self.bonus_resist_cordura))
            self.cordura = max(0, min(self.cordura_max, self.cordura + val))
        elif stat == "voluntad":
            self.voluntad = max(0, min(self.voluntad_max, self.voluntad + val))
        elif stat == "oro":
            self.oro = max(0, min(9999, self.oro + val))
        elif stat == "reputacion":
            self.reputacion = max(-100, min(100, self.reputacion + val))

    def tiene_item(self, iid: str) -> bool:
        return any(i.id == iid for i in self.inventario)

    def add_item(self, item: Item) -> bool:
        if len(self.inventario) >= MAX_INV:
            return False
        self.inventario.append(item)
        return True

    def rem_item(self, iid: str) -> bool:
        for i, it in enumerate(self.inventario):
            if it.id == iid:
                self.inventario.pop(i)
                return True
        return False

    def aprender_conocimiento(self, clave: str):
        self.conocimiento[clave] = True

    def to_dict(self) -> dict:
        return {
            "vida": self.vida,
            "vida_max": self.vida_max,
            "cordura": self.cordura,
            "cordura_max": self.cordura_max,
            "voluntad": self.voluntad,
            "voluntad_max": self.voluntad_max,
            "vel_base": self.vel_base,
            "reputacion": self.reputacion,
            "oro": self.oro,
            "nivel": self.nivel,
            "xp": self.xp,
            "bonus_dano": self.bonus_dano,
            "bonus_resist": self.bonus_resist,
            "bonus_resist_cordura": self.bonus_resist_cordura,
            "arma": self.arma.id if self.arma else "punos",
            "armadura": self.armadura.id if self.armadura else "sin_armadura",
            "inventario": [i.id for i in self.inventario],
            "habilidades": self.habilidades,
            "aliados": [a.id for a in self.aliados],
            "flags": self.flags,
            "mapa_frags": self.mapa_frags,
            "muertes": self.muertes,
            "sellos_lunares": self.sellos_lunares,
            "quests_activas": self.quests_activas,
            "quests_completas": self.quests_completas,
            "logros": self.logros,
            "bestiario": self.bestiario,
            "conocimiento": self.conocimiento,
            "zona": self.zona,
            "zonas_visitadas": self.zonas_visitadas,
            "descansos": self.descansos,
            "ciclo": self.ciclo.value,
            "fase_lunar": self.fase_lunar.value,
            "turno": self.turno,
            "tiempo": self.tiempo,
            "eventos": self.eventos,
            "decisiones": self.decisiones,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Player':
        p = cls()
        for k in [
            "vida", "vida_max", "cordura", "cordura_max", "voluntad", "voluntad_max",
            "vel_base", "reputacion", "oro", "nivel", "xp", "bonus_dano", "bonus_resist",
            "bonus_resist_cordura", "mapa_frags", "muertes", "sellos_lunares",
            "descansos", "turno", "tiempo"
        ]:
            if k in d:
                setattr(p, k, d[k])

        if d.get("arma") in ARMAS:
            p.arma = copy.deepcopy(ARMAS[d["arma"]])
        if d.get("armadura") in ARMADURAS:
            p.armadura = copy.deepcopy(ARMADURAS[d["armadura"]])

        p.inventario = []
        for iid in d.get("inventario", []):
            if iid in CONSUMIBLES:
                p.inventario.append(copy.deepcopy(CONSUMIBLES[iid]))
            elif iid in MISION_ITEMS:
                p.inventario.append(copy.deepcopy(MISION_ITEMS[iid]))
            elif iid in ARMAS:
                p.inventario.append(copy.deepcopy(ARMAS[iid]))
            elif iid in ARMADURAS:
                p.inventario.append(copy.deepcopy(ARMADURAS[iid]))

        p.habilidades = d.get("habilidades", [])
        # Aliados (simplificado, solo ID)
        p.aliados = []
        for aid in d.get("aliados", []):
            if aid in ALIADOS:
                p.aliados.append(copy.deepcopy(ALIADOS[aid]))

        p.flags = d.get("flags", p.flags)
        p.quests_activas = d.get("quests_activas", [])
        p.quests_completas = d.get("quests_completas", [])
        p.logros = d.get("logros", [])
        p.bestiario = d.get("bestiario", {})
        p.conocimiento = d.get("conocimiento", {})
        p.zona = d.get("zona", "zona_1")
        p.zonas_visitadas = d.get("zonas_visitadas", ["zona_1"])
        p.ciclo = Ciclo(d.get("ciclo", "DIA"))
        p.fase_lunar = FaseLunar(d.get("fase_lunar", 0))
        p.eventos = d.get("eventos", [])
        p.decisiones = d.get("decisiones", [])
        return p

# ═══════════════════════════════════════════════════════════════════════════════
# UI MANAGER (con mejoras para mostrar más info)
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
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Para texto invertido
            self.colors = True
        except:
            pass
        curses.curs_set(0)
        scr.keypad(True)

    def resize(self):
        self.my, self.mx = self.scr.getmaxyx()

    def addstr(self, y, x, s, attr=0) -> bool:
        try:
            if 0 <= y < self.my and 0 <= x < self.mx:
                self.scr.addstr(y, x, s[: self.mx - x - 1], attr)
                return True
        except:
            pass
        return False

    def col(self, n):
        return curses.color_pair(n) if self.colors else 0

    def rev(self):
        return curses.A_REVERSE if self.colors else 0

    def barra(self, y, x, val, mx, w=10, c=1):
        try:
            p = max(0, min(w, int(val / mx * w))) if mx > 0 else 0
            self.addstr(y, x, "[" + "█" * p + "░" * (w - p) + "]", self.col(c))
        except:
            pass

    def caja(self, y, x, h, w, titulo=""):
        y = max(0, min(y, self.my - h))
        x = max(0, min(x, self.mx - w))
        try:
            self.addstr(y, x, "╔" + "═" * (w - 2) + "╗")
            for i in range(1, h - 1):
                self.addstr(y + i, x, "║" + " " * (w - 2) + "║")
            self.addstr(y + h - 1, x, "╚" + "═" * (w - 2) + "╝")
            if titulo:
                self.addstr(y, x + 2, f" {titulo} ", self.col(4))
        except:
            pass

    def clear(self):
        self.scr.clear()

    def refresh(self):
        self.scr.refresh()

    def getch(self):
        return self.scr.getch()

    def wait(self):
        self.scr.getch()

# ═══════════════════════════════════════════════════════════════════════════════
# NUEVO: SISTEMA DE SUEÑOS (eventos oníricos)
# ═══════════════════════════════════════════════════════════════════════════════
class DreamEvent:
    def __init__(self, ui, player):
        self.ui = ui
        self.p = player

    def trigger(self):
        """Elige un sueño aleatorio según fase lunar y zona."""
        if self.p.fase_lunar == FaseLunar.LLENA:
            prob_sueño = 0.4
        elif self.p.fase_lunar == FaseLunar.NUEVA:
            prob_sueño = 0.1
        else:
            prob_sueño = 0.2

        if random.random() > prob_sueño:
            return False  # No sueña

        # Lista de posibles sueños
        sueños = [
            self._sueño_profetico,
            self._sueño_pesadilla,
            self._sueño_revelador,
            self._sueño_encuentro,
        ]
        random.choice(sueños)()
        return True

    def _sueño_profetico(self):
        self.ui.clear()
        self.ui.caja(5, 5, 12, 70, "SUEÑO PROFÉTICO")
        self.ui.addstr(7, 10, "Ves una imagen de Kadath, brillante en la distancia.")
        self.ui.addstr(8, 10, "Una voz susurra: 'Busca los tres sellos lunares...'")
        # Otorga conocimiento o pista
        if "profecia_kadath" not in self.p.conocimiento:
            self.p.aprender_conocimiento("profecia_kadath")
        self.ui.addstr(10, 10, "Ganas +10 de cordura.")
        self.p.mod_stat("cordura", 10)
        self.ui.addstr(12, 10, "Pulsa tecla...")
        self.ui.refresh()
        self.ui.wait()

    def _sueño_pesadilla(self):
        self.ui.clear()
        self.ui.caja(5, 5, 10, 70, "PESADILLA")
        self.ui.addstr(7, 10, "Nyarlathotep emerge de las sombras y ríe.")
        perdida = random.randint(10, 25)
        self.p.mod_stat("cordura", -perdida)
        self.ui.addstr(8, 10, f"¡Pierdes {perdida} de cordura!")
        if self.p.cordura <= 30:
            self.ui.addstr(9, 10, "Sientes que algo te observa...")
        self.ui.addstr(12, 10, "Pulsa tecla...")
        self.ui.refresh()
        self.ui.wait()

    def _sueño_revelador(self):
        self.ui.clear()
        self.ui.caja(5, 5, 10, 70, "REVELACIÓN")
        # Revela un objeto oculto en la zona actual
        zona = ZONAS[self.p.zona]
        objetos = zona.get("objetos", [])
        if objetos:
            iid, loc = random.choice(objetos)
            self.ui.addstr(7, 10, f"En un sueño, ves {iid.replace('_',' ')} en {loc}.")
            self.ui.addstr(8, 10, "Cuando despiertas, sabes dónde buscar.")
            # Marcar como conocido (podría implementarse con una bandera en zona)
            # Por simplicidad, lo dejamos así.
        else:
            self.ui.addstr(7, 10, "No hay nada oculto aquí...")
        self.ui.addstr(12, 10, "Pulsa tecla...")
        self.ui.refresh()
        self.ui.wait()

    def _sueño_encuentro(self):
        self.ui.clear()
        self.ui.caja(5, 5, 10, 70, "ENCUENTRO ONÍRICO")
        # Posibilidad de obtener un aliado temporal o objeto
        if random.random() < 0.3 and len(self.p.aliados) < 2:
            aliado = copy.deepcopy(ALIADOS["gato_onirico"])
            self.p.aliados.append(aliado)
            self.ui.addstr(7, 10, "Un gato onírico se te acerca y decide acompañarte.")
        else:
            item = copy.deepcopy(CONSUMIBLES["pocion_cordura"])
            self.p.add_item(item)
            self.ui.addstr(7, 10, f"Encuentras una {item.nombre} a tu lado al despertar.")
        self.ui.addstr(12, 10, "Pulsa tecla...")
        self.ui.refresh()
        self.ui.wait()

# ═══════════════════════════════════════════════════════════════════════════════
# COMBAT ENGINE (ampliado con aliados, estados, cordura)
# ═══════════════════════════════════════════════════════════════════════════════
class Combat:
    def __init__(self, ui: UI, player: Player):
        self.ui = ui
        self.p = player
        self.e: Optional[Enemy] = None
        self.turno = 0
        self.log: List[str] = []
        self.activo = False

    def iniciar(self, enemigo: Enemy) -> str:
        self.e = copy.deepcopy(enemigo)
        self.turno = 0
        self.activo = True
        self.log = [f"¡{self.e.nombre} te ataca!"]

        # Pérdida de cordura inicial por ver a la criatura
        if self.e.cordura_dano > 0:
            self.p.mod_stat("cordura", -self.e.cordura_dano)
            self.log.append(f"Su mera presencia te hace perder {self.e.cordura_dano} de cordura.")

        if self.e.id not in self.p.bestiario:
            self.p.bestiario[self.e.id] = 0
            # Primera vez: revelar descripción
            if self.e.desc_combate:
                self.log.append(self.e.desc_combate)

        return self._loop()

    def _loop(self) -> str:
        while self.activo:
            self.turno += 1
            self._dibujar()

            # Turno jugador (y aliados)
            res = self._turno_jugador()
            if res:
                return res

            if self.e.vida <= 0:
                return self._victoria()

            # Turno enemigo
            self._turno_enemigo()

            if self.p.vida <= 0:
                return "muerte"
            if self.p.cordura <= 0:
                return "locura"

            time.sleep(0.3)

        return "huida"

    def _dibujar(self):
        self.ui.clear()
        titulo = f"⚔ COMBATE - Turno {self.turno} ⚔"
        self.ui.addstr(0, (self.ui.mx - len(titulo)) // 2, titulo, self.ui.col(5) | curses.A_BOLD)

        # Enemigo
        y = 2
        ancho_caja = 40
        x_izq = (self.ui.mx - ancho_caja) // 2
        self.ui.caja(y, x_izq, 5, ancho_caja, self.e.nombre[: ancho_caja - 4])
        pct = self.e.vida / self.e.vidamax if self.e.vidamax > 0 else 0
        blen = int(pct * (ancho_caja - 10))
        self.ui.addstr(
            y + 2,
            x_izq + 2,
            f"HP: [{'█' * blen}{'░' * (ancho_caja - 10 - blen)}] {self.e.vida}/{self.e.vidamax}",
        )

        # Jugador y aliados
        y += 6
        self.ui.caja(y, x_izq, 6 + len(self.p.aliados), ancho_caja, "RANDOLPH CARTER")
        self.ui.addstr(y + 1, x_izq + 2, "VIDA:    ")
        self.ui.barra(y + 1, x_izq + 12, self.p.vida, self.p.vida_max, ancho_caja - 20, 1)
        self.ui.addstr(y + 2, x_izq + 2, "CORDURA: ")
        self.ui.barra(y + 2, x_izq + 12, self.p.cordura, self.p.cordura_max, ancho_caja - 20, 2)
        self.ui.addstr(y + 3, x_izq + 2, "VOLUNTAD:")
        self.ui.barra(y + 3, x_izq + 12, self.p.voluntad, self.p.voluntad_max, ancho_caja - 20, 3)
        linea = 4
        for ally in self.p.aliados:
            self.ui.addstr(y + linea, x_izq + 2, f"{ally.nombre}: {ally.vida}/{ally.vidamax}")
            linea += 1
        self.ui.addstr(y + linea, x_izq + 2, f"Arma: {self.p.arma.nombre[: ancho_caja - 10]}")

        # Log
        y += 7 + len(self.p.aliados)
        for i, line in enumerate(self.log[-4:]):
            self.ui.addstr(y + i, 2, line[: self.ui.mx - 4])

        # Menú
        y = self.ui.my - 5
        self.ui.addstr(y, 2, "[1] Atacar  [2] Usar Objeto  [3] Esquivar  [4] Huir", self.ui.col(4))
        if "conjuro_menor" in self.p.habilidades:
            self.ui.addstr(y + 1, 2, "[5] Conjuro Menor")
        if "invocar_aliado" in self.p.habilidades and len(self.p.aliados) < 2:
            self.ui.addstr(y + 1, 18, "[6] Invocar Aliado")
        self.ui.refresh()

    def _turno_jugador(self) -> Optional[str]:
        k = self.ui.getch()

        if k == ord('1'):
            dano = random.randint(self.p.arma.dmin, self.p.arma.dmax)
            dano += self.p.nivel * 2
            dano = max(1, dano - self.e.defensa)
            dano = int(dano * (1 + self.p.bonus_dano))
            # Aplicar tipo de daño
            if self.p.arma.tdano == "ONIRICO" and self.e.tdano != "COSMICO":
                dano = int(dano * 1.2)  # Los sueños hieren más a lo físico
            elif self.p.arma.tdano == "COSMICO":
                dano = int(dano * 1.5)  # Daño cósmico es devastador
            self.e.vida -= dano
            self.log.append(f"Atacas con {self.p.arma.nombre}! {dano} daño")
            if self.p.arma.dur > 0:
                self.p.arma.dur -= 1
                if self.p.arma.dur <= 2:
                    self.log.append(f"¡{self.p.arma.nombre} casi se rompe!")
                if self.p.arma.dur == 0:
                    self.log.append(f"¡{self.p.arma.nombre} se rompió!")
                    self.p.arma = copy.deepcopy(ARMAS["punos"])

            # Aliados atacan automáticamente
            for ally in self.p.aliados:
                if ally.vida > 0:
                    d_ally = random.randint(ally.dmin, ally.dmax)
                    d_ally = max(1, d_ally - self.e.defensa)
                    self.e.vida -= d_ally
                    self.log.append(f"{ally.nombre} ataca! {d_ally} daño")

        elif k == ord('2'):
            consumibles = [i for i in self.p.inventario if i.usable]
            if not consumibles:
                self.log.append("No tienes consumibles")
                return None
            self._submenu_consumibles(consumibles)

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

        elif k == ord('6') and "invocar_aliado" in self.p.habilidades and len(self.p.aliados) < 2:
            if self.p.voluntad >= 30:
                self.p.mod_stat("voluntad", -30)
                nuevo = copy.deepcopy(ALIADOS["gato_onirico"])
                self.p.aliados.append(nuevo)
                self.log.append("¡Invocas a un gato onírico!")
            else:
                self.log.append("Voluntad insuficiente")

        return None

    def _submenu_consumibles(self, consumibles):
        self.ui.clear()
        self.ui.addstr(2, 2, "Elige un objeto para usar:", self.ui.col(4))
        y = 4
        for idx, it in enumerate(consumibles):
            self.ui.addstr(y, 4, f"[{idx + 1}] {it.nombre}")
            y += 1
        self.ui.addstr(y + 1, 4, "[0] Cancelar")
        self.ui.refresh()

        while True:
            k2 = self.ui.getch()
            if k2 == ord('0'):
                return
            if ord('1') <= k2 <= ord('9'):
                idx = k2 - ord('1')
                if idx < len(consumibles):
                    it = consumibles[idx]
                    for stat, val in it.efecto.items():
                        self.p.mod_stat(stat, val)
                    self.log.append(f"Usas {it.nombre}")
                    self.p.rem_item(it.id)
                    break

    def _turno_enemigo(self):
        # Ataque de aliados (ya atacaron en turno jugador, pero podrían contraatacar? lo dejamos así)

        # Estados del jugador
        if "esquivando" in self.p.estados:
            if random.random() < 0.6:
                self.log.append("¡Esquivas el ataque!")
                del self.p.estados["esquivando"]
                return
            del self.p.estados["esquivando"]

        # Elegir objetivo (jugador o aliado)
        objetivos = [self.p] + self.p.aliados
        vivos = [o for o in objetivos if (isinstance(o, Player) and o.vida > 0) or (isinstance(o, Ally) and o.vida > 0)]
        if not vivos:
            return
        objetivo = random.choice(vivos)

        dano = random.randint(self.e.dmin, self.e.dmax)
        if isinstance(objetivo, Player):
            def_total = self.p.armadura.defensa if self.p.armadura else 0
            if self.e.tdano != "FISICO":
                def_total = self.p.armadura.resist if self.p.armadura else 0
            dano = max(1, dano - def_total)
            dano = int(dano * (1 - self.p.bonus_resist))
            objetivo.mod_stat("vida", -dano)
            self.log.append(f"{self.e.nombre} te ataca! -{dano} vida")
        else:  # aliado
            def_total = objetivo.defensa
            dano = max(1, dano - def_total)
            objetivo.vida -= dano
            self.log.append(f"{self.e.nombre} ataca a {objetivo.nombre}! -{dano} vida")
            if objetivo.vida <= 0:
                self.p.aliados.remove(objetivo)
                self.log.append(f"{objetivo.nombre} ha caído.")

        # Posible pérdida de cordura adicional si el enemigo tiene aura
        if self.e.cordura_dano > 0 and random.random() < 0.2:
            self.p.mod_stat("cordura", -self.e.cordura_dano // 2)
            self.log.append(f"El horror te hace perder {self.e.cordura_dano // 2} cordura.")

    def _victoria(self) -> str:
        self.activo = False
        xp = self.e.xp
        oro = random.randint(self.e.oro_min, self.e.oro_max)

        self.p.xp += xp
        self.p.mod_stat("oro", oro)
        self.p.bestiario[self.e.id] = self.p.bestiario.get(self.e.id, 0) + 1

        if "logro_01" not in self.p.logros:
            self.p.logros.append("logro_01")

        self.p.flags["PACIFISTA"] = False

        # Loot
        for iid, prob in self.e.loot:
            if random.random() < prob:
                if iid in CONSUMIBLES:
                    self.p.add_item(copy.deepcopy(CONSUMIBLES[iid]))
                elif iid in MISION_ITEMS:
                    self.p.add_item(copy.deepcopy(MISION_ITEMS[iid]))

        # Posible conocimiento al derrotar a un ser único
        if self.e.jefe and self.e.id not in self.p.conocimiento:
            self.p.aprender_conocimiento(self.e.id)
            self.log.append(f"Has aprendido algo sobre {self.e.nombre}.")

        self.ui.clear()
        self.ui.caja(5, (self.ui.mx - 45) // 2, 8, 45, "¡VICTORIA!")
        self.ui.addstr(7, (self.ui.mx - 30) // 2, f"Derrotaste a {self.e.nombre}!")
        self.ui.addstr(9, (self.ui.mx - 20) // 2, f"+{xp} XP  +{oro} oro")
        self.ui.addstr(12, (self.ui.mx - 25) // 2, "Pulsa cualquier tecla...")
        self.ui.refresh()
        self.ui.wait()

        return "victoria"

# ═══════════════════════════════════════════════════════════════════════════════
# SAVE MANAGER (igual)
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
        except:
            return False

    def cargar(self, slot: str = "auto") -> Optional[Player]:
        try:
            with open(SAVE_DIR / f"{slot}.json") as f:
                data = json.load(f)
            return Player.from_dict(data["player"])
        except:
            return None

    def slots(self) -> List[dict]:
        result = []
        for s in ["auto", "slot_1", "slot_2", "slot_3"]:
            fp = SAVE_DIR / f"{s}.json"
            if fp.exists():
                try:
                    with open(fp) as f:
                        d = json.load(f)
                    result.append({"nombre": s, "existe": True, "zona": d["player"].get("zona", "?"), "nivel": d["player"].get("nivel", 1)})
                except:
                    result.append({"nombre": s, "existe": True, "corrupto": True})
            else:
                result.append({"nombre": s, "existe": False})
        return result

# ═══════════════════════════════════════════════════════════════════════════════
# GAME CONTROLLER (ampliado)
# ═══════════════════════════════════════════════════════════════════════════════
class Game:
    def __init__(self, scr):
        self.scr = scr
        self.ui = UI(scr)
        self.p: Optional[Player] = None
        self.save = SaveMgr()
        self.combat: Optional[Combat] = None
        self.dream: Optional[DreamEvent] = None
        self.estado = GS.MENU
        self.running = True
        self.resize_needed = False

        def handle_resize(sig, frame):
            self.resize_needed = True

        signal.signal(signal.SIGWINCH, handle_resize)

    def run(self):
        try:
            while self.running:
                if self.resize_needed:
                    self.ui.resize()
                    self.resize_needed = False

                if self.estado == GS.MENU:
                    self._menu()
                elif self.estado == GS.EXPLOR:
                    self._explorar()
                elif self.estado == GS.COMBAT:
                    self._combate()
                elif self.estado == GS.INV:
                    self._inventario()
                elif self.estado == GS.MAPA:
                    self._mapa()
                elif self.estado == GS.PAUSA:
                    self._pausa()
                elif self.estado == GS.LVLUP:
                    self._nivel_up()
                elif self.estado == GS.MUERTE:
                    self._muerte()
                elif self.estado == GS.FINAL:
                    self._final()
                elif self.estado == GS.QUESTS:
                    self._quests()
                elif self.estado == GS.AYUDA:
                    self._ayuda()
                elif self.estado == GS.TIENDA:
                    self._tienda()
                elif self.estado == GS.BESTIARIO:
                    self._bestiario()
                elif self.estado == GS.SUEÑO:
                    self._sueño()
        except Exception as e:
            self._error(e)

    def _error(self, e):
        try:
            self.ui.clear()
            self.ui.caja(5, 5, 10, 60, "ERROR")
            self.ui.addstr(8, 10, f"Error: {str(e)[:45]}")
            if self.p:
                self.save.guardar(self.p, "crash")
            self.ui.addstr(10, 10, "Guardado de emergencia intentado.")
            self.ui.addstr(12, 10, "Pulsa tecla para salir...")
            self.ui.refresh()
            self.ui.wait()
        except:
            pass

    def _menu(self):
        self.ui.clear()
        logo = [
            "██╗  ██╗ █████╗ ██████╗  █████╗ ████████╗██╗  ██╗",
            "██║ ██╔╝██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██║  ██║",
            "█████╔╝ ███████║██║  ██║███████║   ██║   ███████║",
            "██╔═██╗ ██╔══██║██║  ██║██╔══██║   ██║   ██╔══██║",
            "██║  ██╗██║  ██║██████╔╝██║  ██║   ██║   ██║  ██║",
            "╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝"
        ]

        y = 2
        for l in logo:
            x = (self.ui.mx - len(l)) // 2
            self.ui.addstr(y, max(0, x), l, self.ui.col(4) | curses.A_BOLD)
            y += 1

        self.ui.addstr(y + 1, (self.ui.mx - 45) // 2, "La Búsqueda Onírica de la Desconocida Kadath", self.ui.col(6))

        opts = ["[N] Nueva Partida", "[C] Continuar", "[B] Bestiario", "[S] Salir"]
        y += 4
        for o in opts:
            self.ui.addstr(y, (self.ui.mx - len(o)) // 2, o)
            y += 1

        self.ui.addstr(self.ui.my - 2, (self.ui.mx - len(STUDIO)) // 2, STUDIO, self.ui.col(6))
        self.ui.refresh()

        k = self.ui.getch()
        if k in [ord('n'), ord('N')]:
            self.p = Player()
            self.combat = Combat(self.ui, self.p)
            self.dream = DreamEvent(self.ui, self.p)
            self.save.guardar(self.p, "auto")
            self._intro()
            self.estado = GS.EXPLOR
        elif k in [ord('c'), ord('C')]:
            self._cargar()
        elif k in [ord('b'), ord('B')]:
            self.estado = GS.BESTIARIO
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
            "Mi viaje comienza en Ulthar, donde ningún hombre puede matar a un gato..."
        ]
        self.ui.caja(3, 5, len(texto) + 6, 70, "LA BÚSQUEDA COMIENZA")
        y = 6
        for l in texto:
            self.ui.addstr(y, 10, l, self.ui.col(6))
            y += 1
        self.ui.addstr(y + 2, 10, "Pulsa cualquier tecla...")
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
                zn = ZONAS.get(s.get("zona", ""), {}).get("nombre", "?")
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: {zn} - Niv.{s.get('nivel',1)}")
            else:
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: VACÍO", self.ui.col(6))
            y += 2

        self.ui.addstr(y + 1, 4, "[0] Volver")
        self.ui.refresh()

        k = self.ui.getch()
        if ord('1') <= k <= ord('4'):
            idx = k - ord('1')
            if idx < len(slots) and slots[idx].get("existe") and not slots[idx].get("corrupto"):
                p = self.save.cargar(slots[idx]["nombre"])
                if p:
                    self.p = p
                    self.combat = Combat(self.ui, self.p)
                    self.dream = DreamEvent(self.ui, self.p)
                    self.estado = GS.EXPLOR

    def _explorar(self):
        # Si llegó a Kadath, final
        if self.p.zona == "zona_10":
            self.estado = GS.FINAL
            return

        z = ZONAS.get(self.p.zona, {})

        # Primera visita a una zona
        if self.p.zona not in self.p.zonas_visitadas:
            self.p.zonas_visitadas.append(self.p.zona)
            self.p.xp += 25
            self.p.descansos = 0
            # Posibilidad de sueño al llegar a una nueva zona
            if self.dream and random.random() < 0.2:
                self.dream.trigger()

        # Actualizar fase lunar cada cierto tiempo
        if self.p.turno % 50 == 0:
            nueva_fase = (self.p.fase_lunar.value + 1) % 4
            self.p.fase_lunar = FaseLunar(nueva_fase)

        self._dibujar_explor(z)

        k = self.ui.getch()

        if k == ord('1'):
            self._explorar_zona(z)
        elif k == ord('2'):
            self._viajar(z)
        elif k == ord('3'):
            self._descansar(z)
        elif k == ord('4') and z.get("tienda"):
            self.estado = GS.TIENDA
        elif k == ord('5') and z.get("npcs"):
            self._hablar_npc(z)
        elif k in [ord('i'), ord('I')]:
            self.estado = GS.INV
        elif k in [ord('m'), ord('M')]:
            self.estado = GS.MAPA
        elif k in [ord('p'), ord('P')]:
            self.estado = GS.PAUSA
        elif k in [ord('q'), ord('Q')]:
            self.estado = GS.QUESTS
        elif k == ord('?'):
            self.estado = GS.AYUDA
        elif k == ord('b'):
            self.estado = GS.BESTIARIO

        # Comprobar subida de nivel y muerte
        if self.p.puede_subir():
            self.estado = GS.LVLUP
        if self.p.vida <= 0:
            self.estado = GS.MUERTE
        if self.p.cordura <= 0:
            self.estado = GS.FINAL

        self.p.turno += 1
        if self.p.turno % 20 == 0:
            self.p.ciclo = Ciclo.NOCHE if self.p.ciclo == Ciclo.DIA else Ciclo.DIA

        self._check_logros()

    def _dibujar_explor(self, z: dict):
        self.ui.clear()

        nombre = z.get("nombre", "???")
        self.ui.addstr(0, 2, f"═══ {nombre} ═══", self.ui.col(4) | curses.A_BOLD)

        # Mostrar fase lunar y ciclo
        fase = ["🌑 NUEVA", "🌒 CRECIENTE", "🌕 LLENA", "🌘 MENGUANTE"][self.p.fase_lunar.value]
        ciclo = "☀ DÍA" if self.p.ciclo == Ciclo.DIA else "☾ NOCHE"
        self.ui.addstr(0, self.ui.mx - 20, f"{ciclo} {fase}", self.ui.col(6))

        y = 2
        for line in z.get("ascii", "").split("\n")[:6]:
            self.ui.addstr(y, 2, line[:60])
            y += 1

        y += 1
        for line in z.get("desc", "").split("\n")[:3]:
            self.ui.addstr(y, 2, line[:70], self.ui.col(6))
            y += 1

        # HUD derecha
        hx = self.ui.mx - 22
        self.ui.addstr(1, hx, "VIDA:    ")
        self.ui.barra(1, hx + 9, self.p.vida, self.p.vida_max, 8, 1)
        self.ui.addstr(2, hx, "CORDURA: ")
        self.ui.barra(2, hx + 9, self.p.cordura, self.p.cordura_max, 8, 2)
        self.ui.addstr(3, hx, "VOLUNTAD:")
        self.ui.barra(3, hx + 9, self.p.voluntad, self.p.voluntad_max, 8, 3)
        self.ui.addstr(4, hx, f"VEL: {self.p.vel_efectiva():2} | {self.p.cat_rep()[:8]}")
        self.ui.addstr(5, hx, f"◈ ORO: {self.p.oro}", self.ui.col(4))
        self.ui.addstr(6, hx, f"✦ NIV: {self.p.nivel} XP:{self.p.xp}/{self.p.xp_siguiente()}")
        self.ui.addstr(7, hx, f"ALIADOS: {len(self.p.aliados)}")
        self.ui.addstr(8, hx, "─" * 18)
        arma = self.p.arma.nombre if self.p.arma else "Ninguna"
        self.ui.addstr(9, hx, f"ARMA: {arma[:12]}")
        arm = self.p.armadura.nombre if self.p.armadura else "Ninguna"
        self.ui.addstr(10, hx, f"ARM: {arm[:13]}")

        # Menú inferior
        y = self.ui.my - 5
        self.ui.addstr(y, 2, "[1] Explorar  [2] Viajar  [3] Descansar", self.ui.col(4))
        y += 1
        if z.get("tienda"):
            self.ui.addstr(y, 2, "[4] Tienda")
        if z.get("npcs"):
            self.ui.addstr(y, 18, "[5] Hablar")
        y += 1
        self.ui.addstr(y, 2, "[I] Inventario  [M] Mapa  [P] Pausa  [Q] Quests  [?] Ayuda  [B] Bestiario")

        self.ui.refresh()

    def _explorar_zona(self, z: dict):
        # Encuentro
        enc = z.get("encuentros", [])
        mod = 0.7 if self.p.ciclo == Ciclo.DIA else 1.3
        if self.p.fase_lunar == FaseLunar.LLENA:
            mod *= 1.5   # Más encuentros en luna llena

        if "paso_silencioso" in self.p.habilidades and random.random() < 0.3:
            mod = 0

        for eid, prob in enc:
            if random.random() < prob * mod:
                if eid in ENEMIGOS:
                    self.combat.e = copy.deepcopy(ENEMIGOS[eid])
                    self.estado = GS.COMBAT
                    return

        # Objetos
        for iid, loc in z.get("objetos", []):
            if not self.p.tiene_item(iid):
                item = None
                if iid in CONSUMIBLES:
                    item = copy.deepcopy(CONSUMIBLES[iid])
                elif iid in MISION_ITEMS:
                    item = copy.deepcopy(MISION_ITEMS[iid])

                if item and self.p.add_item(item):
                    self.ui.clear()
                    self.ui.caja(8, 10, 5, 45, "¡ENCONTRADO!")
                    self.ui.addstr(10, 15, f"{item.nombre}")
                    self.ui.addstr(11, 15, f"En: {loc}")
                    self.ui.refresh()
                    time.sleep(1.5)
                    return

        # Posibilidad de sueño al explorar
        if self.dream and random.random() < 0.1:
            self.dream.trigger()

        self.ui.addstr(self.ui.my - 3, 2, "Exploras pero no encuentras nada...")
        self.ui.refresh()
        time.sleep(1)

    def _viajar(self, z: dict):
        conex = z.get("conexiones", [])
        if not conex:
            return

        self.ui.clear()
        self.ui.addstr(2, 2, "═══ VIAJAR ═══", self.ui.col(4))

        y = 4
        dests = []
        for zid in conex:
            zdata = ZONAS.get(zid, {})
            dests.append((zid, zdata.get("nombre", zid)))
            self.ui.addstr(y, 4, f"[{len(dests)}] {dests[-1][1]}")
            y += 1

        self.ui.addstr(y + 1, 4, "[0] Cancelar")
        self.ui.refresh()

        k = self.ui.getch()
        if ord('1') <= k <= ord('9'):
            idx = k - ord('1')
            if idx < len(dests):
                self.p.zona = dests[idx][0]
                self.p.descansos = 0
                self.save.guardar(self.p, "auto")

    def _descansar(self, z: dict):
        if not z.get("segura") and not z.get("posada"):
            self.ui.addstr(self.ui.my - 3, 2, "Lugar no seguro para descansar...")
            self.ui.refresh()
            time.sleep(1)
            return

        if self.p.descansos >= 2 and not z.get("posada"):
            self.ui.addstr(self.ui.my - 3, 2, "Ya descansaste suficiente aquí.")
            self.ui.refresh()
            time.sleep(1)
            return

        self.p.mod_stat("cordura", 15)
        self.p.mod_stat("voluntad", 10)
        self.p.mod_stat("vida", 5)
        self.p.descansos += 1

        # Posibilidad de sueño al descansar
        if self.dream:
            self.dream.trigger()

        self.ui.addstr(self.ui.my - 3, 2, "Descansas y recuperas fuerzas...")
        self.ui.refresh()
        time.sleep(1)

    def _hablar_npc(self, z: dict):
        npcs = z.get("npcs", [])
        if not npcs:
            return

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

        self.ui.addstr(y + 1, 4, "[0] Despedirse")
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
                self.ui.addstr(y + 3, 4, "¡Quest completada! +50 oro, +80 XP", self.ui.col(1))
                self.ui.refresh()
                time.sleep(2)
            elif "q01" not in self.p.quests_activas:
                self.p.quests_activas.append("q01")
                self.ui.addstr(y + 3, 4, "¡Nueva quest: El Favor de los Gatos!", self.ui.col(4))
                self.ui.refresh()
                time.sleep(2)

    def _dialogo_zoog(self):
        self.ui.addstr(2, 2, "═══ Zoog Gris ═══", self.ui.col(4))
        self.ui.addstr(4, 4, "¿Qué quieres, soñador?")

        y = 6
        self.ui.addstr(y, 4, "[1] Comerciar")
        y += 1

        if "q02" not in self.p.quests_activas and "q02" not in self.p.quests_completas:
            self.ui.addstr(y, 4, "[2] ¿Necesitas algo? (Quest)")
            y += 1

        if self.p.tiene_item("gatito_onirico") and "q02" in self.p.quests_activas:
            self.ui.addstr(y, 4, "[2] Tengo un gatito...", self.ui.col(4))
            y += 1

        self.ui.addstr(y + 1, 4, "[0] Despedirse")
        self.ui.refresh()

        k = self.ui.getch()
        if k == ord('1'):
            self.estado = GS.TIENDA
        elif k == ord('2'):
            if "q02" not in self.p.quests_activas and "q02" not in self.p.quests_completas:
                self.p.quests_activas.append("q02")
                self.ui.addstr(y + 3, 4, "¡Nueva quest: El Trato de los Zoog!", self.ui.col(4))
                self.ui.refresh()
                time.sleep(2)
            elif self.p.tiene_item("gatito_onirico") and "q02" in self.p.quests_activas:
                self._decision_gatito()

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

        self.ui.addstr(y + 1, 4, "[0] Despedirse")
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
                self.ui.addstr(y + 3, 4, "¡Quest completada!", self.ui.col(1))
                self.ui.refresh()
                time.sleep(2)
            elif "q03" not in self.p.quests_activas:
                self.p.quests_activas.append("q03")
                self.ui.addstr(y + 3, 4, "¡Nueva quest!", self.ui.col(4))
                self.ui.refresh()
                time.sleep(2)

    def _dialogo_kuranes(self):
        self.ui.addstr(2, 2, "═══ Rey Kuranes ═══", self.ui.col(4))
        self.ui.addstr(4, 4, "Celephaïs te da la bienvenida, soñador.")
        self.ui.addstr(5, 4, "Poseo conocimientos sobre los Dioses.")

        y = 7
        if "q04" not in self.p.quests_activas and "q04" not in self.p.quests_completas:
            self.ui.addstr(y, 4, "[1] Háblame de las catacumbas de Zak")
            y += 1
        if "conocimiento_nodens" not in self.p.conocimiento:
            self.ui.addstr(y, 4, "[2] ¿Quién es Nodens?")
            y += 1

        self.ui.addstr(y + 1, 4, "[0] Despedirse")
        self.ui.refresh()

        k = self.ui.getch()
        if k == ord('1') and "q04" not in self.p.quests_activas:
            self.p.quests_activas.append("q04")
            self.ui.addstr(y + 3, 4, "Quest 'El Secreto de las Profundidades' añadida.", self.ui.col(4))
            self.ui.refresh()
            time.sleep(2)
        elif k == ord('2'):
            self.p.aprender_conocimiento("conocimiento_nodens")
            self.ui.addstr(y + 3, 4, "Nodens es el Señor de los Abismos, un Dios benévolo.", self.ui.col(6))
            self.ui.refresh()
            time.sleep(2)

    def _decision_gatito(self):
        self.ui.clear()
        self.ui.caja(5, 5, 10, 55, "DECISIÓN CLAVE")
        self.ui.addstr(7, 10, "¿A quién entregas el Gatito?")
        self.ui.addstr(9, 10, "[1] Devolver a Menes (Gatos aliados)", self.ui.col(1))
        self.ui.addstr(10, 10, "[2] Dar a los Zoog (Mapa, Gatos hostiles)", self.ui.col(5))
        self.ui.addstr(12, 10, "Decisión PERMANENTE.")
        self.ui.refresh()

        while True:
            k = self.ui.getch()
            if k == ord('1'):
                self.p.decisiones.append("gatos")
                self.p.mod_stat("reputacion", 15)
                if "q02" in self.p.quests_activas:
                    self.p.quests_activas.remove("q02")
                break
            elif k == ord('2'):
                self.p.decisiones.append("zoog")
                self.p.rem_item("gatito_onirico")
                if "q02" in self.p.quests_activas:
                    self.p.quests_activas.remove("q02")
                    self.p.quests_completas.append("q02")
                self.p.mod_stat("oro", 30)
                self.p.xp += 60
                self.p.mapa_frags += 1
                self.p.flags["GATOS_HOSTILES"] = True
                self.p.add_item(copy.deepcopy(MISION_ITEMS["mapa_frag"]))
                break

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

            self.ui.addstr(self.ui.my - 3, 2, "[E] Equipar  [U] Usar  [D] Descartar  [X] Cerrar")
            self.ui.refresh()

            k = self.ui.getch()
            if k in [ord('x'), ord('X')]:
                break
            elif k in [ord('e'), ord('E')]:
                self._equipar()
            elif k in [ord('u'), ord('U')]:
                self._usar()
            elif k in [ord('d'), ord('D')]:
                self._descartar()

        self.estado = GS.EXPLOR

    def _equipar(self):
        self.ui.addstr(self.ui.my - 2, 2, "Número a equipar (0 cancelar): ")
        self.ui.refresh()
        k = self.ui.getch()
        if ord('1') <= k <= ord('9'):
            idx = k - ord('1')
            if idx < len(self.p.inventario):
                it = self.p.inventario[idx]
                if it.tipo == "ARMA":
                    if self.p.arma and self.p.arma.id != "punos":
                        if len(self.p.inventario) >= MAX_INV:
                            self.ui.addstr(self.ui.my - 1, 2, "¡Inventario lleno! No puedes cambiar.", self.ui.col(5))
                            self.ui.refresh()
                            time.sleep(1)
                            return
                        self.p.inventario.append(self.p.arma)
                    self.p.arma = it
                    self.p.inventario.pop(idx)
                elif it.tipo == "ARMADURA":
                    if self.p.armadura and self.p.armadura.id != "sin_armadura":
                        if len(self.p.inventario) >= MAX_INV:
                            self.ui.addstr(self.ui.my - 1, 2, "¡Inventario lleno! No puedes cambiar.", self.ui.col(5))
                            self.ui.refresh()
                            time.sleep(1)
                            return
                        self.p.inventario.append(self.p.armadura)
                    self.p.armadura = it
                    self.p.inventario.pop(idx)

    def _usar(self):
        self.ui.addstr(self.ui.my - 2, 2, "Número a usar (0 cancelar): ")
        self.ui.refresh()
        k = self.ui.getch()
        if ord('1') <= k <= ord('9'):
            idx = k - ord('1')
            if idx < len(self.p.inventario):
                it = self.p.inventario[idx]
                if it.usable:
                    for stat, val in it.efecto.items():
                        self.p.mod_stat(stat, val)
                    self.p.inventario.pop(idx)

    def _descartar(self):
        self.ui.addstr(self.ui.my - 2, 2, "Número a descartar (0 cancelar): ")
        self.ui.refresh()
        k = self.ui.getch()
        if ord('1') <= k <= ord('9'):
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
                    it = copy.deepcopy(CONSUMIBLES[iid])
                elif iid in ARMAS:
                    it = copy.deepcopy(ARMAS[iid])
                elif iid in ARMADURAS:
                    it = copy.deepcopy(ARMADURAS[iid])

                if it:
                    items.append(it)
                    color = 0 if it.valor_c <= self.p.oro else self.ui.col(5)
                    self.ui.addstr(y, 4, f"[{len(items)}] {it.nombre:20} - {it.valor_c} ◈", color)
                    y += 1

            self.ui.addstr(y + 1, 4, "[X] Salir")
            self.ui.refresh()

            k = self.ui.getch()
            if k in [ord('x'), ord('X')]:
                break
            elif ord('1') <= k <= ord('9'):
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
        for line in mapa.split("\n"):
            self.ui.addstr(y, 2, line)
            y += 1

        zn = ZONAS.get(self.p.zona, {}).get("nombre", "???")
        self.ui.addstr(y + 1, 4, f"Ubicación: {zn}", self.ui.col(4))
        self.ui.addstr(y + 2, 4, f"Fragmentos mapa: {self.p.mapa_frags}/3")
        self.ui.addstr(y + 3, 4, f"Sellos lunares: {self.p.sellos_lunares}")
        self.ui.addstr(self.ui.my - 2, 2, "Pulsa tecla para volver...")
        self.ui.refresh()
        self.ui.wait()
        self.estado = GS.EXPLOR

    def _pausa(self):
        self.ui.clear()
        self.ui.caja(5, 20, 12, 30, "⏸ PAUSA")

        opts = ["[G] Guardar", "[M] Mapa", "[Q] Quests", "[?] Ayuda", "[X] Volver", "[S] Salir al menú"]
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
        elif k == ord('?'):
            self.estado = GS.AYUDA
        elif k in [ord('x'), ord('X')]:
            self.estado = GS.EXPLOR
        elif k in [ord('s'), ord('S')]:
            self.save.guardar(self.p, "auto")
            self.estado = GS.MENU

    def _guardar_menu(self):
        self.ui.clear()
        self.ui.addstr(2, 2, "═══ GUARDAR ═══", self.ui.col(4))

        slots = self.save.slots()[1:]
        y = 4
        for i, s in enumerate(slots):
            if s.get("existe"):
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: Ocupado")
            else:
                self.ui.addstr(y, 4, f"[{i+1}] {s['nombre']}: Vacío")
            y += 1

        self.ui.addstr(y + 1, 4, "[0] Cancelar")
        self.ui.refresh()

        k = self.ui.getch()
        if ord('1') <= k <= ord('3'):
            slot = f"slot_{k - ord('0')}"
            if self.save.guardar(self.p, slot):
                self.ui.addstr(y + 3, 4, "¡Guardado!", self.ui.col(1))
            else:
                self.ui.addstr(y + 3, 4, "Error", self.ui.col(5))
            self.ui.refresh()
            time.sleep(1)

    def _nivel_up(self):
        self.ui.clear()
        self.ui.addstr(8, 20, "★ ★ ★ ★ ★ ★ ★ ★ ★ ★", self.ui.col(4))
        self.ui.addstr(10, 22, "¡SUBIDA DE NIVEL!", self.ui.col(4) | curses.A_BOLD)
        self.ui.addstr(12, 20, f"Nivel {self.p.nivel} → {self.p.nivel + 1}")
        self.ui.refresh()
        time.sleep(1)

        self.p.subir_nivel()

        if self.p.nivel in HABILIDADES:
            h = HABILIDADES[self.p.nivel]
            self.ui.addstr(14, 15, f"¡Nueva habilidad: {h[1]}!", self.ui.col(1))
            self.ui.refresh()
            time.sleep(1.5)

        # Elegir mejora
        self.ui.clear()
        self.ui.addstr(2, 2, "═══ ELIGE MEJORA ═══", self.ui.col(4))

        pool = copy.copy(MEJORAS)
        random.shuffle(pool)
        opts = pool[:3]

        y = 5
        for i, (mid, desc) in enumerate(opts):
            self.ui.addstr(y, 4, f"[{i+1}] {desc}")
            y += 2
        self.ui.refresh()

        while True:
            k = self.ui.getch()
            if ord('1') <= k <= ord('3'):
                idx = k - ord('1')
                if idx < len(opts):
                    mid, _ = opts[idx]
                    if mid == "vida_15":
                        self.p.vida_max += 15
                        self.p.vida += 15
                    elif mid == "cordura_15":
                        self.p.cordura_max += 15
                        self.p.cordura += 15
                    elif mid == "voluntad_15":
                        self.p.voluntad_max += 15
                        self.p.voluntad += 15
                    elif mid == "dano_10":
                        self.p.bonus_dano += 0.1
                    elif mid == "resist_10":
                        self.p.bonus_resist += 0.1
                    elif mid == "vel_2":
                        self.p.vel_base += 2
                    elif mid == "mente_5":
                        self.p.bonus_resist_cordura += 0.05
                    elif mid == "sueño_lucido":
                        self.p.flags["sueño_lucido"] = True
                    break

        self.estado = GS.EXPLOR

    def _muerte(self):
        self.p.muertes += 1

        try:
            num_zona = int(self.p.zona.split('_')[1])
        except:
            num_zona = 1
        coste = 20 + num_zona * 5

        self.ui.clear()
        self.ui.caja(5, 10, 10, 45, "☠ HAS CAÍDO")

        y = 8
        if self.p.oro >= coste:
            self.ui.addstr(y, 15, f"[1] Resucitar ({coste} ◈)")
        else:
            self.ui.addstr(y, 15, f"[1] Resucitar ({coste} ◈) - Sin oro", self.ui.col(5))
        self.ui.addstr(y + 1, 15, "[2] Cargar guardado")
        self.ui.addstr(y + 2, 15, "[3] Game Over")
        self.ui.refresh()

        while True:
            k = self.ui.getch()
            if k == ord('1') and self.p.oro >= coste:
                self.p.mod_stat("oro", -coste)
                self.p.vida = int(self.p.vida_max * 0.3)
                self.p.cordura = int(self.p.cordura_max * 0.3)
                self.p.zona = "zona_1"
                self.estado = GS.EXPLOR
                break
            elif k == ord('2'):
                p = self.save.cargar("auto")
                if p:
                    self.p = p
                    self.combat = Combat(self.ui, self.p)
                    self.dream = DreamEvent(self.ui, self.p)
                self.estado = GS.EXPLOR
                break
            elif k == ord('3'):
                self.estado = GS.FINAL
                break

    def _final(self):
        self.ui.clear()

        # Múltiples finales según acciones y cordura
        if self.p.cordura <= 0:
            self.ui.caja(3, 5, 12, 65, "FINAL: DEVORADO POR EL CAOS")
            self.ui.addstr(6, 10, "Tu cordura se ha desvanecido.")
            self.ui.addstr(7, 10, "Nyarlathotep reclama tu alma para siempre.")
            self.ui.addstr(9, 10, "Eres una marioneta del Caos Reptante.")
        elif self.p.zona == "zona_10":
            if self.p.cordura > 70 and self.p.flags.get("GATOS_ALIADOS") and self.p.sellos_lunares >= 3:
                self.ui.caja(3, 5, 14, 70, "FINAL: LA APOTEOSIS DEL SOÑADOR")
                self.ui.addstr(6, 10, "Has alcanzado Kadath y los Dioses te reciben.")
                self.ui.addstr(7, 10, "Comprendes que los sueños y la realidad son uno.")
                self.ui.addstr(8, 10, "Te conviertes en un habitante de Kadath, inmortal.")
                self.ui.addstr(10, 10, "★ FINAL VERDADERO ★", self.ui.col(4))
            elif self.p.cordura > 50:
                self.ui.caja(3, 5, 10, 65, "FINAL: EL DESPERTAR")
                self.ui.addstr(6, 10, "Llegaste a Kadath pero no como esperabas.")
                self.ui.addstr(7, 10, "Los Dioses te ignoran. Despiertas en tu cama.")
                self.ui.addstr(8, 10, "Quizás todo fue un sueño...")
            else:
                self.ui.caja(3, 5, 10, 65, "FINAL: LA MALDICIÓN")
                self.ui.addstr(6, 10, "Kadath es una prisión. No puedes escapar.")
                self.ui.addstr(7, 10, "Nyarlathotep te condena a vagar eternamente.")
        elif self.p.flags.get("NYARLATHOTEP_VISTO"):
            self.ui.caja(3, 5, 10, 65, "FINAL: EL ENCUENTRO")
            self.ui.addstr(6, 10, "Has visto al Caos Reptante y sobrevivido.")
            self.ui.addstr(7, 10, "Pero tu mente nunca será la misma.")
        else:
            self.ui.caja(3, 5, 8, 60, "FIN DEL VIAJE")
            self.ui.addstr(6, 10, "Tu búsqueda ha terminado, por ahora...")

        self.ui.addstr(12, 10, f"Nivel: {self.p.nivel}  Turnos: {self.p.turno}")
        self.ui.addstr(13, 10, f"Quests: {len(self.p.quests_completas)}")
        self.ui.addstr(14, 10, f"Enemigos conocidos: {len(self.p.bestiario)}")
        self.ui.addstr(16, 10, STUDIO)
        self.ui.addstr(18, 10, "Pulsa tecla para menú...")
        self.ui.refresh()
        self.ui.wait()

        self.estado = GS.MENU

    def _quests(self):
        self.ui.clear()
        self.ui.addstr(0, 2, "═══ QUESTS ═══", self.ui.col(4))

        y = 2
        if not self.p.quests_activas:
            self.ui.addstr(y, 4, "No tienes quests activas.")
        else:
            for qid in self.p.quests_activas:
                q = QUESTS.get(qid)
                if q:
                    faccion = f" [{q.faccion}]" if q.faccion else ""
                    self.ui.addstr(y, 4, f"• {q.titulo}{faccion}", self.ui.col(4))
                    y += 1
                    self.ui.addstr(y, 6, q.desc[:60])
                    y += 2

        y += 1
        self.ui.addstr(y, 2, "── COMPLETADAS ──", self.ui.col(6))
        y += 1
        for qid in self.p.quests_completas:
            q = QUESTS.get(qid)
            if q:
                self.ui.addstr(y, 4, f"✓ {q.titulo}", self.ui.col(1))
                y += 1

        self.ui.addstr(self.ui.my - 2, 2, "Pulsa tecla para volver...")
        self.ui.refresh()
        self.ui.wait()
        self.estado = GS.EXPLOR

    def _bestiario(self):
        self.ui.clear()
        self.ui.addstr(0, 2, "═══ BESTIARIO ═══", self.ui.col(4))

        if not self.p.bestiario:
            self.ui.addstr(2, 4, "Aún no has encontrado ninguna criatura.")
        else:
            y = 2
            for eid, veces in sorted(self.p.bestiario.items(), key=lambda x: x[0]):
                enemigo = ENEMIGOS.get(eid)
                if enemigo:
                    nombre = enemigo.nombre
                    desc = enemigo.desc_combate[:50] if enemigo.desc_combate else "Una criatura de los sueños."
                    self.ui.addstr(y, 4, f"• {nombre} ({veces} vez/veces)", self.ui.col(6))
                    y += 1
                    self.ui.addstr(y, 6, desc)
                    y += 2
                    if y > self.ui.my - 4:
                        self.ui.addstr(self.ui.my - 2, 2, "Pulsa tecla para más...")
                        self.ui.refresh()
                        self.ui.wait()
                        self.ui.clear()
                        self.ui.addstr(0, 2, "═══ BESTIARIO ═══", self.ui.col(4))
                        y = 2

        self.ui.addstr(self.ui.my - 2, 2, "Pulsa tecla para volver...")
        self.ui.refresh()
        self.ui.wait()
        self.estado = GS.EXPLOR

    def _ayuda(self):
        self.ui.clear()
        self.ui.addstr(0, 2, "═══ AYUDA ═══", self.ui.col(4))

        ayuda = [
            "CONTROLES:",
            "[1-5] Acciones del menú",
            "[I] Inventario  [M] Mapa  [P] Pausa",
            "[Q] Quests  [?] Ayuda  [B] Bestiario",
            "",
            "NOVEDADES v4.0:",
            "• Cordura: si llega a 0, final malo.",
            "• Sueños: ocurren al explorar o descansar.",
            "• Fases lunares afectan encuentros.",
            "• Aliados: gatos oníricos te ayudan.",
            "• Múltiples finales según tus acciones.",
            "",
            f"v{VERSION} - {STUDIO}"
        ]

        y = 2
        for l in ayuda:
            self.ui.addstr(y, 4, l)
            y += 1

        self.ui.addstr(self.ui.my - 2, 2, "Pulsa tecla para volver...")
        self.ui.refresh()
        self.ui.wait()
        self.estado = GS.EXPLOR

    def _sueño(self):
        if self.dream:
            self.dream.trigger()
        self.estado = GS.EXPLOR

    def _check_logros(self):
        if self.p.oro >= 500 and "logro_03" not in self.p.logros:
            self.p.logros.append("logro_03")

        if self.p.zona == "zona_7" and self.p.cordura >= 90 and "logro_04" not in self.p.logros:
            self.p.logros.append("logro_04")

        if len(self.p.bestiario) >= 5 and "logro_05" not in self.p.logros:
            self.p.logros.append("logro_05")

        if self.p.mapa_frags >= 3 and "logro_06" not in self.p.logros:
            self.p.logros.append("logro_06")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main(scr):
    try:
        game = Game(scr)
        game.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        try:
            curses.endwin()
        except:
            pass
        print(f"\nError: {e}")
        print(STUDIO)
        raise

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print(f"\n\n¡Hasta el próximo sueño!\n{STUDIO}")
    except Exception as e:
        print(f"\nError inesperado: {e}\n{STUDIO}")

# ═══════════════════════════════════════════════════════════════════════════════
# KADATH v4.0 — Molvic Studio © 2024
# Basado en "La Búsqueda Onírica de la Desconocida Kadath" de H.P. Lovecraft
# ═══════════════════════════════════════════════════════════════════════════════