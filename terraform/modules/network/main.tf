resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "QuipDashboardVCN"
  dns_label      = "quipdashvcn"
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_IGW"
}

resource "oci_core_nat_gateway" "natgw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_NATGW"
}

resource "oci_core_service_gateway" "sgw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_SGW"

  services {
    service_id = data.oci_core_services.all_services.services[0].id
  }
}

data "oci_core_services" "all_services" {
  filter {
    name   = "name"
    values = ["All IAD Services In Oracle Services Network"]
    regex = true
  }
}

resource "oci_core_subnet" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  cidr_block     = var.public_subnet_cidr
  display_name   = "QuipDashboard_PublicSubnet"
  dns_label      = "public"
  prohibit_public_ip_on_vnic = false
  route_table_id = oci_core_route_table.public_rt.id
  security_list_ids = [oci_core_security_list.public_sl.id]
}

resource "oci_core_subnet" "private" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  cidr_block     = var.private_subnet_cidr
  display_name   = "QuipDashboard_PrivateSubnet"
  dns_label      = "private"
  prohibit_public_ip_on_vnic = true
  route_table_id    = oci_core_route_table.private_rt.id
  security_list_ids = [oci_core_security_list.private_sl.id]
}

# Public Security List (allow inbound 80/443 and outbound all)
resource "oci_core_security_list" "public_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_PublicSL"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6"  # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol = "6"  # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }
}

# Private Security List (no inbound, allow outbound all)
resource "oci_core_security_list" "private_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_PrivateSL"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }
}

# Public Route Table (routes to IGW)
resource "oci_core_route_table" "public_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_PublicRT"

  route_rules {
    cidr_block = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

# Private Route Table (routes to NAT + SGW)
resource "oci_core_route_table" "private_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "QuipDashboard_PrivateRT"

  route_rules {
    cidr_block = "0.0.0.0/0"
    network_entity_id = oci_core_nat_gateway.natgw.id
  }

  route_rules {
    destination_type = "SERVICE_CIDR_BLOCK"
    destination      = data.oci_core_services.all_services.services[0].cidr_block
    network_entity_id = oci_core_service_gateway.sgw.id
  }
}
