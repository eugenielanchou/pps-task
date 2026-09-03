import sounddevice as sd

print("Périphériques audio disponibles:\n")
devices = sd.query_devices()
for i, device in enumerate(devices):
    print(f"{i}: {device['name']}")
    print(f"   Canaux: {device['max_output_channels']} (sortie)")
    print()

# Montre aussi le périphérique par défaut
print(f"\nPériphérique par défaut: {sd.default.device}")
