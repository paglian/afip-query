#!/bin/bash

set -e

cd backend
echo " === run.sh === Starting freeling server..."
./fl --server & 
sleep 2

echo " === run.sh === Starting Django web server..."
cd ../frontend/faqquery
python manage.py runserver &
sleep 2

cd -

echo ""
echo " === run.sh ========================================================== "
echo " If everything went OK, open your web browser at http://127.0.0.1:8000"
echo " ====================================================================="
