                                         CORRECIONES V0.2


CORRECIONES QWEN
# KADATH v0.2 — Correcciones Críticas

**Versión:** 0.1 → 0.2  
**Fecha:** 2024  
**Estado:** ✅ Estable

---

## 🎯 ¿Qué se corrigió?

Se identificaron y solucionaron **6 bugs críticos** que afectaban la estabilidad del juego.

---

## 🐛 Bugs Corregidos

| # | Problema | Solución | Impacto |
|---|----------|----------|---------|
| 1 | `import copy` dentro de funciones (9 veces) | Movido al inicio del archivo | ✅ Rendimiento |
| 2 | Combate retornaba "huida" incluso al ganar | Verifica estado real del enemigo | ✅ Lógica de juego |
| 3 | Loop infinito sin timeout en decisión del gatito | Timeout de 30 segundos | ✅ UX |
| 4 | Saves sin validación de versión | Ahora verifica compatibilidad | ✅ Datos |
| 5 | `split("\n")` incompatible con Windows | Cambiado a `splitlines()` | ✅ Multiplataforma |
| 6 | `except:` genérico que oculta errores | Ahora loguea la excepción específica | ✅ Debugging |

---

## 📊 Mejoras

- **Código más limpio:** Imports centralizados según PEP 8
- **Más estable:** Menos crashes por errores ocultos
- **Más compatible:** Funciona en Linux, macOS y Windows
- **Más seguro:** Validación de saves corruptos o de versión diferente

---

## ⚡ ¿Necesito hacer algo?

**Usuarios existentes:**
- ✅ Tus saves son compatibles
- ⚠️ Verás una advertencia si la versión difiere

**Nuevos usuarios:**
- ✅ Todo funciona correctamente desde el inicio

---

## 🚀 Próximas Mejoras (v3.2)

- [ ] Modularizar código en carpetas
- [ ] Añadir tests unitarios
- [ ] Sistema de logging completo
- [ ] Soporte nativo Windows

---

## 📞 Reportar Bugs

Abre un issue en GitHub incluyendo:
1. Sistema operativo
2. Pasos para reproducir
3. Captura de pantalla (si aplica)

---

**Molvic Studio © 2024**  
*Basado en H.P. Lovecraft (Dominio Público)*

CORRECIONES DEEPSEEK
KADATH v0.1 A V0.2 Cambios y mejoras
Este documento resume las modificaciones aplicadas al código fuente de KADATH v3.0 para obtener la versión 3.1. Los cambios abordan errores críticos, mejoran la jugabilidad y robustecen el código, siguiendo las recomendaciones de una revisión sistemática.

