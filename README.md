# camelot

This was a hobby project of mine to try get a really cheap 'terminal services on demand'
working with AWS EC2 instances that are not always powered on. It would boot the instance,
get its Elastic IP and give you a RDP file to download. You could then shut it off via the
same UI.

# To use

* Populate main.py with various AWS and PASSWD variables as documented there.
* Populate GeoIP.dat which you can download for free.
