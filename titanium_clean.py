#!/usr/bin/env python

import glob
import re
import argparse
import os

app_version = "1.0"
app_name    = "titanium_clean"
app_author  = "Joel Brunenberg <joel@jjim.de>"
app_string  = "{} ver. {} by {} - provided with ABSOLUTELY NO WARRANTY under the licence described in the LICENSE file in this folder.".format(app_name, app_version, app_author)

#    titanium_clean - Titanium Backup Cleaner
#    Copyright (C) 2015  Joel Brunenberg
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

parser = argparse.ArgumentParser(description="{} - A cleaner for Titanium Backup directories to keep the last X and Y oldest backups of app data and their apps.".format(app_string))
parser.add_argument('--path',     '-p', required=True,                    help='Path where the titanium backups are. This is globbed with * so filename prefixes are also possible to only work on a specific glob pattern. Existance is not checked. Be careful. If you want to specify a directory, a trailing slash is mandantory.')
parser.add_argument('--keep-new', '-k', default=4, type=int,              help='how many of the newest backups to keep', metavar="X")
parser.add_argument('--keep-old', '-o', default=0, type=int,              help='how many old backups to keep in any case.', metavar="Y")
parser.add_argument('--keep-apk', '-a', action="store_const", const=True, help="ignore unused APK backups and keep them in case of delete.")
parser.add_argument('--delete',   '-d', action="store_const", const=True, help="delete unwanted files - otherwise only the names are listed.")

args = parser.parse_args()

#       Filenames:
#           uk.co.nickfines.RealCalcPlus-20151231-101820.properties
#           uk.co.nickfines.RealCalcPlus-20151231-101820.tar.gz
#           uk.co.nickfines.RealCalcPlus-bf11b933a567d66b2929729f5203f099.apk.gz
re_app_file  = re.compile("(?P<name>.*)-(?P<apk_hash>[a-f0-9]{16,})\.apk(?P<comp>\..*)?")
re_data_file = re.compile("(?P<name>.*)-(?P<date>[0-9]{8})-(?P<time>[0-9]{6})\.tar(?P<comp>\..*)?")
re_misc_file = re.compile("(?P<name>.*)-(?P<date>[0-9]{8})-(?P<time>[0-9]{6})\.properties(?P<comp>\..*)?")
re_inifile   = re.compile("(?P<key>[^=]+)=(?P<value>.*)")

properties_we_need = [ "app_version_code", "app_apk_md5", "app_gui_label", "app_version_name", "app_data_md5" ]

regexes = [re_app_file, re_data_file, re_misc_file]



class AppBackup(object):
    """Object to represent a single backup of an applikation package.
    Application name is required and checked against later added filenames.
    """
    def __init__(self, name):
        self._name = name
        self._file = None
        self._apk_hash = None
        self._needed = []

    def add_file(self, fn):
        """Method to add a (the) file to the package. Will fail when the file
        belongs to another application, but replaces the old file if there is
        any. Apk files or compressed apk files may be added here.
        """
        app = re_app_file.match(os.path.basename(fn))
        if app:
            app_data = app.groupdict()
            if self._name != app_data["name"]:
                raise Exception("Backup does not belong to this app while processing {} for {} - {}".format(fn, self._name, app_data))
            self._file = fn
            self._apk_hash = app_data["apk_hash"]

    @property
    def needed_by(self):
        """Property to represents how many data backups are requiring this.
        This is not automatic but set by the App() classes update_app_usage()
        method.  The timestamps identifying the individual backups are stored
        in the list self._needed.
        """
        return len(self._needed)

    @property
    def needed(self):
        """Bool property to find out if the application backup is needed by any
        data backups. Returns True, if self._needed has items, False otherwise.
        There is a slightly unobvious way to require this application backup.
        Set this property to a timestamp and this timestamp is added to the
        list of data backups requiring this application backup. Set it to False
        to reset the list to an empty one.
        """
        if len(self._needed) > 0:
            return True
        else:
            return False

    @needed.setter
    def needed(self, value):
        if value == False:
            self._needed = []
        else:
            if value in self._needed:
                return True
            else:
                self._needed.append(value)

    @property
    def apk_hash(self):
        """Property to show the apk hash (usually md5) extracted from the
        filename by the add_file method
        """
        if self._complete:
            return self._apk_hash

    @property
    def complete(self):
        """Property to show, if the object has all required information. This
        should return True after a proper file has been added
        """
        if self._file and self._apk_hash and self._name:
            return True
        else:
            return False

    @property
    def files(self):
        """Return the name of the added file, if set, None otherwise"""
        return self._file

    def __str__(self):
        """Represent the object as string"""
        if self.complete:
            if self._apk_hash:
                btype = "app APK"
            else:
                btype = "unknown"
            if self._needed:
                need = "yes, by {} data backups".format(self.needed_by)
            else:
                need = "no or unknown"
            return "<AppBackup object (complete) for {} '{}' with hash {} with registered file '{}' - needed: {}>".format( btype, self._name, self._apk_hash, self._file, need )
        else:
            return "<AppBackup object (incomplete) for app '{}' with hash {} with registered file '{}'>".format( self._name, self._apk_hash, self._file )

