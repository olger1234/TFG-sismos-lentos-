import os
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from obspy import UTCDateTime

# --------------------------------------------------------------------------------
# 1. Parámetros principales
# --------------------------------------------------------------------------------
stations = ["RIOS", "CCOL", "PJIM", "TSKT"]

# Rango global de fechas
startday = UTCDateTime(2022, 1, 1)
endday   = UTCDateTime(2022, 12, 31)

# Directorios de distintas frecuencias, cada uno con un peso
freq_dirs = [
    r"T:\ULTIMOS22\3000 s\0.02_0.05__2_8",
    r"T:\ULTIMOS22\3000 s\0.015_0.045__1.5_6",
    r"T:\ULTIMOS22\3000 s\0.025_0.055__1.5_6"
]
freq_weights = [1, 1, 1]  # Ejemplo de pesos

# Directorio de salida final
output_dir = r"T:\ULTIMOS22\3000 s\total"
os.makedirs(output_dir, exist_ok=True)

# Intervalo de bloque (2 horas). Se usa para la gráfica y manejo de tiempos
interval_hours = 2

# Eventos SSE (si están en el rango, se dibujan)
sse_events1 = [
    (datetime(2022, 1, 30), datetime(2022, 3, 14), 6.5),
    (datetime(2022, 4, 8), datetime(2022, 5, 8), 6.7)
]
sse_events2 = [
    (datetime(2018, 3, 1), datetime(2018, 3, 31), 6.7),
    (datetime(2018, 8, 15), datetime(2018, 9, 25), 6.5)
]
all_sse_events = sse_events1 + sse_events2  # Los juntamos en una sola lista

# --------------------------------------------------------------------------------
# 2. Funciones auxiliares
# --------------------------------------------------------------------------------

def parse_iso_to_datetime(timestr):
    """
    Convierte un string tipo '2022-10-28T16:00:00' a datetime.
    """
    return datetime.fromisoformat(timestr)

def overlaps_with_range(event_start, event_end, plot_start, plot_end):
    """
    Verifica si el evento SSE [event_start, event_end] se traslapa
    con el rango [plot_start, plot_end].
    """
    return (event_end >= plot_start) and (event_start <= plot_end)

# --------------------------------------------------------------------------------
# 3. Bucle por estación: sumar valores y generar la gráfica
# --------------------------------------------------------------------------------
plot_start = startday.datetime
plot_end   = endday.datetime

