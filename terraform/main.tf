terraform {
  required_version = ">= 1.5.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.35.0"
    }
  }
}

provider "oci" {
  region = var.region
}

resource "oci_core_vcn" "rag" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "${var.project_name}-vcn"
  dns_label      = var.vcn_dns_label
}

resource "oci_core_nat_gateway" "rag" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.rag.id
  display_name   = "${var.project_name}-nat"
}

data "oci_core_services" "all" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

resource "oci_core_service_gateway" "rag" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.rag.id
  display_name   = "${var.project_name}-sgw"

  services {
    service_id = data.oci_core_services.all.services[0].id
  }
}

resource "oci_core_security_list" "functions" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.rag.id
  display_name   = "${var.project_name}-functions-sl"

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_route_table" "functions" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.rag.id
  display_name   = "${var.project_name}-functions-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.rag.id
  }

  route_rules {
    destination       = data.oci_core_services.all.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.rag.id
  }
}

resource "oci_core_subnet" "functions" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.rag.id
  cidr_block                 = var.functions_subnet_cidr
  display_name               = "${var.project_name}-functions-subnet"
  dns_label                  = var.functions_subnet_dns_label
  prohibit_public_ip_on_vnic = true
  route_table_id             = oci_core_route_table.functions.id
  security_list_ids          = [oci_core_security_list.functions.id]
}

resource "oci_functions_application" "rag" {
  compartment_id = var.compartment_ocid
  display_name   = "${var.project_name}-fn-app"
  subnet_ids     = [oci_core_subnet.functions.id]
}
