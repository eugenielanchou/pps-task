import pyxdf

file_path = r"C:\Users\eduwell\Documents\CurrentStudy\sub-P002\ses-S001\eeg\sub-P002_ses-S001_task-Default_run-001_eeg.xdf"

# Charge le fichier XDF
streams, fileheader = pyxdf.load_xdf(file_path)

print(f"📊 Nombre de streams capturés: {len(streams)}")
print()

for i, stream in enumerate(streams):
    info = stream['info']
    print(f"Stream {i+1}: {info['name'][0]}")
    print(f"  Canaux: {info['channel_count'][0]}")
    print(f"  Fréquence: {info['nominal_srate'][0]} Hz")
    print(f"  Durée: {len(stream['time_series'])} samples")
    print()
