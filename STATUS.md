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
