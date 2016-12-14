# Grafana class params
class grafana::params {
  $db_pass = ''
  $db_host = ''
  $version = '3.1.1-1470047149'
  $plugins = ['grafana-piechart-panel', 'jdbranham-diagram-panel', 'mtanda-heatmap-epoch-panel']

}
