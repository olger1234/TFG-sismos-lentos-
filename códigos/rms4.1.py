from obspy import read, UTCDateTime, Stream
import numpy as np
import os

# Parámetros y directorios
stations = ["RIOS"]
components = ["HHZ", "HHN", "HHE"]
dt = 0.01  # Intervalo de muestreo (s) - equivalente a 100 Hz
fn_head = r'T:\RIOS'  # Directorio de entrada
dir_out = r'T:\detecciones2018\rms'  # Directorio de salida de RMS
dir_out_clas = r'T:\detecciones2018\rms_clas'  # Directorio de salida de clasificaciones
log_file_path = os.path.join(dir_out, "debug_log.txt")  # Archivo de log

# Definir el rango de fechas para el procesamiento
startday = UTCDateTime(2018, 1, 1)  # Fecha de inicio
endday = UTCDateTime(2018, 12, 31)    # Fecha de fin

# Definir el intervalo en minutos
interval_minutes = 5  # Ajustar este parámetro para el intervalo deseado
num_intervals = int(1440 / interval_minutes)  # Número de intervalos por día

# Parámetros de clasificación
max_noice = 62.7604
min_noice = 10**-4

# Crear directorios si no existen
os.makedirs(dir_out, exist_ok=True)
os.makedirs(dir_out_clas, exist_ok=True)  # Crear el nuevo directorio de clasificaciones

# Abrimos el archivo de log para escribir
with open(log_file_path, mode="w") as log_file:

    # Listas de RMS alta y baja frecuencia
    rms_hf = [0, 0, 0]  
    rms_lf = [0, 0, 0]  

    for station in stations:
        day = startday  # Comenzar desde la fecha de inicio
        while day <= endday:  # Bucle hasta la fecha de fin
            # Formato juliano: YYYY + día juliano (tres dígitos)
            date = f"{day.year}{str(day.julday).zfill(3)}"
            log_file.write(f"Procesando día {day.strftime('%Y-%m-%d')}\n")
            st = Stream()
            components_loaded = 0  # Contador de componentes cargadas

            # Leer los archivos por componente
            for component in components:
                fn = os.path.join(fn_head, f"i4.{station}.{component}.{date}_0+")
                log_file.write(f"Cargando archivo: {fn}\n")
                
                if os.path.exists(fn):
                    try:
                        st += read(fn)  # Leer archivo
                        components_loaded += 1  # Aumentar el contador de componentes leídas correctamente
                        log_file.write(f"Archivo {fn} leído correctamente.\n")
                    except Exception as e:
                        log_file.write(f"Error al leer el archivo {fn}: {e}\n")
                        continue
                else:
                    log_file.write(f"Archivo no encontrado: {fn}\n")

            # Verificación de si se cargaron todas las componentes
            if components_loaded < 3:
                log_file.write(f"Componentes insuficientes para el día {date} en la estación {station}. Se cargaron {components_loaded} componentes.\n")
                day += 86400  # Pasar al siguiente día
                continue

            # BP alta y baja frecuencia
            st_hf = st.copy().filter(type="bandpass", freqmin=2, freqmax=8, corners=2, zerophase=True)
            st_lf = st.copy().detrend("linear").filter(type="bandpass", freqmin=0.02, freqmax=0.05, corners=2, zerophase=True)

            # Guardar los datos en un archivo CSV por día con formato juliano
            output_file = os.path.join(dir_out, f"{station}_{date}.csv")
            
            # Archivo de clasificación con el formato estación_fecha_clas.csv
            classification_file = os.path.join(dir_out_clas, f"{station}_{date}_clas.csv")
            
            with open(output_file, mode="w") as f_out, open(classification_file, mode="w") as f_class:
                last_category = None  # Para rastrear el último bloque
                
                # RMS por cada intervalo definido
                for interval in range(num_intervals):
                    ipts0 = int(interval * interval_minutes * 60 / dt)
                    ipts1 = min(int((interval + 1) * interval_minutes * 60 / dt), st[0].stats.npts)

                    log_file.write(f"Calculando RMS para el rango de datos {ipts0} a {ipts1} para el intervalo {interval} del día {date}\n")

                    for j in range(3):
                        rms_hf[j] = np.sqrt(np.mean(st_hf[j].data[ipts0:ipts1] ** 2))
                        rms_lf[j] = np.sqrt(np.mean(st_lf[j].data[ipts0:ipts1] ** 2))
                    rms_hfhor = np.sqrt(np.mean(st_hf[1].data[ipts0:ipts1] ** 2 + st_hf[2].data[ipts0:ipts1] ** 2))
                    rms_hfall = np.sqrt(np.mean(st_hf[0].data[ipts0:ipts1] ** 2 + st_hf[1].data[ipts0:ipts1] ** 2 + st_hf[2].data[ipts0:ipts1] ** 2))
                    rms_lfhor = np.sqrt(np.mean(st_lf[1].data[ipts0:ipts1] ** 2 + st_lf[2].data[ipts0:ipts1] ** 2))
                    rms_lfall = np.sqrt(np.mean(st_lf[0].data[ipts0:ipts1] ** 2 + st_lf[1].data[ipts0:ipts1] ** 2 + st_lf[2].data[ipts0:ipts1] ** 2))

                    # Escribir los datos de cada intervalo en el archivo CSV
                    f_out.write(f"{rms_hf[0]:.3e},{rms_hf[1]:.3e},{rms_hf[2]:.3e},{rms_hfhor:.3e},{rms_hfall:.3e},{rms_lf[0]:.3e},{rms_lf[1]:.3e},{rms_lf[2]:.3e},{rms_lfhor:.3e},{rms_lfall:.3e}\n")

                    # Clasificación de RMS
                    category = "b"  # Por defecto es "b"
                    if rms_lfhor > max_noice:
                        category = "a"
                    elif rms_lfhor < min_noice:
                        category = "c"
                    elif last_category == "a" and category == "b":
                        category = "d"  # Reclasificación si sigue después de "a"
                    
                    # Escribir la clasificación en el archivo CSV
                    f_class.write(f"{category}\n")
                    
                    # Actualizar la última categoría
                    last_category = category

            day += 86400  # Pasar al siguiente día
