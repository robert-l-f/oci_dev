terraform {
    required_providers {
        oci = {
            source = "oracle/oci"
            version = ">= 5.35.0"
        }
    }
}

provider "oci" {
    config_file_profile = "DEFAULT"
    region = "us-ashburn-1"
}

module "network" {
    source = "./modules/network"
    compartment_ocid = var.compartment_ocid
}