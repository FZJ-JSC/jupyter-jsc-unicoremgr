# Jupyter-JSC UNICORE manager

This Image is used by [Jupyter-JSC](https://jupyter-jsc.fz-juelich.de) to start JupyterLabs via UNICORE on connected hpc systems.

## Configuration
The UNICORE manager webservice uses a JSON format that allows you to configure the commands.  
  
| Tag | Type | Description |
| ------ | ------ | ------ |
| systems | Dict | System specific configuration |
| systems._name_ | Dict | Required to define system specific configuration for system _name_ |
| systems._name_.site_url | String | Target to communicate with. Most of the time it's a UNICORE Gateway. Default: https://localhost:8080/DEMO-SITE/rest/core |
| systems._name_.pyunicore | Dict | UNICORE speicific configuration. |
| systems._name_.pyunicore.job_archive | String | Path. UNICORE manager service will store files of stopped jobs there. Default: /tmp |
| systems._name_.pyunicore.transport | Dict | UNICORE Transport speicific configuration. |
| systems._name_.pyunicore.transport.certificate_path | String or False | Path to certificate authority file of UNICORE Gateway. False: certificate not verified. Default: False |
| systems._name_.pyunicore.transport.oidc | Boolean | Defines oidc parameter for UNICORE transport. Default: True |
| systems._name_.pyunicore.transport.timeout | Integer | Timeout when communication with UNICORE. Default 120. |
| systems._name_.pyunicore.transport.set_preferences | Boolean | Defines set_preferences parameter for UNICORE transport. Default: True |
| systems._name_.pyunicore.download_after_stop  | Boolean | Download files in job directory, after job was stopped. Default: False |
| systems._name_.pyunicore.delete_after_stop  | Boolean | Delete job directory, after job was stopped. Default: False |
| systems._name_.pyunicore.job_descriptions | Dict | Job Description specific configuration. |
| systems._name_.pyunicore.job_descriptions.base_directory | String | Path to directory where job descriptions are stored. Default: /mnt/config/job_descriptions |
| systems._name_.pyunicore.job_descriptions.template_filename | String | This file will be used as template for each new create job. Default: job_description.json.template |
| systems._name_.pyunicore.job_descriptions.replace_indicators | List of 2 Strings | These indicators will be used to find variables in all job files, which should be replaced with their actual value. \<JUPYTERHUB_API_TOKEN\> will be replaced with the actual value. Default: ["<", ">"] |
| systems._name_.pyunicore.job_descriptions.input | Dict | Input files for Job Description speicific configuration. |
| systems._name_.pyunicore.job_descriptions.input.directory_name | String | Name of the directory where all input files are stored. Default: input |
| systems._name_.pyunicore.job_descriptions.input.skip_prefixs | List of Strings | Files with these prefixs will be skipped in this job. Default: ["skip_"] |
| systems._name_.pyunicore.job_descriptions.input.skip_suffixs | List of Strings | Files with these suffixs will be skipped in this job. Default: [".swp"] |
| systems._name_.pyunicore.job_descriptions.hooks | Dict | Hooks can be used, to specify Job behaviour for different projects, accounts, partitions or vos. |
| systems._name_.pyunicore.job_descriptions.hooks._name_ | Dict | Name of this hook. Will be replaced in input or job_description file. |
| systems._name_.pyunicore.job_descriptions.hooks._name_._key_ | List of Strings | Key/Values to determine specific behaviour. Example: "project": ["training2101", "training2102"] |
| systems._name_.pyunicore.job_descriptions.resource_mapping | Dict | JupyterHub will send us resources as normal user_options. We want to find these and map them to UNICORE specific names |
| systems._name_.pyunicore.job_descriptions.resource_mapping._name_ | String | _name_ as JupyterHub used it in user_options. Value will be the expected key for UNICOREs job description. Example: "resource_nodes": "Nodes" |
| systems._name_.pyunicore.job_descriptions.interactive_partitions | Dict | Mapping of internal partition name, to the name UNICORE expects it. |
| systems._name_.pyunicore.job_descriptions.interactive_partitions._name_ | String | Partition name as configured in UNICORE. `*` and `?` can be used as wildcards. Example: "LoginNode": "juwels*.fz-juelich.de" |
| systems._name_.pyunicore.job_descriptions.unicore_keywords | Dict | Different Keywords, which are expected by UNICORE. More information [here](https://sourceforge.net/p/unicore/wiki/Job_Description/) |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.type_key | String | Define Job type. Default: Job type |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.imports_key | String | Define keyword for Import. Default: Imports |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.imports_from_value | String | Define From value for imports. Default: inline://dummy |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.environment_key | String | Default: Environment |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.skip_environments | List of Strings | Env variables not passed through to job. Default: ["JUPYTERHUB_API_TOKEN", "JPY_API_TOKEN"] |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.interactive | Dict | Define keywords for interactive jobs. |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.interactive.node_key | String | Default: Login Node |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.interactive.type_value | String | Default: interactive |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.normal | String | Define keywords for normal jobs. |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.normal.type_value | String | Default: normal |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.normal.resources_key | String | Default: Resources |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.normal.queue_key | String | Default: Queue |
| systems._name_.pyunicore.job_descriptions.unicore_keywords.normal.set_queue | Boolean | Whether to set the queue in the job description or not. Default: True |
| --- | --- | --- |
| error_messages | Dict | Used to specify error messages, which will inform the user |
