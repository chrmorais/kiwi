#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2005 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
#
# Author(s): Johan Dahlin <jdahlin@async.com.br>
#

"""Environment helpers: path mangling and resource management"""

import gettext
import imp
import os
import sys

from kiwi.python import namedAny

__all__ = ['Application', 'Library', 'app', 'environ', 'require_gazpacho',
           'is_gazpacho_required']

EnvironmentError = EnvironmentError

# From http://tinyurl.com/77ukj
def _is_frozen():
    "Helper function to check if we're frozen in a py2exe'd file"
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") # old py2exe
            or imp.is_frozen("__main__")) # tools/freeze

class Environment:
    """Environment control

    When you want to access a resource on the filesystem, such as
    an image or a glade file you use this object.

    External libraries or applications are free to add extra directories"""

    def __init__(self, root='.'):
        self._resources = {}
        self._root = root

        self._add_resource_variable("glade", "KIWI_GLADE_PATH")
        self._add_resource_variable("image", "KIWI_IMAGE_PATH")

    def get_root(self):
        return self._root

    def get_log_level(self):
        return os.environ.get('KIWI_LOG')

    def _add_resource_variable(self, resource, variable):
        """Add resources from an environment variable"""
        env = os.environ.get(variable, '')
        for path in env.split(os.pathsep):
            if not path:
                continue
            self.add_resource(resource, env)

    def get_resource_paths(self, resource):
        if not resource in self._resources:
            raise EnvironmentError("No resource called: %s" % resource)
        return self._resources[resource]

    def add_resource(self, resource, path):
        path = os.path.join(self._root, path)

        if not os.path.isdir(path):
            raise EnvironmentError("path %s must be a directory" % path)

        self._resources.setdefault(resource, []).append(path)

    def add_resources(self, **kwargs):
        for resource, path in kwargs.items():
            self.add_resource(resource, path)

    def find_resource(self, resource, name):
        """Locate a specific resource of called name of type resource"""

        resource_paths = self.get_resource_paths(resource)
        for path in resource_paths:
            filename = os.path.join(self._root, path, name)
            if os.path.exists(filename):
                return filename

        # Finally try to load the file from the current directory
        filename = os.path.join(self._root, name)
        if os.path.exists(filename):
            return filename

        raise EnvironmentError("Could not find %s resource: %s" % (
            resource, name))

    def _get_epydoc(self):
        if sys.argv == ['IGNORE']:
            return True
        elif os.path.basename(sys.argv[0]) == 'epyrun':
            return True
        return False

    epydoc = property(_get_epydoc)

