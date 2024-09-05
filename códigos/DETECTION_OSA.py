# %%
from obspy import UTCDateTime
import numpy as np
import os
import csv

stations = ["PIRO", "RIOS"]  
startday = UTCDateTime(2018, 8, 15)  # fecha inicio
endday = UTCDateTime(2018, 8, 15)    # fin
threshold = 4  # Umbral de detección (en desviaciones estándar)
fn_cc_head = r'C:\Users\ScruffinNico\resultados\cc'  # Directorio cc
fn_out_head = r'C:\Users\ScruffinNico\resultados\detection' 
dt_cc = 10  
twin_mvave = 500  # Ventana de tiempo CCMA

os.makedirs(fn_out_head, exist_ok=True)

# Configuración para el cálculo del CCMA
arr_mvave = np.ones(int(twin_mvave / dt_cc)) / int(twin_mvave / dt_cc)

for station in stations:
    day = startday
    cc = np.array([])  
    cc_std = np.array([]) 
    nday1 = 0  # días procesados
    nday2 = 0  # días válidos

    while day <= endday:
        nday1 += 1
        date = str(day.year) + str(day.julday).zfill(3)
        day += 86400 
        fn = os.path.join(fn_cc_head, station, date)
        if os.path.exists(fn):
            # datos cc
            cc_tmp = np.loadtxt(fn)
            if cc_tmp.size == 0 or len(cc_tmp.shape) < 2:  # comprobar archivo (si es válido)
                print(f"Advertencia: Archivo de correlación vacío para {date}.")
                continue
            cc = np.concatenate([cc, cc_tmp[:, 1]])  # añade valores del cc
            cc_std = np.concatenate([cc_std, cc_tmp[:, 1]])  # calcula desviación estándar
            nday2 += 1
        else:
            # Si no hay datos para ese día añade ceros
            cc = np.concatenate([cc, np.zeros(int(86400 / dt_cc))])

    # Reemplaza valores inválidos con ceros
    np.nan_to_num(cc, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    np.nan_to_num(cc_std, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

    # Calcular ccma
    cc_mvave = np.convolve(cc, arr_mvave, mode="same")
    posinega = True  # invierte la señal si se necesita

    #desviación estándar y ajusta el signo deccma
    if len(cc_std) > 0:
        cc_std_mvave = np.convolve(cc_std, arr_mvave, mode="same")
        std = np.std(cc_std_mvave)
        if np.count_nonzero(cc_std_mvave > std) < np.count_nonzero(cc_std_mvave < -std):
            posinega = False
            cc = -cc
            cc_mvave = -cc_mvave
    else:
        std = 1

    # Detección de periodos con correlación significativa
    pflag = False
    periods = []
    ndetect = 0
    sec_detects = 0

    for itime in range(cc.size):
        flag = cc_mvave[itime] > threshold * std
        if not pflag and flag:  # inicio de un evento
            itime_start = itime
        if pflag and not flag:  #fin de un evento
            itime_end = itime
            time_start = startday + dt_cc * itime_start
            time_end = startday + dt_cc * itime_end
            periods.append([time_start.year, time_start.month, time_start.day, time_start.hour, time_start.minute, time_start.second,
                            time_end.year, time_end.month, time_end.day, time_end.hour, time_end.minute, time_end.second])
            ndetect += 1
            sec_detects += time_end - time_start
        pflag = flag

    info = [nday1, nday2, ndetect, sec_detects, std, posinega, startday.year, startday.month, startday.day, endday.year, endday.month, endday.day]

    if len(periods) == 0:
        print("No se detectaron eventos. El archivo de salida no contendrá periodos de eventos.")
    
    # Guardar los resultados solo si hay eventos válidos
    with open(os.path.join(fn_out_head, station + ".csv"), 'w') as f:
        writer = csv.writer(f)
        writer.writerow(info)
        if len(periods) > 0:
            writer.writerows(periods)
# %%
import pandas as pd
import os

# Configuración de directorios y estaciones
stations = ["PIRO", "RIOS"]  # Estaciones que analizaste
fn_out_head = r'C:\Users\ScruffinNico\resultados\detection'  # Directorio de salida para los resultados de detección

# Bucle sobre cada estación para cargar y mostrar los resultados
for station in stations:
    detection_file = os.path.join(fn_out_head, f"{station}.csv")
    
    # Verificar si el archivo de detección existe
    if os.path.exists(detection_file):
        # Cargar los resultados desde el archivo CSV
        df = pd.read_csv(detection_file, skiprows=1, header=None, names=['Año Inicio', 'Mes Inicio', 'Día Inicio', 'Hora Inicio', 'Minuto Inicio', 'Segundo Inicio',
                                                                        'Año Fin', 'Mes Fin', 'Día Fin', 'Hora Fin', 'Minuto Fin', 'Segundo Fin'])
        
        # Crear nuevas columnas de fecha y hora combinadas en formato de texto
        df['Fecha Inicio'] = df['Día Inicio'].astype(str) + '/' + df['Mes Inicio'].astype(str) + '/' + df['Año Inicio'].astype(str) + ' ' + \
                             df['Hora Inicio'].astype(str).str.zfill(2) + ':' + df['Minuto Inicio'].astype(str).str.zfill(2) + ':' + df['Segundo Inicio'].astype(str).str.zfill(2)
                             
        df['Fecha Fin'] = df['Día Fin'].astype(str) + '/' + df['Mes Fin'].astype(str) + '/' + df['Año Fin'].astype(str) + ' ' + \
                          df['Hora Fin'].astype(str).str.zfill(2) + ':' + df['Minuto Fin'].astype(str).str.zfill(2) + ':' + df['Segundo Fin'].astype(str).str.zfill(2)
        
        # Seleccionar solo las columnas relevantes para mostrar
        df_display = df[['Fecha Inicio', 'Fecha Fin']]
        
        # Imprimir el número de eventos detectados
        print(f"Se detectaron {len(df)} sismos lentos en la estación {station}:")
        
        # Mostrar los resultados en una tabla
        print(df_display.to_string(index=False))
    else:
        print(f"No se encontró el archivo de detección para la estación {station}.")