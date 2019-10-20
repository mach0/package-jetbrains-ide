#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse
from urllib.error import URLError

import util
import sys
import os
import urllib.request
import re
import json

__author__ = 'Andreas Bader'
__version__ = '0.02'

newVersionURL = "https://data.services.jetbrains.com/products/releases?code=%s&latest=true&type=release"

# format: key = name
#         list of [VersionVarNamesDict, VersionRegex]
#         VersionRegex greps the regex out of version.js
supportedIDEs = {"pycharm": [{"community": "PCC", "professional": "PCP"},
                             "[0-9]+\.[0-9]+(\.[0-9]+){0,1}"],
                 "idea":    [{"community": "IIC", "professional": "IIU"},
                             "[0-9]+\.[0-9]+(\.[0-9]+){0,1}"]
                 }
supportedEditions = ['community', 'professional']


def cleanup(code, log):
    if util.check_folder(os.path.join(script_path, "tmp"), logger, False, False):
        if not util.delete_folder(os.path.join(script_path, "tmp"), logger, True):
            log.error("%s does exist and can not be deleted." % os.path.join(script_path, "tmp"))
            sys.exit(-1)
    sys.exit(code)


def get_download_link(varnames, edition, log, embeddedJava):
    varname = varnames[edition]
    try:
        response = urllib.request.urlopen(newVersionURL % varname, timeout=10)
    except URLError:
        log.error("Error while opening %s. Error was '%s'." % (newVersionURL % varname, sys.exc_info()[0]))
        return None
    try:
        content = response.read().decode('utf-8')
    except UnicodeDecodeError:
        log.error("Error while retrieving %s. Error was '%s'." % (newVersionURL % varname, sys.exc_info()[0]))
        return None
    if response is not None and response.status == 200:
        try:
            parsedjson = json.loads(content)
        except ValueError:
            log.error("Error while parsing json from %s. Error was '%s'." %
                      (newVersionURL % varname, sys.exc_info()[0]))
            return None
        linuxKey = 'linux'
        if not embeddedJava:
            linuxKey = 'linuxWithoutJDK'

        if varname in parsedjson.keys():
            if len(parsedjson[varname]) > 0:
                if "downloads" in parsedjson[varname][0].keys():
                    if linuxKey in parsedjson[varname][0]["downloads"].keys():
                        if "link" in parsedjson[varname][0]["downloads"][linuxKey].keys():
                            return parsedjson[varname][0]["downloads"][linuxKey]["link"]
                        else:
                            log.error("Error while parsing '%s': No 'link' in dictionary." % newVersionURL % varname)
                    else:
                        log.error("Error while parsing '%s': No '%' in dictionary." % newVersionURL % varname, linuxKey)
                else:
                    log.error("Error while parsing '%s': No 'downloads' in dictionary." % newVersionURL % varname)
            else:
                log.error("Error while parsing '%s': No entries in list." % newVersionURL % varname)
        else:
            log.error("Error while parsing '%s': No '%s' in dictionary." % (newVersionURL % varname, varname))
    return None

def fix_vm_options(build_root, ide, appname, bits=""):
    # Fixing vmoptions file(s)
    file1 = open(os.path.join(build_root, "etc", args.ide, "%s.vmoptions.README" % appname), "a")
    file2 = open(os.path.join(build_root, "usr", "share", "jetbrains", appname, "bin", "%s.vmoptions" % args.ide), "r")
    file3 = open(os.path.join(build_root, "usr", "share", "jetbrains", appname, "bin", "%s.vmoptions2" % args.ide), "w")
    file1.write("\nOriginal pycharm.vmoptions:\n")
    for line in file2:
        file1.write(line)
        if "yjpagent" not in line:
            file3.write(line)
    file1.close()
    file2.close()
    file3.close()
    fullpath = os.path.join(build_root, "usr", "share", "jetbrains", appname, "bin",
                                         "%s.vmoptions" % args.ide)
    if not util.delete_file(fullpath, logger):
        logger.error("Error while deleting '%s'." % fullpath)
        cleanup(-1, logger)

    p1 = os.path.join(build_root, "usr", "share", "jetbrains", appname, "bin",
                                       "%s.vmoptions2" % args.ide)
    p2 = os.path.join(build_root, "usr", "share",
                                       "jetbrains", appname, "bin",
                                       "%s.vmoptions" % appname)
    if not util.copy_file(p1, p2, logger):
        logger.error("Error while copying '{} to '{}'.".format(p1, p2))
        cleanup(-1, logger)
    fullpath = os.path.join(build_root, "usr", "share", "jetbrains",
                                         appname, "bin",
                                         "%s.vmoptions2" % args.ide)
    if not util.delete_file(fullpath, logger):
        logger.error(fullpath)
        cleanup(-1, logger)



