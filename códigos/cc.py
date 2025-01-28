from obspy import read, UTCDateTime, Stream
from scipy import signal
import numpy as np
import os
import csv

# ---------------------------------------------------
# 1. PARÁMETROS COMUNES
# ---------------------------------------------------
stations   = ["RIOS", "CCOL", "PJIM", "PLAN"]
components = ["HHZ", "HHN", "HHE"]

# Fechas a procesar
startday = UTCDateTime(2018, 1, 1)
endday   = UTCDateTime(2018, 12, 31)

# Directorios de entrada de datos crudos (en caso de necesitarlos)
fn_heads = [
    r"T:\Estaciones\RIOS",
    r"T:\Estaciones\CCOL",
    r"T:\Estaciones\PJIM",
]

# ---------------------------------------------------
# 2. PARÁMETROS DE FRECUENCIAS (LISTAS)
#    Múltiples combinaciones HF/LF
# ---------------------------------------------------
hf_freq_min_list = [2,   1.5, 1.5]
hf_freq_max_list = [8,   6,   6  ]
lf_freq_min_list = [0.02, 0.015, 0.025]
lf_freq_max_list = [0.05, 0.045, 0.055]

# ---------------------------------------------------
# 3. PARÁMETROS POR ESTACIÓN (LISTAS)
#    Cada elemento corresponde a una estación
# ---------------------------------------------------
# 3.1 dt (intervalo de muestreo original)
dt_list = [0.01, 0.01, 0.01, 0.01]

# 3.2 dt_dec (factor de decimación, en segundos)
#     (E.g., si dt_dec=1 y dt=0.01 => decimas cada 1/0.01=100 muestras)
dt_dec_list = [1, 1, 1, 1]

# 3.3 twin (tamaño de la ventana de correlación en segundos)
twin_list = [300, 300, 360, 300]

# 3.4 dt_cc (resolución temporal con que calcularemos la CC final)
dt_cc_list = [5, 5, 5, 5]

# 3.5 min_twin (tiempo mínimo de datos válidos dentro de la ventana)
min_twin_list = [180, 180, 180, 180]

