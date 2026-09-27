# AGENTS.md

Instrucciones para cualquier agente de código (Claude Code, Copilot, etc.)
que trabaje en este repositorio.

## Proyecto

Sistema de pedidos para un restaurante de un solo local: backend Django
(API REST + Django Channels) y frontend Next.js (panel de administración +
PWA de meseros), con SQLite, pensado para operar 100% en la red WiFi local
del restaurante sin depender de internet.

## Estructura del monorepo

- `/backend` → Django + DRF + Django Channels + SQLite.
- `/frontend` → Next.js (un solo proyecto; rutas para el panel admin y rutas
  para la PWA del mesero).
- `/docs` → documentación del proyecto (incluye `docs/constitution.md`).
- `/specs` → especificaciones por funcionalidad (spec-driven development).

## Instalar y levantar en local

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

## Correr los tests

- Backend: `cd backend && python manage.py test`
- Frontend: `cd frontend && npm test`

## Convenciones de nombres

- Código (variables, funciones, clases, archivos de código): en inglés.
- Backend: `snake_case` para archivos, módulos y funciones (estilo Django).
- Frontend: `kebab-case` para archivos/carpetas, `PascalCase` para componentes.
- Specs en `/specs`: un archivo por funcionalidad, nombrado
  `NNN-nombre-funcionalidad.md`.

## Convención de commits

Mensajes de commit en español, en modo imperativo, con prefijo de tipo:
`feat: agregar endpoint de anulación de pedido`
Tipos válidos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

## Regla obligatoria

**Toda tarea debe respetar `docs/constitution.md`.** Si una tarea entra en
conflicto con alguna regla de la constitución, el agente debe detenerse y
preguntar antes de continuar, en vez de ignorarla o justificar una excepción.
