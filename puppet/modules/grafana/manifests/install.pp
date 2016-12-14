# Installs Grafana package
class grafana::install inherits grafana {

  package { 'grafana':
    ensure => $version
  }

}
