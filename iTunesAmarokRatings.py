#!/usr/bin/env python3

import mysql.connector, subprocess, plistlib, sys

if len(sys.argv) == 1:
    print("Usage: %s [ PATH to iTunes Music Library.xml ]")
    sys.exit(1)

def getInfo(track):
    # Jump to the next 'track' if rating is not present.
    if track.get("Rating") == None:
        return None
    trackA = {
        'title' : track.get("Name"),
        'album' : track.get("Album"),
        'tracknumber' : track.get("Track Number"),
        'rating' : track.get("Rating")
    }
    if track.get("Disc Number") != None:
        trackA['discnumber'] = track.get("Disc Number")
    return trackA

# Define data for starting & connecting to the MySQL embedded server
amarokDir = subprocess.check_output(["kde4-config", "--path", "data"]).decode("utf-8").split(":")[0] + "amarok"
defaultFile = amarokDir + "/my.cnf"
socketFile = amarokDir + "/sock"
dataDir = amarokDir + "/mysqle"

# Create the arguments array for starting the MySQL embedded server
#mysqlArgs = 'mysqld_safe --default-file=' + defaultFile + ' --default-storage-engine=MyISAM' + ' --datadir=' + dataDir + ' -S ' + socketFile + ' --skip-grant-tables'
mysqlArgs = 'mysqld_safe --defaults-file=' + defaultFile + ' --default-storage-engine=MyISAM --datadir=' + dataDir + ' --socket=' + socketFile + ' --skip-grant-tables'

# Start the MySQL embedded server
print("Starting the embedded MySQL server")
MySQLserver = subprocess.Popen(mysqlArgs, cwd=amarokDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

# Load the iTunes Music Library.xml file and process
# only the tracks with ratings
print("Loading iTunes database")
iTunesDB = plistlib.readPlist(sys.argv[1])["Tracks"]
tracks = []

for t in iTunesDB:
    tracks += [getInfo(iTunesDB[t])]

tracks = [t for t in tracks if t is not None]

# Connect to the Amarok MySQL Database using the socket
print("Connecting to Amarok Database")
db = mysql.connector.connect(database='amarok', unix_socket=socketFile)

cursor = db.cursor()

# Store the number of tracks with rating so
# it can be used for a 'progress message'
Updates = len(tracks)
# Initialize a counter at i = 0
i = 0

print("Updating rating for %d files" % Updates)
for t in tracks:
    # Create an empty string which will be used for the cursor.execute()
    # method for updating the ratings
    UpdateRating = "";
    # if len(t) == 5 then it has 'discnumber' attribute as defined
    # by the getInfo() method at the line 5 of this script so it
    # is used for the cursor.execute() statement.
    if len(t) == 5:
        UpdateRating = ("update statistics set rating=%(rating)s where url in (select url from tracks where title=%(title)s and album in (select id from albums where name=%(album)s) and tracknumber=%(tracknumber)s and discnumber=%(discnumber)s)")
    # if len(t) != 5 then len(t) == 4 and will not have 'discnumber'
    # attribute as defined by the getInfo method at the line 5 of
    # this script so it will not be used for the update statement.
    else:
        UpdateRating = ("update statistics set rating=%(rating)s where url in (select url from tracks where title=%(title)s and album in (select id from albums where name=%(album)s) and tracknumber=%(tracknumber)s)")

    cursor.execute(UpdateRating, t)
    # Counter for the "progress status message"
    i += 1
    # output to the stdout, use "\r" to replace the content
    # so it keeps updating and don't use 'len(t)' lines on
    # the console
    sys.stdout.write('\rUpdated so far %d of %d ( %d %% )' % (i, Updates, i/Updates*100))

print("Done.")

# Close the cursor
cursor.close()
# Close the database
db.close()

# Shutdown the embedded MySQL server
print("Shutting down the embedded MySQL server")
shutDown = 'mysqladmin -S ' + socketFile + ' shutdown'
MySQLserverFinish = subprocess.Popen(shutDown, cwd=amarokDir, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
