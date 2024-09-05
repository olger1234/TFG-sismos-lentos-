# TFG sismos lentos - Ólger Arce Gómez - OVSICORI, UNA
 Detección de sismos lentos con una estación usando el método de Masuda e Ide

Tener directorio de entrada con la base de datos en formato permitido por ObSpy (MiniSeed, SAC...)
en un mismo directorio tener todos los archivos con nombre: i4.ESTACIÓN.HHX.FECHA_0+, donde estación es el nombre, X es el componente (Z, N, E), Fecha es año+día (ejemplo 2018227 corresponde al 15 de agosto del 2018)

Orden de ejecución:
1. RMS : calcula el valor cuadrático medio
2. CC: calcula la correlación cruzada
3. DETECTION: detecta sismos lentos con el método de Masuda e Ide
4. eliminate: elimina falsos positivos con un umbral de detección

Adicionalmente se añade un generador, el cual simula una señal sísmica con cierto nivel de ruido guarda el archivo para usarlo en el método de detección.
