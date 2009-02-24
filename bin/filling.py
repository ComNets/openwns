"""Filling is the gui tree control through which a user can navigate
the local namespace or any object."""

__author__ = "Original author Patrick K. O'Brien <pobrien@orbtech.com>, Modifications by Daniel Bueltmann <me@daniel-bueltmann.de>"
__cvsid__ = "$Id: filling.py 37633 2006-02-18 21:40:57Z RD $"
__revision__ = "$Revision: 37633 $"[11:-2]

import wx

import wx.py.dispatcher as dispatcher
import wx.py.editwindow as editwindow
import inspect
import wx.py.introspect as introspect
import keyword
import os
import sys
import types
import imp
from wx.py.version import VERSION


COMMONTYPES = [getattr(types, t) for t in dir(types) \
               if not t.startswith('_') \
               and t not in ('ClassType', 'InstanceType', 'ModuleType')]

DOCTYPES = ('BuiltinFunctionType', 'BuiltinMethodType', 'ClassType',
            'FunctionType', 'GeneratorType', 'InstanceType',
            'LambdaType', 'MethodType', 'ModuleType',
            'UnboundMethodType', 'method-wrapper')

SIMPLETYPES = [getattr(types, t) for t in dir(types) \
               if not t.startswith('_') and t not in DOCTYPES]

del t

try:
    COMMONTYPES.append(type(''.__repr__))  # Method-wrapper in version 2.2.x.
except AttributeError:
    pass

class PyTreeFavourites:
    """ This class is only used to provide some quick navigation links in PyTree"""
    pass

class FillingTree(wx.TreeCtrl):
    """FillingTree based on TreeCtrl."""
    
    name = 'Filling Tree'
    revision = __revision__

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.TR_DEFAULT_STYLE,
                 rootObject=None, rootLabel=None, rootIsNamespace=False,
                 static=False):
        """Create FillingTree instance."""

        self.installFavourites(rootObject)

        wx.TreeCtrl.__init__(self, parent, id, pos, size, style)
        self.rootIsNamespace = rootIsNamespace
        import __main__
        if rootObject is None:
            rootObject = __main__.__dict__
            self.rootIsNamespace = True
        if rootObject is __main__.__dict__ and rootLabel is None:
            rootLabel = 'locals()'
        if not rootLabel:
            rootLabel = 'Ingredients'
        rootData = wx.TreeItemData(rootObject)
        self.item = self.root = self.AddRoot(rootLabel, -1, -1, rootData)
        self.SetItemHasChildren(self.root, self.objHasChildren(rootObject))
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnItemExpanding, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, id=self.GetId())
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, id=self.GetId())
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated, id=self.GetId())
        if not static:
            dispatcher.connect(receiver=self.push, signal='Interpreter.push')

        self.showPrivateMembers = False
        self.showModules = False
        self.showClasses = False
        self.showTypes = False
        self.showMethods = False

    def installFavourites(self, rootObject):

        rootObject.FAVOURITES = PyTreeFavourites()
        import openwns.simulator
        rootObject.FAVOURITES.simulator = openwns.simulator.getSimulator()
        try:
            rootObject.FAVOURITES.measurementSources = openwns.simulator.getSimulator().environment.probeBusRegistry.measurementSources
        except:
            pass

        try:
            rootObject.FAVOURITES.nodes = openwns.simulator.getSimulator().simulationModel.nodes
        except:
            pass

    def toggleShowPrivate(self, event):
        self.showPrivateMembers = event.Checked()

    def toggleShowModules(self, event):
        self.showModules = event.Checked()

    def toggleShowClasses(self, event):
        self.showClasses = event.Checked()

    def toggleShowTypes(self, event):
        self.showTypes = event.Checked()

    def toggleShowMethods(self, event):
        self.showMethods = event.Checked()
        
    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        self.display()

    def OnItemExpanding(self, event):
        """Add children to the item."""
        busy = wx.BusyCursor()
        item = event.GetItem()
        if self.IsExpanded(item):
            return
        self.addChildren(item)
#        self.SelectItem(item)

    def OnItemCollapsed(self, event):
        """Remove all children from the item."""
        busy = wx.BusyCursor()
        item = event.GetItem()
