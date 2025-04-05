# Proyecto de Ajedrez

Este proyecto es una aplicación de ajedrez desarrollada en Python utilizando el framework Textual. La aplicación permite jugar al ajedrez, visualizar el tablero y realizar promociones de piezas.

## Requisitos

- Python 3.8 o superior
- Textual
- Chess

## Instalación

1. Clona el repositorio:
    ```sh
    git clone https://github.com/jesjack/textual-chess
    cd textual-chess
    ```

2. Crea un entorno virtual y actívalo:
    ```sh
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3. Instala las dependencias:
    ```sh
    pip install -r requirements.txt
    ```

## Uso

Para ejecutar la aplicación de ajedrez, utiliza el siguiente comando:
```sh
python src/app.py
```
Para ejecutar el script de visualización de ejecución:
```sh
python exec.py --graph
```

## Estructura del Proyecto
- `src/app.py`: Archivo principal de la aplicación de ajedrez.
- `src/components/`: Contiene los componentes de la interfaz de usuario.
- `src/utils/`: Contiene utilidades y funciones auxiliares.
- `exec.py`: Script para ejecutar y monitorear procesos.
## Funcionalidades
Juego de Ajedrez: Permite jugar una partida de ajedrez completa.
Promoción de Piezas: Interfaz para seleccionar la pieza a la que se desea promocionar un peón.
Visualización de Ejecución: Muestra visualizaciones relacionadas con la ejecución del programa.
Contribuciones
Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para discutir cualquier cambio que desees realizar.


Licencia
Este proyecto está licenciado bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.