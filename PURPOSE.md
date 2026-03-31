# MySkills - propósito

Quiero crear una utilidad para instalar skills.

Quiero que esta utilidad funcione igual que lo hace (skills.sh)[https://skills.sh/]. Es decir

- Exisitirá un repositorio de skills, pero en este caso será un repositorio privado 
- Existirá una herramienta que nos permitirá instalar instalar skills `./myskills add ....`.
    - Esta heramienta se debe comportar igual que el comando `npx skills ...` que se usa en *skills.sh*
    - Esta herramienta debe ser un auto-ejecutable, no quiero que se llame a través de `npx`.

## Funcionalidades esperadas de la herramienta

- Importar una de las skills que haya en un proyecto al repositorio de skills
- Listar las skills del repositorio
- Instalar una skill en un proyecto. Replicar el funcionamiento de `npx skills add ...`.
    - Debe mostrar una lista de agentes de IA soportados y debe permitir elegir con qué agentes se quiere usar.
    - Debe instalar la skill en el directorio más estándar (p.ej en `.agents/skills/<nombre_skill>`) y el resto de instalaciones (como `.claude/skills/<nombre_skill>`) deben ser enlaces simbólicos
- Desinstalar una skill en un proyecto, debe desinstalarse de todos los agentes que la están usando
- Comprobar si hay actualizaciones de las skills instaladas en el proyecto y actualizarlas
- Desinstalar una determinada skill del proyecto