class Library(Environment):
    """A Library is a local environment object, it's a subclass of the
    Environment class.
    It's used by libraries and applications (through the Application class)

    It provides a way to manage local resources, which should only be seen
    in the current context.

    Libraries are usually instantiated in __init__.py in the topmost package
    in your library, an example usage is kiwi itself which does:

    >>> from kiwi.environ import Library
    >>> lib = Library('kiwi')
    >>> if lib.uninstalled:
    >>>     lib.add_global_resource('glade', 'glade')
    >>>     lib.add_global_resource('pixmap', 'pixmaps')

    which is combined with the following class in setup.py:

    >>> from kiwi.dist import InstallLib
    >>> class InstallLib(TemplateInstallLib):
    >>>    name = 'kiwi'
    >>>    global_resources = dict(glade='$datadir/glade',
    >>>                            pixmap='$datadir/pixmaps')
    >>>
    >>> setup(...,
    >>>       data_files=[('share/kiwi/glade',
    >>>                   listfiles('glade', '*.glade')),
    >>>                   ('share/kiwi/pixmaps',
    >>>                   listfiles('pixmaps', '*.png')),
    >>>       cmdclass=dict(install_lib=InstallLib))

    It may seems like a bit of work, but this is everything that's needed
    for kiwi to figure out how to load resources when installed and when
    running in an uninstalled mode, eg directly from the source tree.
    To locate a pixmap called kiwi.png the following is enough:

    >>> from kiwi.environ import environ
    >>> environ.find_resource('pixmap', 'kiwi.png')
    '/usr/share/kiwi/pixmaps/kiwi.png' # installed mode

    Which will lookup the resource kiwi.png in the domain pixmap, which
    points to $datadir/pixmaps (eg $prefix/share/kiwi/pixmaps) when running
    in installed mode and from $builddir/pixmaps otherwise.

    """
    def __init__(self, name, root='..', dirname=None):
        """
        Creates a new library, this is usually called in __init__.py in a
        toplevel package. All resources will be relative to the I{root}
        directory.

        @param name: name of the library
        @param root: root directory
        @param dirname:
        """
        self.name = name

        # py2exe
        if _is_frozen():
            executable = os.path.realpath(os.path.abspath(sys.executable))
            root = os.path.dirname(executable)
        # normal
        else:
            if dirname == None:
                # Figure out the absolute path to the caller
                caller = sys._getframe(1).f_locals['__file__']
                dirname = os.path.split(caller)[0]

            dirname = os.path.realpath(os.path.abspath(dirname))
            root = os.path.abspath(os.path.join(dirname, root))
        Environment.__init__(self, root=root)

        sys.path.insert(0, os.path.join(root, 'lib', 'python%d.%d' %
                                        sys.version_info[:2], 'site-packages'))
        g = globals()
        l = locals()
        try:
            module = __import__(name, g, l)
        except ImportError:
            raise ImportError("Failed to import module %s" % name)

        # Load installed
        try:
            module = __import__(name + '.__installed__', g, l, [name])
        except ImportError:
            uninstalled = True
        else:
            uninstalled = False
            if not hasattr(module, 'resources'):
                raise ValueError("module %s.__installed__ must define a "
                                 "resources attribute" % name)
            if not hasattr(module, 'global_resources'):
                raise ValueError("module %s.__installed__ must define a "
                                 "global_resources attribute" % name)
            self.add_resources(**module.resources)
            self.add_global_resources(**module.global_resources)

        self.uninstalled = uninstalled

    def enable_translation(self, domain=None, locale='locale',
                           charset='utf-8'):
        if not domain:
            domain = self.name
        # XXX: locale should not be a list
        localedir = self._resources.get(locale)
        if localedir:
            gettext.bindtextdomain(domain, localedir[0])
        else:
            print 'Warning, no localedir for: %s' % domain
        gettext.bind_textdomain_codeset(domain, charset)

    def set_application_domain(self, domain):
        """
        Sets the default application domain
        @param domain: the domain
        """
        gettext.textdomain(domain)

    def add_global_resource(self, resource, path):
        """Convenience method to add a global resource.
        This is the same as calling kiwi.environ.environ.add_resource
        """
        global environ
        environ.add_resource(resource, os.path.join(self._root, path))

    def add_global_resources(self, **kwargs):
        for resource, path in kwargs.items():
            self.add_global_resource(resource, path)

class Application(Library):
    """Application extends a L{library}. It's meant to be used
    by applications

    Libraries are usually instantiated in __init__.py in the topmost package
    in your library, an example usage is kiwi itself which does:

    >>> from kiwi.environ import Application
    >>> app = Application('gnomovision')
    >>> if app.uninstalled:
    >>>     app.add_global_resource('glade', 'glade')
    >>>     app.add_global_resource('pixmap', 'pixmaps')

    If you want to do translations, you also need to do the following:

    >>> app.enable_translation()

    @see: L{Library} for more information on how to integrate it with
      the standard distutils configuration.
    """

    def __init__(self, name, root='..', path='main', dirname=None):
        global app
        if app is not None:
            raise TypeError("Application is already set to %r" % app)
        app = self

        if not dirname:
            dirname = os.path.abspath(os.path.dirname(sys.argv[0]))
        Library.__init__(self, name, root, dirname)
        self._path = path

    def _get_main(self):
        try:
            module = namedAny(self._path)
        except ImportError, e:
            raise SystemExit("ERROR: Could not find item '%s', %s" %
                             (self._path, e))

        main = getattr(module, 'main', None)
        if not main or not callable(main):
            raise SystemExit("ERROR: Could not find item '%s' in module %s" %
                             'main', self._path)
        return main

    def enable_translation(self, domain=None, locale='locale',
                           charset='utf-8'):
        if not domain:
            domain = self.name

        Library.enable_translation(self, domain, locale, charset)
        old_domain = gettext.textdomain()
        if old_domain  != 'messages':
            print 'Warning: overriding default domain, was %s' % old_domain

        self.set_application_domain(domain)

    def run(self):
        main = self._get_main()

        try:
            sys.exit(main(sys.argv))
        except KeyboardInterrupt:
            raise SystemExit

_require_gazpacho_loader = False

def require_gazpacho():
    global _require_gazpacho_loader
    _require_gazpacho_loader = True

def is_gazpacho_required():
    global _require_gazpacho_loader
    return _require_gazpacho_loader

# Global variables
environ = Environment()

app = None

