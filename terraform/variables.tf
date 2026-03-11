variable "region" {
  description = "OCI region to deploy into."
  type        = string
}

variable "compartment_ocid" {
  description = "Compartment OCID where resources are created."
  type        = string
}

variable "project_name" {
  description = "Prefix for resource names."
  type        = string
  default     = "rag-stack"
}

variable "vcn_cidr" {
  description = "CIDR for the RAG VCN."
  type        = string
  default     = "10.42.0.0/16"
}

variable "functions_subnet_cidr" {
  description = "Private subnet CIDR for OCI Functions."
  type        = string
  default     = "10.42.1.0/24"
}

variable "vcn_dns_label" {
  description = "DNS label for the VCN (1-15 chars, alphanumeric, starts with letter)."
  type        = string
  default     = "ragvcn"
}

variable "functions_subnet_dns_label" {
  description = "DNS label for the functions subnet."
  type        = string
  default     = "fnsubnet"
}
