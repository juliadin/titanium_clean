# titanium_clean
Small python tool to clean folders created by the android backup tool "Titanium Backup"

## Motivation

If you do regular Titanium Backups on a device with not that much storate you probably know the problem:
You want to keep a reasonable number of backups available on the device and probably this archive gets really 
big. I usually keep 2 backups on the device and sync the TitaniumBackup Folder to a NAS at night - but to be honest,
I want to keep more than 2 copies on the NAS. 

I used FolderSync for some time to sync the TitaniumBackup folder to the NAS including deletions, so if TitaniumBackups
retention period for a backup was over and it was deleted on the device, it was deleted on the NAS as well. 

I wanted to have an intelligent expiry of backups on the NAS that could be different than on the mobile device so 
I could stop syncing deletions to the NAS and keep more than the two backups there that I would keep on my mobile.

## Target

The target was to create a small enough tool with few external dependencies that was able to:

 - Identify backups by the ID of the app
 - keep a certain number of recent data backups for that app
 - keep a certain number of oldest data backups for that app
 - keep all apk backups that are required by the data backups
 - clean up the rest

## Usage
```
# ./titanium_clean.py --help
usage: titanium_clean.py [-h] --path PATH [--keep-new X] [--keep-old Y]
                         [--keep-apk] [--delete]

titanium_clean ver. 1.0 by Joel Brunenberg <joel@jjim.de> - provided with
ABSOLUTELY NO WARRANTY under the licence described in the LICENSE file in this
folder. - A cleaner for Titanium Backup directories to keep the last X and Y
oldest backups of app data and their apps.

optional arguments:
  -h, --help            show this help message and exit
  --path PATH, -p PATH  Path where the titanium backups are. This is globbed
                        with * so filename prefixes are also possible to only
                        work on a specific glob pattern. Existance is not
                        checked. Be careful. If you want to specify a
                        directory, a trailing slash is mandantory.
  --keep-new X, -k X    how many of the newest backups to keep
  --keep-old Y, -o Y    how many old backups to keep in any case.
  --keep-apk, -a        ignore unused APK backups and keep them in case of
                        delete.
  --delete, -d          delete unwanted files - otherwise only the names are
                        listed.

```

## Warranties

This is provided as is. No warranties. This tool may delete all your data. Please read the source and see if it suits your needs. Not for inexperienced users.

## Thanks

Thanks to the Titanium Backup dev team. Its a great app to keep things in check on Android if you are root.
Check out the app here: https://play.google.com/store/apps/details?id=com.keramidas.TitaniumBackup
Support them here with a PRO key: https://play.google.com/store/apps/details?id=com.keramidas.TitaniumBackupPro

Thanks to Tacit Dynamics for FolderSync. Its a good tool to keep folders in sync.
Check out the app here: https://play.google.com/store/apps/details?id=dk.tacit.android.foldersync.full
