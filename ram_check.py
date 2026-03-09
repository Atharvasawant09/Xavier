import psutil

mem = psutil.virtual_memory()

print("Total:", mem.total/1e9, "GB")
print("Used:", mem.used/1e9, "GB")
print("Available:", mem.available/1e9, "GB")