class DataBackup(object):
    """Object to represent a single backup of the data of a package.
    Application name is required and checked against later added filenames.
    """
    def __init__(self, name):
        self._name = name
        self._files = {}
        self._apk_hash = None
        self._data_hash = None
        self._timestamp = None
        self._properties = {}

    def add_file(self, fn):
        """Method to addfiles to this backup. Files are checked against the
        name of the application. The timestamp of the backup is extracted from
        the first file added and is checked against later added files. You
        should add compressed tars and properties files here. Data about
        required application versions, the canonical name of the application,
        human readable version strings etc. are extracted from the
        properties-file and stored in self._properties
        """
        data = re_data_file.match(os.path.basename(fn))
        misc = re_misc_file.match(os.path.basename(fn))

        if data:
            d = data.groupdict()
            f = "data"
        if misc:
            d = misc.groupdict()
            f = "misc"

        timestamp = "{}-{}".format(d["date"], d["time"])
        if self._timestamp and self._timestamp != timestamp:
            raise Exception("Backup does not belong to this timestamp while processing {} for {} - {} vs. {}".format(fn, self._name, timestamp, self._timestamp))
        elif not self._timestamp:
            self._timestamp = timestamp
        if self._name != d["name"]:
            raise Exception("Backup does not belong to this app while processing {} for {} - {}".format(fn, self._name, timestamp))
        if not self._files.has_key(f):
            self._files[f] = fn
        else:
            raise Exception("Backup for app {} from {} already has data file while adding {}".format(self._name, timestamp, fn))

#       If this is a misc file (properties file) we have to parse it for some
#       extra info - most notably the needed application file. We do not use
#       the ConfigParser class here but match on =-separated items per line
#       because the properties file does not have a section header wich
#       ConfigParser does not like.
        if f == "misc":
            with open( self._files[f] , "r" ) as fp:
                for line in fp:
                    match = re_inifile.match(line)
                    if match:
                        d2 = match.groupdict()
                        if d2["key"] in properties_we_need:
                            self._properties[d2["key"]] = d2["value"]
            if self._properties.has_key("app_apk_md5"):
                self._apk_hash = self._properties["app_apk_md5"]
            else:
                # This is probably an app that that does not have an APK
                self._apk_hash = None
            if self._properties.has_key("app_data_md5"):
                self._data_hash = self._properties["app_data_md5"]
            else:
                # This is probably an app that that does not have an APK
                self._data_hash = None

    def __str__(self):
        """Represent the object as string"""
        if self.complete:
            if self._data_hash:
                if self._apk_hash:
                    btype = "normal app"
                else:
                    btype = "data only entity"
            else:
                if self._apk_hash:
                    btype = "APK only app (no data)"
                else:
                    btype = "unknown"
            canonical=""
            if self._properties.has_key("app_gui_label"):
                canonical += self._properties["app_gui_label"]
            if self._properties.has_key("app_version_name"):
                canonical += " ver. {}".format(self._properties["app_version_name"])
            if canonical != "":
                canonical_app_name = " (canonical name: {})".format(canonical)
            return "<DataBackup object (complete) for {} '{}'{} from timestamp {} with registered files {}>".format( btype, self._name, canonical_app_name, self._timestamp, self._properties )
        else:
            return "<DataBackup object (incomplete) for app '{}' from timestamp {} with registered files {}>".format( self._name, self._timestamp, self._files )

    @property
    def timestamp(self):
        """Property to return the timestamp of the backup or None if not yet
        known
        """
        return self._timestamp

    @property
    def files(self):
        """Property to return the filenames of the backup or an empty list if
        not yet known
        """
        return self._files.values()

    @property
    def apk_hash(self):
        """Property to return the apk_hash of the application backup that is
        required for this data snapshot.
        """
        if self.complete:
            return self._apk_hash

    @property
    def complete(self):
        """Property to show, if the object has all required information. This
        should return True after a proper file has been added.
        """
        if self._files.has_key("misc") and self._files.has_key("data") and ( self._apk_hash or self._data_hash ) and self._name and self._timestamp:
            return True
        else:
            return False


