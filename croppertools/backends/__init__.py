import gobject
import traceback
from ..usefulgprop import property as gprop
__all__ = 'decode', 'CropManager', 'ProgressTracker'

MODULES = []

def decode(pbl):
	"""decode(PixbufLoader)
	Decodes an image. A coroutine, though.
	Takes image data on send(). Call close() when there is no more data.
	"""
	#TODO: Recover on error and attempt other backends
	for m in MODULES:
		if hasattr(m, 'decode'): break
	if __debug__: print m
	dec = m.decode(pbl)
	dec.next()
	try:
		imgdata = yield
		while imgdata is not None:
			dec.send(imgdata)
			imgdata = yield
	except GeneratorExit:
		dec.close()

class CropManager(object):
	"""
	Abstracts away the process of selecting backends based on file type, crop 
	sizes, what's installed, phases of the moon, etc.
	
	Attempts to use the highest-quality backend first, and will move to lower 
	ones if it's unavailable/unable.
	"""
	cm = None
	#TODO: Silently move between modules as necessary
	def __init__(self, gfile, pb, data):
		"""Module(gio.File, gtk.gdk.PixBuf, blob)
		Initializes the backend, including loading the file.
		
		Raises a NotImplementedError if this backend can't work on this 
		kind of file.
		"""
		for m in MODULES:
			if not hasattr(m, 'CropManager'): continue
			try:
				self.cm = m.CropManager(gfile, pb, data)
			except NotImplementedError:
				pass
			else:
				if __debug__: print "CropManager:", m.__name__
				break
		else:
			raise NotImplementedError
	
	def do_crop(self, rect, dest):
		"""m.do_crop(gtk.gdk.Rect, gio.File) -> ProgressTracker
		Start performing the crop. The hard work should be done in a back end.
		
		Returns an object that's used for syncronization.
		"""
		return self.cm.do_crop(rect, dest)
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		We're done with this cropping business. Clean up.
		"""
		return self.cm.__exit__(exc_type, exc_val, exc_tb)

class ProgressTracker(gobject.GObject):
#class ProgressTracker(object):
	"""
	Helps syncronize the backends and the UI.
	
	This is basically a deferred.
	"""
	__gsignals__ = {
		'finished': (gobject.SIGNAL_RUN_FIRST, None, ()),
#		'error': (gobject.SIGNAL_RUN_FIRST, None, (type, Exception, object)), #exc_type, exc_val, exc_tb
		'error': (gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)), #exc_type, exc_val, exc_tb
		}
	value = gprop(
		type=gobject.TYPE_DOUBLE,
		nick='percent finished',
		blurb='how done this task is, as a fraction (0 is nothing done, 1 is completely done)',
		minimum=0.0,
		maximum=1.0,
		default=0.0,
		flags=gobject.PARAM_READWRITE
		)
	has_value = gprop(
		type=gobject.TYPE_BOOLEAN,
		nick='barber pole',
		blurb='Do we have a value at all? If this is false, a ProgressBar should be set to barber pole mode.',
		default=False,
		flags=gobject.PARAM_READWRITE
		)
	
	_finished = None
	_err = None
	_autofinish = True
	
	def __init__(self, autofinish=True):
		"""ProgressTracker([bool])
		By default, ProgressTracker will finish on __exit__(). If this is 
		undesirable (because of callbacks and closures), set autofinish() to 
		False.
		"""
		super(ProgressTracker, self).__init__()
		self._autofinish = autofinish
	
	def finish(self):
		if self._err is not None:
			raise RuntimeError("Can call only finish() or error(), never both!")
		self._finished = True
		self.emit('finished')
	
	def error(self, exc_type, exc_val, exc_tb):
		if self._finished is not None:
			raise RuntimeError("Can call only finish() or error(), never both!")
		self._err = exc_type, exc_val, exc_tb
		self.emit('error', exc_type, exc_val, exc_tb)
	
	def connect(self, signal, handler):
		if signal == 'finished' and self._finished is not None: handler(self)
		elif signal == 'error' and self._err is not None: handler(self, *self._err)
		super(ProgressTracker, self).connect(signal, handler)
	
	def connect_after(self, signal, handler):
		if signal == 'finished' and self._finished is not None: handler(self)
		elif signal == 'error' and self._err is not None: handler(self, *self._err)
		super(ProgressTracker, self).connect_after(signal, handler)
	
	def connect_object(self, signal, handler, gobj):
		if signal == 'finished' and self._finished is not None: handler(gobj)
		elif signal == 'error' and self._err is not None: handler(gobj, *self._err)
		super(ProgressTracker, self).connect_object(signal, handler, gobj)
		
	def connect_object_after(self, signal, handler, gobj):
		if signal == 'finished' and self._finished is not None: handler(gobj)
		elif signal == 'error' and self._err is not None: handler(gobj, *self._err)
		super(ProgressTracker, self).connect_object_after(signal, handler, gobj)
	
	def __enter__(self): return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		"""
		Shortcut to handle setting up the props and to call things.
		
		NOTE: This swallows errors so that they can be passed to the 
		appropriate handler. Be careful when mixing try/except and with.
		"""
		if exc_type is None:
			if self._autofinish: self.finish()
		else:
			traceback.print_exception(exc_type, exc_val, exc_tb)
			self.emit('error', exc_type, exc_val, exc_tb)
		return True

import jpegtrans, magickwand, imagemagick, pil, gtkpixbuf
MODULES = filter((lambda m: m.module_available()), [jpegtrans, magickwand, imagemagick, pil, gtkpixbuf])

print MODULES


