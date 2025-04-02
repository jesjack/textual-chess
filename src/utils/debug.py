import time
import asyncio
import functools
import atexit
import signal
import sys
import uuid
import subprocess
from collections import defaultdict
from .visualization import show_execution_visuals

# Almacenamiento para los tiempos de ejecución
execution_times = defaultdict(list)
execution_order = []  # Para rastrear el orden de ejecución
timeline_events = []  # Para la línea de tiempo
_execution_data_shown = False  # Bandera para evitar múltiples llamados
execution_session_id = str(uuid.uuid4())  # ID único para cada ejecución

def timing_decorator(func):
    """
    Decorador que mide el tiempo de ejecución de funciones y almacena los resultados.
    Compatible con funciones síncronas y asíncronas.
    """
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        return mid_wrapper(result, start_time)

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        return mid_wrapper(result, start_time)

    def mid_wrapper(result, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        execution_times[func.__name__].append(execution_time)
        execution_order.append((func.__name__, execution_time))
        timeline_events.append((func.__name__, start_time, end_time))
        return result

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

# Add after execution_session_id definition
git_performance_branch = "performance_tracking"

def get_git_info():
    """Get current Git commit information"""
    try:
        # Get current branch
        current_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True
        ).strip()
        
        # Create performance branch if it doesn't exist
        subprocess.run(
            ["git", "branch", "--no-track", git_performance_branch],
            capture_output=True,
            check=False
        )
        
        # Stash changes, switch to performance branch, and apply changes
        subprocess.run(["git", "stash"], capture_output=True)
        subprocess.run(["git", "checkout", git_performance_branch], capture_output=True)
        subprocess.run(["git", "stash", "apply"], capture_output=True)
        
        # Create commit with execution session ID
        commit_message = f"Performance measurement session: {execution_session_id}"
        subprocess.run(["git", "add", "."], capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True,
            text=True
        )
        
        # Get commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True
        ).strip()
        
        # Switch back to original branch
        subprocess.run(["git", "checkout", current_branch], capture_output=True)
        
        return commit_hash
    except Exception as e:
        print(f"Error getting Git info: {e}", file=sys.stderr)
        return None

# Modify save_execution_data function to include Git information
async def save_execution_data(db_uri="execution_data.db"):
    try:
        import aiosqlite
    except ImportError:
        raise RuntimeError("aiosqlite no está instalado. Instálalo con 'pip install aiosqlite'")

    # Get Git commit information
    git_commit = get_git_info()

    try:
        async with aiosqlite.connect(db_uri) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute("PRAGMA journal_mode = WAL")

            # Crear tablas con una única transacción
            try:
                await db.execute("BEGIN TRANSACTION")

                await db.execute('''
                    CREATE TABLE IF NOT EXISTS execution_sessions (
                        session_id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL
                    )
                ''')

                await db.execute('''
                    CREATE TABLE IF NOT EXISTS execution_times (
                        session_id TEXT,
                        function_name TEXT,
                        execution_time REAL,
                        FOREIGN KEY(session_id) 
                            REFERENCES execution_sessions(session_id)
                            ON DELETE CASCADE
                    )
                ''')

                await db.execute('''
                    CREATE TABLE IF NOT EXISTS execution_order (
                        session_id TEXT,
                        order_index INTEGER,
                        function_name TEXT,
                        execution_time REAL,
                        PRIMARY KEY(session_id, order_index),
                        FOREIGN KEY(session_id) 
                            REFERENCES execution_sessions(session_id)
                            ON DELETE CASCADE
                    )
                ''')

                await db.execute('''
                    CREATE TABLE IF NOT EXISTS timeline_events (
                        session_id TEXT,
                        function_name TEXT,
                        start_time REAL,
                        end_time REAL,
                        FOREIGN KEY(session_id) 
                            REFERENCES execution_sessions(session_id)
                            ON DELETE CASCADE
                    )
                ''')

                await db.execute("COMMIT")
            except Exception as trans_error:
                await db.execute("ROLLBACK")
                print(f"Error en transacción: {trans_error}")
                raise

            # Insertar sesión si no existe
            await db.execute(
                'INSERT INTO execution_sessions (session_id, timestamp) VALUES (?, ?)',
                (execution_session_id, time.time())
            )

            # Insertar datos de ejecución
            for func_name, times in execution_times.items():
                await db.executemany(
                    'INSERT INTO execution_times (session_id, function_name, execution_time) VALUES (?, ?, ?)',
                    [(execution_session_id, func_name, exec_time) for exec_time in times]
                )

            order_data = [
                (execution_session_id, idx, func_name, exec_time)
                for idx, (func_name, exec_time) in enumerate(execution_order)
            ]
            await db.executemany(
                'INSERT INTO execution_order (session_id, order_index, function_name, execution_time) VALUES (?, ?, ?, ?)',
                order_data
            )

            timeline_data = [
                (execution_session_id, func_name, start, end)
                for func_name, start, end in timeline_events
            ]
            await db.executemany(
                'INSERT INTO timeline_events (session_id, function_name, start_time, end_time) VALUES (?, ?, ?, ?)',
                timeline_data
            )

            await db.commit()

            # Add new table for Git tracking
            await db.execute('''
                CREATE TABLE IF NOT EXISTS git_tracking (
                    session_id TEXT PRIMARY KEY,
                    git_commit TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) 
                        REFERENCES execution_sessions(session_id)
                        ON DELETE CASCADE
                )
            ''')

            # Add Git tracking information
            if git_commit:
                await db.execute(
                    'INSERT INTO git_tracking (session_id, git_commit, timestamp) VALUES (?, ?, ?)',
                    (execution_session_id, git_commit, time.time())
                )

    except aiosqlite.Error as e:
        print(f"Error de base de datos: {e}")
        raise
    except Exception as e:
        print(f"Error inesperado: {e}")


