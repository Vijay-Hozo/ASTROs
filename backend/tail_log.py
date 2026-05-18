with open("output.log", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print("LAST 50 LINES OF LOG:")
for line in lines[-50:]:
    print(line.strip())