📦 Cambios estructurales y de organización
Importaciones: Se movió import copy al inicio del archivo, eliminando las importaciones dispersas dentro de funciones. Esto mejora la legibilidad y el rendimiento.
Módulo de señales: El manejador de SIGWINCH ahora establece una bandera (self.resize_needed) en lugar de llamar directamente a ui.resize(). En el bucle principal se verifica la bandera y se redimensiona de forma segura, evitando problemas de concurrencia.
Sistema de peso: Se eliminaron los campos peso y la constante PESO_MAX de todas las definiciones de objetos y del jugador, ya que no se utilizaban en la lógica del juego. Esto simplifica las estructuras de datos.
🐛 Corrección de errores
1. Cálculo del coste de resurrección
Problema: Se usaba int(self.p.zona[-1]) para obtener el número de zona, lo que fallaba con zona_10 (devuelve 0) o si el nombre no terminaba en dígito.
Solución: Se parsea correctamente con int(self.p.zona.split('_')[1]). Además, se añadió un bloque try-except para zonas con formato inesperado, usando un valor por defecto (num_zona = 1).
2. Equipamiento con inventario lleno
Problema: Al cambiar de arma o armadura, se añadía el objeto desequipado al inventario sin comprobar si había espacio, pudiendo superar MAX_INV.
Solución: En _equipar, antes de hacer append se verifica len(self.p.inventario) < MAX_INV. Si no hay espacio, se muestra un mensaje de error y se cancela la operación.
3. Misión q02 (El Trato de los Zoog)
Problema: La misión estaba definida pero nunca se activaba; solo se podía completar si se tenía el gatito y se elegía la opción correcta, pero no aparecía en el registro de misiones.
Solución:
En _dialogo_zoog, se añade la opción para activar la misión si no está activa ni completada.
Al elegir entregar el gatito a los Zoog (opción 2), se completa la misión q02 (si estaba activa) y se otorgan las recompensas correspondientes.
Se actualiza la lógica de _decision_gatito para manejar correctamente la finalización de q02.
4. Rotura de armas
Problema: Las armas tenían durabilidad (dur) que decrecía en combate, pero nunca se comprobaba si llegaba a cero, por lo que nunca se rompían.
Solución: En Combat._turno_jugador, después de restar durabilidad, se verifica if self.p.arma.dur == 0. En ese caso, se cambia el arma a los puños (copy.deepcopy(ARMAS["punos"])) y se registra un mensaje en el log.
5. Victoria al llegar a Kadath
Problema: Alcanzar la zona_10 (Kadath) no desencadenaba ningún final; el juego continuaba indefinidamente.
Solución: En _explorar, al inicio se comprueba if self.p.zona == "zona_10": self.estado = GS.FINAL. El método _final ya estaba preparado para manejar distintos epílogos, incluyendo el de Kadath.
🎮 Mejoras en la jugabilidad
6. Selección de consumibles en combate
Problema: En combate, la opción "Usar Objeto" tomaba automáticamente el primer consumible del inventario, sin dar opción al jugador.
Solución: Se implementa un submenú que lista todos los consumibles disponibles (con teclas numéricas). El jugador puede elegir cuál usar o cancelar (tecla 0). La lógica se encuentra en Combat._turno_jugador.
7. Finales diferenciados según el estado del juego
Mejora: En _final, además de los casos de cordura cero y muerte, se distingue si el jugador llegó a Kadath con alta cordura y la bandera GATOS_ALIADOS activa, mostrando un epílogo especial ("La Apoteosis del Soñador"). Esto añade rejugabilidad y consecuencias narrativas.
8. Diálogos de misiones más coherentes
Menes (_dialogo_menes): Ahora la opción de entregar el gatito solo aparece si la misión q01 está activa y el jugador tiene el objeto.
Zoog (_dialogo_zoog): Se muestra la opción de activar la misión q02 cuando corresponde, y la opción de entregar el gatito solo si la misión está activa.
Arash (_dialogo_arash): Similar a las anteriores, se corrigió la lógica para que la opción de completar la misión q03 aparezca únicamente cuando corresponde.
🖥️ Mejoras en la interfaz y robustez
9. Manejo de terminales pequeñas
Varios métodos de dibujado (caja, addstr, barra) ahora calculan posiciones relativas y recortan cadenas para evitar desbordamientos. Se añadieron comprobaciones de límites en UI.addstr y en UI.caja se ajustan las coordenadas si están fuera de rango.
10. Código más limpio y mantenible
Se eliminaron redundancias (por ejemplo, múltiples import copy).
Se añadieron comentarios en secciones críticas.
Se unificó el estilo de comprobaciones de teclas (if ord('1') <= k <= ord('9') en lugar de comparaciones con caracteres específicos).
Se mejoró la legibilidad de los bucles de entrada en submenús (como en la selección de consumibles).
📁 Gestión de guardado
Guardado automático: Se mantiene el guardado al viajar, y ahora también se guarda después de comprar en tiendas (aunque no se muestra explícitamente, se invoca al cambiar de zona). No se añadió guardado en cada evento para no ralentizar, pero se podría extender fácilmente.
✅ Resumen de cambios por archivo (hipotético)
Módulo / Clase	Cambios aplicados
Item, Player	Eliminado campo peso y constantes relacionadas.
UI	Mejorado caja con ajuste de coordenadas; addstr más seguro.
Combat	Submenú de consumibles; rotura de armas; mejor disposición de elementos en pantalla.
Game	Manejo seguro de SIGWINCH; corrección de coste de resurrección; lógica de misiones q02; final en Kadath; comprobación de espacio al equipar.
SaveMgr	Sin cambios funcionales.
🔮 Próximos pasos sugeridos
Implementar un sistema de peso si se desea (actualmente eliminado).
Añadir pantalla de bestiario y logros para mostrar el progreso.
Permitir vender objetos en tiendas.
Mejorar la accesibilidad para terminales muy pequeños (modo de scroll).
Conclusión: La versión 0.2 de KADATH corrige errores importantes, mejora la experiencia de usuario y establece una base más sólida para futuras expansiones. Todos los cambios han sido probados y se integran sin romper la compatibilidad con partidas guardadas de la versión anterior (salvo por la eliminación del campo peso, que no se usaba).


                                    EXPANSION V0.3

    EXPANSION V0.3 - DEEPSEEK
    # KADATH v0.3 – Expansión Lovecraft: Sueños, Cordura y Múltiples Finales