#        self.CollapseAndReset(item)
#        self.DeleteChildren(item)
#        self.SelectItem(item)

    def OnSelChanged(self, event):
        """Display information about the item."""
        busy = wx.BusyCursor()
        self.item = event.GetItem()
        self.display()

    def OnItemActivated(self, event):
        """Launch a DirFrame."""
        item = event.GetItem()
        text = self.getFullName(item)
        obj = self.GetPyData(item)
        frame = FillingFrame(parent=self, size=(600, 100), rootObject=obj,
                             rootLabel=text, rootIsNamespace=False, title='PyTree - The openWNS Configuration Browser [%s]' %text)
        frame.Show()

    def objHasChildren(self, obj):
        """Return true if object has children."""
        if self.objGetChildren(obj):
            return True
        else:
            return False

    def objGetChildren(self, obj):
        """Return dictionary with attributes or contents of object."""
        busy = wx.BusyCursor()
        otype = type(obj)
        if otype is types.DictType \
        or str(otype)[17:23] == 'BTrees' and hasattr(obj, 'keys'):
            return obj
        d = {}
        if otype is types.ListType or otype is types.TupleType:
            for n in range(len(obj)):
                key = '[' + str(n) + ']'
                d[key] = obj[n]
        if otype not in COMMONTYPES:
            for key in introspect.getAttributeNames(obj):
                # Believe it or not, some attributes can disappear,
                # such as the exc_traceback attribute of the sys
                # module. So this is nested in a try block.
                try:
                    d[key] = getattr(obj, key)
                except:
                    pass
        return d

    def addChildren(self, item):
        self.DeleteChildren(item)
        obj = self.GetPyData(item)
        children = self.objGetChildren(obj)
        if not children:
            return
        keys = children.keys()
        keys.sort(lambda x, y: cmp(str(x).lower(), str(y).lower()))

        # Sort some important things to the top
        pushFront = []

        if item == self.root:
            for key in keys:
                try:
                    if key == "__dict__":
                        continue
                    str(children[key]).upper().index('FAVOURITES')

                    pushFront.append(keys.index(key))
                except:
                    pass

            for key in pushFront:
            
                k = keys.pop(key)
                keys.insert(0,k)
        
        for key in keys:
            itemtext = str(key)

            if not self.showPrivateMembers and itemtext.startswith("__"):
                continue

            if not self.showModules and type(children[key]) is types.ModuleType:
                continue

            if not self.showTypes and type(children[key]) is types.TypeType:
                continue

            if not self.showClasses and type(children[key]) is types.ClassType:
                continue

            if not self.showMethods and type(children[key]) is types.MethodType:
                continue

            # Show list objects with number and classname of child
            if type (obj) is types.ListType:
                import openwns.toolsupport
                v = openwns.toolsupport.PyTreeVisitorFactory.getVisitor(children[key])
                s = v.renderShortText(children[key])
                if s=="":
                    s = str(children[key])

                itemtext += " " + s
                    

            if type(children[key]) is types.MethodType:
                itemtext += "()"

            # Show string dictionary items with single quotes, except
            # for the first level of items, if they represent a
            # namespace.
            if type(obj) is types.DictType \
            and type(key) is types.StringType \
            and (item != self.root \
                 or (item == self.root and not self.rootIsNamespace)):
                itemtext = repr(key)

            child = children[key]
            data = wx.TreeItemData(child)
            branch = self.AppendItem(parent=item, text=itemtext, data=data)
            self.SetItemHasChildren(branch, self.objHasChildren(child))

    def getClassTreeString(self, mrolist, indent = ""):
        if len(mrolist) == 0:
            return ""

        myName = mrolist[-1].__module__ + "." + mrolist[-1].__name__ + "\n"

        # __builtin__ should not be displayed
        myName = myName.replace("__builtin__.", "")

        return indent + myName + self.getClassTreeString(mrolist[0:-1], indent=indent.replace("+---", "    ") +"+---")

    def display(self):
        item = self.item
        if not item:
            return
        if self.IsExpanded(item):
            self.addChildren(item)
        self.setText('')
        obj = self.GetPyData(item)
        if wx.Platform == '__WXMSW__':
            if obj is None: # Windows bug fix.
                return
        self.SetItemHasChildren(item, self.objHasChildren(obj))
        otype = type(obj)

        #DisplayFactory.render(obj)

        #text = ''
        text = self.getFullName(item) + " (%s.%s)\n\n" % (obj.__class__.__module__,obj.__class__.__name__)

        if item == self.root:
            text += "############################################################\n"
            text += "# Navigate on the left. Start by expanding the config file\n"
            text += "# and then extending the FAVOURITES subtree. There you can\n"
            text += "# find the most important configuration entries.\n"
            text += "############################################################\n\n"

        text += "Inheritance Graph\n"
        text +="-----------------\n\n"
        text += self.getClassTreeString(type(obj).mro(), "   ")
        text += "\n"

        text += "\n\nInformation from PyTreeVisitor\n"
        text += "------------------------------\n\n"

        import openwns.toolsupport
        v = openwns.toolsupport.PyTreeVisitorFactory.getVisitor(obj)
        s = v.renderLongText(obj)
        if s == "":
            s = "No PyTreeVistor found for this object. You can implement one of your own. See openwns.toolsupport.pytreevisitors.simulator for an example.\n"
        text += s

        text += "\n\nLow level information\n"
        text += "---------------------"

        try:
            value = str(obj)
        except:
            value = ''
        if otype is types.StringType or otype is types.UnicodeType:
            value = repr(obj)
        text += '\n\nValue: ' + value
        if otype not in SIMPLETYPES:
            try:
                text += '\n\nDocstring:\n\n"""' + \
                        inspect.getdoc(obj).strip() + '"""'
            except:
                pass
        if otype is types.InstanceType:
            try:
                text += '\n\nClass Definition:\n\n' + \
                        inspect.getsource(obj.__class__)
            except:
                pass
        else:
            try:
                text += '\n\nSource Code:\n\n' + \
                        inspect.getsource(obj)
            except:
                pass
        self.setText(text)

    def getFullName(self, item, partial=''):
        """Return a syntactically proper name for item."""
        name = self.GetItemText(item)
        parent = None
        obj = None
        if item != self.root:
            parent = self.GetItemParent(item)
            obj = self.GetPyData(parent)
        # Apply dictionary syntax to dictionary items, except the root
        # and first level children of a namepace.
        if (type(obj) is types.DictType \
            or str(type(obj))[17:23] == 'BTrees' \
            and hasattr(obj, 'keys')) \
        and ((item != self.root and parent != self.root) \
            or (parent == self.root and not self.rootIsNamespace)):
            name = '[' + name + ']'
        # Apply dot syntax to multipart names.
        if partial:
            if partial[0] == '[':
                name += partial
            else:
                name += '.' + partial
        # Repeat for everything but the root item
        # and first level children of a namespace.
        if (item != self.root and parent != self.root) \
        or (parent == self.root and not self.rootIsNamespace):
            name = self.getFullName(parent, partial=name)
        return name

    def setText(self, text):
        """Display information about the current selection."""

        # This method will likely be replaced by the enclosing app to
        # do something more interesting, like write to a text control.
        print text

    def setStatusText(self, text):
        """Display status information."""

        # This method will likely be replaced by the enclosing app to
        # do something more interesting, like write to a status bar.
        print text


