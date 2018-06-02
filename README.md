# ACM_WC

## Description

Kaggle like site for the world cup prediction competition. 

## How to setup

Make sure you install all the requirments; `pip install requirments.txt`

You will then need to place a config folder in the root project directory.

Place the location of the app, and where you want the logging file to reside in the **world_cup.service file**  
Place the **world_cup.service** in `/etc/systemd/`

Run this command `service world_cup start`  
Check that it's running by using `service world_cup stop`

Add the port number to **wp-predictor.insight-centre.org.conf**  
Place **wp-predictor.insight-centre.org.conf** in `/etc/apache2/sites-available`  
Run `sudo a2ensite wp-predictor.insight-centre.org.conf`  
Run `sudo apache2 restart`
