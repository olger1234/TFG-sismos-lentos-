import os
import csv
from obspy import UTCDateTime
from datetime import timedelta
import numpy as np

# =============================================================================
# Parámetros principales
# =============================================================================

stations = ["RIOS", "PJIM", "CCOL", "TSKT"]  # Las mismas estaciones que usas en CCMA.py
dir_ccma = r"T:\ULTIMOS22\3000 s\0.025_0.055__1.5_6\ccma"       # Carpeta de salida de CCMA.py
dir_out_std = r"T:\ULTIMOS22\3000 s\0.025_0.055__1.5_6\std"     # Nueva carpeta para guardar std_neg, std_pos

# Ventana local de ±28 días
par_days = 28 

# Criterios mínimos
min_days_required = 28       # Al menos 28 días efectivos en la ventana
min_coverage_ratio = 0.50    # Al menos 50% de muestras válidas (CCMA != 0)

# Crear carpeta de salida si no existe
os.makedirs(dir_out_std, exist_ok=True)

# =============================================================================
# 1) Leer std_global (calculada en ccma.py) para cada estación
# =============================================================================

global_std = {}
for st in stations:
    station_folder = os.path.join(dir_ccma, st)
    path_std_neg = os.path.join(station_folder, "std_neg.txt")
    path_std_pos = os.path.join(station_folder, "std_pos.txt")

    if not os.path.exists(path_std_neg):
        gneg = 0.0
    else:
        with open(path_std_neg, "r") as fn:
            gneg = float(fn.read().strip())

    if not os.path.exists(path_std_pos):
        gpos = 0.0
    else:
        with open(path_std_pos, "r") as fp:
            gpos = float(fp.read().strip())

    global_std[st] = (gneg, gpos)

# =============================================================================
# Funciones auxiliares para manejar fechas y archivos CCMA
# Ajusta si tus archivos usan otro formato (YYYYMMDD, etc.)
# =============================================================================

def parse_day_str_to_utc(day_str):
    """
    Convierte un string 'YYYYDDD' a UTCDateTime.
    Por ejemplo, '2022015' => 2022, día 15 del año (15 enero 2022).
    Si tus archivos usan 'YYYYMMDD', debes adaptar este parseo.
    """
    year = int(day_str[:4])
    jday = int(day_str[4:])
    return UTCDateTime(year=year, julday=jday)

def format_utc_to_day_str(dt):
    """
    Convierte un UTCDateTime a 'YYYYDDD'.
    Ajusta si deseas otro formato (p.ej. 'YYYYMMDD').
    """
    return f"{dt.year}{str(dt.julday).zfill(3)}"

