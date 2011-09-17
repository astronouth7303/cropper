import gtk, os, gobject
from gtk import gdk
from gobject import TYPE_BOOLEAN, TYPE_BOXED, TYPE_CHAR, TYPE_DOUBLE, TYPE_ENUM, TYPE_FLAGS, TYPE_FLOAT, TYPE_INT, TYPE_INT64, TYPE_STRING, TYPE_UCHAR, TYPE_UINT, TYPE_UINT64, TYPE_ULONG
from box import Box
from modelhelpers import GenericTreeStore
#from gobject.propertyhelper import property as gprop
from usefulgprop import property as gprop
import gio

__all__ = 'BoxListStore', 'make_absolute'

def make_absolute(fn):
	print "make_absolute:", fn,
	rv = gio.File(fn)
	print rv
	return rv

#class tracedict(dict):
#	def __setitem__(self, key, value):
#		print 'tracedict.__setitem__', key, value
#		super(tracedict, self).__setitem__(key, value)
#	def __delitem__(self, key):
#		print 'tracedict.__delitem__', key
#		super(tracedict, self).__delitem__(key, value)
#	def update(self, *p, **kw):
#		print 'tracedict.update', p,kw
#		super(tracedict, self).update(*p, **kw)
#	def get(self, *p, **kw):
#		print 'tracedict.get', p,kw
#		super(tracedict, self).get(*p, **kw)
#	def setdefault(self, *p, **kw):
#		print 'tracedict.setdefault', p,kw
#		super(tracedict, self).setdefault(*p, **kw)
#	def clear(self):
#		print 'tracedict.clear'
#		super(tracedict, self).clear()

class BoxListStore(GenericTreeStore):
	"""
	Columns:
	 0. filename (rw)
	 1. box (rw)
	 2. displayname (ro, from filename)
	 3. x (rw, linked)
	 4. y (rw, linked)
	 5. width (rw, linked)
	 6. height (rw, linked)
	 7. rect (rw, linked)
	 8. color (rw, linked)
	 9. exists (ro, generated)
	 10. exists_img (ro, generated)
	 11. tooltip (ro, generated)
	"""
	exist_image = gprop(
		type=gobject.TYPE_STRING,
		nick='file exists image',
		blurb='Image shown when the filename exists.',
		default=None,
		flags=gobject.PARAM_READWRITE
		)
	no_exist_image = gprop(
		type=gobject.TYPE_STRING,
		nick="file doesn't exists image",
		blurb="Image shown when the filename doesn't exist.",
		default=None,
		flags=gobject.PARAM_READWRITE
		)
	
	_LEN = 12
	_exist_image = _no_exist_image = None
	_ro_columns = 2,9,10,11
	_col_types = (
			str, Box, # True, staight-up columns
			str, # Display name
			int, int, int, int, gdk.Rectangle, gdk.Color, # Linked columns
			bool, str, gobject.TYPE_STRING, # Purely-generated columns
			)
	__data = {} # { id(Box) : (fn, Box, displayfn, connect), }
	__order = [] # [ id(Box), ]
	
	def __init__(self):
		gtk.GenericTreeModel.__init__(self)
#		BaseTreeSortable.on_init(self, )
		self.__data = {}
		self.__order = []
	
#	@generic_sort_func
	def _cmp(self, a, b):
		a = self.__data[a][1]
		b = self.__data[b][1]
		return cmp(a,b)
	
	# Internal methods
	def _fileexists(self, row):
		#TODO: Make this async (somehow)
		return gio.File(self.__data[row][0]).query_exists()
	
	def _abspath(self, path):
		return os.path.abspath(path)
	
	def _createrow(self, fn=None, box=None):
		rv = [None]*4
		if fn is not None:
			rv[0] = fn
			rv[2] = gobject.filename_display_basename(fn) # Getting the display name doesn't work if the file doesn't exist.
		else:
			rv[0] = rv[2] = ''
		rv[1] = Box()
		if box is not None:
			rv[1].rect = box.rect
			rv[1].color = box.color
		rv[3] = rv[1].connect('notify', self._box_changed)
		ref = id(rv[1])
		
		self.__data[ref] = rv # VERY, VERY IMPORTANT
		
		self.__order.append(ref)
		# FIXME: Trigger events when this sorts
