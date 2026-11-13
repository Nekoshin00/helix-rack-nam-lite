# NAM A2 Lite para Helix Rack

Este proyecto adapta [helix-floor-nam-lite](https://github.com/savedadodo/helix-floor-nam-lite)
para **Helix Rack 3.80.0**. Permite generar localmente un firmware modificado
a partir del firmware original y convertir capturas NAM A2 Lite a archivos
WAV para cargarlas en espacios User IR.

> **Proyecto experimental y no oficial.** No tiene afiliación ni soporte de
> Line 6 o Yamaha Guitar Group. Modificar el firmware implica riesgos,
> incluido que el equipo no arranque. Haz un respaldo y confirma el
> procedimiento oficial de recuperación de tu Rack antes de instalarlo.

## Estado

Instalé el firmware completo en mi Rack y probé el audio NAM: funciona.
También instalé las cuatro imágenes de prueba: los presets sonaron en las
primeras tres y la opción NAM apareció en la cuarta.

La **estabilidad prolongada** del firmware en el Rack sigue pendiente de
validar. La carga de DSP y la cantidad de bloques NAM que se pueden usar
también están pendientes de validar. Dejé el detalle de las pruebas y los
riesgos en [STATUS.md](STATUS.md).

Los archivos `nam_rack*.py` son las variantes del kernel adaptadas desde el
proyecto de Floor; el build completo utiliza `nam_rack5.py`.

## Requisitos

- Python 3.10 o posterior.
- Los paquetes de [requirements.txt](requirements.txt).
- Tu propio firmware original Helix Rack 3.80.0
  (`Helix_Rack_v3.80.0_0x7d01f5efb.hxf`, MD5
  `4ef2fdf2e5a45e80ccf3ccdf23cf017d`).

El repositorio **no incluye firmware de Line 6 ni capturas NAM**. No
compartas el firmware original, los archivos intermedios ni el firmware
modificado. `.gitignore` excluye sus extensiones habituales, pero conviene
revisar el contenido antes de publicar cualquier archivo.

## Compilar en Windows

En PowerShell, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe build.py "C:\ruta\Helix_Rack_v3.80.0_0x7d01f5efb.hxf"
```

Reemplaza la ruta por la ubicación de tu firmware original. El resultado se
genera en `helix-rack\build\Helix_Rack_v3.80.0_NAM2_PERSONAL.hxf`. El build
verifica el firmware de entrada, ejecuta las etapas y pruebas simuladas, y
valida la integridad del firmware modificado antes de empaquetarlo. Estas
pruebas no garantizan su funcionamiento ni seguridad en hardware. Para elegir
otra salida, agrega `-o "C:\ruta\salida.hxf"`.

## Convertir capturas

Solo son compatibles modelos **WaveNet NAM A2 Lite de 3 canales**, incluidos
los contenedores SlimmableContainer que los incorporen:

```powershell
.\.venv\Scripts\python.exe tools\nam2ir.py "C:\ruta\captura.nam" -o "C:\ruta\captura.wav"
```

Importa el WAV en un espacio libre de **User IR** con HX Edit. En el Rack
agrega **Amp > NAM > NAM A2 Lite** y ajusta **Model** al número de ese
espacio. El WAV transporta datos del modelo; no es una respuesta a impulso
normal. Empieza con un preset sencillo y volumen bajo.

HX Edit puede eliminar bloques NAM al reescribir presets: crea y edita el
preset en el Rack. El ajuste automático de nivel se basa en una referencia
del HX Stomp que no se ha calibrado para Rack.

## Pruebas

El build ejecuta las pruebas del kernel, de los guards ARM y del título IR.
Las dos últimas también pueden ejecutarse individualmente:

```powershell
.\.venv\Scripts\python.exe helix-rack\rack\test_arm_guards.py
.\.venv\Scripts\python.exe helix-rack\rack\test_ir_title.py
```

## Créditos y licencia

Derivado de [helix-floor-nam-lite](https://github.com/savedadodo/helix-floor-nam-lite)
y [hx-stomp-nam-lite](https://github.com/nocaseguy/hx-stomp-nam-lite).
Neural Amp Modeler es un proyecto de
[Steven Atkinson](https://github.com/sdatkinson/neural-amp-modeler).
El código conserva la licencia y los avisos de los proyectos originales:
consulta [LICENSE](LICENSE) y [NOTICE](NOTICE).