**KADATH v0.3** transforma la experiencia original en un viaje lovecraftiano profundo, donde la cordura es tan valiosa como la vida y los sueños revelan verdades ocultas. Esta versión incorpora nuevos sistemas de juego, mayor rejugabilidad y una atmósfera más inmersiva, todo en un único archivo.

---

## 🌕 Novedades principales

### 1. Sistema de cordura expandido
- Cada criatura tiene un atributo `cordura_dano` que resta cordura al inicio del combate (por su mera presencia).
- El jugador cuenta con `bonus_resist_cordura` (obtenible mediante mejoras o habilidades) para mitigar estas pérdidas.
- Si la cordura llega a cero, se desencadena un final específico de locura permanente.
- Estados alterados (miedo, confusión) pueden afectar el combate (preparado para futuras expansiones).

### 2. Eventos oníricos (sueños)
- Al explorar, descansar o visitar nuevas zonas, existe una probabilidad de tener un sueño (mayor en luna llena).
- Tipos de sueños:
  - **Proféticos**: Revelan pistas sobre Kadath o los sellos lunares.
  - **Pesadillas**: Restan cordura y sumergen al jugador en la inquietud.
  - **Reveladores**: Muestran la ubicación de objetos ocultos en la zona actual.
  - **Encuentros oníricos**: Posibilidad de ganar un aliado (gato onírico) o un objeto consumible.
- La mejora "sueño lúcido" aumenta la probabilidad y calidad de los sueños.

### 3. Fases lunares
- El mundo onírico tiene un ciclo de cuatro fases: **Nueva, Creciente, Llena, Menguante**.
- La fase lunar afecta:
  - Probabilidad de encuentros hostiles (mayor en luna llena).
  - Probabilidad y tipo de sueños.
  - Algunos objetos o eventos especiales solo ocurren en fases específicas.
- El ciclo avanza cada 50 turnos, añadiendo dinamismo al mundo.

### 4. Aliados y combate en grupo
- El jugador puede obtener **aliados** (gatos oníricos, zoogs amigables, ghouls dóciles) a través de eventos, habilidades o decisiones.
- Los aliados aparecen en la interfaz de combate y atacan automáticamente cada turno.
- Pueden recibir daño y morir; si caen, abandonan al grupo.
- Máximo de 2 aliados simultáneos, lo que añade profundidad táctica.

### 5. Bestiario y conocimiento
- Nueva pantalla **Bestiario** (accesible desde el menú principal o con tecla `B`) que registra:
  - Criaturas encontradas y número de veces vistas/derrotadas.
  - Descripciones de cada criatura (si están disponibles).
- Al derrotar a ciertos jefes o completar diálogos, se desbloquean entradas de **conocimiento** que pueden influir en diálogos y finales.

### 6. Múltiples finales
- El desenlace ya no es único; depende de:
  - **Cordura** al llegar a Kadath.
  - **Decisiones clave** (como a quién entregar el gatito).
  - **Sellos lunares** recolectados (hasta 3).
  - **Alianzas con facciones** (Gatos, Zoog, Hombres, Nodens).
- Finales destacados:
  - **Apoteosis del Soñador** (verdadero): Alta cordura, alianza con gatos y tres sellos lunares.
  - **El Despertar**: Llegar a Kadath sin cumplir condiciones especiales.
  - **La Maldición**: Ser atrapado en Kadath por Nyarlathotep.
  - **Locura**: Cuando la cordura llega a cero.
  - **El Encuentro**: Haber visto a Nyarlathotep y sobrevivir.

### 7. Nuevos contenidos
- **Armas y armaduras**: Añadidas la Hoja Lunar, el Báculo de Nodens, la Túnica Sonámbula, etc.
- **Enemigos**: Shantak, Ghoul Antiguo, Gnophkeh, Nyarlathotep (visión), todos con descripciones y efectos de cordura.
- **Misiones**: Cuatro nuevas quests (q04, q05) que exploran las catacumbas, altares y facciones.
- **Objetos de misión y artefactos**: Estatua de Nodens, Cuarzo Sónico, Sello Lunar, etc.
- **Habilidades**: Mente Abierta (nivel 7), Invocar Aliado (8), Visión Cósmica (9), Avatar del Sueño (10).

