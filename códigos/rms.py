from obspy import read, UTCDateTime, Stream
import numpy as np
import os

# ---------------------------------------------------
# 1. PARÁMETROS PRINCIPALES
# ---------------------------------------------------
stations = ["RIOS", "CCOL", "PJIM", "PLAN"]
components = ["HHZ", "HHN", "HHE"]

# Ahora definimos dt_list, un intervalo de muestreo por estación
dt_list = [0.01, 0.01, 0.01, 0.01]  # Ejemplo

# Listas de frecuencias (ejemplo con 3 combinaciones)
hf_freq_min_list = [2,   1.5, 1.5]
hf_freq_max_list = [8,   6,   6  ]
lf_freq_min_list = [0.02, 0.015, 0.025]
lf_freq_max_list = [0.05, 0.045, 0.055]

# Directorios donde se buscarán los archivos de entrada
fn_heads = [
    r"T:\Estaciones\RIOS_TSKT",
    r"T:\Estaciones\CCOL",
    r"T:\Estaciones\PJIM",
]

# Fechas a procesar
startday = UTCDateTime(2018, 1, 1)
endday   = UTCDateTime(2018, 12, 31)

# Intervalo en minutos para el cálculo de RMS
interval_minutes = 1
# Cantidad de intervalos de 1 minuto que hay en 1 día (24*60 = 1440)
num_intervals = int(1440 / interval_minutes)

# ---------------------------------------------------
# NUEVOS PARÁMETROS PARA CONVERSIÓN Y RUIDO
# ---------------------------------------------------
# Factores de conversión: (counts) -> (m/s) por estación
conversion_factor = [6.27604e8, 1.95524e9, 1.95524e9, 2.99113e8]
# Ruido máximo en (m/s)
max_noise = [2e-7, 2e-7, 2e-7, 2e-7]
# Ruido mínimo en (m/s)
min_noise = [1e-4, 1e-3, 1e-3, 1e-4]

