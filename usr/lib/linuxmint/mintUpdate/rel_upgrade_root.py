#!/usr/bin/python3

import os, sys, apt, tempfile, gettext
import subprocess

gettext.install("mintupdate", "/usr/share/locale")

if os.getuid() != 0:
    print("Run this code as root!")
    sys.exit(1)

if len(sys.argv) != 3:
    print("Missing arguments!")
    sys.exit(1)

codename = sys.argv[1]
window_id = int(sys.argv[2])
sources_list = "/usr/share/hamonikr-upgrade-info/%s/official-package-repositories.list" % codename
sources_list2 = "/usr/share/hamonikr-upgrade-info/%s/hamonikr.list" % codename
sources_list3 = "/usr/share/hamonikr-upgrade-info/%s/hamonikr-pkg.list" % codename
blacklist_filename = "/usr/share/hamonikr-upgrade-info/%s/blacklist" % codename
additions_filename = "/usr/share/hamonikr-upgrade-info/%s/additions" % codename
removals_filename = "/usr/share/hamonikr-upgrade-info/%s/removals" % codename
preremovals_filename = "/usr/share/hamonikr-upgrade-info/%s/preremovals" % codename
preferences_file = "/usr/share/hamonikr-upgrade-info/%s/hamonikr-hanla.pref" % codename

if not os.path.exists(sources_list):
    print("Unrecognized release: %s" % codename)
    sys.exit(1)


def install_packages(packages):
    if len(packages) > 0:
        cmd = ["sudo", "/usr/sbin/synaptic", "--hide-main-window", "--non-interactive", "--parent-window-id", "%s" % window_id, "-o", "Synaptic::closeZvt=true"]
        f = tempfile.NamedTemporaryFile()
        for package in packages:
            pkg_line = "%s\tinstall\n" % package
            f.write(pkg_line.encode("utf-8"))
        cmd.append("--set-selections-file")
        cmd.append("%s" % f.name)
        f.flush()
        subprocess.run(cmd)

# dpkg -l package > 'rc' (Settings File Remaining)
def remove_packages(packages):
    if len(packages) > 0:
        cmd = ["sudo", "/usr/sbin/synaptic", "--hide-main-window", "--non-interactive", "--parent-window-id", "%s" % window_id, "-o", "Synaptic::closeZvt=true"]
        f = tempfile.NamedTemporaryFile()
        for package in packages:
            pkg_line = "%s\tdeinstall\n" % package
            f.write(pkg_line.encode("utf-8"))
        cmd.append("--set-selections-file")
        cmd.append("%s" % f.name)
        f.flush()
        subprocess.run(cmd)

# dpkg -l package > 'un' (All Delete)
def purge_packages(packages):
    if len(packages) > 0:
        cmd = ["sudo", "/usr/sbin/synaptic", "--hide-main-window", "--non-interactive", "--parent-window-id", "%s" % window_id, "-o", "Synaptic::closeZvt=true"]
        f = tempfile.NamedTemporaryFile()
        for package in packages:
            pkg_line = "%s\tpurge\n" % package
            f.write(pkg_line.encode("utf-8"))
        cmd.append("--set-selections-file")
        cmd.append("%s" % f.name)
        f.flush()
        subprocess.run(cmd)

def file_to_list(filename):
    returned_list = []
    if os.path.exists(filename):
        with open(filename, 'r') as file_handle:
            for line in file_handle:
                line = line.strip()
                if line == "" or line.startswith("#"):
                    continue
                returned_list.append(line)
    return returned_list

# STEP 1: UPDATE APT SOURCES
#---------------------------
if os.path.exists("/etc/apt/sources.list.d/official-source-repositories.list"):
    subprocess.run(["rm", "-f", "/etc/apt/sources.list.d/official-source-repositories.list"])

if os.path.exists("/etc/apt/sources.list.d/hamonikr.list"):
    subprocess.run(["rm", "-f", "/etc/apt/sources.list.d/hamonikr.list"])

if os.path.exists("/etc/apt/sources.list.d/hamonikr-pkg.list"):
    subprocess.run(["rm", "-f", "/etc/apt/sources.list.d/hamonikr-pkg.list"])

subprocess.run(["cp", sources_list, "/etc/apt/sources.list.d/official-package-repositories.list"])
subprocess.run(["cp", sources_list2, "/etc/apt/sources.list.d/hamonikr.list"])
subprocess.run(["cp", sources_list3, "/etc/apt/sources.list.d/hamonikr-pkg.list"])
subprocess.run(["cp", preferences_file, "/etc/apt/preferences.d/hamonikr-hanla.pref"])

# STEP 2: UPDATE APT CACHE
#-------------------------

cache = apt.Cache()
subprocess.run(["sudo", "/usr/sbin/synaptic", "--hide-main-window", "--update-at-startup", "--non-interactive", "--parent-window-id", "%d" % window_id])

# STEP 2.5 : PRE REMOVE PACKAGE (depends probrem)

removals = file_to_list(preremovals_filename)
purge_packages(removals)

# STEP 3: INSTALL MINT UPDATES
#--------------------------------

dist_upgrade = True

# Reopen the cache to reflect any updates
cache.open(None)
cache.upgrade(dist_upgrade)
changes = cache.get_changes()

blacklist = file_to_list(blacklist_filename)

packages = []
for pkg in changes:
    if (pkg.is_installed and pkg.marked_upgrade):
        package = pkg.name
        newVersion = pkg.candidate.version
        oldVersion = pkg.installed.version
        size = pkg.candidate.size
        sourcePackage = pkg.candidate.source_name
        short_description = pkg.candidate.raw_description
        description = pkg.candidate.description
        if sourcePackage not in blacklist:
            if (newVersion != oldVersion):
                update_type = "package"
                for origin in pkg.candidate.origins:
                    if origin.origin == "linuxmint" or origin.origin == "pkg.hamonikr.org":
                        if origin.component != "romeo" and package != "linux-kernel-generic":
                            packages.append(package)

install_packages(packages)

# STEP 4: ADD PACKAGES
#---------------------

additions = file_to_list(additions_filename)
install_packages(additions)

# STEP 5: REMOVE PACKAGES
#------------------------

removals = file_to_list(removals_filename)
remove_packages(removals)

# STEP 6: UPDATE GRUB
#--------------------

try:
    subprocess.run(["update-grub"])
    if os.path.exists("/usr/share/ubuntu-system-adjustments/systemd/adjust-grub-title"):
        subprocess.run(["/usr/share/ubuntu-system-adjustments/systemd/adjust-grub-title"])
except Exception as detail:
    syslog.syslog("Couldn't update grub: %s" % detail)

# STEP 7: DELETE FILE
#--------------------
subprocess.run(["rm", "/etc/apt/preferences.d/hamonikr-hanla.pref"])