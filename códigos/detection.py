import os
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from obspy import UTCDateTime
from collections import deque

#--------------------------------------------------------------------
# 1. Parámetros de entrada
#--------------------------------------------------------------------
stations = ["RIOS", "CCOL", "PJIM", "TSKT"]    # Lista de estaciones

# Rango de fechas a analizar
startday = UTCDateTime(2022, 1, 1)
endday   = UTCDateTime(2022, 12, 31)

# Directorio con los archivos diarios de CCMA
input_dir = r"T:\ULTIMOS22\3000 s\0.02_0.05__2_8\ccma"

# Directorio donde se guardan los valores diarios de std_neg y std_pos
std_dir = r"T:\ULTIMOS22\3000 s\0.02_0.05__2_8\std"

# Directorio de salida para las figuras
output_dir = r"T:\ULTIMOS22\3000 s\0.02_0.05__2_8\imagenes"
os.makedirs(output_dir, exist_ok=True)

# Ventana deslizante para la probabilidad de valores extremos (5 días)
days = 5
window_seconds = days * 86400

# Bloques de 2 horas para agrupar muestras
interval_hours = 2

#--------------------------------------------------------------------
# 2. Definir los "threshold_neg" y "threshold_pos" como factores 
#    (no con signo).
#--------------------------------------------------------------------
threshold_neg = 4
threshold_pos = 4

# Factores para la lógica de "umbral mínimo"
factor_comparison = 1.15  # Si la diferencia es menor al 15%, se unifican
weight_for_bigger = 1     # Cuánto se reduce el umbral grande

#--------------------------------------------------------------------
# 3. Cargar std_neg y std_pos diarios
#    daily_std[station][day_str] = (std_neg_val, std_pos_val)
#--------------------------------------------------------------------
daily_std = {st: {} for st in stations}

def parse_day_str_to_utc(day_str):
    """
    Convierte 'YYYYDDD' a UTCDateTime (ajústalo si tu CSV usa otro formato).
    """
    year = int(day_str[:4])
    jday = int(day_str[4:])
    return UTCDateTime(year=year, julday=jday)

