"""
Please find copyright information at the end of this document
Por favor encuentra la información de derechos de autor al final de este documento

Este fue el código más estable que encontré en línea, gracias a Jim Term por todo su trabajo.


Mi nombre es Miguel González. ¡Colaboremos juntos!

Redes Sociales / Social Networks: MGonzalez506
dev@mgonzalez506.com
"""

"""
Paquetes necesarios
Módulo Serial --> pip install pyserial
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import serial
import threading
import traceback
import time
import signal
import fcntl
import string
import re

# Need OS-specific method for getting keyboard input.
if os.name == 'nt':
	import msvcrt
	class Console:
		def __init__(self, bufsize = 1):
			# Buffer size > 1 not supported on Windows
			self.tty = True
		def cleanup(self):
			pass
		def getkey(self):
			start = time.time()
			while True:
				z = msvcrt.getch()
				if z == '\0' or z == '\xe0': # function keys
					msvcrt.getch()
				else:
					if z == '\r':
						return '\n'
					return z
				if (time.time() - start) > 0.1:
					return None

	class MySerial(serial.Serial):
		def nonblocking_read(self, size=1):
			# Buffer size > 1 not supported on Windows
			return self.read(1)
elif os.name == 'posix':
	import termios, select, errno
	class Console:
		def __init__(self, bufsize = 65536):
			self.bufsize = bufsize
			self.fd = sys.stdin.fileno()
			if os.isatty(self.fd):
				self.tty = True
				self.old = termios.tcgetattr(self.fd)
				tc = termios.tcgetattr(self.fd)
				tc[3] = tc[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
				tc[6][termios.VMIN] = 1
				tc[6][termios.VTIME] = 0
				termios.tcsetattr(self.fd, termios.TCSANOW, tc)
			else:
				self.tty = False
		def cleanup(self):
			if self.tty:
				termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old)
		def getkey(self):
			# Return -1 if we don't get input in 0.1 seconds, so that
			# the main code can check the "alive" flag and respond to SIGINT.
			[r, w, x] = select.select([self.fd], [], [self.fd], 0.1)
			if r:
				return os.read(self.fd, self.bufsize)
			elif x:
				return ''
			else:
				return None

	class MySerial(serial.Serial):
		def nonblocking_read(self, size=1):
			[r, w, x] = select.select([self.fd], [], [self.fd], self._timeout)
			if r:
				try:
					return os.read(self.fd, size)
				except OSError as e:
					if e.errno == errno.EAGAIN:
						return None
					raise
			elif x:
				raise SerialException("exception (device disconnected?)")
			else:
				return None # timeout

else:
	raise ("Lo siento, no es posible desplegar la información en el terminal de tu plataforma (%s) " % sys.platform)

class JimtermColor(object):
	def __init__(self):
		self.setup(1)
	def setup(self, total):
		if total > 0:
			self.codes = [
				"\x1b[1;33m", # Amarillo
				"\x1b[1;31m", # Rojo
				"\x1b[1;32m", # Verde
				"\x1b[1;34m", # Azul
				"\x1b[1;35m", # Magenta
				"\x1b[1;36m", # Cyan (cian)
				"\x1b[1;31m", # Rojo
				"\x1b[1;37m", # Blanco
				]
			self.reset = "\x1b[0m"
		else:
			self.codes = [""]
			self.reset = ""
	def code(self, n):
		return self.codes[n % len(self.codes)]

class Jimterm:
	"""Normal interactive terminal"""

	def __init__(self,
				 serials,
				 suppress_write_bytes = None,
				 suppress_read_firstnull = True,
				 transmit_all = False,
				 add_cr = False,
				 send_cr = False,
				 raw = True,
				 color = True,
				 bufsize = 65536):

		self.color = JimtermColor()
		if color:
			self.color.setup(len(serials))

		self.serials = serials
		self.suppress_write_bytes = suppress_write_bytes
		self.suppress_read_firstnull = suppress_read_firstnull
		self.last_color = ""
		self.threads = []
		self.transmit_all = transmit_all
		self.add_cr = add_cr
		self.send_cr = send_cr
		self.raw = raw
		self.bufsize = bufsize
		self.quote_re = None
		self.output_lock = threading.Lock()

	def print_header(self, nodes, bauds, output = sys.stdout):
		for (n, (node, baud)) in enumerate(zip(nodes, bauds)):
			output.write(self.color.code(n)
						 + node + ", " + str(baud) + " baudios"
						 + self.color.reset + "\n")
		if sys.stdin.isatty():
			output.write("^C to exit\n")
			output.write("----------\n")
		output.flush()

	def start(self):
		self.alive = True

		# Set up console
		self.console = Console(self.bufsize)

		# serial->console, all devices
		for (n, serial) in enumerate(self.serials):
			self.threads.append(threading.Thread(
				target = self.reader,
				args = (serial, self.color.code(n))
				))

		# console->serial
		self.threads.append(threading.Thread(target = self.writer))

		# start all threads
		for thread in self.threads:
			thread.daemon = True
			thread.start()

	def stop(self):
		self.alive = False

	def join(self):
		for thread in self.threads:
			while thread.is_alive():
				thread.join(0.1)

	def quote_raw(self, data):
		if self.quote_re is None:
			matcher = '[^%s]' % re.escape(string.printable + "\b")
			if sys.version_info < (3,):
				self.quote_re = re.compile(matcher)
				qf = lambda x: ("\\x%02x" % ord(x.group(0)))
			else:
				self.quote_re = re.compile(matcher.encode('ascii'))
				qf = lambda x: ("\\x%02x" % ord(x.group(0))).encode('ascii')
			self.quote_func = qf
		return self.quote_re.sub(self.quote_func, data)

	def reader(self, serial, color):
		"""loop and copy serial->console"""
		first = True
		try:
			if (sys.version_info < (3,)):
				null = '\x00'
			else:
				null = b'\x00'
			_inBuffer = ''
			while self.alive:
				data = serial.nonblocking_read(self.bufsize)
				if data is None:
					continue
				if not len(data):
					raise Exception("read returned EOF")

				# don't print a NULL if it's the first character we
				# read.  This hides startup/port-opening glitches with
				# some serial devices.
				if self.suppress_read_firstnull and first and data[0] == null:
					first = False
					data = data[1:]
				first = False

				self.output_lock.acquire()

				if color != self.last_color:
					self.last_color = color
					os.write(sys.stdout.fileno(), color.encode('utf-8'))

				if self.add_cr:
					if sys.version_info < (3,):
						data = data.replace('\n', '\r\n')
					else:
						data = data.replace(b'\n', b'\r\n')

				if not self.raw:
					data = self.quote_raw(data)
				for x in data:
					if x == 10: #Imprime una linea nueva
						os.write(sys.stdout.fileno(), _inBuffer.encode('utf-8'))
						os.write(sys.stdout.fileno(), "\n".encode('utf-8'))
						_inBuffer = ""
					else:
						_inBuffer += chr(x)
				self.output_lock.release()

		except Exception as e:
			self.console.cleanup()
			sys.stdout.write(color)
			sys.stdout.flush()
			traceback.print_exc()
			sys.stdout.write(self.color.reset)
			sys.stdout.flush()
			os._exit(1)

	def writer(self):
		"""loop and copy console->serial until ^C"""
		try:
			if (sys.version_info < (3,)):
				ctrlc = '\x03'
			else:
				ctrlc = b'\x03'
			while self.alive:
				try:
					c = self.console.getkey()
				except KeyboardInterrupt:
					self.stop()
					return
				if c is None:
					# No input, try again.
					continue
				elif self.console.tty and ctrlc in c:
					# Try to catch ^C that didn't trigger KeyboardInterrupt
					self.stop()
					return
				elif c == '':
					# Probably EOF on input.  Wait a tiny bit so we can
					# flush the remaining input, then stop.
					time.sleep(0.25)
					self.stop()
					return
				else:
					# Remove bytes we don't want to send
					if self.suppress_write_bytes is not None:
						c = c.translate(None, self.suppress_write_bytes)

					if self.send_cr and c == '\n':
							c = '\r'
					# Send character
					if self.transmit_all:
						for serial in self.serials:
							serial.write(c)
					else:
						self.serials[0].write(c)
		except Exception as e:
			self.console.cleanup()
			sys.stdout.write(self.color.reset)
			sys.stdout.flush()
			traceback.print_exc()
			os._exit(1)

	def run(self):
		# Set all serial port timeouts to 0.1 sec
		saved_timeouts = []
		for serial in self.serials:
			saved_timeouts.append(serial.timeout)
			serial.timeout = 0.1

		# Work around https://sourceforge.net/p/pyserial/bugs/151/
		saved_writeTimeouts = []
		for serial in self.serials:
			saved_writeTimeouts.append(serial.writeTimeout)
			serial.writeTimeout = 1000000

		# Handle SIGINT gracefully
		signal.signal(signal.SIGINT, lambda *args: self.stop())

		# Go
		self.start()
		self.join()

		# Restore serial port timeouts
		for (serial, saved) in zip(self.serials, saved_timeouts):
			serial.timeout = saved
		for (serial, saved) in zip(self.serials, saved_writeTimeouts):
			serial.writeTimeout = saved

		# Cleanup
		sys.stdout.write(self.color.reset + "\n")
		self.console.cleanup()

if __name__ == "__main__":
	import argparse
	import re

	formatter = argparse.ArgumentDefaultsHelpFormatter
	description = ("Terminal serial que soporta múltiples dispositivos. "
				   "Si se especifica más de un dispositivo, la información de cada uno"
				   "se despliega en colores diferentes. Sin embargo todas las entradas"
				   "serán direccionadas solamente al primer dispositivo.")
	parser = argparse.ArgumentParser(description = description,
									 formatter_class = formatter)

	parser.add_argument("device", metavar="DEVICE", nargs="+",
						help="Serial device.  Specify DEVICE@BAUD for "
						"per-device baudrates.", default="/dev/ttyACM0")

	parser.add_argument("--quiet", "-q", action="store_true",
						help="Don't print header")

	parser.add_argument("--baudrate", "-b", metavar="BAUD", type=int,
						help="Default baudrate for all devices", default=9600)
	parser.add_argument("--crlf", "-c", action="store_true",
						help="Add CR before incoming LF")
	parser.add_argument("--lfcr", "-C", action="store_true",
						help="Send CR instead of LF on output")
	parser.add_argument("--all", "-a", action="store_true",
						help="Send keystrokes to all devices, not just "
						"the first one")
	parser.add_argument("--mono", "-m", action="store_true",
						help="Don't use colors in output")
	parser.add_argument("--flow", "-f", action="store_true",
						help="Enable RTS/CTS flow control")
	parser.add_argument("--esp", "-e", action="store_true",
						help="Force RTS and DTR high, for ESP boards. Note that"
						" the lines may still glitch low at startup.")
	parser.add_argument("--bufsize", "-z", metavar="SIZE", type=int,
						help="Buffer size for reads and writes", default=65536)

	group = parser.add_mutually_exclusive_group(required = False)
	group.add_argument("--raw", "-r", action="store_true",
					   default=argparse.SUPPRESS,
					   help="Output characters directly "
					   "(default, if stdout is not a tty)")
	group.add_argument("--no-raw", "-R", action="store_true",
					   default=argparse.SUPPRESS,
					   help="Quote unprintable characters "
					   "(default, if stdout is a tty)")

	args = parser.parse_args()
	
	piped = not sys.stdout.isatty()
	raw = "raw" in args or (piped and "no_raw" not in args)

	devs = []
	nodes = []
	bauds = []
	for (n, device) in enumerate(args.device):
		m = re.search(r"^(.*)@([1-9][0-9]*)$", device)
		if m is not None:
			node = m.group(1)
			baud = m.group(2)
		else:
			node = device
			baud = args.baudrate
		if node in nodes:
			sys.stderr.write("error: %s especificado más de una vez\n" % node)
			raise SystemExit(1)
		try:
			dev = MySerial(None, baud, rtscts = args.flow)
			dev.port = node
			if args.esp:
				# Force DTR and RTS high by setting to false
				dev.dtr = False
				dev.rts = False
			dev.open()
		except serial.serialutil.SerialException:
			sys.stderr.write("error abriendo %s\n" % node)
			raise SystemExit(1)
		nodes.append(node)
		bauds.append(baud)
		devs.append(dev)

	term = Jimterm(devs,
				   transmit_all = args.all,
				   add_cr = args.crlf,
				   send_cr = args.lfcr,
				   raw = raw,
				   color = (os.name == "posix" and not args.mono),
				   bufsize = args.bufsize)
	if not args.quiet:
		term.print_header(nodes, bauds, sys.stderr)

	term.run()

"""
Este documento representa una adaptación del código de Jim Paris, traducido a español y corregidos algunos errores
que no permitían que el código funcionara correctamente en Python 3.x

Copyright (c) 2012, Jim Paris <jim@jtan.com> available at https://git.jim.sh/jim/terminal.git
All rights reserved.
Available at: https://git.jim.sh/jim/terminal.git

Based on Miniterm example code which is
Copyright (c) 2001-2011, Chris Liechti <cliechti@gmx.net>
All rights reserved.

"""