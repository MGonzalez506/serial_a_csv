"""
Mi nombre es Miguel González. ¡Colaboremos juntos!

Redes Sociales / Social Networks: MGonzalez506
dev@mgonzalez506.com
"""

"""
Paquetes necesarios
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytz
import csv
from datetime import datetime

def save_buffer(in_str, fecha):
	str_fecha = str(fecha)
	vector_recibido = []
	vector_recibido = in_str.split(',')
	print(vector_recibido)