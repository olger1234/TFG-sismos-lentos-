import os 
import csv
import math
import itertools
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from obspy import UTCDateTime

# --------------------------------------------------------------------------
# 1. Parámetros principales
# --------------------------------------------------------------------------
dir_in = r"T:\ULTIMOS22\3000 s\total"   # Directorio con station.csv por estación (de Totalfreq.py)
dir_out = r"T:\ULTIMOS22\3000 s\red"    # Directorio de salida final
os.makedirs(dir_out, exist_ok=True)

# Definición de las redes (ejemplo)
red1 = ["PJIM", "TSKT"]
red2 = ["RIOS", "CCOL", "PJIM"]
red3 = ["RIOS", "CCOL", "PJIM", "TSKT"]
redes = {
    "red1": red1,
    "red2": red2,
    "red3": red3
}

# Mínimo de estaciones en la subcombinación
min_red = 2

# Rango de fechas a analizar
startday = UTCDateTime(2022, 1, 1)
endday   = UTCDateTime(2022, 12, 31)
plot_start = startday.datetime
plot_end   = endday.datetime

# Intervalo de muestreo (coincide con 2h)
interval_hours = 2

# SSE conocidos
sse_events1 = [
    (datetime(2022, 1, 30), datetime(2022, 3, 14), 6.5),
    (datetime(2022, 4, 8), datetime(2022, 5, 8), 6.7)
]
sse_events2 = [
    (datetime(2018, 3, 1), datetime(2018, 3, 31), 6.7),
    (datetime(2018, 8, 15), datetime(2018, 9, 25), 6.5)
]
all_sse_events = sse_events1 + sse_events2

# --------------------------------------------------------------------------
# 2. Funciones auxiliares
# --------------------------------------------------------------------------
def parse_iso_to_dt(timestr: str) -> datetime:
    """Convierte 'YYYY-MM-DDTHH:MM:SS' a datetime."""
    return datetime.fromisoformat(timestr)

def overlaps(event_start, event_end, global_start, global_end):
    """Verifica si [event_start, event_end] se traslapa con [global_start, global_end]."""
    return not (event_end < global_start or event_start > global_end)

def format_duration(delta_sec: float) -> str:
    """Convierte segundos en 'Xd Xh Xmin Xs'."""
    total = int(delta_sec)
    d = total // 86400
    r = total % 86400
    h = r // 3600
    r = r % 3600
    m = r // 60
    s = r % 60
    parts = []
    if d > 0: parts.append(f"{d}d")
    if h > 0: parts.append(f"{h}h")
    if m > 0: parts.append(f"{m}min")
    if s > 0: parts.append(f"{s}s")
    if not parts:
        parts = ["0s"]
    return " ".join(parts)

def get_combinations(stations_list, min_size):
    """Genera todas las combinaciones de stations_list con longitud >= min_size."""
    results = []
    n = len(stations_list)
    for r in range(min_size, n+1):
        for combo in itertools.combinations(stations_list, r):
            results.append(list(combo))
    return results

# --------------------------------------------------------------------------
# 3. Cargar datos de detección por estación (de T:\ULTIMOS18\total\STATION\station.csv)
# --------------------------------------------------------------------------
all_stations = set()
for r_name, r_list in redes.items():
    for st in r_list:
        all_stations.add(st)
all_stations = list(all_stations)  # Conjunto único de estaciones

