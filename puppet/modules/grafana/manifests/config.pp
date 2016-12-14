# Configures Grafana
class grafana::config {

  $plugins = $::grafana::plugins

  file{ '/etc/grafana/grafana.ini':
    ensure  => present,
    content => template( "${module_name}/grafana.ini.erb" ),
    mode    => '0640',
    owner   => 'root',
    group   => 'grafana',
  }

  # install grafana plugins defined
  ::grafana::plugin { $plugins: }

}
