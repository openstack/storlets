# !/bin/bash

test_dir=${PWD}
cd ../Deploy/playbook
ansible-playbook -i hosts set_test_conf.yml -e run_on_proxy=false
cd ${test_dir}
python sys_test.py
cd ../Deploy/playbook
ansible-playbook -i hosts set_test_conf.yml -e run_on_proxy=true
cd ${test_dir}
python sys_test.py
