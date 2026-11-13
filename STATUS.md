# Estado del port a Helix Rack

**Instalé el build completo y probé el audio NAM en mi Rack: funciona.**
También instalé las cuatro imágenes parciales y el Rack arrancó con cada una.
La estabilidad prolongada sigue pendiente de validar.

```
python build.py ..\Helix_Rack_v3.80.0_0x7d01f5efb.hxf
```
Genera `helix-rack/build/Helix_Rack_v3.80.0_NAM2_PERSONAL.hxf` (47.521.138 B). Pasos: unpack -> stage_slots2 ->
stage_model -> stage_kernel (KernelCheck bit-exacto) -> stage_main -> `l6ia_verify` (ALL OK) ->
test_arm_guards (PASS) -> test_ir_title (PASS) -> pack. Comprueba el MD5 del stock (`4ef2fdf2...`).

## Pruebas por etapas (método del Floor)
El script `python helix-rack\rack\build_staged.py <stock.hxf>` genera las pruebas 1 y 2c
después de ejecutar el build completo. Las pruebas 3 y 4 fueron generadas por separado.
Instalar con Line 6 Updater (Offline), una a una, comprobando arranque y presets antes de pasar a la siguiente:
1. `build/test1_seg0_only.hxf` (seg0 +46.536 B de ceros) - resultado: PASÓ (2026-11-12: arranca, presets suenan)
2. `build/test2c_slots.hxf` (stage_slots2 solo) - resultado: PASÓ (2026-11-12:
   después de un fallo inicial del Updater, se instaló y los presets sonaron).
3. `build/test3_model_only.hxf` - PASÓ la prueba básica (2026-11-12:
   funcionó y se escucharon los presets): modelo y memoria, sin kernel NAM ni cambios ARM.
   Parte del stock, no incluye test2c. Checksums y desempacado verificados; solo cambian entradas 2, 4 y 5.
   No añadir ni utilizar el bloque NAM en esta imagen.
4. `build/test4_ui_only.hxf` - PASÓ la prueba básica (2026-11-12: apareció la opción NAM):
   modelo de test3 más parches ARM, sin kernel NAM.
   Solo cambia la entrada 0 respecto a test3; la entrada 0 coincide con la del build completo actual.
   Checksums y desempacado verificados; MD5 `cd49645a15b5866458b049df80a7e88d`.
   No añadir ni usar el bloque NAM. Reutiliza el tamaño de slots stock, no el de test2c.
   El contador ARM ya evita contar dos veces registros solapados; los casos con límite de 16 y
   campos n=13 y n=16 pasan en el intérprete. El valor real de n en el Rack sigue sin verificarse.
   La nueva imagen extiende seg0 12 bytes más que el relleno instalado en test1.
5. `build/Helix_Rack_v3.80.0_NAM2_PERSONAL.hxf` (completo) - INSTALADO (2026-11-12);
   probé el audio NAM y funcionó (2026-11-12). La estabilidad prolongada no se ha validado.
   MD5 `a8c6887f461bff6fbe7ee9bf6fd16334`.
Conozco el procedimiento para entrar en modo actualización y reinstalar el firmware original;
el procedimiento concreto y su funcionamiento no se han verificado en estas pruebas. Conviene
tener el firmware original a mano.

## Adaptaciones al Rack
- Heaps SHARC a/b, DDR2 (+0x400), registro de primitivas (0x200090), tablas ARM, guards, IR-title: ver constantes
  en `helix-rack/rack/*.py`.
- El cave de seg0 (`0x10013058..0x10020000`) es más pequeño que en el Floor: las listas del navegador se
  colocan en la Tabla 1 original (se supone que queda sin uso tras reubicarla, no está demostrado);
  Tablas 1/2 y HOOK quedan en el cave
  (6.612 B libres en el build actual).
- ID de preset NAM: 380; coste DSP 3600; SDRAM 0x5800 (valores medidos en un Floor, no en un Rack).

## Riesgos sin verificar
La prueba de audio NAM no demuestra estabilidad prolongada ni cubre todas las configuraciones.
La prueba 4 valida de forma básica los parches ARM, no todos sus caminos ni su estabilidad.
Sin validar: uso de SRAM y DDR2
en tiempo de ejecución, `IR_TOP` y composite ids del graph library. En una comparación estática,
la dirección `IR_FLAG` y la base de datos IR aparecen en el código original del Rack en posiciones
correspondientes a las del Floor; esto no demuestra que funcionen en ejecución. Se revisaron 457
composites y 862 blobs de modelo del firmware original sin referencias directas a la primitiva
0x128; otros usos siguen sin descartarse. Un firmware mal parcheado puede
no arrancar. La combinación de dos amplificadores y una Cab Dual en un DSP no se considera segura
con la distribución test2c. En Floor también se observaron congelamientos con imágenes NAM; no se
ha establecido si afectan al Rack. No distribuir firmware original ni modificado.

## Revisión offline del kernel (2026-11-12)
- El HXF completo se descomprime al L6IA generado; su código, registro y tablas coinciden
  con el kernel generado con la configuración predeterminada. Se compararon los handlers
  de las primitivas 0x128 y 0x822 con los registros del firmware original del Rack.
