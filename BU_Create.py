import subprocess
import os
#from utilities import *

def do_backup():
    os.chdir("L:/warehouse/lz")
    try:
        BUP = subprocess.Popen("sqlcmd -S RWDB1 -d warehouse -U RWBackupRestore -P RuddWisd0m -i backup.sql")
        BUP.wait()
        result = True
    except:
        result = False
    return result

def do_restore():
    os.chdir("L:/warehouse/lz")
    try:
        BUP = subprocess.Popen("sqlcmd -S RWDB1 -d warehouse -U RWBackupRestore -P RuddWisd0m -i dropWHTest.sql")
        BUP.wait()
    except:
        pass # this might fail it tries to drop the test database when it may have been dropped already
    try:
        BUP = subprocess.Popen("sqlcmd -S RWDB1 -d warehouse -U RWBackupRestore -P RuddWisd0m -i restore.sql")
        BUP.wait()
        result = True
    except:
        result = False
    return result