# Configure ArgumentParser
parser = argparse.ArgumentParser(prog="package.py", epilog="Supported IDEs: %s\nSupported Editions: %s"
                                                           % (list(supportedIDEs.keys()), supportedEditions),
                                 description="Packages Jetbrains IDEs for Debian/Ubuntu.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-e", "--edition", metavar="EDITION", default=supportedEditions[0],
                    choices=supportedEditions, help="Which Edition should be packaged?")
parser.add_argument("-i", "--ide", metavar="IDE", choices=supportedIDEs.keys(), default=list(supportedIDEs.keys())[0],
                    help="Which IDE should be packaged?")
parser.add_argument("-j", "--java", metavar="JAVA", choices={'y','n'}, default='y',
                    help="Which IDE should be packaged?")
parser.add_argument("-l", "--list", action='store_true', help="list all supported IDEs")
parser.add_argument("-c", "--check", action='store_true',
                    help="check if installed version is older than the newest version available (needs dpkg)")
parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
parser.add_argument('-n', '--no-download', action='store_true', help="skip downloading - assumes already downloaded")
args = parser.parse_args()

# Configure Logging
logLevel = logging.WARN
logging.basicConfig(level=logLevel)
logger = logging.getLogger(__name__)

if args.list:
    print("Supported JetBrains IDEs:")
    for key in supportedIDEs.keys():
        print(key)
    sys.exit(0)

# Checking tools
for tool in ["tar", "dpkg", "fakeroot", "dpkg-deb"]:
    if not util.cmd_exists(tool):
        logger.error("%s not found or not usable." % tool)
        sys.exit(-1)

# Get URL
link = get_download_link(supportedIDEs[args.ide][0], args.edition, logger, args.java!='n')

if link is None:
    logger.error("Could not get url for %s." % args.ide)
    sys.exit(-1)

version = re.search(supportedIDEs[args.ide][1], link.split("/")[-1])
if version is None:
    logger.error("Could not parse version out of '%s'." % link.split("/")[-1])
    sys.exit(-1)

if args.check:
    result = util.run_cmd("dpkg -l | grep '%s' | grep -E -o '%s' | cat" %
                          (args.ide, supportedIDEs[args.ide][1]), logger, True, True).decode('utf-8').replace("\n", "")
    if result is None:
        logger.error("Error while running '%s'." % "dpkg -l | grep '%s' | grep -E -o '%s'" %
                     (args.ide, supportedIDEs[args.ide][1]))
        sys.exit(-1)
    if result != version.group() and result != "":
        print("There is a newer version (%s) than installed (%s) available!" % (version.group(), result))
        sys.exit(1)
    if result == "":
        print("%s %s is not installed." % (args.ide, args.edition))
    sys.exit(0)


appname = "{}-{}".format(args.ide, args.edition)
script_path = util.get_script_path()
build_root = os.path.join(script_path, "tmp", "root")

# Checking folders
if not util.check_folder(os.path.join(script_path, "output"), logger, False, True):
    if not util.create_folder(os.path.join(script_path, "output")):
        logger.error("%s does not exist and can not be created." % os.path.join(script_path, "output"))
        sys.exit(-1)

if not args.no_download:
    if util.check_folder(os.path.join(script_path, "tmp"), logger, False, True):
        if not util.delete_folder(os.path.join(script_path, "tmp"), logger, True):
            logger.error("%s does exist and can not be deleted." % os.path.join(script_path, "tmp"))
        sys.exit(-1)

