# TDD: Human in the Loop

Flujo de trabajo TDD con supervisión humana en puntos clave.

**Objetivo:** Permitir al humano validar el trabajo de la IA antes de avanzar en el ciclo.

---

## Flujo por Ciclo

```
┌─────────────────────────────────────────────────────────────┐
│  1. IA escribe test                                         │
│  2. IA ejecuta test → RED (falla)                           │
│  3. 🛑 REVISIÓN HUMANA #1: ¿El test es correcto?            │
│     └─ Humano aprueba o pide cambios                        │
│  4. IA implementa código mínimo                             │
│  5. IA ejecuta test → GREEN (pasa)                          │
│  6. 🛑 REVISIÓN HUMANA #2: ¿La implementación es correcta?  │
│     └─ Humano aprueba o pide cambios                        │
│  7. Siguiente ciclo o refactor                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Puntos de Revisión

### Revisión #1 — Después de RED

La IA presenta el test fallido. El humano valida:

- ¿El test describe el comportamiento correcto?
- ¿Usa la interfaz pública adecuada?
- ¿El nombre del test es claro?

**Acción:** Aprobar para continuar o solicitar ajustes.

### Revisión #2 — Después de GREEN

La IA presenta la implementación que pasa el test. El humano valida:

- ¿El código es mínimo y correcto?
- ¿No hay over-engineering?
- ¿Cumple con los estándares del proyecto?

**Acción:** Aprobar para siguiente ciclo/refactor o solicitar ajustes.

---

## Reglas

1. La IA **no avanza** sin aprobación humana en cada punto de revisión.
2. Si el humano rechaza, la IA ajusta y vuelve a presentar.
3. El refactor se realiza después de completar los ciclos acordados.

