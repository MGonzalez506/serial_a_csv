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
from datetime import datetime

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
direccion_del_documento = str(THIS_FOLDER + ("/Documentos_CSV/Fecha_de_doc_"))

def save_buffer(in_str):
	fch = datetime.utcnow()
	vector_recibido = in_str.split(',')
	print(fch.strftime('%Y-%m-%d %H:%M:%S.%f %Z') + str(vector_recibido))
	_dir = direccion_del_documento + fch.strftime('%Y') + "_" + fch.strftime('%m') + "_" + fch.strftime('%d') + ".csv"
	if os.path.isfile(_dir):
		save_vector = list()
		save_vector.append(fch)
		for x in vector_recibido: save_vector.append(x)
		with open(_dir, 'a', newline='') as d:
			escribir = csv.writer(d)
			escribir.writerow(save_vector)
	else:
		with open(_dir, 'w', newline='') as d:
			escribir = csv.writer(d)
			escribir.writerow(["Fecha del evento", "Valor", "Fuerza"])