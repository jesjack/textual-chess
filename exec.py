from subprocess import run

if __name__ == "__main__":
    run(["cmd", "/c", "start", "cmd", "/k", r"textual console"])
    run(["cmd", "/c", "start", "cmd", "/k", r"python ./main.py"])
