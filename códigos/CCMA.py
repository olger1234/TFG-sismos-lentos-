import csv
import numpy as np
import os
from obspy import UTCDateTime

# --------------------------------------------------------------------------------
# 1. PARÁMETROS PRINCIPALES
# --------------------------------------------------------------------------------
stations = ["RIOS", "CCOL", "PJIM", "TSKT"]

startday = UTCDateTime(2022, 1, 1)
endday   = UTCDateTime(2022, 12, 31)

# Se definen las listas de frecuencias a procesar (para generar/leer directorios)
hf_freq_min_list = [2,   1.5, 1.5]
hf_freq_max_list = [8,   6,   6  ]
lf_freq_min_list = [0.02, 0.015, 0.025]
lf_freq_max_list = [0.05, 0.045, 0.055]

# Por cada estación, twin_mvave y min_data pueden ser distintos (aunque sean iguales aquí)
# Quedan como listas, índice por estación: twin_mvave_list[i_station], etc.
twin_mvave_list = [3000, 3000, 3000, 3000]  # Ventana en número de muestras
min_data_list   = [2200,  2200,  2200,  2200 ]  # Mínimo de muestras válidas
dt_cc = 5  # Se mantiene la necesidad de dt_cc para indexar datos

# --------------------------------------------------------------------------------
# 2. BUCLE SOBRE LAS COMBINACIONES DE FRECUENCIA
# --------------------------------------------------------------------------------
for hf_freq_min, hf_freq_max, lf_freq_min, lf_freq_max in zip(
    hf_freq_min_list, hf_freq_max_list, lf_freq_min_list, lf_freq_max_list
):
    # Directorios de entrada y salida según la combinación de frecuencias
    dir_base_in  = f"{lf_freq_min}_{lf_freq_max}__{hf_freq_min}_{hf_freq_max}"
    fn_cc_head   = os.path.join(r"T:\ULTIMOS22\3000 s", dir_base_in, "cc")
    fn_out_head  = os.path.join(r"T:\ULTIMOS22\3000 s", dir_base_in, "ccma")

    # Asegurarse de que el directorio de salida exista
    os.makedirs(fn_out_head, exist_ok=True)

    # Diccionario para almacenar los valores de CCMA acumulados por estación
    ccma_values_by_station = {station: [] for station in stations}

    print("===================================================")
    print(f"Calculando CCMA para:")
    print(f"  HF: {hf_freq_min}-{hf_freq_max} Hz | LF: {lf_freq_min}-{lf_freq_max} Hz")
    print(f"  Directorio CC  : {fn_cc_head}")
    print(f"  Directorio CCMA: {fn_out_head}")
    print("===================================================")

    # --------------------------------------------------------------------------------
    # 3. BUCLE SOBRE ESTACIONES
    # --------------------------------------------------------------------------------
    for i_station, station in enumerate(stations):
        twin_mvave = twin_mvave_list[i_station]
        min_data   = min_data_list[i_station]

        # Crear subdirectorio para la estación en la carpeta de salida
        station_outdir = os.path.join(fn_out_head, station)
        os.makedirs(station_outdir, exist_ok=True)

        day = startday
        while day <= endday:
            # Preparar las rutas para el día anterior, actual y siguiente
            # (Igual que en tu código original)
            dates = [day - 86400, day, day + 86400]
            cc_combined = []

            # Cargar los datos de los tres días
            for current_day in dates:
                date_str = f"{current_day.year}{str(current_day.julday).zfill(3)}"
                fn = os.path.join(fn_cc_head, station, date_str + ".csv")

                if os.path.exists(fn):
                    with open(fn, newline='') as csvfile:
                        reader = csv.reader(csvfile)
                        next(reader)  # Saltar cabecera ["Time (s)", "CC Value"]
                        # Convertir a array => [[Time(s), CC], [...], ...]
                        cc_data = np.array([[float(row[0]), float(row[1])] 
                                            for row in reader])
                    # De los datos, solo tomamos la segunda columna (CC), índice 1
                    # => cc_data[:,1]
                    cc_combined.append(cc_data[:, 1])
                else:
                    # Si falta el archivo, llenar con ceros
                    # Tamaño => int(86400 / dt_cc)
                    cc_combined.append(np.zeros(int(86400 // dt_cc)))

            # Concatenar los tres días en un solo array
            cc_combined = np.concatenate(cc_combined)
            num_points = len(cc_combined)

            # Índices para el día central en el array concatenado
            start_central_day = 86400 // dt_cc
            end_central_day   = 2 * 86400 // dt_cc

            ccma_central = np.zeros(end_central_day - start_central_day)

            # Cálculo del promedio móvil (CCMA) solo para el día central
            half_window = int(twin_mvave // (2 * dt_cc))

            for i in range(start_central_day, end_central_day):
                start_idx = max(0, i - half_window)
                end_idx   = min(num_points, i + half_window + 1)

                window_data = cc_combined[start_idx:end_idx]
                # Filtramos los ceros => 'valid_data'
                valid_data = window_data[window_data != 0]

                # Verificar la cantidad mínima de datos válidos
                # El original multiplica len(valid_data) * dt_cc y lo compara con min_data
                # => si len(valid_data)*dt_cc < min_data => 0
                # Mantenemos esa lógica EXACTA
                if len(valid_data) * dt_cc < min_data:
                    ccma_central[i - start_central_day] = 0
                else:
                    ccma_central[i - start_central_day] = np.mean(valid_data)

            # Guardar solo el resultado del día central
            date_str = f"{day.year}{str(day.julday).zfill(3)}"
            output_fn = os.path.join(station_outdir, f"{date_str}.csv")

            with open(output_fn, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Tiempo (s)", "CCMA"])
                for idx, value in enumerate(ccma_central):
                    writer.writerow([idx * dt_cc, value])

            # Acumular los valores de CCMA (no cero) para la estación
            ccma_values_by_station[station].extend(ccma_central[ccma_central != 0])

            day += 86400  # Avanzar al siguiente día

        # Fin while day

    # Cálculo final de las desviaciones estándar para cada estación
    for station, ccma_values in ccma_values_by_station.items():
        ccma_values = np.array(ccma_values)

        positives = ccma_values[ccma_values > 0]
        negatives = ccma_values[ccma_values < 0]

        if positives.size > 0:
            sym_pos = np.concatenate([positives, -positives])
            std_pos = np.std(sym_pos)
        else:
            std_pos = 0

        if negatives.size > 0:
            sym_neg = np.concatenate([negatives, -negatives])
            std_neg = np.std(sym_neg)
        else:
            std_neg = 0

        # Guardar los archivos de desviación estándar
        station_outdir = os.path.join(fn_out_head, station)
        with open(os.path.join(station_outdir, "std_pos.txt"), 'w') as file:
            file.write(f"{std_pos:.6f}\n")

        with open(os.path.join(station_outdir, "std_neg.txt"), 'w') as file:
            file.write(f"{std_neg:.6f}\n")

    # Fin del bucle de estaciones

# Fin del bucle de combinaciones de frecuencia
