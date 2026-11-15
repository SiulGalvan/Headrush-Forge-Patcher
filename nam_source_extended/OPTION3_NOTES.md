# Opción 3: carga diferida ("modelo actual primero, resto en segundo plano")

Cambios en `nam_hook.cpp` (SIN COMPILAR PARA ARM NI PROBAR EN HARDWARE; solo
comprobada la sintaxis en x86 con `g++ -fsyntax-only`):

- El preload ya solo LISTA y ordena los `.nam` (recorrido de directorio) y
  publica `g_models_ready` enseguida. Antes parseaba y construía de prueba TODOS.
- `ensure_loaded(idx)`: parsea + construye de prueba un archivo bajo demanda.
- `switch_model_in_background` carga primero el modelo de la perilla; después
  lanza una sola vez `fill_remaining_models_in_background()` (prioridad idle,
  20 ms entre archivos) que carga el resto.
- Archivo corrupto = ranura muerta (silencio); los índices ya NO se desplazan.
  Esto coincide con el mapeo archivo<->% del Block Manager.
- Las llamadas del hilo de audio solo usan `g_cached_models.size()` (el vector
  se construye una vez antes de publicar `g_models_ready`).

Hay que recompilar los blobs con tu cadena (Bootlin). Si el arranque falla,
vuelve a la versión anterior (`nam_hook.cpp.orig` / blob previo).