### 8. Mejoras en la interfaz
- El HUD muestra ahora la fase lunar y el ciclo día/noche.
- En combate, se muestran los aliados y sus vidas.
- Pantalla de ayuda actualizada con las nuevas características.
- Coordenadas más flexibles para adaptarse a terminales pequeñas.

---

## 🎮 Impacto en la jugabilidad

- La **cordura** se convierte en un recurso crítico que el jugador debe gestionar mediante descanso, objetos y habilidades.
- Los **sueños** añaden una capa de misterio y recompensa por explorar.
- Las **fases lunares** crean un mundo vivo y cambiante.
- Los **aliados** ofrecen nuevas estrategias en combate.
- Los **múltiples finales** incentivan la rejugabilidad y las decisiones significativas.

---

## 📦 Resumen técnico

- Se añadieron nuevas clases (`DreamEvent`, `Ally`) y se ampliaron las existentes (`Player`, `Enemy`, `Item`, `Combat`).
- Se actualizó el sistema de guardado para incluir los nuevos atributos.
- Se mejoró el manejo de señales (SIGWINCH) y la robustez general.
- Se eliminaron restos del sistema de peso no utilizado.

---

**KADATH 0.3** no solo corrige errores, sino que expande el juego hacia una dirección lovecraftiana auténtica, donde la mente del soñador es frágil y los dioses antiguos observan desde las sombras. ¡Que los sueños te guíen!

                                    DEFINITIVA v1.0

KADATH – Registro de cambios (Changelog)
[1.0] – 2024 – Edición Definitiva
Consolidación y equilibrio final
Sueños ajustados: Probabilidades equilibradas (8% explorar, 15% descansar) para que sean especiales sin saturar.

Interfaz pulida: Se muestra "v1.0 - Edición Definitiva" en el menú principal.

Código optimizado: Eliminado el estado GS.SUEÑO no utilizado; máquina de estados simplificada.

Guardado robusto: Todos los atributos (aliados, conocimiento, sellos lunares) se guardan y restauran correctamente.

Estabilidad mejorada: Manejo de señales y comprobaciones de límites en interfaz.

Documentación completa: Comentarios y estructura preparados para mantenimiento.

[0.3] – Expansión Lovecraft
Nuevos sistemas de juego
Sistema de cordura: Cada enemigo tiene cordura_dano; pérdida de cordura al inicio del combate.

Resistencia a cordura: Nuevo atributo bonus_resist_cordura (obtenible vía mejoras/habilidades).

Eventos oníricos (sueños):

Proféticos (pistas sobre Kadath/sellos lunares)

Pesadillas (pérdida de cordura)

Reveladores (muestran objetos ocultos)

Encuentros (aliados/objetos)

Fases lunares: Ciclo de 4 fases que afecta encuentros y sueños.

Aliados en combate: Gatos oníricos y otras criaturas luchan junto al jugador.

Bestiario: Nueva pantalla con registro de criaturas encontradas.

Múltiples finales: Dependen de cordura, decisiones, sellos lunares (0-3) y alianzas.

Contenido expandido:

5 nuevas misiones (q04, q05) con facciones

Nuevos enemigos: Shantak, Ghoul Antiguo, Gnophkeh, Nyarlathotep (visión)

Nuevas armas/armaduras: Hoja Lunar, Báculo de Nodens, Túnica Sonámbula

Habilidades hasta nivel 10 (Mente Abierta, Invocar Aliado, Visión Cósmica, Avatar del Sueño)

Mejoras en interfaz: Muestra fase lunar, aliados en combate, HUD optimizado.

[0.2] – Correcciones y robustez
Parche de estabilidad
Coste de resurrección: Corregido el cálculo (usa int(zona.split('_')[1])).

Equipamiento seguro: Verifica espacio en inventario antes de cambiar equipo.

Misión q02: Ahora se activa correctamente al hablar con el Zoog.

Rotura de armas: Implementada (arma se convierte a puños al llegar a durabilidad 0).

Victoria en Kadath: El juego termina al llegar a zona_10.

Selección de consumibles en combate: Submenú para elegir qué objeto usar.

Manejo de SIGWINCH: Señal gestionada mediante bandera segura.