for station in stations:
    csv_path = os.path.join(std_dir, f"{station}.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # se espera [day_str, std_neg, std_pos]
            for row in reader:
                if len(row) < 3:
                    continue
                day_str = row[0]
                try:
                    std_neg_val = float(row[1])
                    std_pos_val = float(row[2])
                except ValueError:
                    continue
                daily_std[station][day_str] = (std_neg_val, std_pos_val)
    else:
        print(f"[ADVERTENCIA] No existe {station}.csv en {std_dir}")

#--------------------------------------------------------------------
# 4. Estructuras para acumulación (tiempo en HORAS) y eje de tiempo
#--------------------------------------------------------------------
# probabilities_neg / probabilities_pos ahora guardarán "horas acumuladas"
probabilities_neg = {st: [] for st in stations}
probabilities_pos = {st: [] for st in stations}
time_axis = []

# Cada estación lleva una cola con la data (tiempo, exceedances, total_muestras)
data_queues_neg = {st: deque() for st in stations}
data_queues_pos = {st: deque() for st in stations}

#--------------------------------------------------------------------
# Función auxiliar: cuántas muestras hacen "N horas"
#--------------------------------------------------------------------
def muestras_por_bloque(sampling_interval_s, horas):
    return int((horas * 3600) // sampling_interval_s)

#--------------------------------------------------------------------
# 5. Bucle principal: procesar cada día
#--------------------------------------------------------------------
current_day = startday
while current_day <= endday:
    # Formato juliano 'YYYYDDD'
    date_str = f"{current_day.year}{str(current_day.julday).zfill(3)}"
    data_found_for_day = False

    # Para cada estación
    for station in stations:
        file_path = os.path.join(input_dir, station, f"{date_str}.csv")
        if not os.path.exists(file_path):
            continue

        data_found_for_day = True

        # Leer std diarios
        if date_str in daily_std[station]:
            day_std_neg, day_std_pos = daily_std[station][date_str]
        else:
            day_std_neg = 0.0
            day_std_pos = 0.0

        # Leer datos CCMA
        all_times = []
        all_values = []
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)  # ["Time (s)", "CC Value"]
            for row in reader:
                t_s = float(row[0])
                val = float(row[1])
                all_times.append(t_s)
                all_values.append(val)

        if not all_times:
            continue

        # Calcular tasa de muestreo
        if len(all_times) >= 2:
            sampling_interval_s = all_times[1] - all_times[0]
            if sampling_interval_s <= 0:
                sampling_interval_s = 1.0
        else:
            sampling_interval_s = 1.0

        # Bloques de 2 horas
        samples_per_block = muestras_por_bloque(sampling_interval_s, interval_hours)

        # Acumuladores para cada bloque
        current_block_data = []
        current_exceedances_neg = 0.0
        current_exceedances_pos = 0.0

        hourly_total           = []
        hourly_exceedances_neg = []
        hourly_exceedances_pos = []

        #-----------------------------------------------------------
        # Umbrales diario (con posible unificación)
        #-----------------------------------------------------------
        base_threshold_neg = -threshold_neg * day_std_neg  # e.g. -4 * std_neg
        base_threshold_pos =  threshold_pos * day_std_pos  # e.g.  4 * std_pos

        abs_neg = abs(base_threshold_neg)
        abs_pos = abs(base_threshold_pos)

        threshold_smaller = min(abs_neg, abs_pos)
        threshold_bigger  = max(abs_neg, abs_pos)

        # Revisar si se "unifica"
        if threshold_smaller * factor_comparison > threshold_bigger:
            # Parecidos => unificar
            day_unified = threshold_smaller
            usable_neg = -day_unified
            usable_pos =  day_unified
        else:
            # Distintos => reducir el grande
            if abs_neg > abs_pos:
                abs_neg = threshold_smaller * weight_for_bigger
            else:
                abs_pos = threshold_smaller * weight_for_bigger
            usable_neg = -abs_neg
            usable_pos =  abs_pos

        #--------------------------------------------------------------------
        # 6. Recorrer las muestras del día y calcular "exceedances" 
        #    (MISMA LÓGICA DEL ORIGINAL, sin probabilidades)
        #--------------------------------------------------------------------
        for val in all_values:
            current_block_data.append(val)

            # Chequear excedencia NEG
            if val < usable_neg:
                n_neg = abs(val / day_std_neg) if day_std_neg != 0 else 0
                k_neg = threshold_neg  # (4)
                # == LÓGICA ORIGINAL ==
                current_exceedances_neg += max(0, (n_neg - k_neg + 1)**1)

            # Chequear excedencia POS
            elif val > usable_pos:
                n_pos = abs(val / day_std_pos) if day_std_pos != 0 else 0
                k_pos = threshold_pos  # (4)
                # == LÓGICA ORIGINAL ==
                current_exceedances_pos += max(0, (n_pos - k_pos + 1)**1)

            # Cuando completamos el bloque
            if len(current_block_data) == samples_per_block:
                hourly_total.append(len(current_block_data))
                hourly_exceedances_neg.append(current_exceedances_neg)
                hourly_exceedances_pos.append(current_exceedances_pos)

                # Reset
                current_block_data = []
                current_exceedances_neg = 0.0
                current_exceedances_pos = 0.0

        # Bloque incompleto
        if current_block_data:
            hourly_total.append(len(current_block_data))
            hourly_exceedances_neg.append(current_exceedances_neg)
            hourly_exceedances_pos.append(current_exceedances_pos)

        #--------------------------------------------------------------------
        # 7. Actualizar colas y convertir excedances a HORAS
        #    (ya NO se divide entre total_muestras)
        #--------------------------------------------------------------------
        for total, exceed_neg_val, exceed_pos_val in zip(hourly_total,
                                                         hourly_exceedances_neg,
                                                         hourly_exceedances_pos):

            # NEG:
            data_queues_neg[station].append((current_day.datetime, exceed_neg_val, total))
            # Descartar datos fuera de la ventana
            data_queues_neg[station] = deque(
                (t, e, v) for (t, e, v) in data_queues_neg[station]
                if (current_day.datetime - t).total_seconds() <= window_seconds
            )
            total_exceedances_neg = sum(item[1] for item in data_queues_neg[station])

            # === AQUÍ LA DIFERENCIA ===
            # Se multiplica por sampling_interval_s y se divide entre 3600 
            # para convertir "exceedances" a horas
            tiempo_acumulado_neg = (total_exceedances_neg * sampling_interval_s) / 3600.0

            probabilities_neg[station].append(tiempo_acumulado_neg)

            # POS:
            data_queues_pos[station].append((current_day.datetime, exceed_pos_val, total))
            data_queues_pos[station] = deque(
                (t, e, v) for (t, e, v) in data_queues_pos[station]
                if (current_day.datetime - t).total_seconds() <= window_seconds
            )
            total_exceedances_pos = sum(item[1] for item in data_queues_pos[station])

            tiempo_acumulado_pos = (total_exceedances_pos * sampling_interval_s) / 3600.0

            probabilities_pos[station].append(tiempo_acumulado_pos)

    #--------------------------------------------------------------------
    # 8. Actualizar eje de tiempo (time_axis)
    #--------------------------------------------------------------------
    if data_found_for_day:
        # Número de nuevos bloques generados
        new_increments = len(probabilities_neg[stations[0]]) - len(time_axis)
        time_axis.extend([
            current_day.datetime + timedelta(hours=interval_hours*i)
            for i in range(new_increments)
        ])
    else:
        # No hubo datos para este día -> se agregan 12 bloques (24h/2h)
        increments_per_day = 24 // interval_hours
        for st in stations:
            probabilities_neg[st].extend([0]*increments_per_day)
            probabilities_pos[st].extend([0]*increments_per_day)
        time_axis.extend([
            current_day.datetime + timedelta(hours=interval_hours*i)
            for i in range(increments_per_day)
        ])

    current_day += timedelta(days=1)

#--------------------------------------------------------------------
# 9. Calcular promedios (en horas de detección)
#--------------------------------------------------------------------
average_neg = {}
average_pos = {}
for station in stations:
    neg_data = probabilities_neg[station]
    pos_data = probabilities_pos[station]
    average_neg[station] = sum(neg_data)/len(neg_data) if neg_data else 0
    average_pos[station] = sum(pos_data)/len(pos_data) if pos_data else 0

#--------------------------------------------------------------------
# 10. Eventos SSE para resaltar en la gráfica (ejemplo)
#--------------------------------------------------------------------
sse_events1 = [
    (datetime(2022, 1, 30), datetime(2022, 3, 14), 6.5),
    (datetime(2022, 4, 8), datetime(2022, 5, 8), 6.7)
]
sse_events = [
    (datetime(2018, 3, 1), datetime(2018, 3, 31), 6.7),
    (datetime(2018, 8, 15), datetime(2018, 9, 25), 6.5)
]
#--------------------------------------------------------------------
# 11. Graficar resultados por estación
#     Figuras => (10,6); Títulos => fontsize=20; ejes => fontsize=16
#     ticks => 14; 
#     Ejes Y => tiempo (horas) de detección
#--------------------------------------------------------------------
for station in stations:
    station_output_dir = os.path.join(output_dir, station)
    os.makedirs(station_output_dir, exist_ok=True)

    neg_data = probabilities_neg[station]
    pos_data = probabilities_pos[station]

    # PRIMERA GRÁFICA
    fig, ax1 = plt.subplots(figsize=(10,6))
    ax1.set_xlabel("Fecha", fontsize=16)
    ax1.set_ylabel("Tiempo detección (horas) - Neg", color='black', fontsize=16)
    ax1.tick_params(axis='both', labelsize=14, labelcolor='black')

    ax1.plot(
        time_axis[:len(neg_data)],
        neg_data,
        label=f"{station} (Neg)",
        color='black',
        linestyle='--'
    )
    ax1.axhline(
        y=average_neg[station],
        color='green',
        linestyle='--',
        label=f"Promedio Neg ({station})"
    )

    ax2 = ax1.twinx()
    ax2.set_ylabel("Tiempo detección (horas) - Pos", color='blue', fontsize=16)
    ax2.tick_params(axis='y', labelsize=14, labelcolor='blue')

    ax2.plot(
        time_axis[:len(pos_data)],
        pos_data,
        label=f"{station} (Pos)",
        color='blue',
        linestyle='-'
    )
    ax2.axhline(
        y=average_pos[station],
        color='red',
        linestyle='-',
        label=f"Promedio Pos ({station})"
    )

    # Resaltar SSE
    for event_start, event_end, magnitude in sse_events1:
        ax1.axvspan(event_start, event_end, color='gray', alpha=0.3)
        mid_date = event_start + (event_end - event_start)/2
        ax1.text(
            mid_date,
            max(ax1.get_ylim()) * 0.8,
            f"SSE\n$M_{{w}}={magnitude}$",
            ha='center', va='top', fontsize=10, color='black'
        )

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=14)

    plt.title(f"Tiempo detección (hrs) - Ventana {days} días - {station}", fontsize=20)
    fig.tight_layout()
    plt.savefig(os.path.join(station_output_dir, f"probabilidad_ventana_{days}dias_{station}.png"))
    plt.close(fig)

    # SEGUNDA GRÁFICA: relleno donde se supera el promedio
    fig, ax = plt.subplots(figsize=(10,6))
    ax.set_xlabel("Fecha", fontsize=16)
    ax.set_ylabel("Acumulación con peso (negativo)", color='black', fontsize=16)
    ax.tick_params(axis='both', labelsize=10, labelcolor='black')

    proximity_threshold = 3600 * 24  # 24h
    filtered_neg_times = [
        time_axis[i] for i in range(len(neg_data)) if neg_data[i] > average_neg[station]
    ]
    filtered_neg_values = [
        neg_data[i] for i in range(len(neg_data)) if neg_data[i] > average_neg[station]
    ]

    if filtered_neg_times:
        current_times = [filtered_neg_times[0]]
        current_values = [filtered_neg_values[0]]
        for i in range(1, len(filtered_neg_times)):
            if (filtered_neg_times[i] - filtered_neg_times[i-1]).total_seconds() <= proximity_threshold:
                current_times.append(filtered_neg_times[i])
                current_values.append(filtered_neg_values[i])
            else:
                ax.fill_between(current_times, average_neg[station], current_values, color='black', alpha=0.5)
                current_times = [filtered_neg_times[i]]
                current_values = [filtered_neg_values[i]]
        ax.fill_between(current_times, average_neg[station], current_values, color='black', alpha=0.5)

    ax2 = ax.twinx()
    ax2.set_ylabel("Acumulación con peso (positivo)", color='blue', fontsize=16)
    ax2.tick_params(axis='y', labelsize=10, labelcolor='blue')
    filtered_pos_times = [
        time_axis[i] for i in range(len(pos_data)) if pos_data[i] > average_pos[station]
    ]
    filtered_pos_values = [
        pos_data[i] for i in range(len(pos_data)) if pos_data[i] > average_pos[station]
    ]

    if filtered_pos_times:
        current_times = [filtered_pos_times[0]]
        current_values = [filtered_pos_values[0]]
        for i in range(1, len(filtered_pos_times)):
            if (filtered_pos_times[i] - filtered_pos_times[i-1]).total_seconds() <= proximity_threshold:
                current_times.append(filtered_pos_times[i])
                current_values.append(filtered_pos_values[i])
            else:
                ax2.fill_between(current_times, average_pos[station], current_values, color='blue', alpha=0.5)
                current_times = [filtered_pos_times[i]]
                current_values = [filtered_pos_values[i]]
        ax2.fill_between(current_times, average_pos[station], current_values, color='blue', alpha=0.5)

    if time_axis:
        ax.set_xlim(time_axis[0], time_axis[-1])
        ax2.set_xlim(time_axis[0], time_axis[-1])

    # Resaltar SSE
    for event_start, event_end, magnitude in sse_events1:
        ax.axvspan(event_start, event_end, color='gray', alpha=0.3)
        mid_date = event_start + (event_end - event_start)/2
        ax.text(
            mid_date,
            max(ax.get_ylim()) * 0.8,
            f"SSE\n$M_{{w}}={magnitude}$",
            ha='center', va='top', fontsize=10, color='black'
        )

    ax.plot([], [], ' ')
    ax2.plot([], [], ' ')

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=10)

    plt.title(f"Detecciones acumuladas con ventana de {days} días - {station}", fontsize=20)
    fig.tight_layout()
    plt.savefig(os.path.join(station_output_dir, f"puntos_superan_promedios_{station}.png"))
    plt.close(fig)

    # Guardar CSV con tiempos
    csv_path = os.path.join(station_output_dir, f"{station}.csv")
    with open(csv_path, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["time", "type", "value"])
        for t, val in zip(filtered_neg_times, filtered_neg_values):
            writer.writerow([t.isoformat(), "neg", val])
        for t, val in zip(filtered_pos_times, filtered_pos_values):
            writer.writerow([t.isoformat(), "pos", val])

print("Guardado completado con la lógica ORIGINAL de detecciones, mostrando horas acumuladas en vez de probabilidades.")
