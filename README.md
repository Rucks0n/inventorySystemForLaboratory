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
│   ├── ui/             → Pantallas e interfaces gráficas
│   ├── controllers/    → Lógica que conecta UI con datos
│   ├── models/         → Modelos de datos
│   ├── services/       → Servicios (Excel, reportes, etc.)
│   └── utils/          → Logger, validadores, helpers
├── db/
│   ├── database.py     → Conexión SQLite
│   └── migrations/     → Creación de tablas
├── assets/             → Íconos, imágenes, estilos
├── config/             → Settings y constantes
├── data/               → Plantillas Excel
├── tests/              → Tests automatizados
├── logs/               → Logs del sistema (se generan solos)
└── main.py             → Punto de entrada
```

---

## Cómo agregar una pestaña nueva

1. Crea el archivo de vista en `app/ui/nombre_view.py`
2. Importa la vista en `app/ui/main_window.py`
3. Agrega la línea `self.tabs.addTab(NombreView(self.usuario), "Nombre")`

Eso es todo.