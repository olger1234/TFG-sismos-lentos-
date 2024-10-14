import os
import csv
from datetime import datetime, timedelta

# Definir rutas de directorios
rms_clas_dir = r'T:\detecciones2018\rms_clas'
deteccion_dir = r'T:\detecciones2018\detection\2.7'
output_dir = r'T:\detecciones2018\detection_rms'

# Función para leer el archivo de clasificaciones RMS
def leer_clasificaciones(rms_clas_file):
    with open(rms_clas_file, 'r') as f:
        clasificaciones = f.read().splitlines()  # Leer todas las clasificaciones
    return clasificaciones

# Función para verificar si el tiempo de la detección cae en intervalos "b"
def es_deteccion_valida(fecha_inicio, fecha_fin, clasificaciones):
    # Cada intervalo es 86400 / len(clasificaciones) segundos
    interval_length = 86400 / len(clasificaciones)

    # Convertir las fechas de inicio y fin en segundos desde el comienzo del día
    inicio_seg = (fecha_inicio - fecha_inicio.replace(hour=0, minute=0, second=0)).total_seconds()
    fin_seg = (fecha_fin - fecha_fin.replace(hour=0, minute=0, second=0)).total_seconds()

    # Calcular los índices en la lista de clasificaciones
    inicio_idx = int(inicio_seg // interval_length)
    fin_idx = int(fin_seg // interval_length)

    # Verificar que todas las clasificaciones en ese rango sean "b"
    for idx in range(inicio_idx, fin_idx + 1):
        if clasificaciones[idx] != 'b':
            return False
    return True

# Leer detecciones y filtrarlas según las clasificaciones
def filtrar_detecciones(deteccion_file, clasificaciones_file, output_file):
    # Leer clasificaciones
    clasificaciones = leer_clasificaciones(clasificaciones_file)

    with open(deteccion_file, 'r') as f_in, open(output_file, 'w', newline='') as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)

        # Leer encabezado y escribir en archivo de salida
        encabezado = next(reader)
        writer.writerow(encabezado)

        # Filtrar detecciones
        for row in reader:
            fecha_inicio_str = row[0]
            fecha_fin_str = row[1]

            # Saltar la fila si contiene los encabezados o cualquier valor no relacionado con las fechas
            if 'Fecha Inicio' in fecha_inicio_str or 'Fecha Fin' in fecha_fin_str:
                continue  # Omitir la fila del encabezado

            # Verificar si las fechas de la fila no son encabezados (caso de tener una fila sin datos válidos)
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%d/%m/%Y %H:%M:%S')
                fecha_fin = datetime.strptime(fecha_fin_str, '%d/%m/%Y %H:%M:%S')
            except ValueError as e:
                print(f"Error en la conversión de fecha: {e}. Saltando fila.")
                continue  # Saltar esta fila si hay un error en el formato de fecha

            # Verificar si la detección es válida
            if es_deteccion_valida(fecha_inicio, fecha_fin, clasificaciones):
                writer.writerow(row)

# Función principal para procesar todos los archivos
def procesar_detecciones(station):
    julian_day = 10  # Día juliano de ejemplo, ajusta esto a lo necesario
    rms_clas_file = os.path.join(rms_clas_dir, f'{station}_2018{str(julian_day).zfill(3)}_clas.csv')
    deteccion_file = os.path.join(deteccion_dir, f'{station}.csv')
    output_file = os.path.join(output_dir, f'{station}.rms.csv')

    if os.path.exists(rms_clas_file) and os.path.exists(deteccion_file):
        filtrar_detecciones(deteccion_file, rms_clas_file, output_file)
        print(f'Archivo procesado: {output_file}')
    else:
        print(f'Archivo no encontrado para la estación {station} o día {julian_day}')

# Ejecutar para la estación "RIOS"
procesar_detecciones("RIOS")