for folder in [os.path.join(script_path, "tmp"),
               os.path.join(build_root, "usr", "share", "jetbrains", appname),
               os.path.join(build_root, "usr", "share", "applications"),
               os.path.join(build_root, "usr", "bin"),
               os.path.join(build_root, "etc", args.ide),
               os.path.join(build_root, "etc", "sysctl.d"),
               os.path.join(build_root, "DEBIAN")]:
#     if not util.create_folder(folder):
        if not os.path.exists(folder): # and not os.makedirs(folder):
            os.makedirs(folder)
            #logger.error("%s cannot be created." % folder)
            #sys.exit(-1)

if not util.check_folder(os.path.join(script_path, "data"), logger, False, False):
    cleanup(-1, logger)

if not util.check_folder(os.path.join(script_path, "data", args.ide), logger, False, False):
    cleanup(-1, logger)

if not util.check_folder(os.path.join(script_path, "data", args.ide, "debian"), logger, False, False):
    cleanup(-1, logger)

# Checking files
for file in ["control.in", "postinst", "sysctl-99.conf"]:
    if not util.check_file_exists(os.path.join(script_path, "data", args.ide, "debian", file)) and not \
            util.check_file_readable(os.path.join(script_path, "data", args.ide, "debian", file)):
        logger.error("%s does not exist or is not readable." % file)
        cleanup(-1, logger)

for file in ["LICENSE", "Makefile", "pkginfo.in", "prototype.in", "icon.desktop", "start.sh", "vmoptions.README"]:
    if not util.check_file_exists(os.path.join(script_path, "data", args.ide, file)) and not \
            util.check_file_readable(os.path.join(script_path, "data", args.ide, file)):
        logger.error("%s does not exist or is not readable." % file)
        cleanup(-1, logger)

# Download URL
if not args.no_download:
    if util.check_file_exists(os.path.join(script_path, "tmp", link.split("/")[-1])):
        if not util.delete_file(os.path.join(script_path, "tmp", link.split("/")[-1]), logger, False):
            cleanup(-1, logger)

if not args.no_download:
    resp = urllib.request.urlretrieve(link, os.path.join(script_path, "tmp", link.split("/")[-1]), util.progress_hook)
    if resp is None or resp[1]["Connection"] != "close" or int(resp[1]["Content-Length"]) < 100000:
        logger.error("Error while downloading '%s'." % os.path.join(script_path, "tmp", link.split("/")[-1]))
        cleanup(-1, logger)

if not util.run_cmd("tar --strip-components 1 -C %s -zxf %s" %
                    (os.path.join(build_root, "usr", "share", "jetbrains", appname),
                     os.path.join(script_path, "tmp", link.split("/")[-1])), logger, False):
    logger.error("Error while unpacking '%s' to '%s'." %
                 (os.path.join(script_path, "tmp", link.split("/")[-1])),
                 os.path.join(build_root, "usr", "share", "jetbrains", appname))
    cleanup(-1, logger)

# Copy Files
copyList = [
            [os.path.join(script_path, "data", args.ide, "vmoptions.README"),
             os.path.join(build_root, "etc", args.ide, "%s.vmoptions.README" % appname)],
            [os.path.join(script_path, "data", args.ide, "debian", "sysctl-99.conf"),
             os.path.join(build_root, "etc", "sysctl.d", "99-%s.conf" % appname)],
            ]

for copyTuple in copyList:
    if not util.copy_file(copyTuple[0], copyTuple[1], logger):
        cleanup(-1, logger)

fix_vm_options(build_root, args.ide, appname, bits="")

# Copy files that needed fixes (inserts ide name etc.)
copyList = [
            [os.path.join(script_path, "data", args.ide, "icon.desktop"),
             os.path.join(build_root, "usr", "share",
                          "applications", "%s.desktop" % appname)],
            [os.path.join(script_path, "data", args.ide, "start.sh"),
             os.path.join(build_root, "usr", "bin", appname)],
            [os.path.join(script_path, "data", args.ide, "debian", "postinst"),
             os.path.join(build_root, "DEBIAN", "postinst")],
            [os.path.join(script_path, "data", args.ide, "debian", "templates"),
             os.path.join(build_root, "DEBIAN", "templates")],
            [os.path.join(script_path, "data", args.ide, "debian", "control.in"),
             os.path.join(build_root, "DEBIAN", "control")]
            ]

