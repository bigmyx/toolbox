# Grafana Init class
class grafana (
    $db_pass = $::grafana::params::db_pass,
    $db_host = $::grafana::params::db_host,
    $version = $::grafana::params::version,
    $plugins = $::grafana::params::plugins,
  ) inherits grafana::params {

  anchor { 'grafana::begin': } ->
  class { '::grafana::install': } ->
  class { '::grafana::config': } ~>
  class { '::grafana::service': } ->
  anchor { 'grafana::end': }

}