Coordenadas flexibles: Adaptación a terminales pequeñas en todas las pantallas.

Importaciones optimizadas: import copy movido al inicio del archivo.

[0.1] – Versión inicial
Lanzamiento base
Motor TUI con curses y colores.

Sistema de combate por turnos básico.

Inventario con equipamiento de armas/armaduras.

Misiones simples (q01, q02, q03).

10 zonas explorables con conexiones.

Sistema de guardado en JSON.

Ciclo día/noche.

Subida de nivel hasta 7 con habilidades.

KADATH v1.0 representa la culminación de todas estas mejoras, ofreciendo una experiencia lovecraftiana profunda, estable y completamente jugable en terminal.

# 🌙 KADATH v3.0 — La Búsqueda Onírica

> *"No todos los que vagan están perdidos... algunos buscan Kadath."*

**Versión:** 3.0  
**Autor:** Molvic Studio © 2024  
**Licencia:** Basado en H.P. Lovecraft (Dominio Público)  
**Motor:** Python + curses (stdlib)  
**Formato:** Single-file (~1800 líneas)

---

## 🎯 ¿Qué es KADATH?

Juego de rol textual inspirado en *"La Búsqueda Onírica de la Desconocida Kadath"* de H.P. Lovecraft. Explora las Tierras del Sueño, gestiona tu cordura y alcanza la ciudad prohibida.

---

## 🎮 Características Principales

| Sistema | Descripción |
|---------|-------------|
| **Exploración** | 10 zonas únicas (Ulthar, Celephaïs, Leng, Kadath...) |
| **Combate** | Por turnos con armas, armaduras y conjuros |
| **Cordura** | Mecánica lovecraftiana (baja cordura = finales alternativos) |
| **Quests** | 3 misiones principales con decisiones permanentes |
| **Inventario** | 12 slots, equipamiento, consumibles |
| **Progresión** | 7 niveles con habilidades y mejoras |
| **Guardado** | 4 slots automáticos + manuales |
| **Finales** | Múltiples según decisiones y cordura |

---

## 🗺️ Zonas Disponibles

| # | Zona | Tipo | Peligro |
|---|------|------|---------|
| 1 | Ulthar | Ciudad | 🟢 Seguro |
| 2 | Bosque Zoog | Bosque | 🟡 Medio |
| 3 | Dylath-Leen | Puerto | 🟢 Seguro |
| 4 | Montañas del Humo | Montaña | 🔴 Alto |
| 5 | Catacumbas Zak | Mazmorra | 🔴 Alto |
| 6 | Celephaïs | Ciudad | 🟢 Seguro |
| 7 | Mar Oriab | Mar | 🟡 Medio |
| 8 | Inquanok | Ciudad | 🔴 Alto |
| 9 | Meseta Leng | Tierra Prohibida | 🔴 Muy Alto |
| 10 | Kadath | Destino Final | ❓ Desconocido |

---

## ⚔️ Sistema de Juego

### Estadísticas del Jugador
- **Vida** — Muerte si llega a 0
- **Cordura** — Locura si llega a 0 (final alternativo)
- **Voluntad** — Necesaria para conjuros
- **Oro** — Compra en tiendas
- **Nivel** — Máximo 7, con habilidades únicas

### Combate
- Por turnos con menú de acciones
- Opciones: Atacar, Usar Objeto, Esquivar, Huir, Conjuro
- Daño calculado con arma, nivel y defensa enemiga
- Loot aleatorio tras victoria

### Decisiones Clave
- **El Gatito Onírico** — ¿Devolver a los gatos o dar a los Zoog?
- Afecta aliados, reputación y final del juego

---

## 🏆 Logros

| ID | Nombre | Requisito |
|----|--------|-----------|
| logro_01 | Primer Sangre | Derrota tu primer enemigo |
| logro_03 | Rico Soñador | Consigue 500 oro |
| logro_04 | Cordura Frágil | Llega a zona 7 con cordura ≥ 90 |

---

## 🛠️ Requisitos Técnicos

| Requisito | Detalle |
|-----------|---------|
| **Python** | 3.7+ |
| **Dependencias** | Ninguna (stdlib) |
| **Sistema** | Linux, macOS, Windows (con `windows-curses`) |
| **Terminal** | Con soporte curses y colores |

### Instalación

```bash
# Linux/macOS
python3 main.py

# Windows
pip install windows-curses
python main.py
