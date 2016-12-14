define grafana::plugin {

  exec { "grafana-plugin-${title}":
    require => Package['grafana'],
    path => ['/usr/sbin', '/sbin', '/usr/bin', '/bin' ],
    creates => "/var/lib/grafana/plugins/${title}",
    command => "grafana-cli plugins install ${title}"
  }

}