# ---------------------------------------------------
# 4. BUCLE PRINCIPAL SOBRE COMBINACIONES DE FRECUENCIA
# ---------------------------------------------------
for hf_freq_min, hf_freq_max, lf_freq_min, lf_freq_max in zip(
    hf_freq_min_list, hf_freq_max_list, lf_freq_min_list, lf_freq_max_list
):
    # Construye la ruta base según las frecuencias
    dir_base = os.path.join(
        r"T:\SSE",
        f"{lf_freq_min}_{lf_freq_max}__{hf_freq_min}_{hf_freq_max}"
    )

    # Directorio de clasificación (rms_clas) generado por el script de RMS
    clas_dir = os.path.join(dir_base, "rms_clas")

    # Directorio de salida para coeficiente de correlación
    dir_out = os.path.join(dir_base, "cc")
    os.makedirs(dir_out, exist_ok=True)

    print("======================================")
    print(f"Correlación para combinación de frecuencias:")
    print(f"  HF: {hf_freq_min}–{hf_freq_max} Hz | LF: {lf_freq_min}–{lf_freq_max} Hz")
    print(f"  Dir. clasificación: {clas_dir}")
    print(f"  Dir. salida (cc):  {dir_out}")
    print("======================================")

    # ---------------------------------------------------
    # 5. BUCLE SOBRE ESTACIONES
    # ---------------------------------------------------
    for i_station, station in enumerate(stations):
        dt       = dt_list[i_station]       # Intervalo de muestreo
        dt_dec   = dt_dec_list[i_station]   # Paso de decimación
        twin     = twin_list[i_station]     # Tamaño de la ventana (s)
        dt_cc    = dt_cc_list[i_station]    # Intervalo para la CC final
        min_twin = min_twin_list[i_station] # Tiempo mínimo válido (s)

        # Con la ventana (twin) definimos ntwin en muestras decimadas
        # ntwin = twin / dt_dec (porque tras decimar, el "nuevo dt" es dt_dec)
        ntwin = int(twin / dt_dec)

        # Definimos el filtro bandpass para hf_sq
        # (fs = 1/dt) => sample rate original (antes de decimar).
        b, a = signal.butter(2, [lf_freq_min, lf_freq_max], btype="bandpass", fs=int(1/dt))

        # Creamos subcarpeta de salida para la estación
        station_outdir = os.path.join(dir_out, station)
        os.makedirs(station_outdir, exist_ok=True)

        # -----------------------------------------------
        # 5.1 Bucle de días
        # -----------------------------------------------
        day = startday
        while day <= endday:
            date_str = f"{day.year}{str(day.julday).zfill(3)}"
            day += 86400  # Avanzar un día

            # Archivo de clasificación
            clas_file = os.path.join(clas_dir, f"{station}_{date_str}_clas.csv")
            if not os.path.exists(clas_file):
                print(f"[{station}] Clas. no encontrada para {date_str}.")
                continue

            # Leemos la clasificación
            with open(clas_file, 'r') as f:
                reader = csv.reader(f)
                class_data = [row[0] for row in reader]

            # Cada fila del clasificador corresponde a un lapso
            # (p.ej. 86400/1440=60s si es a 1-min en el script de RMS)
            interval_seconds = 86400 / len(class_data)

            # Leemos datos crudos (3 componentes)
            st = Stream()
            for component in components:
                file_found = False
                for fn_head in fn_heads:
                    fn = os.path.join(fn_head, f"i4.{station}.{component}.{date_str}_0+")
                    if os.path.exists(fn):
                        try:
                            st += read(fn)
                            file_found = True
                            break
                        except Exception as e:
                            continue
                if not file_found:
                    print(f"[{station}] Archivo {component} no encontrado para {date_str}.")

            # Verificamos que haya 3 trazas
            if len(st) < 3:
                print(f"[{station}] Menos de 3 componentes en {date_str}.")
                continue

            # Verificamos longitud esperada (evitar días incompletos)
            # Esperamos ~ 86400/dt muestras
            expected_npts = int(86400 / dt)
            # Permitimos cierto margen (±1/dt)
            if any(abs(tr.stats.npts - expected_npts) > int(1/dt) for tr in st):
                print(f"[{station}] Muestras no coinciden con lo esperado en {date_str}.")
                continue

            # Verificamos que todas las trazas tengan la misma npts
            if any(st[0].stats.npts != tr.stats.npts for tr in st):
                print(f"[{station}] Inconsistencia npts entre componentes en {date_str}.")
                continue

            # Filtrado HF (2–8 Hz, etc.)
            st_hf = st.copy().filter(
                type="bandpass",
                freqmin=hf_freq_min,
                freqmax=hf_freq_max,
                corners=2,
                zerophase=True
            )
            # Sumamos potencias HF en las 3 componentes
            hf_sq = np.sum([tr.data**2 for tr in st_hf], axis=0)
            # Filtro bandpass en hf_sq (usando banda LF para "envelope")
            hf_sq_bp = signal.filtfilt(b, a, hf_sq)

            # Filtrado LF (0.02–0.05, etc.),
            # luego integrar y detrend
            st_lf = (
                st.copy()
                  .detrend("linear")
                  .filter(type="bandpass", freqmin=lf_freq_min, freqmax=lf_freq_max, corners=2, zerophase=True)
                  .integrate()
                  .detrend("linear")
            )
            # Tomamos la traza vertical (o la primera en st_lf)
            lf = st_lf[0].data

            # Decimamos hf_sq_bp y lf
            # ratio = round(dt_dec / dt) => factor en muestras
            dec_factor = int(round(dt_dec / dt))
            hf_sq_bp = signal.decimate(hf_sq_bp, dec_factor)
            lf       = signal.decimate(lf, dec_factor)

            # Limpieza de posibles NaNs
            hf_sq_bp = np.nan_to_num(hf_sq_bp, nan=0.0, posinf=0.0, neginf=0.0)
            lf       = np.nan_to_num(lf,       nan=0.0, posinf=0.0, neginf=0.0)

            # Serie de tiempo en la resolución dt_cc
            # time_cc -> [0, dt_cc, 2*dt_cc, ...  < 86400]
            time_cc = np.arange(0, 86400, dt_cc)

            # Array para la CC
            cc = np.zeros(len(time_cc))

            # Recorremos en pasos de dt_cc para calcular CC en cada ventana
            # i va en índices de time_cc (0,1,2,...)
            # ntwin = int(twin / dt_dec) (ya calculado arriba)
            half_ntwin = ntwin // 2

            for i in range(len(time_cc)):
                # Posición (i_wave) en la señal decimada
                i_wave = int(time_cc[i] / dt_dec)  # (s) / (s) => muestras en data decimada
                i_wave_l = i_wave - half_ntwin
                i_wave_r = i_wave + half_ntwin

                # Contamos cuántos segundos "b" hay en la clasificación dentro de la ventana
                valid_count = 0
                for k in range(-half_ntwin, half_ntwin):
                    idx_dec = i_wave + k
                    if idx_dec < 0 or idx_dec >= len(hf_sq_bp):
                        continue

                    # Convertir idx_dec a tiempo real en segundos (respecto al día)
                    time_in_seconds = time_cc[i] + (k * dt_dec)
                    if time_in_seconds < 0 or time_in_seconds >= 86400:
                        continue

                    # Indice en class_data
                    class_index = int(time_in_seconds // interval_seconds)
                    if class_index < 0 or class_index >= len(class_data):
                        continue

                    if class_data[class_index] == "b":
                        valid_count += dt_dec  # (s)

                # Verificar si tenemos min_twin s de datos "b"
                if valid_count < min_twin:
                    cc[i] = 0
                    continue

                # Comprobamos que la ventana [i_wave_l, i_wave_r] esté dentro de hf_sq_bp
                if i_wave_l < 0 or i_wave_r > len(hf_sq_bp):
                    cc[i] = 0
                    continue

                # Calculamos CC
                a1 = hf_sq_bp[i_wave_l:i_wave_r] - np.mean(hf_sq_bp[i_wave_l:i_wave_r])
                a2 = lf[i_wave_l:i_wave_r]       - np.mean(lf[i_wave_l:i_wave_r])

                norm_a1 = np.linalg.norm(a1, ord=2)
                norm_a2 = np.linalg.norm(a2, ord=2)
                if norm_a1 == 0 or norm_a2 == 0:
                    cc[i] = 0
                else:
                    cc[i] = np.dot(a1, a2) / (norm_a1 * norm_a2)

            # Guardamos la CC en un archivo CSV
            output_file = os.path.join(station_outdir, f"{date_str}.csv")
            with open(output_file, mode='w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(['Time (s)', 'CC Value'])
                csvwriter.writerows(zip(time_cc, cc))

        # Fin while day
    # Fin bucle estaciones
# Fin bucle combinaciones HF/LF
