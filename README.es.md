# HeadRush MX5 Forge

Crea en tu propio ordenador un instalador parcheado para el **HeadRush MX5 (firmware 2.7)**:

* descarga el actualizador oficial de inMusic (o usa un archivo que ya tengas),
* aplica el **NAM mod** (Neural Amp Modeler en el pedal Anxiety OD) con **2 o 4 instancias**,
* añade el **MX5 Bridge** (el puente USB-MIDI que usa MX-Edit),
* aplica opcionalmente el **diseño de pedales** (arte del pedal NAM e imágenes de pedal en la cadena), **solo en la versión de 4 instancias**,
* deja una carpeta con `FirmwareUpdater` lista para ejecutar.

> No oficial. Flashear firmware modificado puede dejar el equipo inservible. Recuperación: mantén pulsados los footswitches 1 + 2 al encender y flashea el actualizador oficial. Úsalo bajo tu responsabilidad.

## Modos

| | 2 instancias | 4 instancias |
|---|---|---|
| Anxiety OD | pedal NAM | pedal NAM |
| Anxiety OD V2 | sin tocar | pedal NAM (pierde su sonido original) |
| Imágenes de pedales | **originales** | **diseño de pedales** opcional |
| MX5 Bridge | opcional | opcional |

## Uso

```bash
pip install -r requirements.txt          # Pillow (la interfaz necesita tkinter)
python -m mx5forge                       # interfaz gráfica
python -m mx5forge --instances 4 --design --rack-art ./mis_racks --out ./salida
python -m mx5forge --instances 2 --no-bridge --input FirmwareUpdater_MX5.zip
```

Después ejecuta `FirmwareUpdater.exe` desde la carpeta de salida (si la herramienta indica que faltan `FirmwareUpdater.exe`,
`libusb-1.0.dll` o `Background.png`, cópialos del actualizador oficial) y pulsa el botón de instalar.

Para el diseño con tus propias imágenes de módulos tipo rack, mira `mx5forge/art/rack_art/README.md`.
Nada de HeadRush se incluye en el repositorio: la herramienta lee todo del actualizador oficial en tu ordenador.

## Qué está probado

* El parche NAM en Python reproduce byte a byte el binario Evil, las librerías y los scripts de una imagen MX5 real de 2 instancias hecha con el nam-mod original y MX-Edit (imagen que funciona en el equipo).
* El proceso completo se ejecutó sin conexión sobre una imagen equivalente a la original con 2 instancias + Bridge y con 4 instancias + Bridge + diseño.
* El diseño (QML + imágenes) corresponde a versiones probadas en un MX5 real.

**No probado:** la descarga en línea, la interfaz gráfica (requiere tkinter) y, en el equipo, la combinación de **4 instancias con Anxiety OD V2 secuestrado y el diseño de pedales**. Se agradece que reportes resultados.

Licencias y orígenes: [THIRD_PARTY.md](THIRD_PARTY.md). El proyecto es GPL-3.0 porque incluye código portado del nam-mod.
