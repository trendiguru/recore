(ns image-processing-pipeline
    (:use [streamparse.specs]
    (:gen_class))

(defn pipeline-topology []

    (topology
        {"1" (spout-spec image-spout :p 2)}
        {"2" (bolt-spec {"1" : shuffle}

