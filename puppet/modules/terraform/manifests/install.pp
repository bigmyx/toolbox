# == Class terraform::install
#
# This class is called from terraform for install.
#
class terraform::install inherits ::terraform::params {
  exec{'download-tf':
    cwd     => $::terraform::prefix,
    command => "/usr/bin/curl -s https://releases.hashicorp.com/terraform/${::terraform::version}/terraform_${::terraform::version}_linux_amd64.zip | zcat > terraform && chmod 755 terraform",
    unless  => "/usr/bin/test -f ${::terraform::prefix}/terraform && /usr/bin/test `${::terraform::prefix}/terraform -v | tr -d 'Terraform v'` == ${::terraform::version}"
  }

  # This shoould be present in internal APT repo
  package{'terraform-provider-ami':
    ensure => $::terraform::version
  }
}
