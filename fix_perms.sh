#!/bin/bash

WEBROOT=`dirname $0`

cd $WEBROOT
# Because this directory is obscenely big, move it out of the way first.
sudo mv -v esp/file_cache/render_qsd /esp/tmp/render_qsd
sudo setfacl -Rm default:user:www-data-stanford:r-x,user:www-data-stanford:r-x,default:group:www-data-stanford:r-x,group:www-data-stanford:r-x,default:user:Debian-exim:r-x,user:Debian-exim:r-x,default:group:esp:rwx,group:esp:rwx,default:group:stanford:rwx,group:stanford:rwx $WEBROOT

sudo chmod -R ug+rw $WEBROOT
sudo chmod +x $WEBROOT/mailgates/mailgate.py
sudo chmod +x $WEBROOT/esp/esp/manage.py

sudo chown -R www-data-stanford:www-data-stanford esp
#find esp -type d -exec chmod 550 {} \;
#find esp -type f -exec chmod 440 {} \;
#chmod 550 esp/public/esp.fcgi
#chmod -R 775 esp/public/media/{subsection_images,uploaded,latex}

# Okay, done. Obscene directory, you can come back now.
sudo mv -v /esp/tmp/render_qsd esp/file_cache/render_qsd

cd $WEBROOT/esp/public/media
sudo setfacl -Rm default:user:www-data-stanford:rwx,user:www-data-stanford:rwx,default:group:www-data-stanford:rwx,group:www-data-stanford:rwx subsection_images latex_media uploaded

#DIR=`dirname $0`
#cd $DIR
#chown -R www-data-stanford:www-data-stanford esp
#find esp -type d -exec chmod 550 {} \;
#find esp -type f -exec chmod 440 {} \;
#chmod 550 esp/public/esp.fcgi
#chmod -R 775 esp/public/media/{subsection_images,uploaded,latex}

