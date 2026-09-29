import sys
with open("main.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if "load_dotenv()" in line:
        new_lines.append('        print("Variabili ambiente caricate")\n')
    if "controller = DensoController" in line:
        new_lines.append('        print("DensoController instanziato")\n')
    if "controller.connect()" in line:
        new_lines.append('        print("Connessione riuscita (se non fallisce prima)")\n')
    if "ROBOT_IP = os.getenv" in line:
        new_lines.append('        print(f"IP Robot: {ROBOT_IP}")\n')

with open("main.py", "w") as f:
    f.writelines(new_lines)