# ---------------------------------------------------
# 2. BUCLE PRINCIPAL SOBRE COMBINACIONES DE FRECUENCIA
# ---------------------------------------------------
for hf_freq_min, hf_freq_max, lf_freq_min, lf_freq_max in zip(
    hf_freq_min_list, hf_freq_max_list, lf_freq_min_list, lf_freq_max_list
):
    # Construye la ruta base según las frecuencias
    dir_base = os.path.join(
        r"T:\SSE",
        f"{lf_freq_min}_{lf_freq_max}__{hf_freq_min}_{hf_freq_max}"
    )

    # Directorios de salida para esta combinación de frecuencias
    dir_out = os.path.join(dir_base, "rms")
    dir_out_clas = os.path.join(dir_base, "rms_clas")

    # Crear directorios si no existen
    os.makedirs(dir_out, exist_ok=True)
    os.makedirs(dir_out_clas, exist_ok=True)

    print("======================================")
    print(f"Procesando combinación de frecuencias:")
    print(f"HF: {hf_freq_min}–{hf_freq_max} Hz | LF: {lf_freq_min}–{lf_freq_max} Hz")
    print(f"Carpeta de salida: {dir_base}")
    print("======================================")

    # ---------------------------------------------------
    # 3. BUCLE SOBRE ESTACIONES
    # ---------------------------------------------------
    for station_index, station in enumerate(stations):
        # dt propio de la estación
        dt = dt_list[station_index]

        # Factores de conversión y ruido para la estación
        factor_counts = conversion_factor[station_index]
        noise_max_m_s = max_noise[station_index]
        noise_min_m_s = min_noise[station_index]

        # Reiniciamos la fecha de inicio para cada estación
        day = startday

        # ---------------------------------------------------
        # 4. BUCLE SOBRE DÍAS
        # ---------------------------------------------------
        while day <= endday:
            date = f"{day.year}{str(day.julday).zfill(3)}"
            print(f"\nEstación {station}, día {day.strftime('%Y-%m-%d')}, dt={dt} s")

            st = Stream()
            components_loaded = 0

            # -----------------------------------------------
            # 4.1 Lectura de datos
            # -----------------------------------------------
            for component in components:
                file_found = False
                for fn_head in fn_heads:
                    fn = os.path.join(fn_head, f"i4.{station}.{component}.{date}_0+")
                    if os.path.exists(fn):
                        try:
                            st += read(fn)
                            components_loaded += 1
                            file_found = True
                            break
                        except Exception as e:
                            # Puedes imprimir o manejar la excepción si lo deseas
                            continue

                if not file_found:
                    print(f"Archivo no encontrado para {component}, día {date}")

            # Si no se encuentran al menos 3 componentes, se pasa al siguiente día
            if components_loaded < 3:
                print(f"Componentes insuficientes ({components_loaded}) para {station} el día {date}")
                day += 86400
                continue

            # -----------------------------------------------
            # 4.2 Aplicar filtros HF y LF
            # -----------------------------------------------
            st_hf = st.copy().filter(
                type="bandpass",
                freqmin=hf_freq_min,
                freqmax=hf_freq_max,
                corners=2,
                zerophase=True
            )
            st_lf = st.copy().detrend("linear").filter(
                type="bandpass",
                freqmin=lf_freq_min,
                freqmax=lf_freq_max,
                corners=2,
                zerophase=True
            )

            # -----------------------------------------------
            # 4.3 Preparar archivos de salida
            # -----------------------------------------------
            output_file = os.path.join(dir_out, f"{station}_{date}.csv")
            classification_file = os.path.join(dir_out_clas, f"{station}_{date}_clas.csv")

            with open(output_file, mode="w") as f_out, open(classification_file, mode="w") as f_class:
                categories = []

                # -------------------------------------------
                # 4.4 Bucle sobre intervalos (en minutos)
                # -------------------------------------------
                for interval in range(num_intervals):
                    # ipts0, ipts1 se calculan usando dt específico de esta estación
                    ipts0 = int(interval * interval_minutes * 60 / dt)
                    ipts1 = min(
                        int((interval + 1) * interval_minutes * 60 / dt),
                        st[0].stats.npts
                    )

                    # Vectores para RMS HF y LF en cada componente (en counts)
                    rms_hf = [0, 0, 0]
                    rms_lf = [0, 0, 0]

                    # Calcular RMS para cada componente
                    for j in range(3):
                        data_hf = st_hf[j].data[ipts0:ipts1]
                        data_lf = st_lf[j].data[ipts0:ipts1]

                        if len(data_hf) == 0 or len(data_lf) == 0:
                            rms_hf[j] = 0
                            rms_lf[j] = 0
                        else:
                            rms_hf[j] = np.sqrt(np.mean(data_hf ** 2))
                            rms_lf[j] = np.sqrt(np.mean(data_lf ** 2))

                    # RMS horizontal y total en alta y baja frecuencia (EN COUNTS)
                    rms_hfhor = np.sqrt(rms_hf[1] ** 2 + rms_hf[2] ** 2)
                    rms_hfall = np.sqrt(rms_hf[0] ** 2 + rms_hf[1] ** 2 + rms_hf[2] ** 2)
                    rms_lfhor = np.sqrt(rms_lf[1] ** 2 + rms_lf[2] ** 2)
                    rms_lfall = np.sqrt(rms_lf[0] ** 2 + rms_lf[1] ** 2 + rms_lf[2] ** 2)

                    # Escribir la línea de datos en CSV (RMS en counts)
                    f_out.write(
                        f"{rms_hf[0]:.3e},{rms_hf[1]:.3e},{rms_hf[2]:.3e},"
                        f"{rms_hfhor:.3e},{rms_hfall:.3e},"
                        f"{rms_lf[0]:.3e},{rms_lf[1]:.3e},{rms_lf[2]:.3e},"
                        f"{rms_lfhor:.3e},{rms_lfall:.3e}\n"
                    )

                    # -------------------------------------------
                    # CLASIFICACIÓN
                    # -------------------------------------------
                    # Convertimos el max_noise (m/s) a counts
                    max_noise_counts = factor_counts * noise_max_m_s
                    # Convertimos el min_noise (m/s) a counts
                    min_noise_counts = factor_counts * noise_min_m_s

                    category = "b"
                    if rms_lfhor < min_noise_counts:
                        category = "c"
                    elif rms_lfhor > max_noise_counts:
                        category = "a"

                    categories.append(category)

                # -------------------------------------------
                # 4.5 Post-procesamiento de clasificaciones
                # -------------------------------------------
                # Cambiar "b" a "d" si está entre "a" o "c"
                for i in range(1, len(categories) - 1):
                    if categories[i] == "b":
                        if (categories[i - 1] in {"c", "a"}) or (categories[i + 1] in {"c", "a"}):
                            categories[i] = "d"

                # Extender la "c" ±20 min marcándolas como "c1"
                for i, category in enumerate(categories):
                    if category == "c":
                        for offset in range(-20, 21):
                            idx = i + offset
                            if 0 <= idx < len(categories) and categories[idx] != "c":
                                categories[idx] = "c1"

                # Escribir clasificaciones en archivo
                for category in categories:
                    f_class.write(f"{category}\n")

            # Avanzar un día
            day += 86400

    # Fin del bucle de estaciones

# Fin del bucle de combinaciones de frecuencias
