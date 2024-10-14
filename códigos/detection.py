import csv
import numpy as np
import os
from obspy import UTCDateTime

stations = ["RIOS"]  # Station names
startday = UTCDateTime(2018, 1, 1)  # Start date
endday = UTCDateTime(2018, 12, 31)  # End date
threshold = 4  # Detection threshold in standard deviations
fn_cc_head = r'T:\resultados_finales\modificado\cc'  # CC directory
fn_out_head = r'T:\resultados_finales\modificado\detection'  # Output directory
dt_cc = 10  # Sampling interval for CC data
twin_mvave = 10000  # Moving average window for CCMA
min_std = 0.02  # Desviación estándar mínima
min_data = 500  # Mínimo de segundos válidos para considerar una detección

# Ensure output directory exists
os.makedirs(fn_out_head, exist_ok=True)

for station in stations:
    day = startday
    cc = np.array([])  # Array for CC values
    cc_std = np.array([])  # Array for standard deviation of CC
    nday1 = 0  # Total days processed
    nday2 = 0  # Valid days with data

    while day <= endday:
        nday1 += 1
        date = f"{day.year}{str(day.julday).zfill(3)}"
        day += 86400  # Advance by one day

        fn = os.path.join(fn_cc_head, station, date + ".csv")
        if os.path.exists(fn):
            # Read the CSV file
            with open(fn, newline='') as csvfile:
                reader = csv.reader(csvfile)
                header = next(reader)  # Skip the header

                cc_tmp = []
                for row in reader:
                    cc_tmp.append([float(row[0]), float(row[1])])

            cc_tmp = np.array(cc_tmp)
            if cc_tmp.size == 0 or len(cc_tmp.shape) < 2:
                print(f"Advertencia: Archivo de correlación vacío o inválido para {date}.")
                continue

            # Append CC values
            cc = np.concatenate([cc, cc_tmp[:, 1]])
            cc_std = np.concatenate([cc_std, cc_tmp[:, 1]])
            nday2 += 1
        else:
            # Add zeros if no data for the day
            cc = np.concatenate([cc, np.zeros(int(86400 / dt_cc))])

    # Handle invalid values (NaN, infinity)
    np.nan_to_num(cc, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    np.nan_to_num(cc_std, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

    # Cálculo del promedio móvil, ignorando los valores de CC que son exactamente 0
    cc_mvave = np.zeros_like(cc)  # Prepara una matriz del mismo tamaño para almacenar el promedio móvil
    
    half_window = int(twin_mvave / (2 * dt_cc))  # Mitad de la ventana
    valid_data_count = np.zeros_like(cc)  # Almacenará el número de segundos de datos válidos en cada ventana

    for i in range(len(cc)):
        # Definir el rango de la ventana móvil
        start_idx = max(0, i - half_window)
        end_idx = min(len(cc), i + half_window + 1)

        # Seleccionar los datos válidos dentro de la ventana (valores diferentes de 0)
        valid_data = cc[start_idx:end_idx][cc[start_idx:end_idx] != 0]

        if valid_data.size > 0:
            cc_mvave[i] = np.mean(valid_data)
            valid_data_count[i] = len(valid_data) * dt_cc  # Contar los segundos válidos
        else:
            cc_mvave[i] = 0

    posinega = True

    if len(cc_std) > 0:
        cc_std_mvave = np.convolve(cc_std, np.ones(int(twin_mvave / dt_cc)) / int(twin_mvave / dt_cc), mode="same")
        std = np.std(cc_std_mvave)

        std = max(std, min_std)

        if np.count_nonzero(cc_std_mvave > std) < np.count_nonzero(cc_std_mvave < -std):
            posinega = False
            cc = -cc
            cc_mvave = -cc_mvave
    else:
        std = min_std

    pflag = False
    periods = []
    ndetect = 0
    sec_detects = 0

    for itime in range(cc.size):
        flag = cc_mvave[itime] > threshold * std
        if not pflag and flag:  # Event start
            itime_start = itime
            valid_data_start = valid_data_count[itime_start]
        if pflag and not flag:  # Event end
            itime_end = itime
            valid_data_end = valid_data_count[itime_end]
            valid_data_mean = np.mean(valid_data_count[itime_start:itime_end])

            if valid_data_mean >= min_data:
                # Calcular el tiempo promedio de los datos válidos
                valid_times = np.arange(itime_start, itime_end) * dt_cc  # Tiempos dentro del rango de la ventana
                time_weights = valid_data_count[itime_start:itime_end]  # Los segundos válidos como pesos
                weighted_avg_time = np.average(valid_times, weights=time_weights)  # Tiempo promedio ponderado

                # Convertir el tiempo promedio a UTCDateTime
                time_start = startday + dt_cc * itime_start
                time_end = startday + dt_cc * itime_end
                avg_time = startday + weighted_avg_time

                # Calcular desviación estándar, mediana y cuartiles para la ventana de segundos válidos
                valid_data_std = np.std(valid_data_count[itime_start:itime_end])
                q1 = np.percentile(valid_data_count[itime_start:itime_end], 25)
                q2 = np.percentile(valid_data_count[itime_start:itime_end], 50)  # La mediana
                q3 = np.percentile(valid_data_count[itime_start:itime_end], 75)

                # Asegurar formato consistente para la fecha y hora en el formato deseado
                time_start_str = time_start.strftime('%d/%m/%Y %H:%M:%S')
                time_end_str = time_end.strftime('%d/%m/%Y %H:%M:%S')
                avg_time_str = avg_time.strftime('%d/%m/%Y %H:%M:%S')

                # Guardar el resultado
                periods.append([time_start_str, time_end_str, avg_time_str, valid_data_mean, valid_data_std, valid_data_start, q1, q2, q3, valid_data_end])
                ndetect += 1
                sec_detects += time_end - time_start
        pflag = flag

    info = [nday1, nday2, ndetect, sec_detects, std, posinega, startday.year, startday.month, startday.day, endday.year, endday.month, endday.day]

    if len(periods) == 0:
        print("No se detectaron eventos. El archivo de salida no contendrá periodos de eventos.")

    # Save results
    with open(os.path.join(fn_out_head, station + ".csv"), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(info)
        if len(periods) > 0:
            writer.writerow(['Fecha Inicio', 'Fecha Fin', 'Tiempo Promedio', 'Promedio de segundos válidos', 'Desviación estándar de segundos válidos',
                             'Segundos válidos al inicio', 'Q1 de segundos válidos', 'Q2 de segundos válidos (Mediana)', 'Q3 de segundos válidos',
                             'Segundos válidos al final'])
            writer.writerows(periods)