for copyTuple in copyList:
    # Check is destination exists
    if util.check_file_exists(copyTuple[1]):
        if not util.delete_file(copyTuple[1], logger, False):
            cleanup(-1, logger)

    file1 = open(copyTuple[0], "r")
    file2 = open(copyTuple[1], "w")
    otherEdition = 'community'
    oldEdition = 'iu'
    otherOldEdition = 'ic'
    if args.edition == otherEdition:
        otherEdition = 'professional'
        oldEdition = "ic"
        otherOldEdition = 'iu'
    for line in file1:
        file2.write(
            line.replace("OTHER_EDITION2", otherEdition.upper())
                .replace("OTHER_EDITION", otherEdition)
                .replace("VERSION", version.group())
                .replace("EDITION2", args.edition.upper())
                .replace("EDITION", args.edition)
                .replace("OLD1", oldEdition)
                .replace("OLD2", oldEdition.upper())
                .replace("OLD3", otherOldEdition)
                .replace("OLD4", otherOldEdition.upper())
                .replace("APPNAME", appname)
                )
    file1.close()
    file2.close()

# Chmod Start Skript and sysctl
for file in [os.path.join(build_root, "usr", "bin", appname),
             os.path.join(build_root, "etc", "sysctl.d", "99-%s.conf" % appname),
             os.path.join(build_root, "DEBIAN", "postinst")]:
    if not util.run_cmd("chmod +rx %s" % file, logger, False):
        logger.error("Error while running chmod +rx on '%s'." % file)
        cleanup(-1, logger)

if util.check_file_exists(os.path.join(script_path, "tmp", "fakeroot.save")):
    if not util.delete_file(os.path.join(script_path, "tmp", "fakeroot.save"), logger, False):
        cleanup(-1, logger)

file1 = open(os.path.join(script_path, "tmp", "fakeroot.save"), "w")
file1.write("")
file1.close()

# package it!
cmd = "fakeroot -i %s -s %s -- chown -R root:root %s" % (os.path.join(script_path, "tmp", "fakeroot.save"),
                                                         os.path.join(script_path, "tmp", "fakeroot.save"),
                                                         os.path.join(build_root))
if not util.run_cmd(cmd, logger, False):
    logger.error("Error while exexuting '%s'." % cmd)
    cleanup(-1, logger)

cmd = "fakeroot -i %s -s %s -- dpkg-deb -b %s %s" % (os.path.join(script_path, "tmp", "fakeroot.save"),
                                                     os.path.join(script_path, "tmp", "fakeroot.save"),
                                                     os.path.join(build_root),
                                                     os.path.join(script_path,
                                                                  "tmp", "%s-%s-%s.deb"
                                                                  % (args.ide, args.edition, version.group())))
if not util.run_cmd(cmd, logger, False):
    logger.error("Error while exexuting '%s'." % cmd)
    cleanup(-1, logger)

# copy package
if not util.check_file_exists(
        os.path.join(script_path, "tmp", "%s-%s-%s.deb" % (args.ide, args.edition, version.group()))):
    logger.error("Error '%s' was not created." %
                 os.path.join(script_path,
                              "tmp", "%s-%s-%s.deb" % (args.ide, args.edition, version.group())))
    cleanup(-1, logger)

if not util.copy_file(
        os.path.join(script_path, "tmp", "%s-%s-%s.deb" % (args.ide, args.edition, version.group())),
        os.path.join(script_path, "output", "%s-%s-%s.deb" % (args.ide, args.edition, version.group())),
        logger):
    cleanup(-1, logger)

# cleanup
# if util.check_file_exists(os.path.join(script_path, "tmp", "fakeroot.save")):
#     if not util.delete_file(os.path.join(script_path, "tmp", "fakeroot.save"), logger, False):
#         cleanup(-1, logger)

print("Finished packaging %s to %s. Install now with dpkg -i %s."
      % (args.ide,
         os.path.join(script_path, "output", "%s-%s-%s.deb" % (args.ide, args.edition, version.group())),
         os.path.join(script_path, "output", "%s-%s-%s.deb" % (args.ide, args.edition, version.group()))))
cleanup(0, logger)
sys.exit(0)
