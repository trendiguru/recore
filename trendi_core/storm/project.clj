TODO
{
    "serializer": "json",
    "topology_specs": "topologies/",
    "virtualenv_specs": "virtualenvs/",
    "envs": {
        "prod": {
            "user": "storm",
            "nimbus": "storm1.my-cluster.com",
            "workers": [
                "storm1.my-cluster.com",
                "storm2.my-cluster.com",
                "storm3.my-cluster.com"
            ],
            "log": {
                "path": "/var/log/storm/streamparse",
                "file": "pystorm_{topology_name}_{component_name}_{task_id}_{pid}.log",
                "max_bytes": 100000,
                "backup_count": 10,
                "level": "info"
            },
            "use_ssh_for_nimbus": true,
            "virtualenv_root": "/data/virtualenvs/"
        }
    }
}
