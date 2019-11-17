
# A django Lab information framework

This is highly experimental, only partially functional, and should be used for entertainment purposes only.

You can install and try locally using these commands (after `cd` ing to the directory you've cloned/uncompressed).

```bash
pip3 install virtualenv
python3 -m virtualenv venv
source venv/bin/activate
pip install django django-reversion django-select2 qrcode
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py shell --command="from lims.tests import populate_test_data; populate_test_data()"
python3 manage.py runserver
```