def load_ccma_data(station):
    """
    Carga todos los archivos .csv de CCMA para una estación dada.
    Devuelve un diccionario: day_str -> lista de valores CCMA.
    (day_str típicamente 'YYYYDDD')
    """
    station_folder = os.path.join(dir_ccma, station)
    data_by_day = {}
    if not os.path.exists(station_folder):
        return data_by_day

    for file_name in os.listdir(station_folder):
        if not file_name.endswith(".csv"):
            continue
        # Extraemos "YYYYDDD" del nombre
        day_str = file_name.replace(".csv", "")

        file_path = os.path.join(station_folder, file_name)
        ccma_values = []
        with open(file_path, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # ["Tiempo (s)", "CCMA"]
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    val = float(row[1])
                    ccma_values.append(val)
                except ValueError:
                    pass

        data_by_day[day_str] = ccma_values

    return data_by_day

# =============================================================================
# Paso 1: Cargar datos de CCMA para todas las estaciones
# =============================================================================

all_ccma_data = {}
for st in stations:
    all_ccma_data[st] = load_ccma_data(st)

# =============================================================================
# Estructura para guardar std_neg y std_pos: 
# std_by_station_and_day[station][day_str] = (std_neg, std_pos)
# =============================================================================

std_by_station_and_day = {st: {} for st in stations}

# =============================================================================
# Paso 2: Calcular std_neg y std_pos para cada día (ventana ± par_days)
# =============================================================================

def calc_std_neg_pos(values_array):
    """
    Recibe un array con valores CCMA != 0.
    Retorna (std_neg, std_pos) siguiendo el criterio de ccma.py
    usando distribución simétrica: 
      - positives -> concatenar(positives, -positives) => std
      - negatives -> concatenar(negatives, -negatives) => std
    """
    positives = values_array[values_array > 0]
    negatives = values_array[values_array < 0]

    # Calcular std_pos
    if positives.size > 0:
        sym_pos = np.concatenate([positives, -positives])
        std_pos = np.std(sym_pos, ddof=0)  # ddof=0 => población
    else:
        std_pos = 0.0

    # Calcular std_neg
    if negatives.size > 0:
        sym_neg = np.concatenate([negatives, -negatives])
        std_neg = np.std(sym_neg, ddof=0)
    else:
        std_neg = 0.0

    return std_neg, std_pos

for station in stations:
    data_by_day = all_ccma_data[station]  # {day_str: [ccma_vals]}
    day_str_list = sorted(data_by_day.keys(), key=lambda ds: parse_day_str_to_utc(ds))

    for dstr in day_str_list:
        day_utc = parse_day_str_to_utc(dstr)
        left_utc  = day_utc - 86400 * par_days
        right_utc = day_utc + 86400 * par_days

        combined_ccma = []
        days_in_window = 0

        # 1) Contar días en la ventana
        for candidate_str in day_str_list:
            cand_utc = parse_day_str_to_utc(candidate_str)
            if left_utc <= cand_utc <= right_utc:
                days_in_window += 1

        if days_in_window < min_days_required:
            std_by_station_and_day[station][dstr] = (None, None)
            continue

        # 2) Validar ratio de cobertura
        total_ccma_points = 0
        nonzero_points = 0

        for candidate_str in day_str_list:
            cand_utc = parse_day_str_to_utc(candidate_str)
            if left_utc <= cand_utc <= right_utc:
                ccma_list = data_by_day[candidate_str]
                total_ccma_points += len(ccma_list)
                nonzero_points     += sum(1 for v in ccma_list if v != 0.0)

        if total_ccma_points == 0:
            std_by_station_and_day[station][dstr] = (None, None)
            continue

        coverage_ratio = nonzero_points / total_ccma_points
        if coverage_ratio < min_coverage_ratio:
            std_by_station_and_day[station][dstr] = (None, None)
            continue

        # 3) Recolectar CCMA != 0 en la ventana
        for candidate_str in day_str_list:
            cand_utc = parse_day_str_to_utc(candidate_str)
            if left_utc <= cand_utc <= right_utc:
                valid_vals = [v for v in data_by_day[candidate_str] if v != 0.0]
                combined_ccma.extend(valid_vals)

        arr_ccma = np.array(combined_ccma, dtype=float)
        if len(arr_ccma) == 0:
            std_by_station_and_day[station][dstr] = (None, None)
        else:
            std_neg, std_pos = calc_std_neg_pos(arr_ccma)
            std_by_station_and_day[station][dstr] = (std_neg, std_pos)

# =============================================================================
# Paso 3: Rellenar valores None usando el día válido más cercano (hacia adelante y atrás)
# =============================================================================

def fill_missing_with_nearest(day_list, std_map):
    """
    day_list: lista ordenada de day_str
    std_map: diccionario day_str -> (std_neg, std_pos) o (None, None)

    Recorre la lista dos veces:
      1) hacia adelante,
      2) hacia atrás
    para rellenar (None, None) con el valor más cercano disponible.
    """
    # Hacia adelante
    last_valid = None
    for dstr in day_list:
        neg_pos = std_map[dstr]
        if neg_pos[0] is not None and neg_pos[1] is not None:
            last_valid = neg_pos
        else:
            if last_valid is not None:
                std_map[dstr] = last_valid

    # Hacia atrás
    next_valid = None
    for dstr in reversed(day_list):
        neg_pos = std_map[dstr]
        if neg_pos[0] is not None and neg_pos[1] is not None:
            next_valid = neg_pos
        else:
            if next_valid is not None:
                std_map[dstr] = next_valid

for station in stations:
    day_str_list = sorted(all_ccma_data[station].keys(), key=lambda ds: parse_day_str_to_utc(ds))
    fill_missing_with_nearest(day_str_list, std_by_station_and_day[station])

# =============================================================================
# Paso 3b: Asignar la std global a los días que sigan en None
# (solo si definitivamente no hubo día cercano válido)
# =============================================================================
for station in stations:
    gneg, gpos = global_std[station]
    for dstr, (std_neg, std_pos) in std_by_station_and_day[station].items():
        if std_neg is None or std_pos is None:
            std_by_station_and_day[station][dstr] = (gneg, gpos)

# =============================================================================
# Paso 4: Guardar en {station}.csv con columnas: day_str, std_neg, std_pos
#         Si el archivo existe, solo agregamos días faltantes
#         *** Se agrega tope de 0.1 al final ***
# =============================================================================

for station in stations:
    output_file = os.path.join(dir_out_std, f"{station}.csv")
    existing_days = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # "day_str", "std_neg", "std_pos"
            for row in reader:
                if row:
                    existing_days.add(row[0])

    with open(output_file, 'a', newline='') as f:
        writer = csv.writer(f)
        # Si está vacío, ponemos cabecera
        if os.path.getsize(output_file) == 0:
            writer.writerow(["day_str", "std_neg", "std_pos"])

        day_str_list = sorted(all_ccma_data[station].keys(), key=lambda ds: parse_day_str_to_utc(ds))
        for dstr in day_str_list:
            if dstr not in existing_days:
                (std_neg, std_pos) = std_by_station_and_day[station][dstr]
                # Por seguridad, si quedara None
                if std_neg is None:
                    std_neg = global_std[station][0]
                if std_pos is None:
                    std_pos = global_std[station][1]

                # *** Ajustar máximo a 0.1 ***
                if std_neg > 0.1:
                    std_neg = 0.1
                if std_pos > 0.1:
                    std_pos = 0.1

                # Guardar con 6 decimales
                writer.writerow([dstr, f"{std_neg:.6f}", f"{std_pos:.6f}"])

print("Cálculo de std_neg y std_pos completado. Archivos guardados en:", dir_out_std)