for station in stations:
    # Diccionario donde acumulamos la detección final:
    #   accum_data[dt] = [neg_val, pos_val]
    #   *neg_val* será el valor máximo en ese instante para "neg"
    #   *pos_val* será el valor máximo en ese instante para "pos"
    accum_data = {}

    # (A) Recorremos cada frecuencia y combinamos sus valores
    for freq_dir, weight in zip(freq_dirs, freq_weights):
        # Se asume que en freq_dir\imagenes\{station}\{station}.csv
        # existe un archivo con columnas [time, type, value]
        station_csv_path = os.path.join(freq_dir, "imagenes", station, f"{station}.csv")
        if not os.path.exists(station_csv_path):
            continue

        with open(station_csv_path, 'r', newline='') as infile:
            reader = csv.reader(infile)
            header = next(reader, None)  # ["time", "type", "value"]
            for row in reader:
                if len(row) < 3:
                    continue

                timestr, typ, val_str = row[0], row[1], row[2]
                try:
                    val = float(val_str)
                except ValueError:
                    continue

                dt = parse_iso_to_datetime(timestr)
                # Solo consideramos si dt está dentro de [startday, endday]
                if dt < plot_start or dt > plot_end:
                    continue

                if dt not in accum_data:
                    accum_data[dt] = [0.0, 0.0]  # [neg, pos]

                # Multiplicamos por su peso
                weighted_val = weight * val

                # Si es "neg", tomamos el valor MÁXIMO
                if typ == "neg":
                    accum_data[dt][0] = max(accum_data[dt][0], weighted_val)
                # Si es "pos", lo mismo
                elif typ == "pos":
                    accum_data[dt][1] = max(accum_data[dt][1], weighted_val)

    # (B) Ordenamos las marcas de tiempo
    sorted_times = sorted(accum_data.keys())

    # (C) Crear carpeta de salida para la estación
    station_out_dir = os.path.join(output_dir, station)
    os.makedirs(station_out_dir, exist_ok=True)

    # (D) Guardar archivo final station.csv (time, type, value)
    out_csv_path = os.path.join(station_out_dir, f"{station}.csv")
    with open(out_csv_path, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["time", "type", "value"])
        for dt in sorted_times:
            neg_val = accum_data[dt][0]
            pos_val = accum_data[dt][1]
            # Si ambos = 0, no se escribe
            if abs(neg_val) > 0:
                writer.writerow([dt.isoformat(), "neg", f"{neg_val:.6e}"])
            if abs(pos_val) > 0:
                writer.writerow([dt.isoformat(), "pos", f"{pos_val:.6e}"])

    # (E) Para graficar, reconstruimos arrays de (time_list, neg_vals, pos_vals)
    #     con una resolución de 2 horas desde plot_start hasta plot_end
    time_list = []
    neg_vals  = []
    pos_vals  = []

    current_time = plot_start
    while current_time <= plot_end:
        if current_time in accum_data:
            neg_vals.append(accum_data[current_time][0])
            pos_vals.append(accum_data[current_time][1])
        else:
            neg_vals.append(0.0)
            pos_vals.append(0.0)
        time_list.append(current_time)
        current_time += timedelta(hours=interval_hours)

    # --------------------------------------------------------------------------
    # (F) Gráfica SIN promedio: rellenar desde 0 hasta cada valor
    # --------------------------------------------------------------------------
    # >>> Ajustamos la figura a (10, 6), fuente de títulos=20, ejes=16, ticks=14
    fig, ax = plt.subplots(figsize=(10, 6))  # Tamaño de figura

    ax.set_xlabel("Fecha", fontsize=16)                # Eje X
    ax.set_ylabel("Acumulación (negativo)", color='black', fontsize=16)
    ax.tick_params(axis='both', labelsize=10, labelcolor='black')

    proximity_threshold = 3600 * 24  # 24h
    if time_list:
        current_times  = [time_list[0]]
        current_values = [neg_vals[0]]
        for i in range(1, len(time_list)):
            delta_sec = (time_list[i] - time_list[i - 1]).total_seconds()
            if delta_sec <= proximity_threshold:
                current_times.append(time_list[i])
                current_values.append(neg_vals[i])
            else:
                ax.fill_between(
                    current_times,
                    0,
                    current_values,
                    color='black',
                    alpha=0.5
                )
                current_times  = [time_list[i]]
                current_values = [neg_vals[i]]
        ax.fill_between(
            current_times,
            0,
            current_values,
            color='black',
            alpha=0.5
        )

    ax2 = ax.twinx()
    ax2.set_ylabel("Acumulación (positivo)", color='blue', fontsize=16)
    ax2.tick_params(axis='y', labelsize=10, labelcolor='blue')

    if time_list:
        current_times  = [time_list[0]]
        current_values = [pos_vals[0]]
        for i in range(1, len(time_list)):
            delta_sec = (time_list[i] - time_list[i - 1]).total_seconds()
            if delta_sec <= proximity_threshold:
                current_times.append(time_list[i])
                current_values.append(pos_vals[i])
            else:
                ax2.fill_between(
                    current_times,
                    0,
                    current_values,
                    color='blue',
                    alpha=0.5
                )
                current_times  = [time_list[i]]
                current_values = [pos_vals[i]]
        ax2.fill_between(
            current_times,
            0,
            current_values,
            color='blue',
            alpha=0.5
        )

    ax.set_xlim(plot_start, plot_end)
    ax2.set_xlim(plot_start, plot_end)

    # Resaltar SSE si caen en este rango
    for (event_start, event_end, magnitude) in all_sse_events:
        if overlaps_with_range(event_start, event_end, plot_start, plot_end):
            ax.axvspan(event_start, event_end, color='gray', alpha=0.3)
            mid_date = event_start + (event_end - event_start) / 2
            ax.text(
                mid_date,
                max(ax.get_ylim()) * 0.8,
                f"SSE\n$M_{{w}}={magnitude}$",
                ha='center',
                va='top',
                fontsize=10,
                color='black'
            )

    # Título con fuente tamaño 20
    plt.title(f"Detecciones en 3 combinaciones de frecuencias - {station} - 2022", fontsize=20)

    fig.tight_layout()
    out_fig_path = os.path.join(station_out_dir, f"puntos_todos_{station}.png")
    plt.savefig(out_fig_path)
    plt.close(fig)

print("Proceso completado. Archivos finales y gráficas almacenadas en:", output_dir)
