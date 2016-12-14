# == Class: terraform
#
# Full description of class terraform here.
#
# === Parameters
#
# [*sample_parameter*]
#   Explanation of what this parameter affects and what it defaults to.
#
class terraform (
  $version = $::terraform::params::terraform_version,
  $prefix = $::terraform::params::terraform_prefix,
) inherits ::terraform::params {

  validate_string($version)
  validate_string($prefix)

  class { '::terraform::install': } ->
  Class['::terraform']
}
