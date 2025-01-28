# TFG sismos lentos - Ólger Arce Gómez - OVSICORI, UNA
 Detección de sismos lentos usando el método de Masuda e Ide

Tener directorio de entrada con la base de datos en formato permitido por ObSpy (MiniSeed, SAC...)
en un mismo directorio tener todos los archivos con nombre: i4.ESTACIÓN.HHX.FECHA_0+, donde estación es el nombre, X es el componente (Z, N, E), Fecha es año+día (ejemplo 2018227 corresponde al 15 de agosto del 2018)

Orden de ejecución:
1. RMS : calcula el valor cuadrático medio
2. CC: calcula la correlación cruzada
3. CCMA: calcula el promedio móvil del CC. Luego su desviación estándar global
4. std: calcula la desviación estándar diaria según una ventana de tiempo dada
5. Detection: detecta sismos lentos con el método de Masuda e Ide, utilizando distinción del signo del CCMA y umbrales adaptativos
6. Total: combina las detecciones de todas las combinaciones de frecuencias definidas
7. red: hace detecciones conjuntas en redes de estaciones. Entre más estaciones hacen la detección, más confiable es

Adicionalmente se agregan los resultados obtenidos del estudio
