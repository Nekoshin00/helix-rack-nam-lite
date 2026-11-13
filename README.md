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

### Capturas ligeras: preparación

El conversor admite `--layers` para guardar el número de capas activas en
el WAV, siguiendo el formato de [helix-lt-nam](https://github.com/andreidevs/helix-lt-nam).
La captura debe estar entrenada
previamente como A2 Lite ligero; esta opción no la entrena ni la modifica.
El firmware actual **todavía procesa las 23 capas**, así que esto no reduce
su carga DSP. Instalé una imagen completa experimental con kernel,
modelos y tablas de interfaz en mi Rack y las pruebas funcionaron. La
estabilidad prolongada y la carga DSP real siguen sin verificarse.
Los cuatro modelos usan provisionalmente el coste 3600 del
build anterior; no está calibrado en Rack ni garantiza seguridad o ahorro
real de DSP. El build normal no permite activar esta opción.

```powershell
.\.venv\Scripts\python.exe tools\nam2ir.py "C:\ruta\captura-ligera.nam" -o "C:\ruta\captura-ligera.wav" --layers
```

## Pruebas

El build ejecuta las pruebas del kernel, de los guards ARM y del título IR.
Las dos últimas también pueden ejecutarse individualmente:

```powershell
.\.venv\Scripts\python.exe helix-rack\rack\test_arm_guards.py
.\.venv\Scripts\python.exe helix-rack\rack\test_ir_title.py
```

Para probar el kernel experimental de capas en el simulador, sin generar
firmware instalable:

```powershell
.\.venv\Scripts\python.exe tests\check_light_kernel.py
.\.venv\Scripts\python.exe tests\check_light_transitions.py
.\.venv\Scripts\python.exe tests\check_light_dma_abort.py
.\.venv\Scripts\python.exe tests\check_light_memory.py
.\.venv\Scripts\python.exe tests\check_light_limit_changes.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_light*.py"
```

El simulador compara el audio con la referencia y comprueba límites de capas;
no mide el tiempo real de DSP ni demuestra estabilidad en el Rack.
Para comprobar tablas, navegador, títulos y límites de una imagen L6IA
experimental ya ensamblada offline, se puede ejecutar
`python tests\check_light_ui.py "C:\ruta\imagen.l6ia"`. No genera un HXF.

### Primera prueba en Rack para capturas ligeras

La primera imagen de prueba solo amplía la memoria `seg0`; por lo demás usa
el firmware original. **No contiene ningún bloque NAM**, tampoco el que ya
funciona en el build normal. No sirve para probar capturas ni ahorro de DSP.
Modificar firmware puede impedir el arranque.

Antes de probarla, respalda los presets y User IR, deja seleccionado un
preset sin NAM y confirma que puedes recuperar el Rack. No cargues ni guardes
presets con NAM mientras uses esta imagen: el firmware original no conoce esos
bloques y podría eliminarlos. Conserva el firmware original y el build NAM
probado para reinstalarlos si hace falta.

Para generarla sin modificar el build normal:

```powershell
.\.venv\Scripts\python.exe helix-rack\rack\build_light_stage1.py "C:\ruta\Helix_Rack_v3.80.0_0x7d01f5efb.hxf"
```

La salida es `helix-rack\build\Rack_light_test1_seg0_only.hxf`. El generador
no sobrescribe archivos existentes. Tras instalarla con Line 6 Updater en
modo offline, comprueba el arranque, el audio y el cambio entre presets sin
NAM. La imagen no verifica la interfaz ni el kernel de capturas ligeras.

## Créditos y licencia

Derivado de [helix-floor-nam-lite](https://github.com/savedadodo/helix-floor-nam-lite)
y [hx-stomp-nam-lite](https://github.com/nocaseguy/hx-stomp-nam-lite).
La implementación experimental de capas está adaptada de
[helix-lt-nam](https://github.com/andreidevs/helix-lt-nam).
Neural Amp Modeler es un proyecto de
[Steven Atkinson](https://github.com/sdatkinson/neural-amp-modeler).
El código conserva la licencia y los avisos de los proyectos originales:
consulta [LICENSE](LICENSE) y [NOTICE](NOTICE).
