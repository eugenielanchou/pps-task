import pyxdf
import mne

file_path = r"C:\Users\eduwell\Documents\CurrentStudy\sub-P002\ses-S001\eeg\sub-P002_ses-S001_task-Default_run-001_eeg.xdf"

# Charge le fichier XDF
streams, fileheader = pyxdf.load_xdf(file_path)

# Trouve le stream EEG (g.HIamp)
eeg_stream = None
markers_stream = None

for stream in streams:
    if "HA-2012" in stream['info']['name'][0]:  # g.HIamp
        eeg_stream = stream
    elif "PPS_Markers" in stream['info']['name'][0]:
        markers_stream = stream

if eeg_stream is None:
    print("ERROR: No EEG stream found")
else:
    # Extrait les données EEG
    data = eeg_stream['time_series'].T  # (n_channels, n_samples)
    sfreq = float(eeg_stream['info']['nominal_srate'][0])

    # Crée les infos du canal
    ch_names = [f"Ch{i}" for i in range(data.shape[0])]
    ch_types = ['eeg'] * data.shape[0]
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)

    # Crée un objet RawArray MNE
    raw = mne.io.RawArray(data, info)

    # Ajoute les markers comme annotations
    if markers_stream is not None:
        marker_times = markers_stream['time_stamps']
        marker_values = markers_stream['time_series'].flatten()

        annotations = mne.Annotations(
            onset=marker_times,
            duration=[0.0] * len(marker_times),
            description=[f"Trigger_{int(v)}" for v in marker_values]
        )
        raw.set_annotations(annotations)
        print(f"Added {len(marker_times)} markers")

    print(raw)
    print("\nAnnotations (markers):")
    print(raw.annotations)

    # Check amplitude
    print(f"\nEEG Amplitude:")
    print(f"  Min: {data.min():.2e} V")
    print(f"  Max: {data.max():.2e} V")
    print(f"  Std: {data.std():.2e} V")

    # Apply bandpass filter for better visibility
    print("\nApplying 0.5-40 Hz filter...")
    raw.filter(0.5, 40, verbose=False)

    # Visualize with better scaling
    print("Opening visualization window...")
    raw.plot(duration=10, n_channels=10, scalings='auto')
