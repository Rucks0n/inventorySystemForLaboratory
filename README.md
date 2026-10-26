# Sistema de Inventario

Aplicación de escritorio para gestión de inventario, construida con Python + PyQt6 + SQLite.

---

## Requisitos

- Python 3.11 o superior
- pip

---

## Instalación

```bash
# 1. Clonar o descargar el proyecto
# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el sistema
python main.py
```

---

## Usuario por defecto (primera ejecución)

| Campo      | Valor    |
|------------|----------|
| Usuario    | admin    |
| Contraseña | admin123 |

> ⚠️ Cambia la contraseña después del primer ingreso.

---

## Estructura del proyecto

```
sistema_inventario/
├── app/
│   ├── ui/
│   │   ├── importar/       → Asistente para importar inventarios (pantallas)
│   │   └── ...             → Pantallas e interfaces gráficas
│   ├── controllers/        → Lógica que conecta UI con datos
│   ├── models/             → Modelos de datos
│   ├── services/
│   │   ├── importador/     → Importar inventarios desde Excel/CSV (lógica)
│   │   └── ...             → Otros servicios (Excel, reportes, etc.)
│   └── utils/              → Logger, validadores, helpers
├── db/
│   ├── database.py         → Conexión SQLite
│   ├── migraciones.py      → Aplica los cambios de la base de datos, en orden
│   ├── migrations/         → Un archivo por cambio: migration_001.py, 002, 003…
│   ├── respaldos.py        → Copias de seguridad automáticas
│   └── respaldos/          → Las copias (se generan solas; no se suben a git)
├── assets/                 → Íconos, imágenes, estilos
├── config/                 → Settings y constantes
├── tests/                  → Pruebas automáticas
├── logs/                   → Logs del sistema (se generan solos)
└── main.py                 → Punto de entrada
```

---

## Cómo agregar una pestaña nueva

1. Crea el archivo de vista en `app/ui/nombre_view.py`
2. Importa la vista en `app/ui/main_window.py`
3. Agrega la línea `self.tabs.addTab(NombreView(self.usuario), "Nombre")`

Eso es todo.

---

## Importar un inventario desde Excel o CSV

En **Inventario → 📥 Importar inventario** (solo administradores) se abre un asistente de 5 pasos:

1. **Archivo**: elige el `.xlsx` o `.csv` y marca las hojas que quieres importar. Ahí mismo
   puedes descargar una **plantilla** lista para llenar.
2. **Columnas**: el programa adivina qué columna es cada dato por su nombre (sin importar el
   orden, las mayúsculas ni las tildes). Corrige lo que no acierte. Si todos los archivos de un
   laboratorio se ven igual, guarda el formato y la próxima vez se aplica solo.
3. **Depósitos y opciones**: cada hoja es un depósito, o una columna dice el depósito, o todo va
   a uno solo. Aquí también se elige el tipo por defecto y qué hacer con los ítems que ya existen.
4. **Revisión**: se revisa TODO el archivo antes de guardar. Se ve cuántos ítems se crean y qué
   filas tienen problemas (con el número de fila y el motivo). Se puede descargar el reporte en Excel.
5. **Guardado**: se guarda todo o nada, y antes se hace una copia de seguridad.

Reglas que conviene conocer:

- Solo **Nombre** y **Cantidad** son obligatorios; código, ubicación, observaciones, tipo y unidad son opcionales.
- Las cantidades son **números enteros**. Para líquidos usa una unidad pequeña (mL en vez de L).
- Un ítem "ya existe" si coincide el **depósito + nombre + código/referencia**. Por eso se puede
  subir el mismo archivo otra vez sin duplicar nada.
- Las filas con errores **no se importan**, pero no frenan a las demás. Corrige el Excel y súbelo
  completo de nuevo.
- Para reconocer un nombre de columna nuevo (por ejemplo, si un laboratorio llama «Insumo» al
  nombre), agrégalo en `app/services/importador/campos.py`.

El importador está dividido en piezas pequeñas (leer → mapear → revisar → guardar); cada archivo
de `app/services/importador/` explica al inicio qué hace.

---

## Base de datos: migraciones y respaldos

Los cambios a la base de datos son **migraciones numeradas** (`db/migrations/migration_00N.py`).
Al iniciar, el programa aplica las que falten, en orden, y guarda cuáles ya se aplicaron. Antes de
migrar una base que ya tenía datos, y antes de cada importación, se crea una copia en
`db/respaldos/` (se conservan las últimas 10).

**Regla para escribir código que usa la base de datos:** abre SIEMPRE la conexión así, para que se
cierre sola aunque algo falle (si queda abierta, la base se bloquea y todo da «database is locked»):

```python
from db.database import conexion

with conexion() as conn:
    conn.execute("UPDATE ...")
    conn.commit()          # solo si hubo INSERT / UPDATE / DELETE
```

Para agregar un cambio: crea `migration_00N.py` con una función `ejecutar()` y regístrala en la
lista `MIGRACIONES` de `db/migraciones.py`. **Nunca edites una migración que ya se aplicó.**

---

## Pruebas automáticas

```bash
python -m unittest discover -s tests -t .
```

Cada prueba usa una base de datos temporal: nunca toca tu inventario real. Las pruebas de las
pantallas corren sin ventana (modo *offscreen*) y se saltan solas si PyQt6 no está instalado.