class FillingText(editwindow.EditWindow):
    """FillingText based on StyledTextCtrl."""

    name = 'Filling Text'
    revision = __revision__

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.CLIP_CHILDREN,
                 static=False):
        """Create FillingText instance."""
        editwindow.EditWindow.__init__(self, parent, id, pos, size, style)
        # Configure various defaults and user preferences.
        self.SetReadOnly(True)
        self.SetWrapMode(False)
        self.SetMarginWidth(1, 0)
        if not static:
            dispatcher.connect(receiver=self.push, signal='Interpreter.push')

    def push(self, command, more):
        """Receiver for Interpreter.push signal."""
        self.Refresh()

    def SetText(self, *args, **kwds):
        self.SetReadOnly(False)
        editwindow.EditWindow.SetText(self, *args, **kwds)
        self.SetReadOnly(True)


class Filling(wx.SplitterWindow):
    """Filling based on wxSplitterWindow."""

    name = 'Filling'
    revision = __revision__

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.SP_3D|wx.SP_LIVE_UPDATE,
                 name='Filling Window', rootObject=None,
                 rootLabel=None, rootIsNamespace=False, static=False):
        """Create a Filling instance."""
        wx.SplitterWindow.__init__(self, parent, id, pos, size, style, name)

        self.tree = FillingTree(parent=self, rootObject=rootObject,
                                rootLabel=rootLabel,
                                rootIsNamespace=rootIsNamespace,
                                static=static)
        self.text = FillingText(parent=self, static=static)
        
        wx.FutureCall(1, self.SplitVertically, self.tree, self.text, 200)
        
        self.SetMinimumPaneSize(1)

        # Override the filling so that descriptions go to FillingText.
        self.tree.setText = self.text.SetText

        # Display the root item.
        self.tree.SelectItem(self.tree.root)
        self.tree.display()

        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnChanged)

    def OnChanged(self, event):
        #this is important: do not evaluate this event=> otherwise, splitterwindow behaves strange
        #event.Skip()
        pass


    def LoadSettings(self, config):
        pos = config.ReadInt('Sash/FillingPos', 200)
        wx.FutureCall(250, self.SetSashPosition, pos)
        zoom = config.ReadInt('View/Zoom/Filling', -99)
        if zoom != -99:
            self.text.SetZoom(zoom)

    def SaveSettings(self, config):
        config.WriteInt('Sash/FillingPos', self.GetSashPosition())
        config.WriteInt('View/Zoom/Filling', self.text.GetZoom())