def show_execution_times():
    global _execution_data_shown
    if _execution_data_shown:
        return
    _execution_data_shown = True

    async def fetch_last_session_data():
        try:
            import aiosqlite
        except ImportError:
            print("Error: aiosqlite no está instalado.", file=sys.stderr)
            return

        try:
            async with aiosqlite.connect("execution_data.db") as db:
                # Obtener última sesión
                cursor = await db.execute(
                    "SELECT session_id FROM execution_sessions ORDER BY timestamp DESC LIMIT 1"
                )
                session_row = await cursor.fetchone()
                if not session_row:
                    print("No hay datos históricos disponibles")
                    return
                session_id = session_row[0]

                # Obtener datos de la sesión
                execution_times = defaultdict(list)
                execution_order = []
                timeline_events = []

                # Execution times
                cursor = await db.execute(
                    "SELECT function_name, execution_time FROM execution_times WHERE session_id = ?",
                    (session_id,)
                )
                async for row in cursor:
                    execution_times[row[0]].append(row[1])

                # Execution order
                cursor = await db.execute(
                    "SELECT function_name, execution_time FROM execution_order WHERE session_id = ? ORDER BY order_index",
                    (session_id,)
                )
                async for row in cursor:
                    execution_order.append((row[0], row[1]))

                # Timeline events
                cursor = await db.execute(
                    "SELECT function_name, start_time, end_time FROM timeline_events WHERE session_id = ? ORDER BY start_time",
                    (session_id,)
                )
                async for row in cursor:
                    timeline_events.append((row[0], row[1], row[2]))

                # Mostrar visualización
                show_execution_visuals(execution_times, execution_order, timeline_events)

        except Exception as e:
            print(f"Error al cargar datos: {e}", file=sys.stderr)

    # Ejecutar la carga de datos
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(fetch_last_session_data())
    except RuntimeError:
        try:
            asyncio.run(fetch_last_session_data())
        except Exception as e:
            print(f"Error al ejecutar: {e}", file=sys.stderr)

def _handle_exit(signum=None, frame=None):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(save_execution_data())  # Agregar la tarea al event loop
        loop.create_task(show_execution_times())  # Agregar visualización al event loop
    else:
        asyncio.run(save_execution_data())
        show_execution_times()
    sys.exit(0)

async def _handle_excepthook(exc_type, exc_value, traceback):
    await save_execution_data()
    show_execution_times()
    sys.__excepthook__(exc_type, exc_value, traceback)

# Registro de manejadores
atexit.register(_handle_exit)
sys.excepthook = _handle_excepthook

SIGNALS_TO_HANDLE = []
for sig_name in ['SIGINT', 'SIGTERM', 'SIGHUP']:
    if hasattr(signal, sig_name):
        SIGNALS_TO_HANDLE.append(getattr(signal, sig_name))

for sig in SIGNALS_TO_HANDLE:
    try:
        signal.signal(sig, _handle_exit)
    except (ValueError, RuntimeError):
        pass

# Alias para mayor comodidad
timeit = timing_decorator
