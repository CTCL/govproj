govproj
=======

Code for governance project tasks

Twitter
-------
Code to potentially use in the future to scrape twitter data for representatives. Performs three searches per candidate based on office held and office level.

Steps to run:
 - add file of example office holders that have twitter data
 - run twitter_test.py, which will run three twitter searches for each row in the office holder file and output the data into a search results file 

Old Processing
--------------
Old style processing that keeps all files in Dropbox, passing them to relevant directories as necessary and rematching ocdid every time representative information is processes

Steps to run:
 - copy config.example.py to config.py, edit BASE_DIR appropriately.
 - run assign_ocdids.py - this will take files from raw format, assign ocdids, and move them to the staging environment
 - run valdidate_data.py - this will cycle through the files and create an error report output with flagged issues, unsure matches, etc.
 - run create_json.py - this will generate the json formatted data that Google is looking for, including generating the id's for each data type
 - zip up all json files
 - upload to ballotinfo.org
 - unzip to apache_root/office_data
 - email the Googs to let them know the data has been updated

New Processing
--------------
So I was working through cleaning this up to make it functional, and then a funny thing happened. The Old Processing code is now cleaner and more functional than the new stuff. Whoops. Use the old stuff, work towards moving to the new format

Utility Scripts
---------------
Scripts for specific tasks, explained below

 - clean_raw_data.py - pulls out non-ascii characters from raw (social_media candidate info) files
 - email_office_holders.py - Script to send emails to office holders with the information we have on them
 - track_changes.py - write out the diff of multiple json sets

Secrets
-------
Login and API information for accounts
