"""
Mi nombre es Miguel González. ¡Colaboremos juntos!

Redes Sociales / Social Networks: MGonzalez506
dev@mgonzalez506.com
"""

"""
Paquetes necesarios:

Módulo Serial --> pip install pyserial
Módulo para convertir zonas horarias --> pip install pytz
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import pytz
import csv
import pytz
from pytz import timezone
from datetime import datetime

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
direccion_del_documento = str(THIS_FOLDER + ("/Documentos_CSV/Fecha_de_doc_"))

zona_horaria = 'America/Regina'
formato_de_timestamp = "%Y-%m-%d %H:%M:%S.%f %Z%z"

def save_buffer(in_str):
	utc_ahora = datetime.now(pytz.timezone('UTC'))
	vector_recibido = in_str.split(',')
	fecha = utc_ahora.astimezone(pytz.timezone(zona_horaria))
	print(fecha)
	print("\t\t" + str(vector_recibido))
	_dir = direccion_del_documento + fecha.strftime('%Y') + "_" + fecha.strftime('%m') + "_" + fecha.strftime('%d') + ".csv"
	if os.path.isfile(_dir):
		save_vector = list()
		save_vector.append(fecha)
		for x in vector_recibido: save_vector.append(x)
		with open(_dir, 'a', newline='') as d:
			escribir = csv.writer(d)
			escribir.writerow(save_vector)
	else:
		with open(_dir, 'w', newline='') as d:
			escribir = csv.writer(d)
			escribir.writerow(["Fecha del evento", "Valor", "Fuerza"])