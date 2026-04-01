# MySkills - Listado de tareas pendientes

## 1. `myskills list` cuando una skill instalada necesita actualizarse

Si la versión de la skill en el repositorio no coincide con la actual, el comando `myskills list` en vez de 
indicar que la skills está `[✓ installed]` debería indicar que necesita actualizarse

## 2. Re-generar la caché local

En algunas ocasiones puede ocurrir que la caché local del repositorio se quede inconsisntete. Deberíamos
tener algún comando que la re-genere, es decir, la borre y se vuelva a clonar el repositorio fresco.

## 3. Detectar inconsistencias en el caché local durante `myskills list`

**Problema**: Cuando el caché local del repositorio (`~/.cache/myskills/repo/`) tiene commits que no existen en el repositorio remoto, `myskills list` muestra skills que en realidad no están disponibles en el repositorio compartido.

**Ejemplo real**: Si un `myskills import` falla al hacer push, la skill queda solo en el caché local pero aparece en `list` como si estuviera disponible en el repositorio.

**Solución esperada**: El comando `list` debe detectar cuando el caché local está desincronizado con el remoto y advertir al usuario sobre esta inconsistencia, indicando cómo resolverla.

## 4. Revertir cambios automáticamente cuando `myskills import` falla al publicar

**Problema**: Si `myskills import` falla durante la publicación al repositorio remoto (después de haber copiado archivos y creado el commit local), el caché local queda en estado inconsistente: contiene una skill que no existe en el repositorio remoto.

**Consecuencia**: El usuario ve la skill en `myskills list` pero otros colaboradores no la ven. La skill aparece como "disponible" solo localmente.

**Solución esperada**: Cuando el push falla, el comando debe deshacer automáticamente todos los cambios realizados (commit y archivos copiados), dejando el caché en el mismo estado que tenía antes de ejecutar el import. El usuario debe recibir un mensaje claro indicando que el import falló y que los cambios fueron revertidos.