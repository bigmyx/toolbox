# == Class terraform::params
#
# This class is meant to be called from terraform.
# It sets variables according to platform.
#
class terraform::params {
  $terraform_version = '0.7.13'
  $terraform_prefix = '/usr/local/bin'
}
