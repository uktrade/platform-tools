# Migration tools

You will need to log into cf cli - the scripts pick up the access key in ~/.cf/config


get-ci-conf.py - combines the ci-pipeline-config yaml files based on the namespace field: ci-conf.yaml is the outputi  
get-paas-config.py - retrieves paas data; output is in ci-conf.yaml  
combine-ci-paas-config.py - combines the previous two files; output: full-config.yaml  
build-copilot-config.py - takes full-config.yaml and renders individual copilot-bootstrap input files; see ../copilot-bootstrap-config/ for output  

Output files:  
paas-conf.yaml  
ci-conf.yaml  
full-config.yaml  
