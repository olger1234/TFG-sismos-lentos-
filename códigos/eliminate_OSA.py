# %%
from obspy import UTCDateTime
import csv
import os

stations = ["PIRO", "RIOS"] 
rms_th = 1 * 10**-7  # Umbral de ruido RMS
years = list(range(2018, 2019))  # años a procesar
fn_detection_head = r'C:\Users\ScruffinNico\resultados\detection'  # entrada resultados de detección
fn_rms_head = r'C:\Users\ScruffinNico\resultados\rms'  # entrada RMS
fn_out_head = r'C:\Users\ScruffinNico\resultados\detection_rms'  

os.makedirs(fn_out_head, exist_ok=True)

for station in stations:
    starttime = UTCDateTime(years[0], 1, 1, 0, 0, 0)
    endtime = UTCDateTime(years[-1], 12, 31, 23, 59, 59)  

    rms = []
    for year in years:
        rms_filename = os.path.join(fn_rms_head, f"{station}_{year}.csv")  # Nombre del archivo RMS
        with open(rms_filename, mode="r") as f:
            for row in f:
                # Comprobación de RMS correspondiente a componentes horizontales
                if row.strip().split(",")[8] == "":
                    rms.append(True)
                    continue
                if float(row.strip().split(",")[8]) > rms_th:  # Compara con el umbral de RMS
                    rms.append(True)  # Marca como verdadero si supera el umbral
                    continue
                rms.append(False)  # O falso

    periods = []
    ndetect = 0
    sec_detects = 0

    # Procesa resultados de detección
    detection_filename = os.path.join(fn_detection_head, f"{station}.csv")
    with open(detection_filename, mode="r") as f:
        header = f.readline().strip().split(",")  
        for row in f:
            eventinfo = row.strip().split(",")

            if not row.strip(): 
                continue

            if len(eventinfo) < 12 or any(col.strip() == "" for col in eventinfo[:12]):
                print(f"Error al procesar la fila (datos faltantes o mal formateados): {row}")
                continue  

            try:
                y1, mo1, d1, h1, mi1, s1 = [int(eventinfo[i]) for i in range(6)]
                y2, mo2, d2, h2, mi2, s2 = [int(eventinfo[i]) for i in range(6, 12)]
            except ValueError as e:
                print(f"Error al convertir los datos de la fila: {row}. Detalle: {e}")
                continue  

            t1 = UTCDateTime(y1, mo1, d1, h1, mi1, s1)  # inicio del evento
            t2 = UTCDateTime(y2, mo2, d2, h2, mi2, s2)  # fin del evento

            # Convertir tiempo a índices para RMS
            irms1 = int((t1 - starttime) / 3600)  
            irms2 = int((t2 - starttime) / 3600)

            # Verifica si los niveles de ruido RMS son bajos durante todo el evento
            if sum(rms[irms1:irms2 + 1]) == 0:
                periods.append([y1, mo1, d1, h1, mi1, s1, y2, mo2, d2, h2, mi2, s2])
                ndetect += 1  # Incrementa el contador de eventos detectados
                sec_detects += t2 - t1  # Suma la duración del evento

    # sctualiza el encabezado con el número de eventos detectados después del filtrado
    header[2] = ndetect
    header[3] = sec_detects

    output_filename = os.path.join(fn_out_head, f"{station}.csv")
    with open(output_filename, mode="w") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(periods)
# %%
import pandas as pd
import os

stations = ["PIRO", "RIOS"]
fn_out_head = r'C:\Users\ScruffinNico\resultados\detection_rms'

for station in stations:
    detection_file = os.path.join(fn_out_head, f"{station}.csv")
    
    if os.path.exists(detection_file):
        df = pd.read_csv(detection_file, skiprows=1, header=None, names=['Año Inicio', 'Mes Inicio', 'Día Inicio', 'Hora Inicio', 'Minuto Inicio', 'Segundo Inicio',
                                                                        'Año Fin', 'Mes Fin', 'Día Fin', 'Hora Fin', 'Minuto Fin', 'Segundo Fin'])
        
        df['Fecha Inicio'] = df['Día Inicio'].astype(str) + '/' + df['Mes Inicio'].astype(str) + '/' + df['Año Inicio'].astype(str) + ' ' + \
                             df['Hora Inicio'].astype(str).str.zfill(2) + ':' + df['Minuto Inicio'].astype(str).str.zfill(2) + ':' + df['Segundo Inicio'].astype(str).str.zfill(2)
                             
        df['Fecha Fin'] = df['Día Fin'].astype(str) + '/' + df['Mes Fin'].astype(str) + '/' + df['Año Fin'].astype(str) + ' ' + \
                          df['Hora Fin'].astype(str).str.zfill(2) + ':' + df['Minuto Fin'].astype(str).str.zfill(2) + ':' + df['Segundo Fin'].astype(str).str.zfill(2)
        
        df_display = df[['Fecha Inicio', 'Fecha Fin']]
        
        print(f"Se detectaron {len(df)} sismos lentos en la estación {station} después del filtrado por RMS:")
        
        # resultados en tabla
        print(df_display.to_string(index=False))
    else:
        print(f"No se encontró el archivo de detección filtrada para la estación {station}.")