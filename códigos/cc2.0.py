# %%
from obspy import read, UTCDateTime, signal, Stream
from scipy import signal
import numpy as np
import os
import csv

# Parámetros
startday = UTCDateTime(2018, 1, 1)
endday = UTCDateTime(2018, 12, 31)
stations = ["RIOS"]  # Estaciones
components = ["HHZ", "HHN", "HHE"]  # Componentes: vertical, norte-sur, este-oeste
fn_head = r'T:\RIOS'  # Directorio de entrada
clas_dir = r'T:\detecciones2018\rms_clas'  # Directorio de clasificación
dt = 0.01  # Intervalo de muestreo original
dt_dec = 1.0
twin = 300  # ventana de calculo de CC
ntwin = int(twin / dt_dec)
dt_cc = 10  # Tiempo CC
dir_out = r'T:\detecciones2018\cc'  

os.makedirs(dir_out, exist_ok=True)

# Serie de tiempo
time_cc = np.arange(0, 86400, dt_cc)
# Filtro BP
b, a = signal.butter(2, [0.02, 0.05], "bandpass", fs=int(1 / dt))

for station in stations:
    os.makedirs(os.path.join(dir_out, station), exist_ok=True)
    day = startday
    while day <= endday:
        # Formato fecha
        date = str(day.year) + str(day.julday).zfill(3)
        day += 86400

        # Leer archivo de clasificación
        clas_file = os.path.join(clas_dir, f"{station}_{date}_clas.csv")
        if not os.path.exists(clas_file):
            print(f"Archivo de clasificación no encontrado para {date}.")
            continue

        # Cargar datos de clasificación
        with open(clas_file, 'r') as f:
            reader = csv.reader(f)
            class_data = [row[0] for row in reader]

        # Determinar el intervalo en segundos por cada clase
        interval_seconds = 86400 / len(class_data)

        st = Stream()
        for component in components:
            fn = os.path.join(fn_head, f"i4.{station}.{component}.{date}_0+")
            if os.path.exists(fn):
                st += read(fn)

        # Verificación de datos completos
        if len(st) < 3:
            print(f"Componentes insuficientes para el día {date} en la estación {station}.")
            continue
        if any(abs(tr.stats.npts - int(86400 / dt)) > int(1 / dt) for tr in st):
            continue
        if any(st[0].stats.npts != tr.stats.npts for tr in st):
            continue

        # BP para HF
        st_hf = st.copy().filter(type="bandpass", freqmin=2, freqmax=8, corners=2, zerophase=True)
        hf_sq = np.sum([tr.data ** 2 for tr in st_hf], axis=0)
        hf_sq_bp = signal.filtfilt(b, a, hf_sq)

        # BP para LF
        st_lf = st.copy().detrend("linear").filter(type="bandpass", freqmin=0.02, freqmax=0.05, corners=2, zerophase=True).integrate().detrend("linear")
        lf = st_lf[0].data

        # Decimación de las señales
        hf_sq_bp = signal.decimate(hf_sq_bp, round(dt_dec / dt))
        lf = signal.decimate(lf, round(dt_dec / dt))

        # Manejo de valores NaN o infinitos
        hf_sq_bp = np.nan_to_num(hf_sq_bp, nan=0.0, posinf=0.0, neginf=0.0)
        lf = np.nan_to_num(lf, nan=0.0, posinf=0.0, neginf=0.0)

        # Calculo de CC con verificación de la clase "b"
        cc = np.zeros(int(86400 / dt_cc))
        for i in range(int(twin / 2 / dt_cc), int((86400 - twin / 2) / dt_cc)):
            i_wave = int(i * dt_cc / dt_dec)
            i_wave_l = i_wave - int(ntwin / 2)
            i_wave_r = i_wave + int(ntwin / 2)

            # Calcular el tiempo actual en segundos desde el inicio del día
            time_in_seconds = i * dt_cc

            # Calcular el índice correspondiente en el archivo de clasificación
            class_index = int(time_in_seconds // interval_seconds)

            # Verificación de la clase asignada en el archivo clas
            if class_data[class_index] != 'b':
                # Si no es clase 'b', asignar 0 a ese índice de CC
                cc[i] = 0
                continue

            # Verificación de límites para evitar índices fuera de rango
            if i_wave_l >= 0 and i_wave_r <= len(hf_sq_bp):
                a1 = hf_sq_bp[i_wave_l:i_wave_r] - np.mean(hf_sq_bp[i_wave_l:i_wave_r])
                a2 = lf[i_wave_l:i_wave_r] - np.mean(lf[i_wave_l:i_wave_r])
                cc[i] = np.dot(a1, a2) / (np.linalg.norm(a1, ord=2) * np.linalg.norm(a2, ord=2))

        # Guardar resultados en formato CSV
        output_file = os.path.join(dir_out, station, f"{date}.csv")
        with open(output_file, mode='w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Time (s)', 'CC Value'])  # Escribir encabezado
            csvwriter.writerows(zip(time_cc, cc))  # Escribir datos