#		self.__order.sort(key=lambda k: self.__data[k][1])
#		print '_createrow:','self.__data:', self.__data
		return ref
	
	_in_set = False
	def _box_changed(self, box, prop):
		rowref = id(box)
		if rowref not in self.__data: return
		if not self._in_set: 
			self.row_changed(self.on_get_path(rowref), self.create_tree_iter(rowref)) # Signal is generated by set as well
	
	# Properties
	def get_exist_image(self):
		return self._exist_image
	def set_exist_image(self, value):
		self._exist_image = value
		self.foreach(lambda model, path, iter, ud: model.row_changed(path, iter))
	exist_image = property(get_exist_image, set_exist_image)
	
	def get_no_exist_image(self):
		return self._no_exist_image
	def set_no_exist_image(self, value):
		self._no_exist_image = value
		self.foreach(lambda model, path, iter, ud: model.row_changed(path, iter))
	no_exist_image = property(get_no_exist_image, set_no_exist_image)
	
	def do_get_property(self, property):
		if property.name == 'exist-image':
			return self.get_exist_image()
		elif property.name == 'no-exist-image':
			return self.get_no_exist_image()
		else:
			raise AttributeError, 'unknown property %s' % property.name
	
	def do_set_property(self, property, value):
		if property.name == 'exist-image':
			self.set_exist_image(value)
		elif property.name == 'no-exist-image':
			self.set_no_exist_image(value)
		else:
			raise AttributeError, 'unknown property %s' % property.name
	
	# Implementation
	def on_get_flags(self):
		return gtk.TREE_MODEL_LIST_ONLY|gtk.TREE_MODEL_ITERS_PERSIST
	
	def on_get_n_columns(self):
		return self._LEN
	
	def on_get_column_type(self, index):
		return self._col_types[index]
	
	def on_get_iter(self, path):
		try:
			return self.__order[path[0]]
		except IndexError:
			pass
	
	def on_get_path(self, rowref):
		return self.__order.index(rowref),
	
	def on_get_value(self, ref, column):
		if 0 <= column < 3:
			if column == 2:
				return unicode(self.__data[ref][column])
			return self.__data[ref][column]
		elif 3 <= column < 9: # Linked
			box = self.__data[ref][1]
			if column == 3: # x
				return box.rect.x
			elif column == 4: # y
				return box.rect.y
			elif column == 5: # width
				return box.rect.width
			elif column == 6: # height
				return box.rect.height
			elif column == 7: # rect
#				print "on_get_value", box.rect
				return box.rect
			elif column == 8: # color
				return box.color
		elif column == 9: # Generated
			return self._fileexists(ref)
		elif column == 10: # Generated
			return self._exist_image if self._fileexists(ref) else self._no_exist_image
		elif column == 11: # Generated
			return self.__data[ref][1].dimensions_text()
		else:
			raise IndexError
	
	def on_set_value(self, idx, column, value):
		self._in_set = True
		try:
			row = self.__data[idx]
			box = row[1]
			if not isinstance(value, self._col_types[column]):
				raise TypeError, "Column %i expecting %s, got %s" % (
					idx, self._col_types[idx].__name__, type(value).__name__)
			if column in self._ro_columns:
				raise ValueError, "Can't set column %i" % idx
			elif column == 0: # filename
				row[0] = self._abspath(value)
				row[2] = value # displayname
			elif column == 1: # box
				# Don't actually change the box instance because that invalidates the iters
				row[1].rect = value.rect
				row[1].color = value.color
			elif column == 3: # x
				box.rect.x = value
			elif column == 4: # y
				box.rect.y = value
			elif column == 5: # width
				box.rect.width = value
			elif column == 6: # height
				box.rect.height = value
			elif column == 7: # rect
				box.rect = value
			elif column == 8: # color
				box.color = value
		finally:
			self._in_set = False
	
	def on_iter_next(self, rowref):
		idx = self.__order.index(rowref)
		idx += 1
		if idx >= len(self.__data):
			return None
		else:
			return self.__order[idx]
	
	def on_iter_children(self, parent):
		if parent is None and len(self.__order):
			return self.__order[0]
	
	def on_iter_has_child(self, rowref):
		return rowref is None # Can rowref be None?
	
	def on_iter_n_children(self, rowref):
		if rowref is None: # Necessary?
			return len(self.__data)
		else:
			return 0
	
	def on_iter_nth_child(self, parent, n):
		if parent is None:
			return self.__order[n]
	
	def on_iter_parent(self, child):
		pass # No, this is not a placeholder
	
	def on_resort(self):
		oldorder = self.__order[:]
		self.__order.sort(key=lambda k: self.__data[k][1])
		self.rows_reordered((), None, map(self.__order.index, self.__order))
	
	def _insert(self, row=None):
		if row is None:
			row = None, None
		else:
			row = row[0:2]
			if not (len(row) < 1 or isinstance(row[0], str)):
				raise ValueError, "Must have (str,Box,...), received %r" % row
			if not (len(row) < 2 or isinstance(row[1], Box)):
				raise ValueError, "Must have (str,Box,...), received %r" % row
		return self._createrow(*row)
	
	def on_remove(self, rowref):
		self.__order.remove(rowref)
		row = self.__data[rowref]
		del self.__data[rowref]
#		print 'on_remove:','self.__data:', self.__data
		row[1].disconnect(row[3])
	
	def on_clear(self):
		for k in self.__data.keys():
			path = self.on_get_path(k)
			self.row_deleted(path)
			self.on_remove(k)
		assert len(self.__data) == 0
		self.__data.clear()
		self.__order = []
#		print 'on_clear:','self.__data:', self.__data
		
	on_prepend = _insert
	on_append = _insert
	
	def on_insert(self, position, row=None):
		return self._insert(row)
	
	def on_insert_before(self, sibling, row=None):
		return self._insert(row)
	
	def on_insert_after(self, sibling, row=None):
		return self._insert(row)

if __name__ == "__main__":
	bls = BoxListStore()
	bls.append(['', Box(gtk.gdk.Rectangle(124,191,248,383), gtk.gdk.color_parse('#F0A'))])
	bls.append(['', Box(gtk.gdk.Rectangle(50,100,200,300), gtk.gdk.color_parse('#AF0'))])
	print 'Data:'
	for i, row in enumerate(map(tuple, bls)):
		print '%i. %r' % (i, row)

