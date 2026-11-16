# HeadRush — Forge Patch Mod
_Antiguamente MX5 Compatibility Layer_

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Platform: HeadRush](https://img.shields.io/badge/HEADRUSH-MX5%20%7C%20PEDALBOARD-red)](#)
[![NAM Core](https://img.shields.io/badge/Engine-Neural%20Amp%20Modeler-green.svg)](https://github.com/sdatkinson/NeuralAmpModelerCore)
[![Release: v2.7 Extended](https://img.shields.io/badge/Release-v1.0%20Galvanized-success.svg)]()

Capa de compatibilidad entre modificaciones avanzadas de firmware para **HeadRush MX5** Y **Pedalboard** en la version de **Firmware 2.7**, que integra nativamente [Neural Amp Modeler (NAM)](https://github.com/sdatkinson/NeuralAmpModelerCore) directamente en el motor de audio en tiempo real (`/usr/Evil/Evil`). El mismo se integra tambien con accesibilidad MIDI avanzada via usb y puerto midi para poder manejar el equipo desde Windows o Mac mediante una version modificada de [MX5-BRIDGE y MX-EDIT](https://github.com/TicT4x/MX-Edit).

Asi también, se integra un mod para mostrar el arte de los pedales directo en el editor de pantalla como fue mostrado en el material promocional, esto esta basado en el repositorio de [GIGBOARD_NAM_PNG](https://github.com/iosumurillo/GIGBOARD_NAM_AMP_PNG) y optimizado con mejoras propias para no impactar en el rendimiento.

### ¿Cómo descargar el parche? (Releases)

Para instalar el mod en tu pedalera, existen 2 vias de sin necesidad de compilar código fuente:

| Archivo | Descripción | Descarga Directa |
| :--- | :--- | :--- |
| **Firmware Updater (NAM A2 + BRIDGE + ARTMOD)** | Flasheador automático para HeadRush MX5 ya parchado con soporte Dual NAM + MX-EDIT + ARTMOD | [Descargar .exe]
| **Forge Patcher** | Constructor de update.img para parchar modularmente la instalación y elegir que componentes integrar | [Descargar .exe] |

> **Release Actual**: [v1.0]

> **Guía técnica y manual de usuario detallado**: [GUIA DE MODULOS "WIP"](GUIA_1.0.md)

---

## Características Principales

- **Doble Bloque NAM en Cadena**:
  - **Pedal Anxiety OD (NAM)** (y Anxiety OD V2): Inferencia transparente como pedal de saturación/overdrive con controles de Input Trim, Level y selector de modelo.
- **Gráficos Integrados en Pantalla Táctil**:
  - Gráficos integrados en los recursos QML/RCC de HeadRush con soporte de NAM PEDAL y arte de la 2da generación para los pedales tipo Rack
- **MXBRIDGE-lite(NUEVO EN V1)**:
  - Herramienta que permite enviar y recibir señales MIDI desde un ordenador hacia la pedalera y viceversa, pilar para el funcionamiento de MXEDIT, a su vez para evitar sobrecargar del USB, desactiva MIDI USB al activar USB-AUDIO y lo reactiva al desactivar USB-AUDIO. Esto soluciona problemas de ralentización del equipo al usarlo como placa de audio
-  **NAM EXTENDED V2(NUEVO EN V1)**: Modificación de los hilos del modulo NAM y su lógica de lectura para mejorar la carga de los archivos y reducir los artefactos. A su vez, realiza una carga diferida para reducir considerablemente el silencio al cambiar entre NAM en un mismo rig.
- **NAM EXTENDED AMP (NUEVO EN V1)**: Secuestro del modelo LEAD 800 BRIGHT para integrar controles de EQ y X2AMP con el uso de NAM, no utilizar junto a NAM de 4 instancias, ya que cargar 6 modulos NAM va a sobrecargar el sistema y puede forzar a tener que realizar un reseteo de Fabrica para salir del bucle de crasheo en arranque.

---

## Mapeo de Controles

### Bloque Pedal: Anxiety OD (NAM)

| Control | Rango | Función Técnica |
| :--- | :--- | :--- |
| **Tone** | 0% – 100% | **Input Trim**: 50% = Ganancia Unitaria (0.0 dB). 0% = Mute, 100% = +12 dB. |
| **Drive** | 0% – 100% | **Selector de Modelo NAM**: Selecciona el archivo `.nam` correspondiente del pendrive USB (`0%` = Archivo 0, `100%` = Archivo 100). |
| **Level** | 0% – 100% | **Output Trim**: 50% = Salida Unitaria (0.0 dB). 0% = Mute, 100% = +12 dB. |
| **On/Off**| Bypass | Paso en seco directo (*dry passthrough*). |

### Bloque Amplificador: 82 LEAD 800 (NAM)

| Página | Control | Rango | Función Técnica |
| :--- | :--- | :--- | :--- |
| **Pág 1** | **Gain** | 0% – 100% | Ganancia de entrada previa a la red neuronal (50% = 0 dB). |
| **Pág 1** | **Presence** | 0% – 100% | Filtro High-Shelf activo en 6 kHz ($\pm 10\text{ dB}$, 50% = plano). |
| **Pág 1** | **Master** | 0% – 100% | Nivel de salida general post-inferencia y EQ (50% = 0 dB). |
| **Pág 2** | **Bass** | 0% – 100% | Filtro Low-Shelf centrado en 100 Hz ($\pm 12\text{ dB}$, 50% = plano). |
| **Pág 2** | **Mid** | 0% – 100% | Filtro Peaking en 750 Hz, $Q=1.0$ ($\pm 12\text{ dB}$, 50% = plano). |
| **Pág 2** | **Treble** | 0% – 100% | Filtro High-Shelf en 3.5 kHz ($\pm 12\text{ dB}$, 50% = plano). |
| **Pág 3** | **Depth** | 0% – 100% | **Selector de Modelo NAM**: Mapeo 1:1 exacto alfabético de perfiles USB. |
| **Pág 3** | **Bright** | OFF / ON | **Filtro Tight HPF (150 Hz)**: Elimina graves fangosos antes de la distorsión. |

---

## Via de instalacion
**Instalación Rápida**
1. Conecta tu HeadRush MX5 o Pedalboard mediante USB a la PC mediante.
2. En la pedalera, entra en **Global Settings -> Firmware Update**.
3. Ejecuta `Firmware Updater (NAM A2 + BRIDGE + ARTMOD).exe` tras descargarlo de la carpeta /release o descargarlo directamente desde Releases.
4. Sigue los pasos en pantalla hasta que la pedalera complete el flasheo y reinicie.

**Instalación Personalizada**

1. Descarga `Headrush Forge Patcher v1.exe` o compilalo con `build_windows.bat` (Requieres de Phyton para ello)
2. Seleccionas que partes de los modulos necesitas, si integras el mod de arte, deberas conseguir por tus propios medios las imagenes de los modulos rack ya que no forman parte de update.img, por lo que deberas seleccionar una carpeta con estas imagenes dentro del parcheador en la opción "Your rack module art". Caso contrario, los pedales tipo rack como DYNIII Compressor saldran con las graficas originales (cuadros de colores)
4. Elegir en que directorio se creara la carpeta del nuevo firmware
5. Presionar `Build Updater`
6. Realizar lo mismo que la instalación rapida

---
## Funciones experimentales (Completado)
_Todas las funciones experimentales han sido testeadas y se confirmo su correcto funcionamiento en los dispostivitos tanto MX5 como Pedalboard. Por lo tanto, forman parte de la v1. Proximamente se añadira una nueva lista de funciones experimentales para añadir nuevas caractetisticas_
---

## Recuperación y Seguridad

El mod preserva la estructura de actualización oficial de HeadRush. Para restaurar el firmware original de fábrica en cualquier momento:
1. Pon la MX5 en modo actualización de firmware presionando los footswitch 1+2 al prender el equipo.
2. Ejecuta el actualizador oficial de HeadRush Firmware 2.7.
3. Restaurar la imagen original del sistema.

---

## DESCARGO DE RESPONSABILIDAD

Al instalar esta modificación, aceptas que lo haces bajo tu propia responsabilidad. Por lo tanto, no me responsabilizo por posibles daños, incluidos daños permanentes, que pudieran ocasionarse en los dispositivos como consecuencia de su instalación o utilización.

Esta modificación no es un desarrollo completamente original ni un producto creado íntegramente por mí. Se trata de una capa de compatibilidad e integración entre modificaciones y proyectos preexistentes, cuyos respectivos autores y repositorios originales se detallan a continuación:

**1. NAM MOD**
- Autor: Lorenzo Gabriele
- Repositorio: https://github.com/lolgab/headrush-nam-mod/tree/main

**2. NAM EXTENDED**
- Autor: Josu Murillo
- Repositorio: https://github.com/iosumurillo/GIGBOARD_NAM_AMP_PNG
- Nota: Por el momento, de este proyecto únicamente se ha integrado la funcionalidad relacionada con la visualización del arte de los pedales.

**3. MX5 BRIDGE**
- Autor: TicT4x
- Repositorio: https://github.com/TicT4x/MX-Edit

Se reconoce y agradece el trabajo de los desarrolladores originales, cuyos proyectos hicieron posible esta integración.

Agradecimiento especial a George Mavimbela quien aporto los iconos de los pedales rack de la pedalera HR PRIME

## Licencia

- El código del mod y los hooks de integración están bajo la licencia [GPL v3](LICENSE).
- NeuralAmpModelerCore está bajo la licencia [MIT](https://github.com/sdatkinson/NeuralAmpModelerCore/blob/main/LICENSE).
- Las marcas HeadRush, Gigboard, MX5 y Pedalboard son marcas registradas de inMusic Brands, Inc. Este proyecto es una modificación comunitaria independiente y de código abierto sin afiliación con inMusic Brands.
