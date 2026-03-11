output "functions_application_id" {
  description = "OCI Functions application OCID to use with fn deploy --app."
  value       = oci_functions_application.rag.id
}

output "functions_application_name" {
  description = "OCI Functions application display name."
  value       = oci_functions_application.rag.display_name
}

output "functions_subnet_id" {
  description = "Private subnet OCID used by the OCI Functions application."
  value       = oci_core_subnet.functions.id
}

output "vcn_id" {
  description = "VCN OCID for the stack."
  value       = oci_core_vcn.rag.id
}