class App(object):
    """Object to represent an application. Contains 2 groups of backups ... one
    for application backups and one for data backups. You normally interact
    with App() objects and not with the contained backup objects.
    """
    def __init__(self, name):
        self._name = name
        self._data_backups = {}
        self._app_backups = {}

    def update_app_usage(self, reset=False):
        """Method to update the information in the required application
        backups, which data backups require them. Is called automatically after
        adding a file and while cleaning backups using the clean() method.
        Takes an optional argument 'reset' that defaults to False that
        cleans any known information about required backups before redetecting.
        """
        if reset:
            for app in self._app_backups.values():
                app.needed=False
        for data in self._data_backups.values():
            if data.apk_hash:
                if data.apk_hash in self._app_backups.keys():
                    self._app_backups[data.apk_hash].needed = data.timestamp

    def add_file(self, fn):
        """Method to add a file to this app. Takes a filename as the only
        argument. This autodetects the filetype and adds it to the appropriate
        backup object.  New backup objects are created as needed. File
        detection is done by regex matching on the filenames. No feedback is
        given if the operation was successful.
        """
        app  = re_app_file.match(os.path.basename(fn))
        data = re_data_file.match(os.path.basename(fn))
        misc = re_misc_file.match(os.path.basename(fn))
        if app:
            apk_hash = app.group("apk_hash")
            if not self._app_backups.has_key(apk_hash):
                self._app_backups[apk_hash] = AppBackup(self._name)
            if not self._app_backups[apk_hash].complete:
                self._app_backups[apk_hash].add_file(fn)
            else:
                pass
        elif data or misc:

            if data:
                d = data.groupdict()
                f = "data"
            if misc:
                d = misc.groupdict()
                f = "misc"

            timestamp = "{}-{}".format(d["date"], d["time"])
            if not self._data_backups.has_key(timestamp):
                self._data_backups[timestamp] = DataBackup(self._name)
            if not self._data_backups[timestamp].complete:
                self._data_backups[timestamp].add_file(fn)
                self.update_app_usage()
            else:
                pass
        self.update_app_usage()

    def old_backups(self, keep, keep_old):
        """Generator to yield all timestamps of data backups that are exceeding
        the count of backups to keep. Takes an int argument 'keep' to specify
        how many of the new backups to keep and an int argument 'keep_old' to
        specify how many of the oldest backups to keep.
        """
        for timestamp in sorted(self._data_backups.keys())[keep_old:keep * -1 ]:
            yield timestamp

    def clean_old_backups( self, keep, keep_old, delete=False ):
        """Generator to yield all affected filenames of data backups exceeding
        the count of backups to keep. Takes three arguments: int keep to specify
        how many new backups to keep, int keep_old to specify how many of the
        oldest backups to keep and optional bool delete (defaults to False).
        If delete is set, files are unlinked immediately after yielding their
        filename. Backups are only removed if they are marked as complete.
        """
        for timestamp in self.old_backups(keep, keep_old):
            if self._data_backups[timestamp].complete:
                for filename in self._data_backups[timestamp].files:
                    yield filename
                    if delete:
                        os.remove(filename)
                del self._data_backups[timestamp]

    def unused_apks(self, delete=False):
        """Generator to yield all affected filenames of application package
        backups that are not currently required by any data packages. Usage is
        recalculated from all present data backups before doing anything. Takes
        an optional argument 'delete' that defaults to False. If delete is
        True, files are unlinked immediately after yielding.
        """
        self.update_app_usage(reset=True)
        for hash, backup in self._app_backups.items():
            if not backup.needed:
                yield backup.files
                if delete:
                    os.remove(backup.files)
                del self._app_backups[hash]

    def clean(self, keep, keep_old, keep_apk, delete=False):
        """Method to list all the filenames of any backups in this app that are
        exceeding the specified keep count or not required anymore (in the case
        of application backups). Takes an int argument keep that specifies how
        many new backups to keep, an int argument keep_old to specify how many
        old backups to keep and an optional argument delete that defaults to
        False and specifies if the files should be deleted. Filenames are
        printed regardless of deletion. After deleting data backups that are
        exceeding the keep count, all application backups that remain unused
        then are listed (and removed in case of delete) unless keep_apk is set.
        """
        for fn in self.clean_old_backups( keep, keep_old, delete ):
            print fn
        if not keep_apk:
            for fn in self.unused_apks( delete ):
                print fn

    def __str__(self):
        """Represent the application object as a string. This returns a
        multiline string.
        """
        return "<App '{}' with {} apks and {} data backups: \nAPK {}\nDATA {}\n>".format(self._name, len(self._app_backups.keys()), len(self._data_backups.keys()), "".join([ "\n - {}".format(str(self._app_backups[x])) for x in sorted(self._app_backups.keys())]) , "".join([ "\n - {}".format(str(self._data_backups[x])) for x in sorted(self._data_backups.keys())]) )

Apps = {}

# Find all files in the specified path.
files = glob.glob( args.path + "*" )
for fn in files:
    for regex in regexes:
        match = regex.match(os.path.basename(fn))
        if match:
            app = match.group("name")
            if not app in Apps.keys():
                Apps[app] = App(app)
            Apps[app].add_file(fn)

# Iterate over all found app objects and perform the requested cleaning operation.
for item in sorted(Apps):
    Apps[item].clean(keep=args.keep_new, keep_old=args.keep_old, keep_apk=args.keep_apk, delete=args.delete)
