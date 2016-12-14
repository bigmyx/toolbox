include_recipe 'java'

tomcat_user  = 'tomcat'
tomcat_group = 'tomcat'

tomcat_install 'guacamole' do
  tomcat_user    tomcat_user
  tomcat_group   tomcat_group
  exclude_manager true
end

remote_file '/opt/tomcat_guacamole/webapps/guacamole.war' do
  owner  tomcat_group
  group  tomcat_group
  mode   '0644'
  source "http://downloads.sourceforge.net/project/guacamole/current/binary/guacamole-#{node['guacamole']['version']}.war"
  action :create_if_missing
end

tomcat_service 'guacamole' do
  action [:start, :enable]
  env_vars [{ 'GUACAMOLE_HOME' => '/etc/guacamole', 'CATALINA_PID' => '$CATALINA_BASE/bin/tomcat.pid' }]
  tomcat_user tomcat_user
  tomcat_group tomcat_user
end