station_detections = {}
for station in all_stations:
    station_csv = os.path.join(dir_in, station, f"{station}.csv")
    detections = set()
    if os.path.exists(station_csv):
        with open(station_csv, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # ["time","type","value"]
            for row in reader:
                if len(row) < 3:
                    continue
                t_str, t_type, t_val = row
                dt = parse_iso_to_dt(t_str)
                if plot_start <= dt <= plot_end:
                    detections.add(dt)
    station_detections[station] = detections

# --------------------------------------------------------------------------
# 4. Lógica principal por cada red
# --------------------------------------------------------------------------
for red_name, stations_list in redes.items():
    red_dir = os.path.join(dir_out, red_name)
    os.makedirs(red_dir, exist_ok=True)

    combos = get_combinations(stations_list, min_red)  
    intervals_by_combo = {}

    # ----------------------------------------------------------------------
    # 4.1 Procesar cada subcombinación
    # ----------------------------------------------------------------------
    for combo in combos:
        combo_name = "_".join(combo)
        combo_dir = os.path.join(red_dir, combo_name)
        os.makedirs(combo_dir, exist_ok=True)

        # Intersección de detecciones
        common_set = station_detections[combo[0]]
        for st in combo[1:]:
            common_set = common_set.intersection(station_detections[st])

        times_sorted = sorted(common_set)

        # Unir consecutivos (asumiendo delta = 2h => mismo evento)
        intervals = []
        if times_sorted:
            start_event = times_sorted[0]
            last_time   = times_sorted[0]
            for i in range(1, len(times_sorted)):
                dt = times_sorted[i]
                delta_sec = (dt - last_time).total_seconds()
                if abs(delta_sec - interval_hours*3600) < 1.0:
                    last_time = dt
                else:
                    intervals.append((start_event, last_time))
                    start_event = dt
                    last_time   = dt
            intervals.append((start_event, last_time))

        intervals_by_combo[combo_name] = intervals

        # 4.1.1 Guardar CSV de subcombinación
        csv_path = os.path.join(combo_dir, f"{combo_name}.csv")
        with open(csv_path, 'w', newline='') as out_f:
            wr = csv.writer(out_f)
            wr.writerow(["time_ini","time_end","duration"])
            for (ini, fin) in intervals:
                dur_sec = (fin - ini).total_seconds()
                wr.writerow([ini.isoformat(), fin.isoformat(), format_duration(dur_sec)])

        # 4.1.2 Generar la gráfica individual de esta subcombinación
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlabel("Fecha")
        ax.set_ylabel(f"Detección Conjunta ({combo_name})", color='black')

        # Construimos un timeline de 2h para todo el rango
        time_list = []
        val_list  = []
        current_time = plot_start
        while current_time <= plot_end:
            # ver si current_time cae en algún intervalo (ini, fin)
            is_detected = 0
            for (ini, fin) in intervals:
                if ini <= current_time <= fin:
                    is_detected = 1
                    break
            time_list.append(current_time)
            val_list.append(is_detected)
            current_time += timedelta(hours=interval_hours)

        # Rellenar
        if any(val_list):
            state = 0
            seg_start = None
            for i in range(len(val_list)):
                v = val_list[i]
                if v == 1 and state == 0:
                    seg_start = time_list[i]
                    state = 1
                elif v == 0 and state == 1:
                    seg_end = time_list[i]
                    ax.axvspan(seg_start, seg_end, color='blue', alpha=0.3)
                    state = 0
            if state == 1:
                seg_end = time_list[-1]
                ax.axvspan(seg_start, seg_end, color='blue', alpha=0.3)

        # Resaltar SSE
        for (sse_ini, sse_fin, magnitude) in all_sse_events:
            if overlaps(sse_ini, sse_fin, plot_start, plot_end):
                ax.axvspan(sse_ini, sse_fin, color='gray', alpha=0.2)
                mid_sse = sse_ini + (sse_fin - sse_ini)/2
                ax.text(
                    mid_sse,
                    max(ax.get_ylim()) * 0.8,
                    f"SSE\n$M_{{w}}={magnitude}$",
                    ha='center',
                    va='top',
                    fontsize=10,
                    color='black'
                )

        ax.tick_params(axis='y', labelcolor='black')
        ax.set_xlim(plot_start, plot_end)
        ax.set_ylim(0, 1)

        plt.title(f"{red_name} - Subcombinación {combo_name}")
        fig.tight_layout()

        out_fig_path = os.path.join(combo_dir, f"{combo_name}.png")
        plt.savefig(out_fig_path)
        plt.close(fig)

    # ----------------------------------------------------------------------
    # 4.2 Crear analysis.csv => mezcla de todas las subcombinaciones
    # ----------------------------------------------------------------------
    all_entries = []
    for combo_name, intervals_list in intervals_by_combo.items():
        combo_size = combo_name.count("_") + 1
        for (ini, fin) in intervals_list:
            dur_sec = (fin - ini).total_seconds()
            dur_str = format_duration(dur_sec)
            all_entries.append((ini, fin, dur_str, combo_name, combo_size))

    # Ordenar por time_ini asc, luego combo_size asc
    all_entries.sort(key=lambda x: (x[0], x[4]))

    analysis_csv_path = os.path.join(red_dir, "analysis.csv")
    with open(analysis_csv_path, 'w', newline='') as out_f:
        wr = csv.writer(out_f)
        wr.writerow(["time_ini","time_end","duration","subred"])
        for (ini, fin, dur_str, combo_name, size) in all_entries:
            wr.writerow([ini.isoformat(), fin.isoformat(), dur_str, combo_name])

    # ----------------------------------------------------------------------
    # 4.3 Generar las gráficas por cardinalidad (2.. n)
    #     >> Aquí implementamos los cambios solicitados <<
    # ----------------------------------------------------------------------
    max_cardinality = len(stations_list)
    from matplotlib.cm import get_cmap
    cmap = get_cmap("tab10")

    color_map_dict = {}
    for i, combo in enumerate(combos):
        c_name = "_".join(combo)
        color_map_dict[c_name] = cmap(i % 10)  # repetirá si hay >10 combos

    for c in range(min_red, max_cardinality+1):
        combos_c = [cb for cb in combos if len(cb) == c]

        # Figura y fuentes
        fig, ax = plt.subplots(figsize=(10,6))  
        ax.set_xlabel("Fecha", fontsize=16)    
        ax.tick_params(axis='x', labelsize=12)
        # Ocultamos eje Y
        ax.set_ylabel("")
        ax.set_yticks([])
        ax.tick_params(axis='y', labelleft=False, labelsize=14)

        base_level = 0.8
        band_step = 0.03

        # Para controlar la leyenda: solo agregamos subcombinaciones que 
        # hayan dibujado algo
        legend_patches = []
        combos_that_plotted = set()

        for i_combo, combo in enumerate(combos_c):
            c_name = "_".join(combo)
            intervals_c = intervals_by_combo[c_name]
            if not intervals_c:
                # Si no hay intervalos => no hay nada que pintar
                continue

            color_sub = color_map_dict[c_name]
            band_bottom = base_level + band_step*i_combo
            band_top    = band_bottom + band_step
            if band_top > 1.0:
                band_top = 1.0

            # Rellenar para cada intervalo en 2 franjas: [0,0.8] y [band_bottom, band_top]
            for (ini, fin) in intervals_c:
                # Franja 0 -> 0.8
                ax.fill_betweenx(
                    [0, 0.8],
                    ini,
                    fin,
                    color=color_sub,
                    alpha=0.4
                )
                # Franja "exclusiva" [band_bottom, band_top]
                ax.fill_betweenx(
                    [band_bottom, band_top],
                    ini,
                    fin,
                    color=color_sub,
                    alpha=0.4
                )

            # Si llegamos aquí, se pintó algo => se agrega a leyenda
            combos_that_plotted.add(c_name)

        # Resaltar SSE
        for (sse_ini, sse_fin, magnitude) in all_sse_events:
            if overlaps(sse_ini, sse_fin, plot_start, plot_end):
                ax.axvspan(sse_ini, sse_fin, ymin=0, ymax=1, color='gray', alpha=0.2)
                mid_sse = sse_ini + (sse_fin - sse_ini)/2
                ax.text(
                    mid_sse,
                    0.95,
                    f"SSE\n$M_{{w}}={magnitude}$",
                    ha='center',
                    va='top',
                    fontsize=10,
                    color='black'
                )

        ax.set_xlim(plot_start, plot_end)
        ax.set_ylim(0, 1.05)

        # Construir la leyenda
        for combo in combos_c:
            c_name = "_".join(combo)
            if c_name in combos_that_plotted:
                color_sub = color_map_dict[c_name]
                legend_patches.append(
                    plt.Line2D([0],[0],
                        marker='s', color=color_sub, alpha=0.4,
                        linestyle='None', markersize=10,
                        label=c_name
                    )
                )
        if legend_patches:
            ax.legend(
                handles=legend_patches,
                title=f"Subred",
                loc="upper right",
                facecolor="white",
                framealpha=0.7
            )

        plt.title(f"Detección conjunta en subredes de {c} estaciones - en 2022", fontsize=20)
        fig.tight_layout()

        out_fig_path_c = os.path.join(red_dir, f"subredes_{c}_est.png")
        plt.savefig(out_fig_path_c)
        plt.close(fig)

print("Proceso completado. Archivos analysis.csv y figuras generadas en:", dir_out)