- El bloque de instrucciones de arranque de Floor asociado a la configuración PICR coincide
  byte a byte con el del Rack. No demuestra el comportamiento de DMA durante la ejecución.
- No hay datos inicializados por el LDR original en R1 ni en la ubicación nueva del heap 6;
  R2 y R3 están incluidos en bloques de puesta a cero. Esto no demuestra que esas zonas
  estén libres de uso dinámico.
- KernelCheck pasó en el build con umbral de velocidad relajado a 60.000 instrucciones:
  no es una medición de tiempo real del Rack. Pasaron también las pruebas simuladas de DMA
  atascado y recuperación; no prueban el hardware ni los manejadores originales.

## Capturas ligeras (trabajo en curso)
- El conversor puede escribir el número de capas con `--layers`; el firmware instalado
  procesa todas las capas y no obtiene ahorro de DSP.
- El kernel experimental adapta la lógica del LT y se prueba con
  `python tests\check_light_kernel.py`. No está habilitado en el build normal.
- En el simulador, 23, 20, 16 y 14 capas coincidieron con la referencia.
  La media fue de 35.700, 33.008, 29.722 y 27.588 instrucciones simuladas,
  respectivamente; estos valores no miden ciclos ni carga DSP real.
- `tests\check_light_transitions.py` pasó con modelos de distintas capas,
  cambios entre capturas, múltiples instancias, reemplazo de captura y
  recuperación simulada ante DMA bloqueado y canal ocupado. No valida el
  controlador DMA del Rack.
- `tests\check_light_dma_abort.py` comprobó 14 y 23 capas con estado DMA
  ocupado tras la desactivación: liberación tras 5 o 999 sondeos y sin
  liberación. La prueba verifica el aplazamiento de limpieza y la recuperación
  simulada; no reproduce interrupciones ni el controlador original.
- `tests\check_light_memory.py` comprobó los extremos y direcciones vecinas
  de DM y PM con rangos de prueba, y el tamaño mínimo y un tamaño insuficiente
  de SDRAM. La SDRAM insuficiente conserva el comportamiento existente de
  dejar pasar la señal; estas pruebas no verifican la memoria dinámica real.
- `tests\check_light_limit_changes.py` pasó al cambiar o reemplazar una captura
  por otra que excede el límite y después volver a una válida. En la transición
  el simulador produce la cola del modelo anterior y del ecualizador;
  la prueba compara esa salida con la referencia en vez de exigir silencio
  instantáneo.
- La etapa de modelos experimental genera cuatro grafos con límites de
  23, 20, 16 y 14 capas. Sus entradas y límites se revisaron en una imagen
  intermedia offline. Las tablas ARM y el navegador se integraron y verificaron
  offline con IDs de preset 380, 382, 516 y 572; el 380 sigue siendo el del
  modelo original. Los títulos IR se probaron en el intérprete ARM.
- La imagen L6IA experimental completa pasó `l6ia_verify`; Entry 2 conservó
  4.180 bytes de espacio y el cave ARM 6.408 bytes. Esto no demuestra que
  las ubicaciones sean seguras en ejecución real.
- Los cuatro modelos declaran provisionalmente el coste 3600 del build
  anterior. No está medido en Rack ni garantiza que no se sobrecargue el DSP.
- La entrada ARM normal y las variantes 555 se compararon byte a byte con
  la implementación anterior. La entrada ARM normal también coincide con
  la de la imagen instalada.
- El build normal se volvió a generar y coincidió byte a byte con la imagen
  instalada (SHA-256 `bc461c4244fdc0e78caac61a07597f1fff216a9786d6f4a87f7ec23a4d10ec21`).
- En una construcción offline de la etapa DSP, Entry 2 conservó 4.180 bytes de espacio.
  La distribución simulada dejó 5 palabras libres en R1, 5 en R3 y 87 en R2;
  esto no demuestra que esas regiones sean seguras en ejecución real.
- Se generó la primera prueba por etapas, `Rack_light_test1_seg0_only.hxf`:
  aumenta seg0 en 46.752 bytes de ceros; el resto de las entradas conserva el
  firmware original. La imagen no contiene NAM ni el kernel ligero. Integridad
  y contenido verificados offline; **no se ha instalado ni probado en Rack**.
  SHA-256 `0d94d69011b12fb57f45ddc9412efc1f71a9f829f5e12c57537afde9f3cde124`.
  Respaldar presets y User IR antes de instalar; no cargar ni guardar presets
  con NAM mientras esta imagen esté instalada.
- Se generó por separado `Rack_light_full_EXPERIMENTAL.hxf` con las cuatro
  variantes y el kernel ligero, sin modificar el build normal. Pasaron
  KernelCheck, la revisión de la interfaz, las pruebas ARM y `l6ia_verify`;
  el HXF empaquetado se desempaquetó y coincidió con el L6IA verificado.
  SHA-256 `4600f42ca70efe239534f38a5254de8a908890a96cf51a5f8788a221b31fe331`.
  La instalé en el Rack y reporté que todo funciona (2026-11-13). El
  reporte no incluye mediciones de carga DSP ni estabilidad prolongada.
- Faltan pruebas adicionales de fallos y memoria, validación en hardware por
  etapas y la medición del uso real de DSP en Rack.
  Las mediciones y los costes del LT no deben darse por válidos para Rack.
