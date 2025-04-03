from subprocess import Popen, CREATE_NEW_CONSOLE, run
import threading
import sys

from src.utils.visualization import show_execution_visuals

def monitor_process(process, others):
    process.wait()  # Espera a que el proceso se cierre
    for p in others:
        if p.poll() is None:  # Si el proceso aún está activo
            # Fuerza el cierre del proceso y sus hijos en Windows
            run(["taskkill", "/F", "/T", "/PID", str(p.pid)], shell=True)

if __name__ == "__main__":

    args = sys.argv[1:]
    if '--graph' in args:
        show_execution_visuals()
        sys.exit()

    # Iniciar las ventanas
    p1 = Popen(["cmd", "/k", "textual console"], creationflags=CREATE_NEW_CONSOLE)
    p2 = Popen(["cmd", "/k", "textual run --dev ./main.py"], creationflags=CREATE_NEW_CONSOLE)

    # Hilos para monitorear y cerrar procesos restantes
    t1 = threading.Thread(target=monitor_process, args=(p1, [p2]))
    t2 = threading.Thread(target=monitor_process, args=(p2, [p1]))

    t1.start()
    t2.start()

    # Esperar a que ambos hilos terminen
    t1.join()
    t2.join()