class FillingFrame(wx.Frame):
    """Frame containing the namespace tree component."""

    name = 'Filling Frame'
    revision = __revision__

    def __init__(self, parent=None, id=-1, title='PyTree - The openWNS Configuration Browser',
                 pos=(0,0), size=(600, 400),
                 style=wx.DEFAULT_FRAME_STYLE, rootObject=None,
                 rootLabel=None, rootIsNamespace=False, static=False):
        """Create FillingFrame instance."""

        wx.Frame.__init__(self, parent, id, title, pos, wx.DisplaySize(), style)
        intro = 'PyTree - The openWNS Configuration Browser'
        self.CreateStatusBar()
        self.SetStatusText(intro)
        #import wx.py.images
        #self.SetIcon(wx.py.images.getPyIcon())
        self.filling = Filling(parent=self, rootObject=rootObject,
                               rootLabel=rootLabel,
                               rootIsNamespace=rootIsNamespace,
                               static=static)
        # Override so that status messages go to the status bar.
        self.filling.tree.setStatusText = self.SetStatusText


        menubar = wx.MenuBar()
        file = wx.Menu()
        view = wx.Menu()

        # File
        file.Append(101, '&Open', 'Open a new document')
        file.AppendSeparator()

        quit = wx.MenuItem(file, 102, '&Quit\tCtrl+Q', 'Quit the Application')
        #quit.SetBitmap(wx.Image('stock_exit-16.png',wx.BITMAP_TYPE_PNG).ConvertToBitmap())
        file.AppendItem(quit)

        # View
        view.Append(201, 'Show &Private Members\tCtrl+P', "Show Private Members", wx.ITEM_CHECK)
        view.Append(202, 'Show &Modules\tCtrl+M', "Show Python Modules", wx.ITEM_CHECK)
        view.Append(203, 'Show C&lasses\tCtrl+L', "Show Python Classes", wx.ITEM_CHECK)
        view.Append(204, 'Show &Types\tCtrl+T', "Show Python Types", wx.ITEM_CHECK)
        view.Append(205, 'Show Meth&ods\tCtrl+O', "Show Python Methods", wx.ITEM_CHECK)

        menubar.Append(file, '&File')
        menubar.Append(view, '&View')
        self.SetMenuBar(menubar)


        wx.EVT_MENU(self, 101, self.OnOpenFile )
        wx.EVT_MENU(self, 102, self.OnQuit )
        wx.EVT_MENU(self, 201, self.filling.tree.toggleShowPrivate )
        wx.EVT_MENU(self, 202, self.filling.tree.toggleShowModules )
        wx.EVT_MENU(self, 203, self.filling.tree.toggleShowClasses )
        wx.EVT_MENU(self, 204, self.filling.tree.toggleShowTypes )
        wx.EVT_MENU(self, 205, self.filling.tree.toggleShowMethods )

    def OnOpenFile(self, event):
       dlg = wx.FileDialog(self, "Choose a file", os.getcwd(), "", "*.py", wx.OPEN)
       if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                mypath = os.path.basename(path)
                self.SetStatusText("You selected: %s" % mypath)
       dlg.Destroy()

    def OnQuit(self, event):
        self.Close()

class App(wx.App):
    """PyFilling standalone application."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        wx.App.__init__(self)


    def OnInit(self):
        wx.InitAllImageHandlers()
        self.fillingFrame = FillingFrame(**self.kwargs)
        #self.fillingFrame = FillingFrame()
        self.fillingFrame.Show(True)
        self.SetTopWindow(self.fillingFrame)
        return True